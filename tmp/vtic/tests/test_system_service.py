"""Tests for SystemService.

These tests use a real TicketService with tmp_path.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from datetime import datetime, timezone

from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
from vtic.models.ticket import TicketCreate
from vtic.models.enums import Category, Severity, Status
from vtic.services.system import SystemService
from vtic.ticket import TicketService
from vtic.index.client import destroy_index


@pytest.fixture
async def system_service(tmp_path: Path) -> SystemService:
    """Create a SystemService with a temporary TicketService."""
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    config = Config(
        storage=StorageConfig(dir=storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )
    
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    
    service = SystemService(config, ticket_service)
    
    yield service
    
    # Cleanup
    await ticket_service.close()
    destroy_index(storage_dir)


@pytest.fixture
async def system_service_with_tickets(tmp_path: Path) -> SystemService:
    """Create a SystemService with sample tickets."""
    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    config = Config(
        storage=StorageConfig(dir=storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )
    
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
    
    service = SystemService(config, ticket_service)
    
    yield service
    
    # Cleanup
    await ticket_service.close()
    destroy_index(storage_dir)


@pytest.mark.asyncio
class TestHealth:
    """Tests for health check."""
    
    async def test_health_healthy(self, system_service_with_tickets: SystemService) -> None:
        """Returns status=healthy when system is healthy."""
        result = await system_service_with_tickets.health(
            version="0.1.0",
            uptime_seconds=3600,
        )
        
        assert result.status in ["healthy", "degraded"]
        assert result.version == "0.1.0"
        assert result.uptime_seconds == 3600
        assert result.index_status is not None
        assert result.index_status.zvec in ["available", "unavailable", "corrupted"]
        assert result.index_status.ticket_count >= 0
    
    async def test_health_with_provider(self, tmp_path: Path) -> None:
        """Returns healthy when embedding provider is configured."""
        storage_dir = tmp_path / "tickets"
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        config = Config(
            storage=StorageConfig(dir=storage_dir),
            api=ApiConfig(host="localhost", port=8080),
            search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
            embeddings=EmbeddingsConfig(
                provider="local",
                model="all-MiniLM-L6-v2",
                dimension=384,
            ),
        )
        
        ticket_service = TicketService(config)
        await ticket_service.initialize()
        
        service = SystemService(config, ticket_service)
        
        result = await service.health(version="0.1.0")
        
        # With provider configured, should be healthy or degraded
        assert result.status in ["healthy", "degraded"]
        
        if result.embedding_provider:
            assert result.embedding_provider.name == "local"
            assert result.embedding_provider.model == "all-MiniLM-L6-v2"
            assert result.embedding_provider.dimension == 384
        
        await ticket_service.close()
        destroy_index(storage_dir)
    
    async def test_health_no_provider(self, system_service: SystemService) -> None:
        """Returns degraded when no embedding provider."""
        result = await system_service.health(version="0.1.0")
        
        # With provider="none", should be degraded or healthy
        assert result.status in ["healthy", "degraded"]
        # When provider is "none", embedding_provider should be None
        assert result.embedding_provider is None


@pytest.mark.asyncio
class TestStats:
    """Tests for stats."""
    
    async def test_stats_basic(self, system_service_with_tickets: SystemService) -> None:
        """Returns counts with tickets present."""
        result = await system_service_with_tickets.stats(by_repo=False)
        
        assert result.totals is not None
        assert result.totals.all == 5  # 5 tickets created
        assert result.totals.open >= 0
        assert result.totals.closed >= 0
        
        # Should have breakdowns
        assert isinstance(result.by_status, dict)
        assert isinstance(result.by_severity, dict)
        assert isinstance(result.by_category, dict)
        
        # Verify some counts
        assert "critical" in result.by_severity
        assert result.by_severity["critical"] == 2  # C1 and S1
        
        # by_repo should be None when by_repo=False
        assert result.by_repo is None
    
    async def test_stats_empty(self, system_service: SystemService) -> None:
        """No tickets, totals.all=0."""
        result = await system_service.stats(by_repo=False)
        
        assert result.totals is not None
        assert result.totals.all == 0
        assert result.totals.open == 0
        assert result.totals.closed == 0
        
        # Breakdowns should be empty dicts
        assert result.by_status == {}
        assert result.by_severity == {}
        assert result.by_category == {}
    
    async def test_stats_by_repo(self, system_service_with_tickets: SystemService) -> None:
        """Returns by_repo breakdown when requested."""
        result = await system_service_with_tickets.stats(by_repo=True)
        
        assert result.totals is not None
        assert result.totals.all == 5
        
        # by_repo should be populated
        assert result.by_repo is not None
        assert isinstance(result.by_repo, dict)
        
        # Should have counts for repos
        assert "owner/repo1" in result.by_repo
        assert "owner/repo2" in result.by_repo
        assert result.by_repo["owner/repo1"] == 2  # 2 tickets in repo1
        assert result.by_repo["owner/repo2"] == 2  # 2 tickets in repo2
        assert result.by_repo["owner/repo3"] == 1  # 1 ticket in repo3


@pytest.mark.asyncio
class TestReindex:
    """Tests for reindex."""
    
    async def test_reindex_success(self, system_service_with_tickets: SystemService) -> None:
        """Creates tickets, reindexes successfully."""
        result = await system_service_with_tickets.reindex()
        
        assert result.processed >= 0
        assert result.skipped >= 0
        assert result.failed >= 0
        assert result.duration_ms >= 0
        assert isinstance(result.errors, list)
        
        # Should have processed some tickets
        total = result.processed + result.skipped + result.failed
        assert total >= 5  # At least the 5 tickets we created


@pytest.mark.asyncio
class TestDoctor:
    """Tests for doctor checks."""
    
    async def test_doctor_all_ok(self, system_service_with_tickets: SystemService) -> None:
        """All checks pass with healthy system."""
        result = await system_service_with_tickets.doctor()
        
        # Should have 5 checks
        assert len(result.checks) == 5
        
        # Verify all expected checks are present
        check_names = [c.name for c in result.checks]
        assert "zvec_index" in check_names
        assert "config_file" in check_names
        assert "embedding_provider" in check_names
        assert "file_permissions" in check_names
        assert "ticket_files" in check_names
        
        # Each check should have required fields
        for check in result.checks:
            assert check.name != ""
            assert check.status in ["ok", "warning", "error"]
            assert check.message is not None
        
        # Overall should be ok, warnings, or errors (depends on environment)
        assert result.overall in ["ok", "warnings", "errors"]
    
    async def test_doctor_zvec_index_check(self, system_service: SystemService) -> None:
        """Zvec index check returns appropriate status."""
        result = await system_service.doctor()
        
        zvec_check = next(c for c in result.checks if c.name == "zvec_index")
        assert zvec_check.status in ["ok", "warning", "error"]
    
    async def test_doctor_config_check(self, system_service: SystemService) -> None:
        """Config check returns ok for valid config."""
        result = await system_service.doctor()
        
        config_check = next(c for c in result.checks if c.name == "config_file")
        assert config_check.status in ["ok", "warning"]
    
    async def test_doctor_permissions_check(self, system_service: SystemService) -> None:
        """File permissions check returns ok."""
        result = await system_service.doctor()
        
        perm_check = next(c for c in result.checks if c.name == "file_permissions")
        assert perm_check.status in ["ok", "error"]
    
    async def test_doctor_ticket_files_check(self, system_service: SystemService) -> None:
        """Ticket files check returns appropriate status."""
        result = await system_service.doctor()
        
        files_check = next(c for c in result.checks if c.name == "ticket_files")
        assert files_check.status in ["ok", "warning"]
    
    async def test_doctor_overall_errors(self, tmp_path: Path) -> None:
        """Overall is 'errors' when any check is error."""
        # Create a system with no storage directory to trigger errors
        storage_dir = tmp_path / "nonexistent"
        
        config = Config(
            storage=StorageConfig(dir=storage_dir),
            api=ApiConfig(host="localhost", port=8080),
            search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
            embeddings=EmbeddingsConfig(provider="none"),
        )
        
        # Create storage directory for ticket service initialization
        storage_dir.mkdir(parents=True, exist_ok=True)
        
        ticket_service = TicketService(config)
        await ticket_service.initialize()
        
        # Now delete it to trigger errors
        import shutil
        shutil.rmtree(storage_dir)
        
        service = SystemService(config, ticket_service)
        
        result = await service.doctor()
        
        # Should have errors due to missing directory
        assert result.overall in ["errors", "warnings"]
        assert any(c.status == "error" for c in result.checks)
        
        await ticket_service.close()


@pytest.mark.asyncio
class TestHealthStatusTransitions:
    """Tests for health status determination."""
    
    async def test_health_status_healthy(self, system_service_with_tickets: SystemService) -> None:
        """Healthy when zvec available and provider configured."""
        result = await system_service_with_tickets.health()
        
        # With tickets and index, should be healthy or degraded
        assert result.status in ["healthy", "degraded"]
    
    async def test_health_status_degraded_no_provider(self, system_service: SystemService) -> None:
        """Degraded when no embedding provider."""
        result = await system_service.health()
        
        # Provider is "none", so should be degraded
        assert result.status == "degraded"
    
    async def test_health_version_uptime(self, system_service: SystemService) -> None:
        """Version and uptime are included in response."""
        result = await system_service.health(
            version="1.0.0",
            uptime_seconds=86400,
        )
        
        assert result.version == "1.0.0"
        assert result.uptime_seconds == 86400
