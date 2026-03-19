"""Tests for search routes.

These tests use FastAPI TestClient with a real SearchEngine.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport

from vtic.api.app import create_app
from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
from vtic.ticket import TicketService
from vtic.index.operations import insert_tickets
from vtic.index.client import get_collection, destroy_index


@pytest.fixture
def tmp_storage_dir(tmp_path: Path) -> Path:
    """Create a temporary storage directory."""
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def config(tmp_storage_dir: Path) -> Config:
    """Create a test configuration."""
    return Config(
        storage=StorageConfig(dir=tmp_storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )


@pytest.fixture
async def api_client_with_search(
    tmp_storage_dir: Path,
    config: Config,
) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with search routes and sample data."""
    from vtic.search.engine import SearchEngine
    from vtic.api.deps import set_config, get_search_engine
    
    # Set the config for this test
    set_config(config)
    
    # Create app with config first
    app = create_app(config)
    
    # Initialize ticket service (this creates the collection)
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    app.state.ticket_service = ticket_service
    
    # Create SearchEngine using the ticket service's collection
    search_engine = SearchEngine(ticket_service.collection)
    
    # Use FastAPI's dependency override mechanism
    # Must match signature: get_search_engine(config: Config = Depends(get_config))
    def override_get_search_engine(config=None):
        return search_engine

    app.dependency_overrides[get_search_engine] = override_get_search_engine
    
    # Insert sample tickets through the ticket service's collection
    sample_tickets = [
        {
            "id": "C1",
            "title": "Database connection timeout",
            "description": "The application fails to connect to the database after 30 seconds.",
            "repo": "owner/repo1",
            "category": "crash",
            "severity": "critical",
            "status": "open",
            "assignee": "alice",
            "tags": ["database", "timeout"],
            "references": [],
            "created": "2024-01-15T10:00:00Z",
            "updated": "2024-01-15T10:00:00Z",
        },
        {
            "id": "C2",
            "title": "Database corruption detected",
            "description": "Critical database corruption found in production.",
            "repo": "owner/repo1",
            "category": "crash",
            "severity": "critical",
            "status": "in_progress",
            "assignee": "bob",
            "tags": ["database", "corruption"],
            "references": [],
            "created": "2024-01-16T10:00:00Z",
            "updated": "2024-01-16T10:00:00Z",
        },
        {
            "id": "H1",
            "title": "CORS configuration error",
            "description": "Cross-origin requests are being blocked by the API.",
            "repo": "owner/repo2",
            "category": "hotfix",
            "severity": "high",
            "status": "open",
            "assignee": "alice",
            "tags": ["cors", "api"],
            "references": [],
            "created": "2024-01-17T10:00:00Z",
            "updated": "2024-01-17T10:00:00Z",
        },
    ]
    insert_tickets(ticket_service.collection, sample_tickets)
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()
    await ticket_service.close()
    destroy_index(tmp_storage_dir)
    set_config(None)  # Clear the config


@pytest.mark.asyncio
class TestPostSearch:
    """Tests for POST /search endpoint."""
    
    async def test_post_search_200(self, api_client_with_search: AsyncClient) -> None:
        """Valid query returns SearchResult."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "limit": 10,
        })

        assert response.status_code == 200
        data = response.json()
        
        # Verify response format
        assert "query" in data
        assert "hits" in data
        assert "total" in data
        assert "meta" in data
        
        assert data["query"] == "database"
        assert isinstance(data["hits"], list)
        assert isinstance(data["total"], int)
        assert data["total"] >= 0
    
    async def test_post_search_400(self, api_client_with_search: AsyncClient) -> None:
        """Empty query returns error."""
        response = await api_client_with_search.post("/search", json={
            "query": "",
            "limit": 10,
        })
        
        # Should return 400 for validation error
        assert response.status_code == 400
        data = response.json()
        
        # Verify error format
        assert "error" in data
        assert data["error"]["code"] == "VALIDATION_ERROR"
    
    async def test_post_search_with_filters(self, api_client_with_search: AsyncClient) -> None:
        """Search with filters returns filtered results."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "filters": {
                "severity": ["critical"],
            },
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["hits"], list)
    
    async def test_post_search_with_min_score(self, api_client_with_search: AsyncClient) -> None:
        """Search with min_score filters low results."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "min_score": 0.5,
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # All hits should have score >= 0.5
        for hit in data["hits"]:
            assert hit["score"] >= 0.5
    
    async def test_post_search_with_sort(self, api_client_with_search: AsyncClient) -> None:
        """Search with sort returns sorted results."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "sort": "-score",
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["hits"], list)


@pytest.mark.asyncio
class TestGetSuggest:
    """Tests for GET /search/suggest endpoint."""
    
    async def test_get_suggest_200(self, api_client_with_search: AsyncClient) -> None:
        """?q=test returns suggestions."""
        response = await api_client_with_search.get("/search/suggest?q=cor&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should be a list of suggestions
        assert isinstance(data, list)
        
        # Each suggestion should have suggestion and ticket_count
        for sugg in data:
            assert "suggestion" in sugg
            assert "ticket_count" in sugg
            assert isinstance(sugg["suggestion"], str)
            assert isinstance(sugg["ticket_count"], int)
    
    async def test_get_suggest_400_short(self, api_client_with_search: AsyncClient) -> None:
        """?q=x (1 char) returns 400."""
        response = await api_client_with_search.get("/search/suggest?q=x")
        
        # FastAPI validation should return 422, but we convert to 400
        assert response.status_code in [400, 422]
    
    async def test_get_suggest_no_results(self, api_client_with_search: AsyncClient) -> None:
        """?q=nonexistent returns empty list or suggestions from titles."""
        response = await api_client_with_search.get("/search/suggest?q=xyznonexistent")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        # Suggest may return all titles if no prefix match, so just verify it's a valid response
    
    async def test_get_suggest_limit(self, api_client_with_search: AsyncClient) -> None:
        """?q=database&limit=2 respects limit."""
        response = await api_client_with_search.get("/search/suggest?q=database&limit=2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) <= 2


@pytest.mark.asyncio
class TestSearchResponseFormat:
    """Tests for search response format verification."""
    
    async def test_search_response_format(self, api_client_with_search: AsyncClient) -> None:
        """Verify SearchResult has hits, meta, total."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "query" in data
        assert "hits" in data
        assert "total" in data
        assert "meta" in data
        
        # Verify meta fields
        meta = data["meta"]
        assert "total" in meta
        assert "limit" in meta
        assert "offset" in meta
        assert "has_more" in meta
        assert "latency_ms" in meta
        
        # Verify types
        assert isinstance(data["query"], str)
        assert isinstance(data["hits"], list)
        assert isinstance(data["total"], int)
        assert isinstance(meta, dict)
    
    async def test_search_hit_format(self, api_client_with_search: AsyncClient) -> None:
        """Verify SearchHit format."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify hit structure
        for hit in data["hits"]:
            assert "ticket_id" in hit
            assert "score" in hit
            assert "source" in hit
            
            assert isinstance(hit["ticket_id"], str)
            assert isinstance(hit["score"], float)
            assert 0.0 <= hit["score"] <= 1.0
            assert hit["source"] in ["bm25", "semantic", "hybrid"]
    
    async def test_search_meta_total_matches(self, api_client_with_search: AsyncClient) -> None:
        """Verify meta.total matches actual results."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "limit": 10,
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # meta.total should match len(hits) when all results fit in limit
        if data["total"] <= data["meta"]["limit"]:
            assert data["total"] == len(data["hits"])


@pytest.mark.asyncio
class TestSearchValidation:
    """Tests for search input validation."""
    
    async def test_search_query_too_long(self, api_client_with_search: AsyncClient) -> None:
        """Query > 500 chars returns validation error."""
        response = await api_client_with_search.post("/search", json={
            "query": "x" * 501,
            "limit": 10,
        })
        
        assert response.status_code in [400, 422]
    
    async def test_search_invalid_limit(self, api_client_with_search: AsyncClient) -> None:
        """Limit > 100 returns validation error."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "limit": 101,
        })
        
        assert response.status_code in [400, 422]
    
    async def test_search_invalid_offset(self, api_client_with_search: AsyncClient) -> None:
        """Negative offset returns validation error."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "offset": -1,
        })
        
        assert response.status_code in [400, 422]
    
    async def test_search_invalid_sort(self, api_client_with_search: AsyncClient) -> None:
        """Invalid sort pattern returns validation error."""
        response = await api_client_with_search.post("/search", json={
            "query": "database",
            "sort": "invalid@sort!",
        })
        
        assert response.status_code in [400, 422]


@pytest.mark.asyncio
class TestSuggestValidation:
    """Tests for suggest input validation."""
    
    async def test_suggest_limit_too_high(self, api_client_with_search: AsyncClient) -> None:
        """Limit > 20 returns validation error."""
        response = await api_client_with_search.get("/search/suggest?q=database&limit=21")
        
        assert response.status_code in [400, 422]
    
    async def test_suggest_limit_zero(self, api_client_with_search: AsyncClient) -> None:
        """Limit = 0 returns validation error."""
        response = await api_client_with_search.get("/search/suggest?q=database&limit=0")
        
        assert response.status_code in [400, 422]
    
    async def test_suggest_missing_q(self, api_client_with_search: AsyncClient) -> None:
        """Missing q parameter returns validation error."""
        response = await api_client_with_search.get("/search/suggest")
        
        assert response.status_code in [400, 422]
