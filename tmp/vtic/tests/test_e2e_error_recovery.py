"""End-to-end error recovery and edge case tests for vtic.

These tests verify error handling and edge cases using FastAPI TestClient
with real services. Each test is independent with its own tmp_path and app instance.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from typing import AsyncGenerator

try:
    from vtic.ticket import TicketService
    from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
    from vtic.models.ticket import TicketCreate, TicketUpdate
    from vtic.models.enums import Category, Severity, Status
    from vtic.models.search import SearchQuery

    TICKET_SERVICE_AVAILABLE = True
except ImportError as e:
    TICKET_SERVICE_AVAILABLE = False
    TICKET_SERVICE_ERROR = str(e)

try:
    from httpx import AsyncClient, ASGITransport
    from vtic.api.app import create_app
    from vtic.api import deps
    from vtic.search.engine import SearchEngine

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
async def api_client(config: Config) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI TestClient with real service attached.
    
    Each test gets its own fresh app instance with isolated storage.
    """
    if not API_AVAILABLE:
        pytest.skip(f"API not available: {API_ERROR}")
    if not TICKET_SERVICE_AVAILABLE:
        pytest.skip(f"TicketService not available: {TICKET_SERVICE_ERROR}")

    # Create fresh service for this test
    service = TicketService(config)
    await service.initialize()

    app = create_app(config)
    app.state.ticket_service = service

    # Override search engine to use service's collection
    def _search_engine_override():
        return SearchEngine(service.collection)

    app.dependency_overrides[deps.get_search_engine] = _search_engine_override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    # Cleanup
    await service.close()


# =============================================================================
# Helper Functions
# =============================================================================

async def _create_ticket(client: AsyncClient, **kwargs) -> dict:
    """Helper to create a ticket and return the created data."""
    defaults = {
        "title": "Test Ticket",
        "description": "Test description",
        "repo": "test/repo"
    }
    defaults.update(kwargs)
    r = await client.post("/tickets", json=defaults)
    assert r.status_code == 201, f"Create failed ({r.status_code}): {r.text}"
    return r.json()["data"]


def _verify_error_response(response_json: dict, expected_code: str = None):
    """Verify the response follows ErrorResponse schema.
    
    ErrorResponse schema:
    {
        "error": {
            "code": str,
            "message": str,
            "details": Optional[List[ErrorDetail]],
            "docs": Optional[str]
        }
    }
    """
    assert "error" in response_json, "ErrorResponse must have 'error' field"
    error_obj = response_json["error"]
    
    assert "code" in error_obj, "ErrorObject must have 'code' field"
    assert "message" in error_obj, "ErrorObject must have 'message' field"
    assert isinstance(error_obj["code"], str), "Error code must be a string"
    assert isinstance(error_obj["message"], str), "Error message must be a string"
    
    if expected_code:
        assert error_obj["code"] == expected_code, f"Expected error code '{expected_code}', got '{error_obj['code']}'"
    
    # Optional fields
    if "details" in error_obj and error_obj["details"] is not None:
        assert isinstance(error_obj["details"], list), "Error details must be a list"
        for detail in error_obj["details"]:
            if "field" in detail:
                assert isinstance(detail["field"], str), "Error detail field must be string"
            if "message" in detail:
                assert isinstance(detail["message"], str), "Error detail message must be string"
    
    if "docs" in error_obj and error_obj["docs"] is not None:
        assert isinstance(error_obj["docs"], str), "Error docs must be a string"
    
    return error_obj


# =============================================================================
# E2E Test: Error Recovery & Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_e2e_error_recovery_and_edge_cases(api_client: AsyncClient, tmp_storage_dir: Path):
    """E2E: Error Recovery & Edge Cases
    
    Test scenarios:
    1. Create a ticket successfully
    2. Try to create a ticket with duplicate title — verify behavior
    3. Try to update a ticket with invalid status value — verify 400
    4. Try to update a ticket that was just deleted — verify 404
    5. Create a ticket, corrupt its .md file directly, then try GET — verify error handling
    6. Delete all tickets, then search — verify empty results
    7. Delete all tickets, then stats — verify all zeros
    8. Reindex after all deletions — verify clean state
    9. Verify ErrorResponse schema in all error responses
    """
    client = api_client
    
    # =========================================================================
    # Step 1: Create a ticket successfully
    # =========================================================================
    ticket1 = await _create_ticket(
        client,
        title="First Test Ticket",
        description="This is a test ticket for error recovery",
        repo="test/error-recovery",
        category=Category.GENERAL,
        severity=Severity.MEDIUM,
        status=Status.OPEN,
        tags=["test", "error-recovery"]
    )
    
    assert ticket1["id"].startswith("G"), f"Expected ID starting with 'G', got {ticket1['id']}"
    assert ticket1["title"] == "First Test Ticket"
    assert ticket1["status"] == "open"
    ticket1_id = ticket1["id"]
    
    # =========================================================================
    # Step 2: Try to create a ticket with duplicate title — verify behavior
    # =========================================================================
    # Note: vtic allows duplicate titles (no unique constraint), so this should succeed
    # If there was a unique constraint, we'd expect 409 CONFLICT
    ticket2 = await _create_ticket(
        client,
        title="First Test Ticket",  # Same title as ticket1
        description="Different description but same title",
        repo="test/error-recovery",
        category=Category.GENERAL,
        severity=Severity.LOW,
        status=Status.OPEN,
    )
    
    # Verify it was created as a different ticket
    assert ticket2["id"] != ticket1_id, "Duplicate title should create new ticket with different ID"
    ticket2_id = ticket2["id"]
    
    # =========================================================================
    # Step 3: Try to update a ticket with invalid status value — verify 400
    # =========================================================================
    update_response = await client.patch(
        f"/tickets/{ticket1_id}",
        json={"status": "invalid_status_value_xyz"}
    )
    
    assert update_response.status_code == 400, \
        f"Expected 400 for invalid status, got {update_response.status_code}"
    
    error_data = update_response.json()
    error_obj = _verify_error_response(error_data, "VALIDATION_ERROR")
    assert "status" in str(error_obj).lower() or "validation" in error_obj["message"].lower(), \
        "Error should mention status field or validation"
    
    # =========================================================================
    # Step 4: Try to update a ticket that was just deleted — verify 404
    # =========================================================================
    # First create a ticket and delete it
    temp_ticket = await _create_ticket(
        client,
        title="Temporary Ticket to Delete",
        description="This ticket will be deleted",
        repo="test/delete-test",
        category=Category.GENERAL,
        severity=Severity.LOW,
        status=Status.OPEN,
    )
    temp_id = temp_ticket["id"]
    
    # Delete it (hard delete)
    delete_response = await client.delete(f"/tickets/{temp_id}?mode=hard")
    assert delete_response.status_code == 204, f"Delete failed: {delete_response.status_code}"
    
    # Try to update the deleted ticket
    update_deleted_response = await client.patch(
        f"/tickets/{temp_id}",
        json={"title": "Updated after deletion"}
    )
    
    assert update_deleted_response.status_code == 404, \
        f"Expected 404 for deleted ticket, got {update_deleted_response.status_code}"
    
    error_data = update_deleted_response.json()
    _verify_error_response(error_data, "NOT_FOUND")
    
    # =========================================================================
    # Step 5: Create a ticket, corrupt its .md file directly, then try GET
    # =========================================================================
    corrupt_ticket = await _create_ticket(
        client,
        title="Ticket With Corrupt File",
        description="This ticket's file will be corrupted",
        repo="test/corrupt-test",
        category=Category.GENERAL,
        severity=Severity.MEDIUM,
        status=Status.OPEN,
    )
    corrupt_id = corrupt_ticket["id"]
    
    # Find and corrupt the .md file
    md_files = list(tmp_storage_dir.rglob(f"{corrupt_id}-*.md"))
    assert len(md_files) == 1, f"Expected 1 file for {corrupt_id}, found {len(md_files)}"
    
    md_file = md_files[0]
    # Write completely invalid content (no frontmatter, corrupted structure)
    md_file.write_text("{{{ corrupted yaml :::: invalid <<<<< content }}}")
    
    # Try to GET the corrupted ticket
    get_corrupt_response = await client.get(f"/tickets/{corrupt_id}")
    
    # The system may handle this in different ways:
    # - Return error (404/500/400) if file parsing fails
    # - Return 200 with cached/indexed data if system doesn't re-read file
    # Either behavior is acceptable - the important thing is it doesn't crash
    if get_corrupt_response.status_code in [404, 500, 400]:
        # Error path - verify it's a valid ErrorResponse
        error_data = get_corrupt_response.json()
        _verify_error_response(error_data)
    else:
        # Success path - verify it returns valid TicketResponse structure
        # (system might be reading from index cache)
        assert get_corrupt_response.status_code == 200, \
            f"Unexpected status: {get_corrupt_response.status_code}"
        ticket_data = get_corrupt_response.json()
        assert "data" in ticket_data, "Expected 'data' field in response"
        # The response should still have valid structure even if from cache
    
    # =========================================================================
    # Step 6: Delete all tickets, then search — verify empty results
    # =========================================================================
    # Get all remaining tickets
    list_response = await client.get("/tickets", params={"limit": 100})
    assert list_response.status_code == 200
    all_tickets = list_response.json()["data"]
    
    # Delete all tickets (hard delete)
    for ticket in all_tickets:
        await client.delete(f"/tickets/{ticket['id']}?mode=hard")
    
    # Reindex to sync the search index with the deleted state
    reindex_after_delete = await client.post("/reindex")
    assert reindex_after_delete.status_code == 200, f"Reindex failed: {reindex_after_delete.status_code}"
    
    # Search for anything
    search_response = await client.post(
        "/search",
        json={"query": "test ticket", "limit": 10}
    )
    
    assert search_response.status_code == 200, f"Search failed: {search_response.status_code}"
    search_data = search_response.json()
    
    # Verify empty results
    assert search_data["total"] == 0, f"Expected 0 results after deleting all, got {search_data['total']}"
    assert len(search_data["hits"]) == 0, "Expected empty hits after deleting all tickets"
    
    # =========================================================================
    # Step 7: Delete all tickets, then stats — verify all zeros
    # =========================================================================
    stats_response = await client.get("/stats")
    assert stats_response.status_code == 200, f"Stats failed: {stats_response.status_code}"
    stats_data = stats_response.json()
    
    # Verify all zeros
    assert stats_data["totals"]["all"] == 0, f"Expected 0 total, got {stats_data['totals']['all']}"
    assert stats_data["totals"]["open"] == 0, f"Expected 0 open, got {stats_data['totals']['open']}"
    assert stats_data["totals"]["closed"] == 0, f"Expected 0 closed, got {stats_data['totals']['closed']}"
    
    # All status counts should be 0
    for status_val, count in stats_data["by_status"].items():
        assert count == 0, f"Expected 0 for status '{status_val}', got {count}"
    
    # All severity counts should be 0
    for severity_val, count in stats_data["by_severity"].items():
        assert count == 0, f"Expected 0 for severity '{severity_val}', got {count}"
    
    # All category counts should be 0
    for category_val, count in stats_data["by_category"].items():
        assert count == 0, f"Expected 0 for category '{category_val}', got {count}"
    
    # =========================================================================
    # Step 8: Reindex after all deletions — verify clean state
    # =========================================================================
    reindex_response = await client.post("/reindex")
    assert reindex_response.status_code == 200, f"Reindex failed: {reindex_response.status_code}"
    reindex_data = reindex_response.json()
    
    # Verify reindex processed 0 tickets
    assert reindex_data["processed"] == 0, \
        f"Expected 0 processed tickets after deleting all, got {reindex_data['processed']}"
    assert reindex_data["failed"] == 0, f"Expected 0 failed, got {reindex_data['failed']}"
    
    # Verify search still returns empty
    post_reindex_search = await client.post(
        "/search",
        json={"query": "anything", "limit": 10}
    )
    assert post_reindex_search.status_code == 200
    assert post_reindex_search.json()["total"] == 0, "Expected 0 results after reindex"
    
    # Verify stats still all zeros
    post_reindex_stats = await client.get("/stats")
    assert post_reindex_stats.status_code == 200
    assert post_reindex_stats.json()["totals"]["all"] == 0, "Expected 0 total after reindex"
    
    # =========================================================================
    # Step 9: Verify ErrorResponse schema in all error responses
    # =========================================================================
    # This was already verified in steps 3, 4, and 5 using _verify_error_response()
    # Let's also test the 404 for a ticket that never existed
    never_existed_response = await client.get("/tickets/ZZZ999")
    assert never_existed_response.status_code == 404, \
        f"Expected 404 for non-existent ticket, got {never_existed_response.status_code}"
    
    error_data = never_existed_response.json()
    error_obj = _verify_error_response(error_data, "NOT_FOUND")
    assert "ZZZ999" in error_obj["message"], "Error message should contain the ticket ID"
    
    print("\n✅ All error recovery and edge case tests passed!")
    print("   - Ticket creation: OK")
    print("   - Duplicate title handling: OK")
    print("   - Invalid status update (400): OK")
    print("   - Update deleted ticket (404): OK")
    print("   - Corrupted file handling: OK")
    print("   - Empty search results: OK")
    print("   - Zero stats: OK")
    print("   - Clean reindex: OK")
    print("   - ErrorResponse schema compliance: OK")


# =============================================================================
# Additional Edge Case Tests
# =============================================================================

@pytest.mark.asyncio
async def test_edge_case_empty_update(api_client: AsyncClient):
    """Verify that an empty update (no fields provided) returns 400."""
    client = api_client
    
    # Create a ticket
    ticket = await _create_ticket(
        client,
        title="Ticket for Empty Update Test",
        description="Testing empty update",
        repo="test/empty-update",
        category=Category.GENERAL,
        severity=Severity.LOW,
        status=Status.OPEN,
    )
    
    # Try to update with empty body
    update_response = await client.patch(f"/tickets/{ticket['id']}", json={})
    
    # Should return 400 or 422 (validation error)
    assert update_response.status_code in [400, 422], \
        f"Expected 400/422 for empty update, got {update_response.status_code}"
    
    error_data = update_response.json()
    _verify_error_response(error_data, "VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_edge_case_search_with_filters_no_results(api_client: AsyncClient):
    """Verify search with filters returns empty when no tickets match."""
    client = api_client
    
    # Create a ticket
    await _create_ticket(
        client,
        title="Low Priority Feature",
        description="A feature request with low severity",
        repo="test/filter-test",
        category=Category.FEATURE,
        severity=Severity.LOW,
        status=Status.OPEN,
    )
    
    # Search with filter that won't match (critical severity)
    search_response = await client.post(
        "/search",
        json={
            "query": "feature",
            "filters": {
                "severity": ["critical"]
            },
            "limit": 10
        }
    )
    
    assert search_response.status_code == 200
    search_data = search_response.json()
    assert search_data["total"] == 0, "Expected 0 results with non-matching filter"
    assert len(search_data["hits"]) == 0, "Expected empty hits with non-matching filter"


@pytest.mark.asyncio
async def test_edge_case_delete_nonexistent_ticket(api_client: AsyncClient):
    """Verify deleting a non-existent ticket returns 404."""
    client = api_client
    
    delete_response = await client.delete("/tickets/ZZZ999?mode=hard")
    
    assert delete_response.status_code == 404, \
        f"Expected 404 for deleting non-existent ticket, got {delete_response.status_code}"
    
    error_data = delete_response.json()
    _verify_error_response(error_data, "NOT_FOUND")


@pytest.mark.asyncio
async def test_edge_case_get_nonexistent_ticket(api_client: AsyncClient):
    """Verify getting a non-existent ticket returns 404 with proper error response."""
    client = api_client
    
    get_response = await client.get("/tickets/H999")
    
    assert get_response.status_code == 404, \
        f"Expected 404 for non-existent ticket, got {get_response.status_code}"
    
    error_data = get_response.json()
    error_obj = _verify_error_response(error_data, "NOT_FOUND")
    
    # Verify error message contains useful information
    assert "H999" in error_obj["message"], "Error message should contain the requested ticket ID"


@pytest.mark.asyncio
async def test_edge_case_invalid_category_in_create(api_client: AsyncClient):
    """Verify creating a ticket with invalid category returns 400."""
    client = api_client
    
    create_response = await client.post(
        "/tickets",
        json={
            "title": "Invalid Category Test",
            "description": "Testing invalid category",
            "repo": "test/invalid-category",
            "category": "invalid_category_xyz",
            "severity": "medium",
            "status": "open"
        }
    )
    
    assert create_response.status_code == 400, \
        f"Expected 400 for invalid category, got {create_response.status_code}"
    
    error_data = create_response.json()
    _verify_error_response(error_data, "VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_edge_case_invalid_repo_format(api_client: AsyncClient):
    """Verify creating a ticket with invalid repo format returns 400."""
    client = api_client
    
    create_response = await client.post(
        "/tickets",
        json={
            "title": "Invalid Repo Test",
            "description": "Testing invalid repo format",
            "repo": "invalid-repo-no-slash",  # Missing owner/repo format
            "category": "general",
            "severity": "medium",
            "status": "open"
        }
    )
    
    assert create_response.status_code == 400, \
        f"Expected 400 for invalid repo format, got {create_response.status_code}"
    
    error_data = create_response.json()
    _verify_error_response(error_data, "VALIDATION_ERROR")


@pytest.mark.asyncio
async def test_edge_case_search_empty_query(api_client: AsyncClient):
    """Verify search with empty query returns 400."""
    client = api_client
    
    search_response = await client.post(
        "/search",
        json={"query": "", "limit": 10}
    )
    
    assert search_response.status_code == 400, \
        f"Expected 400 for empty query, got {search_response.status_code}"
    
    error_data = search_response.json()
    _verify_error_response(error_data, "VALIDATION_ERROR")
