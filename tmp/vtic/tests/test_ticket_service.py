"""Tests for the TicketService orchestrator.

These tests verify that the TicketService correctly coordinates between
the markdown file storage and Zvec index operations.
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from vtic.models.config import Config
from vtic.models.ticket import TicketCreate, TicketUpdate, TicketSummary
from vtic.models.enums import Category, Severity, Status
from vtic.errors import NotFoundError, ValidationError
from vtic.ticket import TicketService


@pytest.fixture
def temp_service(tmp_path: Path) -> TicketService:
    """Create a TicketService with a temporary config for testing."""
    # Create a test config pointing to tmp_path
    config = Config()
    config.storage.dir = tmp_path / "tickets"
    
    # Create service (this initializes the Zvec collection)
    service = TicketService(config)
    
    yield service
    
    # Cleanup: destroy Zvec index after test
    from vtic.index.client import destroy_index
    destroy_index(config.storage.dir)


# Helper to run async tests
def run_async(coro):
    """Helper to run async tests in sync test functions."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    
    if loop and loop.is_running():
        # We're already in an async context, need to create task
        return asyncio.ensure_future(coro)
    else:
        # No running loop, create one
        return asyncio.run(coro)


class TestCreateTicket:
    """Tests for TicketService.create_ticket()."""
    
    @pytest.mark.asyncio
    async def test_create_ticket_roundtrip(self, temp_service: TicketService) -> None:
        """Test create → get roundtrip ensures file exists and index has it."""
        # Create a ticket
        data = TicketCreate(
            title="Test Ticket",
            description="A test ticket description",
            repo="owner/repo",
            category=Category.CRASH,
            severity=Severity.HIGH,
        )
        
        created = await temp_service.create_ticket(data)
        
        # Verify we can get it back
        fetched = await temp_service.get_ticket(created.id)
        
        assert fetched.id == created.id
        assert fetched.title == "Test Ticket"
        assert fetched.description == "A test ticket description"
        assert fetched.repo == "owner/repo"
        assert fetched.category == Category.CRASH
        assert fetched.severity == Severity.HIGH
        assert fetched.status == Status.OPEN  # Default
    
    @pytest.mark.asyncio
    async def test_create_ticket_generates_correct_id_prefix(self, temp_service: TicketService) -> None:
        """Test that category=crash generates C1 prefix."""
        data = TicketCreate(
            title="Crash Ticket",
            description="A crash ticket",
            repo="owner/repo",
            category=Category.CRASH,
        )
        
        created = await temp_service.create_ticket(data)
        
        assert created.id.startswith("C")
        assert created.id == "C1"
    
    @pytest.mark.asyncio
    async def test_create_ticket_generates_slug(self, temp_service: TicketService) -> None:
        """Test that title is converted to slug."""
        data = TicketCreate(
            title="My Test Ticket Title",
            description="Description here",
            repo="owner/repo",
        )
        
        created = await temp_service.create_ticket(data)
        
        assert created.slug == "my-test-ticket-title"
    
    @pytest.mark.asyncio
    async def test_create_ticket_auto_timestamps(self, temp_service: TicketService) -> None:
        """Test that created and updated timestamps are auto-filled."""
        before = datetime.now(timezone.utc)
        
        data = TicketCreate(
            title="Timestamp Test",
            description="Testing timestamps",
            repo="owner/repo",
        )
        
        created = await temp_service.create_ticket(data)
        
        after = datetime.now(timezone.utc)
        
        assert created.created is not None
        assert created.updated is not None
        assert before <= created.created <= after
        assert before <= created.updated <= after
    
    @pytest.mark.asyncio
    async def test_create_ticket_sequence_increment(self, temp_service: TicketService) -> None:
        """Test that creating 2 crash tickets generates C1, C2."""
        data1 = TicketCreate(
            title="First Crash",
            description="First crash ticket",
            repo="owner/repo",
            category=Category.CRASH,
        )
        data2 = TicketCreate(
            title="Second Crash",
            description="Second crash ticket",
            repo="owner/repo",
            category=Category.CRASH,
        )
        
        created1 = await temp_service.create_ticket(data1)
        created2 = await temp_service.create_ticket(data2)
        
        assert created1.id == "C1"
        assert created2.id == "C2"


class TestGetTicket:
    """Tests for TicketService.get_ticket()."""
    
    @pytest.mark.asyncio
    async def test_get_ticket_returns_correct_fields(self, temp_service: TicketService) -> None:
        """Test that get_ticket returns all correct fields."""
        # Create a ticket with all fields
        data = TicketCreate(
            title="Full Ticket",
            description="Full description",
            repo="owner/repo",
            category=Category.SECURITY,
            severity=Severity.CRITICAL,
            status=Status.IN_PROGRESS,
            assignee="testuser",
            tags=["tag1", "tag2"],
            references=["C1"],
        )
        
        created = await temp_service.create_ticket(data)
        
        # Get it back
        fetched = await temp_service.get_ticket(created.id)
        
        assert fetched.id == created.id
        assert fetched.title == "Full Ticket"
        assert fetched.description == "Full description"
        assert fetched.repo == "owner/repo"
        assert fetched.category == Category.SECURITY
        assert fetched.severity == Severity.CRITICAL
        assert fetched.status == Status.IN_PROGRESS
        assert fetched.assignee == "testuser"
        assert fetched.tags == ["tag1", "tag2"]
    
    @pytest.mark.asyncio
    async def test_get_ticket_not_found_raises(self, temp_service: TicketService) -> None:
        """Test that getting a non-existent ticket raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            await temp_service.get_ticket("X999")
        
        assert "X999" in str(exc_info.value)
        assert "not found" in str(exc_info.value).lower()


class TestUpdateTicket:
    """Tests for TicketService.update_ticket()."""
    
    @pytest.mark.asyncio
    async def test_update_ticket_updates_file_and_index(self, temp_service: TicketService) -> None:
        """Test that update modifies both file and index."""
        # Create a ticket
        data = TicketCreate(
            title="Original Title",
            description="Original description",
            repo="owner/repo",
            status=Status.OPEN,
        )
        
        created = await temp_service.create_ticket(data)
        
        # Update it
        update_data = TicketUpdate(
            title="Updated Title",
            status=Status.IN_PROGRESS,
        )
        
        updated = await temp_service.update_ticket(created.id, update_data)
        
        assert updated.title == "Updated Title"
        assert updated.status == Status.IN_PROGRESS
        
        # Verify by fetching again
        fetched = await temp_service.get_ticket(created.id)
        assert fetched.title == "Updated Title"
        assert fetched.status == Status.IN_PROGRESS
    
    @pytest.mark.asyncio
    async def test_update_ticket_description_append(self, temp_service: TicketService) -> None:
        """Test that description_append appends content."""
        # Create a ticket
        data = TicketCreate(
            title="Test Ticket",
            description="Original description",
            repo="owner/repo",
        )
        
        created = await temp_service.create_ticket(data)
        
        # Append to description
        update_data = TicketUpdate(
            description_append="\n\n## Additional Info\nMore details here.",
        )
        
        updated = await temp_service.update_ticket(created.id, update_data)
        
        assert "Original description" in updated.description
        assert "## Additional Info" in updated.description
        assert "More details here." in updated.description
    
    @pytest.mark.asyncio
    async def test_update_ticket_invalid_status_transition_raises(self, temp_service: TicketService) -> None:
        """Test that invalid status transitions raise ValidationError."""
        # Create a blocked ticket
        data2 = TicketCreate(
            title="Blocked Ticket",
            description="Description",
            repo="owner/repo",
            status=Status.BLOCKED,
        )
        blocked = await temp_service.create_ticket(data2)
        
        # Blocked cannot go to FIXED directly
        update_data = TicketUpdate(status=Status.FIXED)
        
        with pytest.raises(ValidationError) as exc_info:
            await temp_service.update_ticket(blocked.id, update_data)
        
        assert "Invalid status transition" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_update_ticket_status_fixed_sets_updated(self, temp_service: TicketService) -> None:
        """Test that updating status to fixed updates the timestamp."""
        # Create a ticket
        data = TicketCreate(
            title="Test Ticket",
            description="Description",
            repo="owner/repo",
            status=Status.IN_PROGRESS,
        )
        
        created = await temp_service.create_ticket(data)
        original_updated = created.updated
        
        # Small delay to ensure timestamp changes
        import time
        time.sleep(0.01)
        
        # Update to fixed
        update_data = TicketUpdate(status=Status.FIXED)
        updated = await temp_service.update_ticket(created.id, update_data)
        
        assert updated.status == Status.FIXED
        assert updated.updated > original_updated


class TestDeleteTicket:
    """Tests for TicketService.delete_ticket()."""
    
    @pytest.mark.asyncio
    async def test_delete_ticket_soft(self, temp_service: TicketService) -> None:
        """Test soft delete moves file to .trash/."""
        # Create a ticket
        data = TicketCreate(
            title="Delete Me",
            description="To be deleted",
            repo="owner/repo",
        )
        
        created = await temp_service.create_ticket(data)
        
        # Soft delete
        await temp_service.delete_ticket(created.id, mode="soft")
        
        # Verify ticket is gone from index
        with pytest.raises(NotFoundError):
            await temp_service.get_ticket(created.id)
        
        # Verify file is in trash
        trash_dir = temp_service.base_dir / ".trash"
        assert trash_dir.exists()
        trash_files = list(trash_dir.glob(f"{created.id}-*.md"))
        assert len(trash_files) == 1
    
    @pytest.mark.asyncio
    async def test_delete_ticket_hard(self, temp_service: TicketService) -> None:
        """Test hard delete removes file permanently."""
        # Create a ticket
        data = TicketCreate(
            title="Delete Me",
            description="To be deleted",
            repo="owner/repo",
        )
        
        created = await temp_service.create_ticket(data)
        
        # Find the original file path
        from vtic.store import paths as store_paths
        original_paths = store_paths.resolve_path(temp_service.base_dir, created.id)
        assert len(original_paths) == 1
        original_path = original_paths[0]
        
        # Hard delete
        await temp_service.delete_ticket(created.id, mode="hard")
        
        # Verify ticket is gone from index
        with pytest.raises(NotFoundError):
            await temp_service.get_ticket(created.id)
        
        # Verify file is gone
        assert not original_path.exists()
    
    @pytest.mark.asyncio
    async def test_delete_ticket_not_found_raises(self, temp_service: TicketService) -> None:
        """Test that deleting a non-existent ticket raises NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            await temp_service.delete_ticket("X999")
        
        assert "X999" in str(exc_info.value)


class TestListTickets:
    """Tests for TicketService.list_tickets()."""
    
    @pytest.mark.asyncio
    async def test_list_tickets_empty_returns_empty(self, temp_service: TicketService) -> None:
        """Test that listing with no tickets returns empty list."""
        results = await temp_service.list_tickets()
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_list_tickets_with_filters(self, temp_service: TicketService) -> None:
        """Test listing with repo and category filters."""
        # Create tickets in different repos and categories
        tickets = [
            TicketCreate(title="Repo1 Crash", description="Desc", repo="owner/repo1", category=Category.CRASH),
            TicketCreate(title="Repo1 Security", description="Desc", repo="owner/repo1", category=Category.SECURITY),
            TicketCreate(title="Repo2 Crash", description="Desc", repo="owner/repo2", category=Category.CRASH),
        ]
        
        for t in tickets:
            await temp_service.create_ticket(t)
        
        # Filter by repo
        repo1_results = await temp_service.list_tickets(repo="owner/repo1")
        assert len(repo1_results) == 2
        
        # Filter by category
        crash_results = await temp_service.list_tickets(category="crash")
        assert len(crash_results) == 2
        
        # Filter by both
        specific_results = await temp_service.list_tickets(repo="owner/repo1", category="crash")
        assert len(specific_results) == 1
        assert specific_results[0].title == "Repo1 Crash"
    
    @pytest.mark.asyncio
    async def test_list_tickets_pagination(self, temp_service: TicketService) -> None:
        """Test limit and offset pagination."""
        # Create several tickets
        for i in range(5):
            data = TicketCreate(
                title=f"Ticket {i}",
                description=f"Description {i}",
                repo="owner/repo",
            )
            await temp_service.create_ticket(data)
        
        # Test limit
        limited = await temp_service.list_tickets(limit=2)
        assert len(limited) == 2
        
        # Test offset
        offset = await temp_service.list_tickets(limit=2, offset=2)
        assert len(offset) == 2
        
        # Verify different results
        limited_ids = {t.id for t in limited}
        offset_ids = {t.id for t in offset}
        assert limited_ids.isdisjoint(offset_ids)


class TestReindexAll:
    """Tests for TicketService.reindex_all()."""
    
    @pytest.mark.asyncio
    async def test_reindex_all(self, temp_service: TicketService) -> None:
        """Test reindexing recreates index from markdown files."""
        # Create some tickets
        for i in range(3):
            data = TicketCreate(
                title=f"Ticket {i}",
                description=f"Description {i}",
                repo="owner/repo",
            )
            await temp_service.create_ticket(data)
        
        # Reindex
        result = await temp_service.reindex_all()
        
        # Verify result structure
        assert "processed" in result
        assert "skipped" in result
        assert "failed" in result
        assert "duration_ms" in result
        assert "errors" in result
        
        # Should have processed 3 tickets
        assert result["processed"] == 3
        assert result["failed"] == 0
        
        # Verify tickets are still accessible
        tickets = await temp_service.list_tickets()
        assert len(tickets) == 3


class TestValidation:
    """Tests for input validation."""
    
    @pytest.mark.asyncio
    async def test_create_ticket_validates_required_fields(self, temp_service: TicketService) -> None:
        """Test that creating a ticket without required fields fails."""
        # Empty title
        with pytest.raises(ValueError):
            data = TicketCreate(
                title="",  # Empty title
                description="Description",
                repo="owner/repo",
            )
            await temp_service.create_ticket(data)
        
        # Empty description
        with pytest.raises(ValueError):
            data = TicketCreate(
                title="Title",
                description="",  # Empty description
                repo="owner/repo",
            )
            await temp_service.create_ticket(data)


class TestDifferentCategoryPrefixes:
    """Tests for different category ID prefixes."""
    
    @pytest.mark.asyncio
    async def test_category_prefixes(self, temp_service: TicketService) -> None:
        """Test that different categories get correct prefixes."""
        test_cases = [
            (Category.CRASH, "C"),
            (Category.HOTFIX, "H"),
            (Category.FEATURE, "F"),
            (Category.SECURITY, "S"),
            (Category.GENERAL, "G"),
        ]
        
        for category, expected_prefix in test_cases:
            data = TicketCreate(
                title=f"{category.value} ticket",
                description="Test",
                repo="owner/repo",
                category=category,
            )
            
            created = await temp_service.create_ticket(data)
            
            assert created.id.startswith(expected_prefix), f"Category {category.value} should have prefix {expected_prefix}"
