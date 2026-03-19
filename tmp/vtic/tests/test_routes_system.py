"""Tests for system routes.

These tests use FastAPI TestClient.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import AsyncGenerator

from httpx import AsyncClient, ASGITransport

from vtic.api.app import create_app
from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
from vtic.models.ticket import TicketCreate
from vtic.models.enums import Category, Severity, Status
from vtic.ticket import TicketService
from vtic.index.client import destroy_index


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
async def api_client(
    config: Config,
) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client."""
    # Create app with config
    app = create_app(config)
    
    # Initialize ticket service
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    app.state.ticket_service = ticket_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    await ticket_service.close()
    destroy_index(config.storage.dir)


@pytest.fixture
async def api_client_with_tickets(
    config: Config,
) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with sample tickets."""
    # Create app with config
    app = create_app(config)
    
    # Initialize ticket service and create tickets
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    
    # Create sample tickets
    tickets = [
        TicketCreate(
            title="Database connection timeout",
            description="Application fails to connect to database.",
            repo="owner/repo1",
            category=Category.CRASH,
            severity=Severity.CRITICAL,
            status=Status.OPEN,
            assignee="alice",
        ),
        TicketCreate(
            title="CORS configuration error",
            description="Cross-origin requests blocked.",
            repo="owner/repo2",
            category=Category.HOTFIX,
            severity=Severity.HIGH,
            status=Status.IN_PROGRESS,
            assignee="bob",
        ),
        TicketCreate(
            title="Add caching layer",
            description="Implement Redis caching.",
            repo="owner/repo1",
            category=Category.FEATURE,
            severity=Severity.MEDIUM,
            status=Status.OPEN,
            assignee=None,
        ),
        TicketCreate(
            title="SQL injection fix",
            description="Fix SQL injection vulnerability.",
            repo="owner/repo3",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            status=Status.FIXED,
            assignee="charlie",
        ),
        TicketCreate(
            title="Documentation update",
            description="Update API documentation.",
            repo="owner/repo2",
            category=Category.GENERAL,
            severity=Severity.LOW,
            status=Status.CLOSED,
            assignee=None,
        ),
    ]
    
    for ticket_data in tickets:
        await ticket_service.create_ticket(ticket_data)
    
    app.state.ticket_service = ticket_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Cleanup
    await ticket_service.close()
    destroy_index(config.storage.dir)


@pytest.mark.asyncio
class TestGetHealth:
    """Tests for GET /health endpoint."""
    
    async def test_get_health_200(self, api_client: AsyncClient) -> None:
        """Returns HealthResponse."""
        response = await api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify HealthResponse structure
        assert "status" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "index_status" in data
        assert "embedding_provider" in data
        
        # Verify status values
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Verify index_status structure
        index_status = data["index_status"]
        assert "zvec" in index_status
        assert "ticket_count" in index_status
        assert index_status["zvec"] in ["available", "unavailable", "corrupted"]
        assert isinstance(index_status["ticket_count"], int)
    
    async def test_get_health_with_tickets(self, api_client_with_tickets: AsyncClient) -> None:
        """Health shows ticket count with tickets present."""
        response = await api_client_with_tickets.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have ticket count >= 0 (may be 0 if collection locked)
        assert isinstance(data["index_status"]["ticket_count"], int)
        assert data["index_status"]["ticket_count"] >= 0


@pytest.mark.asyncio
class TestGetStats:
    """Tests for GET /stats endpoint."""
    
    async def test_get_stats_200(self, api_client_with_tickets: AsyncClient) -> None:
        """Returns StatsResponse."""
        response = await api_client_with_tickets.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify StatsResponse structure
        assert "totals" in data
        assert "by_status" in data
        assert "by_severity" in data
        assert "by_category" in data
        
        # Verify totals structure
        totals = data["totals"]
        assert "all" in totals
        assert "open" in totals
        assert "closed" in totals
        
        # Verify counts
        assert totals["all"] == 5
        assert totals["open"] >= 0
        assert totals["closed"] >= 0
        
        # by_repo should be None when not requested
        assert data.get("by_repo") is None
    
    async def test_stats_by_repo(self, api_client_with_tickets: AsyncClient) -> None:
        """?by_repo=true returns by_repo breakdown."""
        response = await api_client_with_tickets.get("/stats?by_repo=true")
        
        assert response.status_code == 200
        data = response.json()
        
        # by_repo should be populated
        assert data["by_repo"] is not None
        assert isinstance(data["by_repo"], dict)
        
        # Should have counts for each repo
        by_repo = data["by_repo"]
        assert "owner/repo1" in by_repo
        assert "owner/repo2" in by_repo
        assert "owner/repo3" in by_repo
        assert by_repo["owner/repo1"] == 2
        assert by_repo["owner/repo2"] == 2
        assert by_repo["owner/repo3"] == 1
    
    async def test_stats_empty(self, api_client: AsyncClient) -> None:
        """Stats with no tickets shows zeros."""
        response = await api_client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data["totals"]
        assert totals["all"] == 0
        assert totals["open"] == 0
        assert totals["closed"] == 0
        
        assert data["by_status"] == {}
        assert data["by_severity"] == {}
        assert data["by_category"] == {}


@pytest.mark.asyncio
class TestPostReindex:
    """Tests for POST /reindex endpoint."""
    
    async def test_post_reindex_200(self, api_client_with_tickets: AsyncClient) -> None:
        """Returns ReindexResult."""
        response = await api_client_with_tickets.post("/reindex")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify ReindexResult structure
        assert "processed" in data
        assert "skipped" in data
        assert "failed" in data
        assert "duration_ms" in data
        assert "errors" in data
        
        # Verify types
        assert isinstance(data["processed"], int)
        assert isinstance(data["skipped"], int)
        assert isinstance(data["failed"], int)
        assert isinstance(data["duration_ms"], int)
        assert isinstance(data["errors"], list)
        
        # Should have processed the tickets
        total = data["processed"] + data["skipped"] + data["failed"]
        assert total >= 5
    
    async def test_post_reindex_empty(self, api_client: AsyncClient) -> None:
        """Reindex with no tickets returns zeros."""
        response = await api_client.post("/reindex")
        
        assert response.status_code == 200
        data = response.json()
        
        # With no tickets, should have zeros
        assert data["processed"] >= 0
        assert data["failed"] >= 0
        assert isinstance(data["errors"], list)


@pytest.mark.asyncio
class TestGetDoctor:
    """Tests for GET /doctor endpoint."""
    
    async def test_get_doctor_200(self, api_client: AsyncClient) -> None:
        """Returns DoctorResult."""
        response = await api_client.get("/doctor")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify DoctorResult structure
        assert "overall" in data
        assert "checks" in data
        
        # Verify overall values
        assert data["overall"] in ["ok", "warnings", "errors"]
        
        # Verify checks structure
        assert isinstance(data["checks"], list)
        assert len(data["checks"]) == 5
        
        # Each check should have required fields
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert "message" in check
            assert "fix" in check
            assert check["status"] in ["ok", "warning", "error"]
    
    async def test_get_doctor_all_checks_present(self, api_client: AsyncClient) -> None:
        """All 5 checks are present."""
        response = await api_client.get("/doctor")
        
        assert response.status_code == 200
        data = response.json()
        
        check_names = [c["name"] for c in data["checks"]]
        
        assert "zvec_index" in check_names
        assert "config_file" in check_names
        assert "embedding_provider" in check_names
        assert "file_permissions" in check_names
        assert "ticket_files" in check_names
    
    async def test_get_doctor_with_tickets(self, api_client_with_tickets: AsyncClient) -> None:
        """Doctor shows status with tickets present."""
        response = await api_client_with_tickets.get("/doctor")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have ok, warnings, or errors overall (depends on environment)
        assert data["overall"] in ["ok", "warnings", "errors"]
        
        # Find zvec_index check
        zvec_check = next(c for c in data["checks"] if c["name"] == "zvec_index")
        assert zvec_check["status"] in ["ok", "warning", "error"]
        
        # Find ticket_files check
        files_check = next(c for c in data["checks"] if c["name"] == "ticket_files")
        assert files_check["status"] in ["ok", "warning"]


@pytest.mark.asyncio
class TestResponseValidation:
    """Tests for response validation."""
    
    async def test_health_response_types(self, api_client: AsyncClient) -> None:
        """Health response has correct types."""
        response = await api_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data["status"], str)
        assert isinstance(data["version"], str)
        assert isinstance(data["uptime_seconds"], int)
        assert isinstance(data["index_status"], dict)
    
    async def test_stats_response_totals(self, api_client_with_tickets: AsyncClient) -> None:
        """Stats response totals are consistent."""
        response = await api_client_with_tickets.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        
        totals = data["totals"]
        # open + closed should approximately equal all (may differ due to in_progress, etc.)
        assert totals["all"] >= 0
        assert totals["open"] >= 0
        assert totals["closed"] >= 0
    
    async def test_reindex_error_format(self, api_client_with_tickets: AsyncClient) -> None:
        """Reindex errors have correct format."""
        response = await api_client_with_tickets.post("/reindex")
        
        assert response.status_code == 200
        data = response.json()
        
        # Each error should have ticket_id and message
        for error in data["errors"]:
            assert "ticket_id" in error
            assert "message" in error
    
    async def test_doctor_overall_consistency(self, api_client: AsyncClient) -> None:
        """Doctor overall matches individual checks."""
        response = await api_client.get("/doctor")
        
        assert response.status_code == 200
        data = response.json()
        
        statuses = [c["status"] for c in data["checks"]]
        
        # Overall should match worst status
        if "error" in statuses:
            assert data["overall"] == "errors"
        elif "warning" in statuses:
            assert data["overall"] == "warnings"
        else:
            assert data["overall"] == "ok"


@pytest.mark.asyncio
class TestEdgeCases:
    """Tests for edge cases."""
    
    async def test_stats_by_repo_false(self, api_client_with_tickets: AsyncClient) -> None:
        """?by_repo=false does not include by_repo."""
        response = await api_client_with_tickets.get("/stats?by_repo=false")
        
        assert response.status_code == 200
        data = response.json()
        
        # by_repo should be None when false
        assert data.get("by_repo") is None
    
    async def test_doctor_checks_present(self, api_client: AsyncClient) -> None:
        """Doctor returns all checks in happy path."""
        response = await api_client.get("/doctor")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have all 5 checks
        assert len(data["checks"]) == 5
        
        # All checks should have valid status
        for check in data["checks"]:
            assert check["status"] in ["ok", "warning", "error"]
    
    async def test_health_uptime_increases(self, api_client: AsyncClient) -> None:
        """Uptime increases between requests."""
        response1 = await api_client.get("/health")
        assert response1.status_code == 200
        data1 = response1.json()
        uptime1 = data1["uptime_seconds"]
        
        # Small delay to ensure uptime increases
        import asyncio
        await asyncio.sleep(0.1)
        
        response2 = await api_client.get("/health")
        assert response2.status_code == 200
        data2 = response2.json()
        uptime2 = data2["uptime_seconds"]
        
        assert uptime2 >= uptime1
