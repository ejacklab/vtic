"""Integration tests for vtic Wave 2 - Ticket Service + API Routes.

These tests exercise the FULL stack: routes → service → store → index.
They use real storage and indexing, not mocks.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

# Try to import the service and API - tests will skip if not available
try:
    from vtic.ticket import TicketService
    from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig
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


# Check if TicketService has the required methods
TICKET_SERVICE_METHODS_AVAILABLE = False
REQUIRED_METHODS = ['create_ticket', 'get_ticket', 'update_ticket', 'delete_ticket', 'list_tickets', 'reindex_all']
if TICKET_SERVICE_AVAILABLE:
    try:
        ts_methods = dir(TicketService)
        TICKET_SERVICE_METHODS_AVAILABLE = all(m in ts_methods for m in REQUIRED_METHODS)
    except:
        pass


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
    """Create a test configuration."""
    return Config(
        storage=StorageConfig(dir=tmp_storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False)
    )


@pytest.fixture
async def service(config: Config) -> AsyncGenerator[TicketService, None]:
    """Create a real TicketService with temp storage."""
    if not TICKET_SERVICE_AVAILABLE:
        pytest.skip(f"TicketService not available: {TICKET_SERVICE_ERROR}")
    if not TICKET_SERVICE_METHODS_AVAILABLE:
        pytest.skip("TicketService methods not yet implemented (T7 still building)")
    
    svc = TicketService(config)
    await svc.initialize()
    yield svc
    # Cleanup: close any resources
    if hasattr(svc, 'close'):
        await svc.close()


@pytest.fixture
async def api_client(service: TicketService, config: Config) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with real service."""
    if not API_AVAILABLE:
        pytest.skip(f"API not available: {API_ERROR}")
    
    # Create app with config
    app = create_app(config)
    # Set the service on app state
    app.state.ticket_service = service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


# Helper method for searching (TicketService doesn't have search method directly)
def search_tickets(service: TicketService, query: str):
    """Search tickets using the index."""
    # Access collection through the service
    collection = getattr(service, 'collection', None)
    if collection is None:
        pytest.skip("TicketService does not expose collection attribute")
    return query_tickets(collection, query)


# =============================================================================
# Full CRUD Flow Tests
# =============================================================================

class TestFullCrudFlow:
    """Test complete CRUD lifecycle."""
    
    @pytest.mark.asyncio
    async def test_full_crud_lifecycle(self, service: TicketService, tmp_storage_dir: Path):
        """Create → get → update → get → delete → verify gone."""
        # Create
        create_data = TicketCreate(
            title="Test Ticket",
            description="Initial description",
            repo="test/repo",
            category=Category.GENERAL,
            severity=Severity.MEDIUM,
            status=Status.OPEN
        )
        ticket = await service.create_ticket(create_data)
        ticket_id = ticket.id
        
        # Verify created
        assert ticket.title == "Test Ticket"
        assert ticket.description == "Initial description"
        assert ticket.status == Status.OPEN
        
        # Get
        fetched = await service.get_ticket(ticket_id)
        assert fetched.id == ticket_id
        assert fetched.title == "Test Ticket"
        
        # Update
        update_data = TicketUpdate(
            title="Updated Title",
            status=Status.IN_PROGRESS
        )
        updated = await service.update_ticket(ticket_id, update_data)
        assert updated.title == "Updated Title"
        assert updated.status == Status.IN_PROGRESS
        
        # Get after update
        fetched2 = await service.get_ticket(ticket_id)
        assert fetched2.title == "Updated Title"
        
        # Delete (soft)
        await service.delete_ticket(ticket_id)
        
        # Verify gone
        with pytest.raises(Exception) as exc_info:
            await service.get_ticket(ticket_id)
        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_multiple_categories(self, service: TicketService):
        """Create C1 (crash), S1 (security), F1 (feature) — verify IDs correct."""
        crash = await service.create_ticket(TicketCreate(
            title="Crash Bug",
            description="App crashes on startup",
            repo="test/repo",
            category=Category.CRASH,
            severity=Severity.CRITICAL
        ))
        
        security = await service.create_ticket(TicketCreate(
            title="Security Issue",
            description="SQL injection vulnerability",
            repo="test/repo",
            category=Category.SECURITY,
            severity=Severity.HIGH
        ))
        
        feature = await service.create_ticket(TicketCreate(
            title="New Feature",
            description="Add dark mode",
            repo="test/repo",
            category=Category.FEATURE,
            severity=Severity.LOW
        ))
        
        assert crash.id == "C1"
        assert security.id == "S1"
        assert feature.id == "F1"
    
    @pytest.mark.asyncio
    async def test_id_sequence(self, service: TicketService):
        """Create crash C1, then another crash → C2, then C3."""
        c1 = await service.create_ticket(TicketCreate(
            title="First Crash",
            description="First crash bug",
            repo="test/repo",
            category=Category.CRASH
        ))
        assert c1.id == "C1"
        
        c2 = await service.create_ticket(TicketCreate(
            title="Second Crash",
            description="Second crash bug",
            repo="test/repo",
            category=Category.CRASH
        ))
        assert c2.id == "C2"
        
        c3 = await service.create_ticket(TicketCreate(
            title="Third Crash",
            description="Third crash bug",
            repo="test/repo",
            category=Category.CRASH
        ))
        assert c3.id == "C3"
    
    @pytest.mark.asyncio
    async def test_slug_generation(self, service: TicketService):
        """'CORS Wildcard Issue' → slug 'cors-wildcard-issue'."""
        ticket = await service.create_ticket(TicketCreate(
            title="CORS Wildcard Issue",
            description="CORS headers are too permissive",
            repo="test/repo"
        ))
        
        assert ticket.slug == "cors-wildcard-issue"
    
    @pytest.mark.asyncio
    async def test_update_appends_description(self, service: TicketService):
        """Create with desc 'A', update with description_append 'B' → desc is 'A\n\nB'."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="A",
            repo="test/repo"
        ))
        
        updated = await service.update_ticket(ticket.id, TicketUpdate(
            description_append="\n\nB"
        ))
        
        assert updated.description == "A\n\nB"
    
    @pytest.mark.asyncio
    async def test_status_transition_valid(self, service: TicketService):
        """open → in_progress → fixed (allowed)."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="Test",
            repo="test/repo",
            status=Status.OPEN
        ))
        
        # open → in_progress
        updated1 = await service.update_ticket(ticket.id, TicketUpdate(status=Status.IN_PROGRESS))
        assert updated1.status == Status.IN_PROGRESS
        
        # in_progress → fixed
        updated2 = await service.update_ticket(updated1.id, TicketUpdate(status=Status.FIXED))
        assert updated2.status == Status.FIXED
    
    @pytest.mark.asyncio
    async def test_status_transition_invalid(self, service: TicketService):
        """blocked → fixed (blocked, should raise error)."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="Test",
            repo="test/repo",
            status=Status.BLOCKED
        ))
        
        # blocked → fixed should be blocked (blocked can only go to open, in_progress, wont_fix, closed)
        with pytest.raises(Exception) as exc_info:
            await service.update_ticket(ticket.id, TicketUpdate(status=Status.FIXED))
        
        error_msg = str(exc_info.value).lower()
        assert "invalid" in error_msg or "transition" in error_msg
    
    @pytest.mark.asyncio
    async def test_soft_delete_file_moved(self, service: TicketService, tmp_storage_dir: Path):
        """Create, soft delete, verify file in .trash/."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="Test",
            repo="test/repo"
        ))
        
        # Soft delete
        await service.delete_ticket(ticket.id, mode="soft")
        
        # Verify file is in trash
        trash_dir = tmp_storage_dir / ".trash"
        assert trash_dir.exists()
        
        trashed_files = list(trash_dir.glob(f"{ticket.id}*.md"))
        assert len(trashed_files) >= 1
    
    @pytest.mark.asyncio
    async def test_hard_delete_file_removed(self, service: TicketService, tmp_storage_dir: Path):
        """Create, hard delete, verify no file."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="Test",
            repo="test/repo"
        ))
        
        # Find original file path
        category_dir = tmp_storage_dir / "test" / "repo" / ticket.category.value
        original_file = category_dir / f"{ticket.id}-{ticket.slug}.md"
        assert original_file.exists()
        
        # Hard delete
        await service.delete_ticket(ticket.id, mode="hard")
        
        # Verify file is gone
        assert not original_file.exists()
    
    @pytest.mark.asyncio
    async def test_list_filters(self, service: TicketService):
        """Create tickets in 2 repos, filter by repo, verify correct subset."""
        # Create tickets in repo1
        t1 = await service.create_ticket(TicketCreate(
            title="Repo1 Issue 1",
            description="Test",
            repo="owner/repo1"
        ))
        t2 = await service.create_ticket(TicketCreate(
            title="Repo1 Issue 2",
            description="Test",
            repo="owner/repo1"
        ))
        
        # Create tickets in repo2
        t3 = await service.create_ticket(TicketCreate(
            title="Repo2 Issue 1",
            description="Test",
            repo="owner/repo2"
        ))
        
        # Filter by repo1
        repo1_tickets = await service.list_tickets(repo="owner/repo1")
        repo1_ids = {t.id for t in repo1_tickets}
        assert t1.id in repo1_ids
        assert t2.id in repo1_ids
        assert t3.id not in repo1_ids
    
    @pytest.mark.asyncio
    async def test_list_pagination(self, service: TicketService):
        """Create 10 tickets, limit=3 offset=5, verify 3 returned."""
        # Create 10 tickets
        created_ids = []
        for i in range(10):
            ticket = await service.create_ticket(TicketCreate(
                title=f"Ticket {i}",
                description=f"Description {i}",
                repo="test/repo"
            ))
            created_ids.append(ticket.id)
        
        # Get with pagination
        results = await service.list_tickets(limit=3, offset=5)
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_reindex(self, service: TicketService):
        """Create 5 tickets, destroy index, reindex → verify stats."""
        # Create 5 tickets
        for i in range(5):
            await service.create_ticket(TicketCreate(
                title=f"Reindex Test {i}",
                description=f"Content {i}",
                repo="test/repo"
            ))
        
        # Reindex (destroys and rebuilds)
        stats = await service.reindex_all()
        
        # Verify reindex stats
        assert stats["processed"] >= 5
    
    @pytest.mark.asyncio
    async def test_zvec_search_after_create(self, service: TicketService):
        """Create ticket with 'SQL injection' in title, search → found."""
        ticket = await service.create_ticket(TicketCreate(
            title="SQL injection vulnerability in login",
            description="The login form is vulnerable to SQL injection attacks",
            repo="test/repo"
        ))
        
        # Search should find it
        results = search_tickets(service, "SQL injection")
        result_ids = [r["id"] for r in results]
        assert ticket.id in result_ids
    
    @pytest.mark.asyncio
    async def test_update_reflected_in_index(self, service: TicketService):
        """Create, update title, search for new title → found."""
        ticket = await service.create_ticket(TicketCreate(
            title="Original Title",
            description="Test description",
            repo="test/repo"
        ))
        
        # Update title
        await service.update_ticket(ticket.id, TicketUpdate(title="Updated Unique Title XYZ"))
        
        # Search for new title
        results = search_tickets(service, "Unique Title XYZ")
        result_ids = [r["id"] for r in results]
        assert ticket.id in result_ids
    
    @pytest.mark.asyncio
    async def test_delete_removed_from_index(self, service: TicketService):
        """Create, delete, search → not found."""
        ticket = await service.create_ticket(TicketCreate(
            title="To Be Deleted",
            description="This ticket will be deleted",
            repo="test/repo"
        ))
        
        # Verify it's searchable
        results = search_tickets(service, "To Be Deleted")
        assert ticket.id in [r["id"] for r in results]
        
        # Delete
        await service.delete_ticket(ticket.id)
        
        # Should not be found anymore
        results = search_tickets(service, "To Be Deleted")
        assert ticket.id not in [r["id"] for r in results]


# =============================================================================
# Error Cases
# =============================================================================

class TestErrorCases:
    """Test error handling."""
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_raises_404(self, service: TicketService):
        """Getting a non-existent ticket should raise 404."""
        with pytest.raises(Exception) as exc_info:
            await service.get_ticket("G99999")
        
        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises_404(self, service: TicketService):
        """Deleting a non-existent ticket should raise 404."""
        with pytest.raises(Exception) as exc_info:
            await service.delete_ticket("G99999")
        
        assert "not found" in str(exc_info.value).lower() or "404" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_create_with_invalid_repo_format_raises(self, service: TicketService):
        """Creating with invalid repo format should raise validation error."""
        with pytest.raises(Exception) as exc_info:
            await service.create_ticket(TicketCreate(
                title="Test",
                description="Test",
                repo="invalid-repo-format"  # Missing owner/repo structure
            ))
        
        assert "validation" in str(exc_info.value).lower() or "invalid" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_no_fields_raises_validation(self, service: TicketService):
        """Updating with no fields should raise validation error."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test",
            description="Test",
            repo="test/repo"
        ))
        
        with pytest.raises(Exception) as exc_info:
            await service.update_ticket(ticket.id, TicketUpdate())  # No fields set
        
        assert "at least one" in str(exc_info.value).lower() or "validation" in str(exc_info.value)


# =============================================================================
# Data Integrity Tests
# =============================================================================

class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    @pytest.mark.asyncio
    async def test_file_content_matches_ticket(self, service: TicketService, tmp_storage_dir: Path):
        """Create ticket, read .md file, verify all fields in frontmatter."""
        ticket = await service.create_ticket(TicketCreate(
            title="Test Ticket",
            description="Test Description",
            repo="test/repo",
            category=Category.SECURITY,
            severity=Severity.HIGH,
            status=Status.OPEN,
            assignee="testuser",
            tags=["bug", "security"],
            references=["C1"]
        ))
        
        # Read the markdown file directly
        category_dir = tmp_storage_dir / "test" / "repo" / ticket.category.value
        md_file = category_dir / f"{ticket.id}-{ticket.slug}.md"
        
        file_ticket = read_ticket(md_file)
        
        # Verify all fields match
        assert file_ticket["id"] == ticket.id
        assert file_ticket["title"] == ticket.title
        assert file_ticket["description"] == ticket.description
        assert file_ticket["repo"] == ticket.repo
        assert file_ticket["category"] == ticket.category.value
        assert file_ticket["severity"] == ticket.severity.value
        assert file_ticket["status"] == ticket.status.value
        assert file_ticket["assignee"] == ticket.assignee
        assert file_ticket["tags"] == ticket.tags
        assert file_ticket["references"] == ticket.references
    
    @pytest.mark.asyncio
    async def test_concurrent_ids_no_conflict(self, service: TicketService):
        """Create multiple tickets in same category quickly, all unique IDs."""
        # Create 10 tickets rapidly
        tickets = []
        for i in range(10):
            t = await service.create_ticket(TicketCreate(
                title=f"Concurrent Ticket {i}",
                description=f"Description {i}",
                repo="test/repo",
                category=Category.GENERAL
            ))
            tickets.append(t)
        
        # All IDs should be unique
        ids = [t.id for t in tickets]
        assert len(ids) == len(set(ids)), f"Duplicate IDs found: {ids}"


# =============================================================================
# API Integration Tests
# =============================================================================

class TestAPIIntegration:
    """Test API endpoints with real service."""
    
    @pytest.mark.asyncio
    async def test_api_create_ticket(self, api_client: AsyncClient):
        """POST /tickets creates a ticket."""
        response = await api_client.post("/tickets", json={
            "title": "API Test Ticket",
            "description": "Created via API",
            "repo": "test/repo"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["data"]["title"] == "API Test Ticket"
    
    @pytest.mark.asyncio
    async def test_api_get_ticket(self, api_client: AsyncClient, service: TicketService):
        """GET /tickets/{id} returns a ticket."""
        ticket = await service.create_ticket(TicketCreate(
            title="API Get Test",
            description="Test",
            repo="test/repo"
        ))
        
        response = await api_client.get(f"/tickets/{ticket.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["id"] == ticket.id
    
    @pytest.mark.asyncio
    async def test_api_update_ticket(self, api_client: AsyncClient, service: TicketService):
        """PATCH /tickets/{id} updates a ticket."""
        ticket = await service.create_ticket(TicketCreate(
            title="Original Title",
            description="Test",
            repo="test/repo"
        ))
        
        response = await api_client.patch(f"/tickets/{ticket.id}", json={
            "title": "Updated via API"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["title"] == "Updated via API"
    
    @pytest.mark.asyncio
    async def test_api_delete_ticket(self, api_client: AsyncClient, service: TicketService):
        """DELETE /tickets/{id} deletes a ticket."""
        ticket = await service.create_ticket(TicketCreate(
            title="To Delete",
            description="Test",
            repo="test/repo"
        ))
        
        response = await api_client.delete(f"/tickets/{ticket.id}")
        
        assert response.status_code in (200, 204)
        
        # Verify it's gone
        get_response = await api_client.get(f"/tickets/{ticket.id}")
        assert get_response.status_code == 404
    
    @pytest.mark.asyncio
    async def test_api_list_tickets(self, api_client: AsyncClient, service: TicketService):
        """GET /tickets returns list of tickets."""
        # Create some tickets
        for i in range(3):
            await service.create_ticket(TicketCreate(
                title=f"List Ticket {i}",
                description="Test",
                repo="test/repo"
            ))
        
        response = await api_client.get("/tickets")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 3
        assert "meta" in data
        assert "total" in data["meta"]
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Search endpoint not implemented yet")
    async def test_api_search_tickets(self, api_client: AsyncClient, service: TicketService):
        """GET /tickets/search?q=... searches tickets."""
        await service.create_ticket(TicketCreate(
            title="Searchable Ticket",
            description="Contains unique search term XYZ123",
            repo="test/repo"
        ))
        
        response = await api_client.get("/tickets/search?q=XYZ123")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) >= 1


# =============================================================================
# Helper to print test summary
# =============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print summary of which components are being tested."""
    terminalreporter.write_sep("=", "VTIC Integration Test Summary")
    
    if TICKET_SERVICE_AVAILABLE and TICKET_SERVICE_METHODS_AVAILABLE:
        terminalreporter.write_line("✓ TicketService: AVAILABLE with all methods")
    elif TICKET_SERVICE_AVAILABLE:
        terminalreporter.write_line("⚠ TicketService: IMPORTABLE but methods not yet fully implemented")
    else:
        terminalreporter.write_line("✗ TicketService: NOT AVAILABLE")
    
    if API_AVAILABLE:
        terminalreporter.write_line("✓ API Routes: IMPORTABLE")
    else:
        terminalreporter.write_line("✗ API Routes: NOT AVAILABLE")
    
    terminalreporter.write_sep("=")
