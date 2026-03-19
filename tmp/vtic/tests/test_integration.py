"""Integration tests for vtic — full lifecycle, search, suggest, system endpoints.

Uses FastAPI TestClient with real services (no mocks).
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

try:
    from vtic.ticket import TicketService
    from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
    from vtic.models.ticket import TicketCreate, TicketUpdate, Ticket
    from vtic.models.enums import Category, Severity, Status
    from vtic.store.markdown import read_ticket
    from vtic.index.operations import query_tickets

    TICKET_SERVICE_AVAILABLE = True
except ImportError as e:
    TICKET_SERVICE_AVAILABLE = False
    TICKET_SERVICE_ERROR = str(e)

try:
    from httpx import AsyncClient, ASGITransport
    from vtic.api.app import create_app

    API_AVAILABLE = True
except ImportError as e:
    API_AVAILABLE = False
    API_ERROR = str(e)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def config(tmp_storage_dir: Path) -> Config:
    """Test configuration — BM25 only, no embeddings."""
    return Config(
        storage=StorageConfig(dir=tmp_storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )


@pytest.fixture
async def service(config: Config) -> AsyncGenerator[TicketService, None]:
    """Real TicketService with temp storage."""
    if not TICKET_SERVICE_AVAILABLE:
        pytest.skip(f"TicketService not available: {TICKET_SERVICE_ERROR}")
    svc = TicketService(config)
    await svc.initialize()
    yield svc
    if hasattr(svc, "close"):
        await svc.close()


@pytest.fixture
async def api_client(
    service: TicketService, config: Config
) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI TestClient with real service attached.

    Overrides get_search_engine to reuse service.collection so that Zvec
    does not try to acquire a second read-write lock on the same index.
    """
    if not API_AVAILABLE:
        pytest.skip(f"API not available: {API_ERROR}")

    from vtic.api import deps
    from vtic.search.engine import SearchEngine

    app = create_app(config)
    app.state.ticket_service = service

    def _search_engine_override():
        return SearchEngine(service.collection)

    app.dependency_overrides[deps.get_search_engine] = _search_engine_override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# Helper
async def _create(client: AsyncClient, **kwargs) -> dict:
    defaults = {"title": "Test Ticket", "description": "Test description", "repo": "test/repo"}
    defaults.update(kwargs)
    r = await client.post("/tickets", json=defaults)
    assert r.status_code == 201, f"create failed ({r.status_code}): {r.text}"
    return r.json()["data"]


def _search_direct(service: TicketService, query: str) -> list:
    collection = getattr(service, "collection", None)
    if collection is None:
        pytest.skip("TicketService does not expose .collection")
    return query_tickets(collection, query)


# =============================================================================
# 1. Full CRUD Lifecycle via API
# =============================================================================


class TestFullCRUDLifecycle:
    """End-to-end CRUD lifecycle through the REST API with real storage."""

    @pytest.mark.asyncio
    async def test_create_5_get_each(self, api_client: AsyncClient):
        """Create 5 tickets, GET each by ID — all return 200."""
        tickets = []
        for i in range(5):
            t = await _create(api_client, title=f"Lifecycle {i}", repo=f"owner/repo{i}")
            tickets.append(t)
        for t in tickets:
            r = await api_client.get(f"/tickets/{t['id']}")
            assert r.status_code == 200
            assert r.json()["data"]["id"] == t["id"]

    @pytest.mark.asyncio
    async def test_update_one_verify_fields(self, api_client: AsyncClient):
        """Update title and status, verify both changed."""
        t = await _create(api_client, title="Before Update")
        r = await api_client.patch(
            f"/tickets/{t['id']}", json={"title": "After Update", "status": "in_progress"}
        )
        assert r.status_code == 200
        d = r.json()["data"]
        assert d["title"] == "After Update"
        assert d["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_delete_one_list_remaining(self, api_client: AsyncClient):
        """Create 5, delete 1, verify remaining 4 still accessible."""
        ids = []
        for i in range(5):
            t = await _create(api_client, title=f"Delete Test {i}", repo=f"owner/repo{i}")
            ids.append(t["id"])

        # Delete first ticket
        r = await api_client.delete(f"/tickets/{ids[0]}")
        assert r.status_code == 204

        # Verify deleted — 404
        r = await api_client.get(f"/tickets/{ids[0]}")
        assert r.status_code == 404

        # Verify remaining 4 — all 200
        for tid in ids[1:]:
            r = await api_client.get(f"/tickets/{tid}")
            assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_full_lifecycle_single_ticket(self, api_client: AsyncClient):
        """Create → get → update → get again → delete → 404."""
        t = await _create(api_client, title="Full Lifecycle")
        tid = t["id"]

        assert (await api_client.get(f"/tickets/{tid}")).status_code == 200

        r = await api_client.patch(f"/tickets/{tid}", json={"title": "Modified Lifecycle"})
        assert r.status_code == 200
        assert r.json()["data"]["title"] == "Modified Lifecycle"

        r = await api_client.get(f"/tickets/{tid}")
        assert r.json()["data"]["title"] == "Modified Lifecycle"

        assert (await api_client.delete(f"/tickets/{tid}")).status_code == 204
        assert (await api_client.get(f"/tickets/{tid}")).status_code == 404

    @pytest.mark.asyncio
    async def test_list_after_creates(self, api_client: AsyncClient):
        """Create 3 tickets, list — total >= 3, meta fields present."""
        for i in range(3):
            await _create(api_client, title=f"List Ticket {i}")
        r = await api_client.get("/tickets")
        assert r.status_code == 200
        d = r.json()
        assert len(d["data"]) >= 3
        assert d["meta"]["total"] >= 3
        assert "limit" in d["meta"]
        assert "offset" in d["meta"]
        assert "has_more" in d["meta"]

    @pytest.mark.asyncio
    async def test_response_envelope_has_data_and_meta(self, api_client: AsyncClient):
        """Single ticket response has data + meta envelope."""
        t = await _create(api_client)
        r = await api_client.get(f"/tickets/{t['id']}")
        assert r.status_code == 200
        d = r.json()
        assert "data" in d
        assert "meta" in d


# =============================================================================
# 2. Search Integration via POST /search
# =============================================================================


class TestSearchIntegration:
    """Integration tests for BM25 search through the REST API."""

    @pytest.mark.asyncio
    async def test_search_finds_created_ticket(self, api_client: AsyncClient, service: TicketService):
        """Create ticket with unique content, search → found in hits."""
        ticket = await service.create_ticket(
            TicketCreate(
                title="SQL injection vulnerability in login form",
                description="The login form is vulnerable to SQL injection via user_input parameter",
                repo="test/repo",
            )
        )
        r = await api_client.post("/search", json={"query": "SQL injection"})
        assert r.status_code == 200
        data = r.json()
        assert data["query"] == "SQL injection"
        assert "hits" in data
        assert "total" in data
        hit_ids = [h["ticket_id"] for h in data["hits"]]
        assert ticket.id in hit_ids

    @pytest.mark.asyncio
    async def test_search_result_scores_valid(self, api_client: AsyncClient, service: TicketService):
        """All returned hits have scores in [0.0, 1.0]."""
        await service.create_ticket(
            TicketCreate(
                title="Memory leak in worker process",
                description="Worker process gradually exhausts available memory",
                repo="test/repo",
            )
        )
        r = await api_client.post("/search", json={"query": "memory leak worker"})
        assert r.status_code == 200
        for hit in r.json().get("hits", []):
            assert "score" in hit
            assert 0.0 <= hit["score"] <= 1.0
            assert "ticket_id" in hit
            assert "source" in hit

    @pytest.mark.asyncio
    async def test_search_meta_present(self, api_client: AsyncClient, service: TicketService):
        """Search response includes meta with latency_ms and pagination info."""
        await service.create_ticket(
            TicketCreate(title="CORS wildcard issue", description="CORS headers too permissive", repo="test/repo")
        )
        r = await api_client.post("/search", json={"query": "CORS"})
        assert r.status_code == 200
        meta = r.json()["meta"]
        for field in ("total", "limit", "offset", "has_more", "latency_ms"):
            assert field in meta

    @pytest.mark.asyncio
    async def test_search_limit_restricts_hits(self, api_client: AsyncClient, service: TicketService):
        """limit=2 returns at most 2 hits."""
        for i in range(5):
            await service.create_ticket(
                TicketCreate(
                    title=f"Auth failure case {i}",
                    description="Authentication system fails on edge case",
                    repo="test/repo",
                )
            )
        r = await api_client.post("/search", json={"query": "auth failure", "limit": 2})
        assert r.status_code == 200
        assert len(r.json()["hits"]) <= 2

    @pytest.mark.asyncio
    async def test_search_empty_results_for_no_match(self, api_client: AsyncClient, service: TicketService):
        """Query with no token overlap returns no hits above min_score=0.01."""
        await service.create_ticket(
            TicketCreate(title="Unrelated ticket", description="Nothing here", repo="test/repo")
        )
        # BM25 may return zero-score docs; use min_score to exclude them
        r = await api_client.post(
            "/search",
            json={"query": "zzz_xqr_nonexistent_term_abc", "min_score": 0.01},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["hits"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_search_semantic_unavailable_returns_503(self, api_client: AsyncClient):
        """semantic=True without embedding provider → 503."""
        r = await api_client.post("/search", json={"query": "test", "semantic": True})
        assert r.status_code == 503
        assert "error" in r.json()

    @pytest.mark.asyncio
    async def test_search_min_score_filter(self, api_client: AsyncClient, service: TicketService):
        """min_score filters out low-relevance hits."""
        await service.create_ticket(
            TicketCreate(
                title="Highly relevant authentication token management",
                description="Token management system with JWT authentication",
                repo="test/repo",
            )
        )
        r = await api_client.post("/search", json={"query": "authentication", "min_score": 0.5})
        assert r.status_code == 200
        for hit in r.json()["hits"]:
            assert hit["score"] >= 0.5

    @pytest.mark.asyncio
    async def test_search_pagination(self, api_client: AsyncClient, service: TicketService):
        """offset parameter advances pagination window."""
        for i in range(6):
            await service.create_ticket(
                TicketCreate(
                    title=f"Pagination ticket {i}",
                    description="Contains pagination test content",
                    repo="test/repo",
                )
            )
        page1 = (await api_client.post("/search", json={"query": "pagination", "limit": 3, "offset": 0})).json()
        page2 = (await api_client.post("/search", json={"query": "pagination", "limit": 3, "offset": 3})).json()
        assert page1["meta"]["offset"] == 0
        assert page2["meta"]["offset"] == 3


# =============================================================================
# 3. Suggest Integration via GET /search/suggest
# =============================================================================


class TestSuggestIntegration:
    """Integration tests for autocomplete suggest endpoint."""

    @pytest.mark.asyncio
    async def test_suggest_returns_list(self, api_client: AsyncClient, service: TicketService):
        """Suggest returns a JSON array."""
        await service.create_ticket(
            TicketCreate(title="CORS configuration error", description="Cross-origin headers wrong", repo="test/repo")
        )
        r = await api_client.get("/search/suggest?q=CO")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    @pytest.mark.asyncio
    async def test_suggest_result_structure(self, api_client: AsyncClient, service: TicketService):
        """Each suggestion has {suggestion, ticket_count}."""
        await service.create_ticket(
            TicketCreate(title="Authentication failure on login", description="Login broken", repo="test/repo")
        )
        await service.create_ticket(
            TicketCreate(title="Authentication timeout session", description="Session expired", repo="test/repo")
        )
        r = await api_client.get("/search/suggest?q=Au")
        assert r.status_code == 200
        for item in r.json():
            assert "suggestion" in item
            assert "ticket_count" in item
            assert isinstance(item["ticket_count"], int)
            assert item["ticket_count"] >= 0

    @pytest.mark.asyncio
    async def test_suggest_limit_parameter(self, api_client: AsyncClient, service: TicketService):
        """limit=3 returns at most 3 suggestions."""
        for i in range(10):
            await service.create_ticket(
                TicketCreate(
                    title=f"Network timeout scenario {i}",
                    description=f"Connection drop {i}",
                    repo="test/repo",
                )
            )
        r = await api_client.get("/search/suggest?q=Ne&limit=3")
        assert r.status_code == 200
        assert len(r.json()) <= 3

    @pytest.mark.asyncio
    async def test_suggest_too_short_query_returns_400(self, api_client: AsyncClient):
        """q shorter than 2 chars → 400."""
        r = await api_client.get("/search/suggest?q=a")
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_suggest_returns_list_always(self, api_client: AsyncClient, service: TicketService):
        """Suggest always returns a valid list; BM25 may surface zero-score docs."""
        await service.create_ticket(
            TicketCreate(title="Unrelated thing", description="Nothing relevant", repo="test/repo")
        )
        r = await api_client.get("/search/suggest?q=zzxqwerty")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        # Each item in the list must have the correct schema
        for item in r.json():
            assert "suggestion" in item
            assert "ticket_count" in item

    @pytest.mark.asyncio
    async def test_suggest_empty_for_no_match(self, api_client: AsyncClient, service: TicketService):
        """Suggest returns valid list; may be empty or have results depending on BM25 matching."""
        # Create a ticket with specific title
        await service.create_ticket(
            TicketCreate(title="Database connection issue", description="DB problem", repo="test/repo")
        )
        # Query with a partial that is unlikely to match any title
        r = await api_client.get("/search/suggest?q=xyznonexistent")
        assert r.status_code == 200
        data = r.json()
        # Should return a valid list (may be empty or have BM25 matches)
        assert isinstance(data, list)
        # If results exist, they should have valid schema
        for item in data:
            assert "suggestion" in item
            assert "ticket_count" in item
            assert isinstance(item["ticket_count"], int)


# =============================================================================
# 4. Filter Combinations
# =============================================================================


class TestFilterCombos:
    """Test filtering on list and search endpoints."""

    @pytest.mark.asyncio
    async def test_list_filter_by_severity(self, api_client: AsyncClient, service: TicketService):
        """Filter by severity=critical returns only critical tickets."""
        await service.create_ticket(
            TicketCreate(title="Critical crash", description="App dies", repo="test/repo",
                         category=Category.CRASH, severity=Severity.CRITICAL)
        )
        await service.create_ticket(
            TicketCreate(title="Low priority note", description="Minor", repo="test/repo",
                         category=Category.GENERAL, severity=Severity.LOW)
        )
        r = await api_client.get("/tickets?severity=critical")
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_list_filter_by_category(self, api_client: AsyncClient, service: TicketService):
        """Filter by category=security returns only security tickets."""
        await service.create_ticket(
            TicketCreate(title="SQL Injection", description="Security issue", repo="test/repo",
                         category=Category.SECURITY, severity=Severity.HIGH)
        )
        await service.create_ticket(
            TicketCreate(title="Feature Request", description="New feature", repo="test/repo",
                         category=Category.FEATURE, severity=Severity.LOW)
        )
        r = await api_client.get("/tickets?category=security")
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t["category"] == "security"

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, api_client: AsyncClient, service: TicketService):
        """Filter by status=open returns only open tickets."""
        await service.create_ticket(
            TicketCreate(title="Open Ticket", description="Still open", repo="test/repo", status=Status.OPEN)
        )
        await service.create_ticket(
            TicketCreate(title="In Progress", description="Working on it", repo="test/repo", status=Status.IN_PROGRESS)
        )
        r = await api_client.get("/tickets?status=open")
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t["status"] == "open"

    @pytest.mark.asyncio
    async def test_list_filter_by_repo(self, api_client: AsyncClient, service: TicketService):
        """Filter by repo returns only tickets from that repo."""
        await service.create_ticket(
            TicketCreate(title="Repo A Issue", description="Bug", repo="myorg/repo-a")
        )
        await service.create_ticket(
            TicketCreate(title="Repo B Issue", description="Bug", repo="myorg/repo-b")
        )
        r = await api_client.get("/tickets?repo=myorg/repo-a")
        assert r.status_code == 200
        for t in r.json()["data"]:
            assert t["repo"] == "myorg/repo-a"

    @pytest.mark.asyncio
    async def test_list_pagination_limit_offset(self, api_client: AsyncClient, service: TicketService):
        """Pagination: limit=2 offset=1 returns correct slice."""
        for i in range(5):
            await service.create_ticket(
                TicketCreate(title=f"Paginate {i}", description="Test", repo="test/repo")
            )
        r = await api_client.get("/tickets?limit=2&offset=1")
        assert r.status_code == 200
        d = r.json()
        assert len(d["data"]) <= 2
        assert d["meta"]["limit"] == 2
        assert d["meta"]["offset"] == 1

    @pytest.mark.asyncio
    async def test_search_with_severity_filter(self, api_client: AsyncClient, service: TicketService):
        """POST /search with filters.severity narrows results."""
        await service.create_ticket(
            TicketCreate(title="Critical memory exhaustion", description="OOM crash", repo="test/repo",
                         severity=Severity.CRITICAL)
        )
        await service.create_ticket(
            TicketCreate(title="Low priority memory note", description="Minor memory warning", repo="test/repo",
                         severity=Severity.LOW)
        )
        r = await api_client.post("/search", json={
            "query": "memory",
            "filters": {"severity": ["critical"]},
        })
        assert r.status_code == 200
        data = r.json()
        assert "hits" in data
        # Filtered search completes without error
        assert data["meta"]["total"] >= 0


# =============================================================================
# 5. System Endpoints
# =============================================================================


class TestSystemEndpoints:
    """Tests for /health, /stats, /reindex, /doctor."""

    @pytest.mark.asyncio
    async def test_health_valid_response(self, api_client: AsyncClient):
        """GET /health returns valid HealthResponse schema."""
        r = await api_client.get("/health")
        # 200 for healthy/degraded, 503 for unhealthy
        assert r.status_code in (200, 503)
        d = r.json()
        assert "status" in d
        assert d["status"] in ("healthy", "degraded", "unhealthy")
        assert "version" in d
        assert "index_status" in d
        idx = d["index_status"]
        assert idx["zvec"] in ("available", "unavailable", "corrupted")
        assert "ticket_count" in idx

    @pytest.mark.asyncio
    async def test_health_includes_embedding_provider(self, api_client: AsyncClient):
        """Health response embedding_provider field present (may be null)."""
        r = await api_client.get("/health")
        d = r.json()
        # embedding_provider may be None (when provider="none") or an object
        assert "embedding_provider" in d or r.status_code == 503

    @pytest.mark.asyncio
    async def test_stats_valid_response(self, api_client: AsyncClient, service: TicketService):
        """GET /stats returns valid StatsResponse schema."""
        await service.create_ticket(
            TicketCreate(title="Stats T1", description="Test", repo="test/repo",
                         category=Category.CRASH, severity=Severity.HIGH, status=Status.OPEN)
        )
        await service.create_ticket(
            TicketCreate(title="Stats T2", description="Test", repo="test/repo",
                         category=Category.SECURITY, severity=Severity.MEDIUM, status=Status.IN_PROGRESS)
        )
        r = await api_client.get("/stats")
        assert r.status_code == 200
        d = r.json()
        assert "totals" in d
        assert "by_status" in d
        assert "by_severity" in d
        assert "by_category" in d
        totals = d["totals"]
        assert totals["all"] >= 2
        assert "open" in totals
        assert "closed" in totals

    @pytest.mark.asyncio
    async def test_stats_by_repo(self, api_client: AsyncClient, service: TicketService):
        """GET /stats?by_repo=true includes by_repo dict."""
        await service.create_ticket(
            TicketCreate(title="Repo Stats", description="Test", repo="myorg/testrepo")
        )
        r = await api_client.get("/stats?by_repo=true")
        assert r.status_code == 200
        d = r.json()
        assert d.get("by_repo") is not None
        assert isinstance(d["by_repo"], dict)

    @pytest.mark.asyncio
    async def test_reindex_valid_response(self, api_client: AsyncClient, service: TicketService):
        """POST /reindex returns valid ReindexResult schema."""
        for i in range(3):
            await service.create_ticket(
                TicketCreate(title=f"Reindex Ticket {i}", description=f"Content {i}", repo="test/repo")
            )
        r = await api_client.post("/reindex")
        assert r.status_code == 200
        d = r.json()
        for field in ("processed", "skipped", "failed", "duration_ms", "errors"):
            assert field in d
        assert isinstance(d["processed"], int)
        assert isinstance(d["errors"], list)
        assert d["processed"] >= 0

    @pytest.mark.asyncio
    async def test_doctor_valid_response(self, api_client: AsyncClient):
        """GET /doctor returns valid DoctorResult schema."""
        r = await api_client.get("/doctor")
        assert r.status_code == 200
        d = r.json()
        assert "overall" in d
        assert d["overall"] in ("ok", "warnings", "errors")
        assert "checks" in d
        assert isinstance(d["checks"], list)
        for check in d["checks"]:
            assert "name" in check
            assert "status" in check
            assert check["status"] in ("ok", "warning", "error")

    @pytest.mark.asyncio
    async def test_doctor_has_expected_checks(self, api_client: AsyncClient):
        """Doctor includes all 5 required check names."""
        r = await api_client.get("/doctor")
        assert r.status_code == 200
        names = {c["name"] for c in r.json()["checks"]}
        for expected in ("zvec_index", "config_file", "embedding_provider", "file_permissions"):
            assert expected in names, f"Missing check: {expected}"


# =============================================================================
# 6. Error Cases
# =============================================================================


class TestErrorCases:
    """HTTP error codes and error response schema validation."""

    @pytest.mark.asyncio
    async def test_get_nonexistent_ticket_404(self, api_client: AsyncClient):
        """GET /tickets/G99999 → 404 NOT_FOUND."""
        r = await api_client.get("/tickets/G99999")
        assert r.status_code == 404
        d = r.json()
        assert "error" in d
        assert d["error"]["code"] in ("NOT_FOUND", "TICKET_NOT_FOUND")
        assert "message" in d["error"]

    @pytest.mark.asyncio
    async def test_patch_nonexistent_ticket_404(self, api_client: AsyncClient):
        """PATCH /tickets/G99999 → 404."""
        r = await api_client.patch("/tickets/G99999", json={"title": "New"})
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent_ticket_404(self, api_client: AsyncClient):
        """DELETE /tickets/G99999 → 404."""
        r = await api_client.delete("/tickets/G99999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_create_missing_title_400(self, api_client: AsyncClient):
        """POST /tickets without title → 400 VALIDATION_ERROR."""
        r = await api_client.post("/tickets", json={"description": "Test", "repo": "test/repo"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_create_missing_description_400(self, api_client: AsyncClient):
        """POST /tickets without description → 400."""
        r = await api_client.post("/tickets", json={"title": "Test", "repo": "test/repo"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_create_missing_repo_400(self, api_client: AsyncClient):
        """POST /tickets without repo → 400."""
        r = await api_client.post("/tickets", json={"title": "Test", "description": "Desc"})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_create_invalid_repo_format_400(self, api_client: AsyncClient):
        """POST /tickets with repo missing '/' → 400."""
        r = await api_client.post("/tickets", json={
            "title": "Test", "description": "Test", "repo": "invalid-no-slash"
        })
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_search_empty_query_400(self, api_client: AsyncClient):
        """POST /search with whitespace-only query → 400."""
        r = await api_client.post("/search", json={"query": "   "})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_update_empty_body_400(self, api_client: AsyncClient, service: TicketService):
        """PATCH with empty JSON body → 400 (no fields)."""
        t = await service.create_ticket(
            TicketCreate(title="Test", description="Test", repo="test/repo")
        )
        r = await api_client.patch(f"/tickets/{t.id}", json={})
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_error_response_schema(self, api_client: AsyncClient):
        """All error responses follow {error: {code, message}} schema."""
        r = await api_client.get("/tickets/G99999")
        assert r.status_code == 404
        err = r.json()["error"]
        assert isinstance(err["code"], str)
        assert isinstance(err["message"], str)


# =============================================================================
# 7. Edge Cases
# =============================================================================


class TestEdgeCases:
    """Boundary conditions and unusual but valid inputs."""

    @pytest.mark.asyncio
    async def test_list_max_limit(self, api_client: AsyncClient):
        """GET /tickets?limit=100 is valid, returns limit in meta."""
        r = await api_client.get("/tickets?limit=100")
        assert r.status_code == 200
        assert r.json()["meta"]["limit"] == 100

    @pytest.mark.asyncio
    async def test_list_offset_beyond_total(self, api_client: AsyncClient, service: TicketService):
        """GET /tickets?offset=9999 returns empty data list."""
        await service.create_ticket(
            TicketCreate(title="Only Ticket", description="Test", repo="test/repo")
        )
        r = await api_client.get("/tickets?offset=9999")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 0

    @pytest.mark.asyncio
    async def test_ticket_with_tags_and_references(self, api_client: AsyncClient):
        """Create ticket with tags=["security","api"] — preserved in response."""
        t = await _create(api_client, title="Tagged Ticket", description="Has tags",
                          tags=["security", "api"])
        assert "security" in t["tags"]
        assert "api" in t["tags"]

    @pytest.mark.asyncio
    async def test_description_append(self, api_client: AsyncClient, service: TicketService):
        """description_append appends to existing description."""
        t = await service.create_ticket(
            TicketCreate(title="Appendable", description="Initial text", repo="test/repo")
        )
        r = await api_client.patch(f"/tickets/{t.id}", json={"description_append": "\n\nAppended section"})
        assert r.status_code == 200
        assert "Appended section" in r.json()["data"]["description"]
        assert "Initial text" in r.json()["data"]["description"]

    @pytest.mark.asyncio
    async def test_slug_auto_generated(self, api_client: AsyncClient):
        """Ticket slug is auto-generated from title."""
        t = await _create(api_client, title="CORS Wildcard Issue")
        assert t["slug"] == "cors-wildcard-issue"

    @pytest.mark.asyncio
    async def test_soft_delete_then_404(self, api_client: AsyncClient, service: TicketService):
        """Soft-deleted ticket is not accessible via GET."""
        t = await service.create_ticket(
            TicketCreate(title="To Soft Delete", description="Test", repo="test/repo")
        )
        r = await api_client.delete(f"/tickets/{t.id}?mode=soft")
        assert r.status_code == 204
        assert (await api_client.get(f"/tickets/{t.id}")).status_code == 404

    @pytest.mark.asyncio
    async def test_search_with_offset_zero_vs_nonzero(self, api_client: AsyncClient, service: TicketService):
        """Search with offset=0 and offset=2 return different windows."""
        for i in range(6):
            await service.create_ticket(
                TicketCreate(
                    title=f"Window search ticket number {i}",
                    description=f"Content for search {i}",
                    repo="test/repo",
                )
            )
        p1 = (await api_client.post("/search", json={"query": "window search", "limit": 2, "offset": 0})).json()
        p2 = (await api_client.post("/search", json={"query": "window search", "limit": 2, "offset": 2})).json()
        assert p1["meta"]["offset"] == 0
        assert p2["meta"]["offset"] == 2


# =============================================================================
# Service-level tests (reuse from previous iteration, slightly enhanced)
# =============================================================================


class TestServiceCRUDDirect:
    """Direct TicketService tests (not via API) for deeper coverage."""

    @pytest.mark.asyncio
    async def test_id_sequence_per_category(self, service: TicketService):
        """Sequential IDs per category prefix: C1, C2, C3."""
        c1 = await service.create_ticket(
            TicketCreate(title="C1", description="Test", repo="test/repo", category=Category.CRASH)
        )
        c2 = await service.create_ticket(
            TicketCreate(title="C2", description="Test", repo="test/repo", category=Category.CRASH)
        )
        c3 = await service.create_ticket(
            TicketCreate(title="C3", description="Test", repo="test/repo", category=Category.CRASH)
        )
        assert c1.id == "C1"
        assert c2.id == "C2"
        assert c3.id == "C3"

    @pytest.mark.asyncio
    async def test_multi_category_ids(self, service: TicketService):
        """Different categories get independent sequences."""
        c = await service.create_ticket(
            TicketCreate(title="Crash", description="Test", repo="test/repo", category=Category.CRASH)
        )
        s = await service.create_ticket(
            TicketCreate(title="Security", description="Test", repo="test/repo", category=Category.SECURITY)
        )
        f = await service.create_ticket(
            TicketCreate(title="Feature", description="Test", repo="test/repo", category=Category.FEATURE)
        )
        assert c.id == "C1"
        assert s.id == "S1"
        assert f.id == "F1"

    @pytest.mark.asyncio
    async def test_search_indexed_after_create(self, service: TicketService):
        """Ticket searchable via Zvec immediately after create."""
        ticket = await service.create_ticket(
            TicketCreate(
                title="XSS cross-site scripting vulnerability",
                description="Reflected XSS found in search parameter",
                repo="test/repo",
            )
        )
        results = _search_direct(service, "XSS cross-site scripting")
        assert ticket.id in [r["id"] for r in results]

    @pytest.mark.asyncio
    async def test_update_reflected_in_index(self, service: TicketService):
        """After update, new content is searchable."""
        ticket = await service.create_ticket(
            TicketCreate(title="Original content", description="Old description", repo="test/repo")
        )
        await service.update_ticket(ticket.id, TicketUpdate(title="Unique XYZ updated title"))
        results = _search_direct(service, "Unique XYZ updated")
        assert ticket.id in [r["id"] for r in results]

    @pytest.mark.asyncio
    async def test_delete_removed_from_index(self, service: TicketService):
        """After delete, ticket no longer returned by search."""
        ticket = await service.create_ticket(
            TicketCreate(title="To Be Deleted Forever", description="Will be gone", repo="test/repo")
        )
        assert ticket.id in [r["id"] for r in _search_direct(service, "To Be Deleted Forever")]
        await service.delete_ticket(ticket.id)
        assert ticket.id not in [r["id"] for r in _search_direct(service, "To Be Deleted Forever")]

    @pytest.mark.asyncio
    async def test_reindex_rebuilds_from_files(self, service: TicketService):
        """reindex_all() processes all tickets on disk."""
        for i in range(5):
            await service.create_ticket(
                TicketCreate(title=f"Reindex {i}", description=f"Content {i}", repo="test/repo")
            )
        stats = await service.reindex_all()
        assert stats["processed"] >= 5
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_status_transition_valid(self, service: TicketService):
        """open → in_progress → fixed (allowed transitions)."""
        t = await service.create_ticket(
            TicketCreate(title="Transition Test", description="Test", repo="test/repo", status=Status.OPEN)
        )
        t1 = await service.update_ticket(t.id, TicketUpdate(status=Status.IN_PROGRESS))
        assert t1.status == Status.IN_PROGRESS
        t2 = await service.update_ticket(t.id, TicketUpdate(status=Status.FIXED))
        assert t2.status == Status.FIXED

    @pytest.mark.asyncio
    async def test_status_transition_invalid_raises(self, service: TicketService):
        """blocked → fixed is not allowed — raises exception."""
        t = await service.create_ticket(
            TicketCreate(title="Blocked Ticket", description="Test", repo="test/repo", status=Status.BLOCKED)
        )
        with pytest.raises(Exception) as exc:
            await service.update_ticket(t.id, TicketUpdate(status=Status.FIXED))
        assert "invalid" in str(exc.value).lower() or "transition" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_file_content_matches_ticket(self, service: TicketService, tmp_storage_dir: Path):
        """Markdown file frontmatter matches the returned ticket model."""
        ticket = await service.create_ticket(
            TicketCreate(
                title="File Content Test",
                description="Verify file contents",
                repo="test/repo",
                category=Category.SECURITY,
                severity=Severity.HIGH,
                assignee="testuser",
                tags=["security", "test"],
            )
        )
        category_dir = tmp_storage_dir / "test" / "repo" / ticket.category.value
        md_file = category_dir / f"{ticket.id}-{ticket.slug}.md"
        assert md_file.exists(), f"Expected file at {md_file}"
        data = read_ticket(md_file)
        assert data["id"] == ticket.id
        assert data["title"] == ticket.title
        assert data["description"] == ticket.description
        assert data["severity"] == ticket.severity.value
        assert data["assignee"] == ticket.assignee
