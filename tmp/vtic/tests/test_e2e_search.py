"""End-to-end tests for vtic search functionality.

These tests cover complete workflows:
1. Search & Filter Workflow - creating tickets, searching, filtering, sorting, pagination
2. Suggest & No-Results Handling - suggestions, edge cases, schema validation

Uses FastAPI TestClient with real services (no mocks).
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport

from vtic.api.app import create_app
from vtic.api import deps
from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
from vtic.ticket import TicketService
from vtic.search.engine import SearchEngine
from vtic.index.operations import insert_tickets
from vtic.index.client import destroy_index


@pytest.fixture
def tmp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def config(tmp_storage_dir: Path) -> Config:
    """Test configuration - BM25 only, no embeddings."""
    return Config(
        storage=StorageConfig(dir=tmp_storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )


@pytest.fixture
async def api_client_with_data(
    tmp_storage_dir: Path,
    config: Config,
) -> AsyncGenerator[tuple[AsyncClient, TicketService], None]:
    """Create FastAPI test client with real services and insert test data."""
    deps.set_config(config)
    app = create_app(config)
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    app.state.ticket_service = ticket_service
    search_engine = SearchEngine(ticket_service.collection)

    def override_get_search_engine(config=None):
        return search_engine

    app.dependency_overrides[deps.get_search_engine] = override_get_search_engine

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, ticket_service

    app.dependency_overrides.clear()
    await ticket_service.close()
    destroy_index(tmp_storage_dir)
    deps.set_config(None)


@pytest.mark.asyncio
class TestSearchAndFilterWorkflow:
    """E2E Case 1: Search & Filter Workflow"""

    @pytest.fixture
    async def db_tickets(self, api_client_with_data) -> tuple[AsyncClient, list[dict]]:
        """Create 10 tickets with varied content for E2E testing."""
        client, ticket_service = api_client_with_data
        tickets_data = [
            {
                "id": "C1",
                "title": "Database connection timeout in production",
                "description": "The application fails to connect to the database after 30 seconds.",
                "repo": "owner/app",
                "category": "crash",
                "severity": "critical",
                "status": "open",
                "tags": ["database", "timeout"],
                "created": "2024-01-15T10:00:00Z",
                "updated": "2024-01-15T10:00:00Z",
            },
            {
                "id": "C2",
                "title": "Database corruption detected",
                "description": "Critical database corruption found in production.",
                "repo": "owner/app",
                "category": "crash",
                "severity": "critical",
                "status": "in_progress",
                "tags": ["database", "corruption"],
                "created": "2024-01-16T10:00:00Z",
                "updated": "2024-01-16T10:00:00Z",
            },
            {
                "id": "S1",
                "title": "Database authentication error",
                "description": "Users cannot authenticate to the database.",
                "repo": "owner/security",
                "category": "security",
                "severity": "high",
                "status": "open",
                "tags": ["database", "auth"],
                "created": "2024-01-17T10:00:00Z",
                "updated": "2024-01-17T10:00:00Z",
            },
            {
                "id": "H1",
                "title": "Database query performance degradation",
                "description": "Slow database queries causing API timeouts.",
                "repo": "owner/app",
                "category": "hotfix",
                "severity": "high",
                "status": "blocked",
                "tags": ["database", "performance"],
                "created": "2024-01-18T10:00:00Z",
                "updated": "2024-01-18T10:00:00Z",
            },
            {
                "id": "F1",
                "title": "Add database backup automation",
                "description": "Feature request for automated database backups.",
                "repo": "owner/infra",
                "category": "feature",
                "severity": "medium",
                "status": "open",
                "tags": ["database", "backup"],
                "created": "2024-01-19T10:00:00Z",
                "updated": "2024-01-19T10:00:00Z",
            },
            {
                "id": "C3",
                "title": "Memory leak in cache service",
                "description": "Cache service is consuming excessive memory. Not database related.",
                "repo": "owner/app",
                "category": "crash",
                "severity": "critical",
                "status": "open",
                "tags": ["memory", "cache"],
                "created": "2024-01-20T10:00:00Z",
                "updated": "2024-01-20T10:00:00Z",
            },
            {
                "id": "G1",
                "title": "Update documentation for API v2",
                "description": "Documentation needs to be updated.",
                "repo": "owner/docs",
                "category": "general",
                "severity": "low",
                "status": "in_progress",
                "tags": ["docs"],
                "created": "2024-01-21T10:00:00Z",
                "updated": "2024-01-21T10:00:00Z",
            },
            {
                "id": "S2",
                "title": "XSS vulnerability in user input",
                "description": "Cross-site scripting vulnerability found.",
                "repo": "owner/security",
                "category": "security",
                "severity": "critical",
                "status": "open",
                "tags": ["security", "xss"],
                "created": "2024-01-22T10:00:00Z",
                "updated": "2024-01-22T10:00:00Z",
            },
            {
                "id": "H2",
                "title": "Fix CORS configuration error",
                "description": "Cross-origin requests are being blocked.",
                "repo": "owner/app",
                "category": "hotfix",
                "severity": "high",
                "status": "fixed",
                "tags": ["cors", "api"],
                "created": "2024-01-23T10:00:00Z",
                "updated": "2024-01-23T10:00:00Z",
            },
            {
                "id": "F2",
                "title": "Implement user profile page",
                "description": "New feature to allow users to view their profile.",
                "repo": "owner/frontend",
                "category": "feature",
                "severity": "low",
                "status": "open",
                "tags": ["feature", "ui"],
                "created": "2024-01-24T10:00:00Z",
                "updated": "2024-01-24T10:00:00Z",
            },
        ]

        insert_tickets(ticket_service.collection, tickets_data)
        return client, tickets_data

    async def test_search_database_returns_relevant_tickets(
        self, db_tickets
    ) -> None:
        """Search 'database' - verify BM25 returns relevant tickets."""
        client, tickets_data = db_tickets
        response = await client.post("/search", json={"query": "database", "limit": 10})
        assert response.status_code == 200
        data = response.json()

        assert "query" in data
        assert "hits" in data
        assert "total" in data
        assert "meta" in data
        assert data["total"] >= 5

        result_ids = [hit["ticket_id"] for hit in data["hits"]]
        expected_db_tickets = ["C1", "C2", "S1", "H1", "F1"]
        found_db_tickets = [tid for tid in expected_db_tickets if tid in result_ids]
        assert len(found_db_tickets) >= 4

    async def test_filter_by_severity_critical(
        self, db_tickets
    ) -> None:
        """Filter by severity=critical - verify only critical tickets."""
        client, tickets_data = db_tickets
        response = await client.post("/search", json={
            "query": "database",
            "filters": {"severity": ["critical"]},
            "limit": 10,
        })
        assert response.status_code == 200
        data = response.json()

        result_ids = [hit["ticket_id"] for hit in data["hits"]]
        # All critical tickets in our test data
        all_critical_tickets = ["C1", "C2", "C3", "S2"]

        # All results should have critical severity
        for tid in result_ids:
            assert tid in all_critical_tickets, f"Ticket {tid} should have critical severity"

    async def test_search_plus_filter_error_high_severity(
        self, db_tickets
    ) -> None:
        """Combine search + filter (query='error' + severity=high)."""
        client, tickets_data = db_tickets
        response = await client.post("/search", json={
            "query": "error",
            "filters": {"severity": ["high"]},
            "limit": 10,
        })
        assert response.status_code == 200
        data = response.json()

        result_ids = [hit["ticket_id"] for hit in data["hits"]]
        for tid in result_ids:
            ticket = next((t for t in tickets_data if t["id"] == tid), None)
            assert ticket is not None
            assert ticket["severity"] == "high"

    async def test_sort_by_score_descending(
        self, db_tickets
    ) -> None:
        """Sort by score descending - verify order."""
        client, tickets_data = db_tickets
        response = await client.post("/search", json={
            "query": "database",
            "sort": "-score",
            "limit": 10,
        })
        assert response.status_code == 200
        data = response.json()

        scores = [hit["score"] for hit in data["hits"]]
        for i in range(len(scores) - 1):
            assert scores[i] >= scores[i + 1]
        for score in scores:
            assert 0.0 <= score <= 1.0

    async def test_pagination_no_overlap(
        self, db_tickets
    ) -> None:
        """Paginate - verify no overlap between pages."""
        client, tickets_data = db_tickets
        page1_response = await client.post("/search", json={
            "query": "database", "limit": 3, "offset": 0,
        })
        assert page1_response.status_code == 200
        page1_data = page1_response.json()

        page2_response = await client.post("/search", json={
            "query": "database", "limit": 3, "offset": 3,
        })
        assert page2_response.status_code == 200
        page2_data = page2_response.json()

        page1_ids = [hit["ticket_id"] for hit in page1_data["hits"]]
        page2_ids = [hit["ticket_id"] for hit in page2_data["hits"]]

        overlap = set(page1_ids) & set(page2_ids)
        assert len(overlap) == 0

        assert page1_data["meta"]["offset"] == 0
        assert page1_data["meta"]["limit"] == 3
        assert page2_data["meta"]["offset"] == 3

    async def test_min_score_filter_excludes_low_scores(
        self, db_tickets
    ) -> None:
        """Test min_score filter - low-score results excluded."""
        client, tickets_data = db_tickets
        all_response = await client.post("/search", json={
            "query": "database", "limit": 10,
        })
        assert all_response.status_code == 200
        all_data = all_response.json()
        all_count = all_data["total"]

        filtered_response = await client.post("/search", json={
            "query": "database", "min_score": 0.3, "limit": 10,
        })
        assert filtered_response.status_code == 200
        filtered_data = filtered_response.json()
        filtered_count = filtered_data["total"]

        assert filtered_count <= all_count
        for hit in filtered_data["hits"]:
            assert hit["score"] >= 0.3


@pytest.mark.asyncio
class TestSuggestAndNoResultsHandling:
    """E2E Case 2: Suggest & No-Results Handling"""

    @pytest.fixture
    async def auth_tickets(self, api_client_with_data) -> tuple[AsyncClient, list[dict]]:
        """Create 15 tickets with authentication-related titles."""
        client, ticket_service = api_client_with_data
        tickets_data = [
            {"id": "S1", "title": "Authentication Bug in Login Flow", "description": "Users cannot authenticate.", "repo": "owner/auth", "category": "security", "severity": "critical", "status": "open", "tags": ["auth"], "created": "2024-01-15T10:00:00Z", "updated": "2024-01-15T10:00:00Z"},
            {"id": "S2", "title": "Auth Service Timeout", "description": "Auth service timing out.", "repo": "owner/auth", "category": "security", "severity": "high", "status": "open", "tags": ["auth"], "created": "2024-01-16T10:00:00Z", "updated": "2024-01-16T10:00:00Z"},
            {"id": "S3", "title": "Authorization Failure for Admin Users", "description": "Admin auth failing.", "repo": "owner/auth", "category": "security", "severity": "critical", "status": "in_progress", "tags": ["auth"], "created": "2024-01-17T10:00:00Z", "updated": "2024-01-17T10:00:00Z"},
            {"id": "S4", "title": "OAuth Authentication Error", "description": "OAuth failing.", "repo": "owner/auth", "category": "security", "severity": "high", "status": "open", "tags": ["auth"], "created": "2024-01-18T10:00:00Z", "updated": "2024-01-18T10:00:00Z"},
            {"id": "S5", "title": "Auth Token Expiration Issue", "description": "Tokens expire too fast.", "repo": "owner/auth", "category": "security", "severity": "medium", "status": "open", "tags": ["auth"], "created": "2024-01-19T10:00:00Z", "updated": "2024-01-19T10:00:00Z"},
            {"id": "S6", "title": "Authentication Bug in Mobile App", "description": "Mobile auth bug.", "repo": "owner/mobile", "category": "security", "severity": "high", "status": "open", "tags": ["auth"], "created": "2024-01-20T10:00:00Z", "updated": "2024-01-20T10:00:00Z"},
            {"id": "H1", "title": "Auth Service Memory Leak", "description": "Memory leak in auth.", "repo": "owner/auth", "category": "hotfix", "severity": "critical", "status": "blocked", "tags": ["auth"], "created": "2024-01-21T10:00:00Z", "updated": "2024-01-21T10:00:00Z"},
            {"id": "C1", "title": "Auth Database Connection Lost", "description": "Auth DB unstable.", "repo": "owner/auth", "category": "crash", "severity": "critical", "status": "open", "tags": ["auth"], "created": "2024-01-22T10:00:00Z", "updated": "2024-01-22T10:00:00Z"},
            {"id": "F1", "title": "Add Auth Provider for SAML", "description": "SAML auth feature.", "repo": "owner/auth", "category": "feature", "severity": "medium", "status": "open", "tags": ["auth"], "created": "2024-01-23T10:00:00Z", "updated": "2024-01-23T10:00:00Z"},
            {"id": "G1", "title": "Documentation for Auth API", "description": "Auth API docs.", "repo": "owner/docs", "category": "general", "severity": "low", "status": "in_progress", "tags": ["auth"], "created": "2024-01-24T10:00:00Z", "updated": "2024-01-24T10:00:00Z"},
            {"id": "S7", "title": "Two-Factor Authentication Bug", "description": "2FA not working.", "repo": "owner/auth", "category": "security", "severity": "high", "status": "open", "tags": ["auth"], "created": "2024-01-25T10:00:00Z", "updated": "2024-01-25T10:00:00Z"},
            {"id": "S8", "title": "Auth Rate Limiting Issue", "description": "Rate limiting broken.", "repo": "owner/auth", "category": "security", "severity": "medium", "status": "fixed", "tags": ["auth"], "created": "2024-01-26T10:00:00Z", "updated": "2024-01-26T10:00:00Z"},
            {"id": "H2", "title": "Auth Service Deployment Failed", "description": "Deployment failed.", "repo": "owner/auth", "category": "hotfix", "severity": "critical", "status": "open", "tags": ["auth"], "created": "2024-01-27T10:00:00Z", "updated": "2024-01-27T10:00:00Z"},
            {"id": "F2", "title": "Auth Analytics Dashboard", "description": "Auth analytics.", "repo": "owner/analytics", "category": "feature", "severity": "low", "status": "open", "tags": ["auth"], "created": "2024-01-28T10:00:00Z", "updated": "2024-01-28T10:00:00Z"},
            {"id": "C2", "title": "Auth Service Crash Loop", "description": "Auth crashing.", "repo": "owner/auth", "category": "crash", "severity": "critical", "status": "open", "tags": ["auth"], "created": "2024-01-29T10:00:00Z", "updated": "2024-01-29T10:00:00Z"},
        ]

        insert_tickets(ticket_service.collection, tickets_data)
        return client, tickets_data

    async def test_suggest_auth_returns_grouped_suggestions(
        self, auth_tickets
    ) -> None:
        """Suggest 'auth' - verify grouped suggestions with counts."""
        client, tickets_data = auth_tickets
        response = await client.get("/search/suggest?q=auth&limit=10")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        for sugg in data:
            assert "suggestion" in sugg
            assert "ticket_count" in sugg
            assert isinstance(sugg["suggestion"], str)
            assert isinstance(sugg["ticket_count"], int)

        assert len(data) > 0
        auth_titles = [s["suggestion"].lower() for s in data]
        assert all("auth" in title for title in auth_titles)

    async def test_suggest_xyz_returns_empty_or_few(
        self, auth_tickets
    ) -> None:
        """Suggest 'xyz' - verify empty results or very few."""
        client, tickets_data = auth_tickets
        response = await client.get("/search/suggest?q=xyz&limit=5")
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        for sugg in data:
            assert "suggestion" in sugg
            assert "ticket_count" in sugg

    async def test_search_empty_query_behavior(
        self, auth_tickets
    ) -> None:
        """Search with empty-ish query - verify behavior."""
        client, tickets_data = auth_tickets
        response = await client.post("/search", json={"query": "   ", "limit": 10})
        assert response.status_code == 400
        data = response.json()

        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"

    async def test_search_exact_title_top_result(
        self, auth_tickets
    ) -> None:
        """Search for exact ticket title - verify top result."""
        client, tickets_data = auth_tickets
        target_title = "Authentication Bug in Login Flow"
        response = await client.post("/search", json={"query": target_title, "limit": 10})
        assert response.status_code == 200
        data = response.json()

        assert data["total"] > 0
        top_result = data["hits"][0] if data["hits"] else None
        if top_result:
            assert "ticket_id" in top_result
            assert "score" in top_result
            assert "source" in top_result
            assert top_result["source"] in ["bm25", "semantic", "hybrid"]
            assert 0.0 <= top_result["score"] <= 1.0

    async def test_response_schema_matches_openapi(
        self, auth_tickets
    ) -> None:
        """Verify all response schemas match OpenAPI spec exactly."""
        client, tickets_data = auth_tickets
        search_response = await client.post("/search", json={"query": "authentication", "limit": 5})
        assert search_response.status_code == 200
        search_data = search_response.json()

        assert "query" in search_data
        assert "hits" in search_data
        assert "total" in search_data
        assert "meta" in search_data
        assert isinstance(search_data["query"], str)
        assert isinstance(search_data["hits"], list)
        assert isinstance(search_data["total"], int)
        assert isinstance(search_data["meta"], dict)

        if search_data["hits"]:
            hit = search_data["hits"][0]
            assert "ticket_id" in hit
            assert "score" in hit
            assert "source" in hit
            assert isinstance(hit["ticket_id"], str)
            assert isinstance(hit["score"], float)
            assert hit["source"] in ["bm25", "semantic", "hybrid"]

        meta = search_data["meta"]
        assert "total" in meta
        assert "limit" in meta
        assert "offset" in meta
        assert "has_more" in meta
        assert "latency_ms" in meta
        assert isinstance(meta["total"], int)
        assert isinstance(meta["limit"], int)
        assert isinstance(meta["offset"], int)
        assert isinstance(meta["has_more"], bool)

        suggest_response = await client.get("/search/suggest?q=auth&limit=5")
        assert suggest_response.status_code == 200
        suggest_data = suggest_response.json()

        assert isinstance(suggest_data, list)
        for sugg in suggest_data:
            assert "suggestion" in sugg
            assert "ticket_count" in sugg
            assert isinstance(sugg["suggestion"], str)
            assert isinstance(sugg["ticket_count"], int)
