"""End-to-end system tests for vtic API.

E2E Case 1: System Operations & Error Handling
- Health check, doctor, stats, reindex operations
- Error response validation (404, 400)

E2E Case 2: Concurrent Operations Simulation
- Rapid ticket creation (50 tickets)
- Pagination, search, update, delete workflows
- Stats verification throughout lifecycle

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
    from vtic.models.ticket import TicketCreate, TicketUpdate
    from vtic.models.enums import Category, Severity, Status
    from vtic.models.api import ErrorResponse

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
    """FastAPI TestClient with real service attached."""
    if not API_AVAILABLE:
        pytest.skip(f"API not available: {API_ERROR}")

    app = create_app(config)
    app.state.ticket_service = service

    def _search_engine_override():
        return SearchEngine(service.collection)

    app.dependency_overrides[deps.get_search_engine] = _search_engine_override

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# =============================================================================
# E2E Case 1: System Operations & Error Handling
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_system_operations_and_error_handling(api_client: AsyncClient) -> None:
    """E2E Case 1: System Operations & Error Handling
    
    1. Health check — verify response schema (status, version, index_status)
    2. Doctor — run all 5 diagnostic checks, verify results
    3. Stats — with 0 tickets, verify all counts are 0
    4. Create 20 tickets, run stats again — verify counts updated
    5. Reindex — verify reindex result (ticket count matches)
    6. Test error responses:
       - GET /tickets/nonexistent → 404
       - POST /tickets with missing title → 400
       - PATCH /tickets/nonexistent → 404
       - DELETE /tickets/nonexistent → 404
    7. Verify all error responses match ErrorResponse schema
    """
    client = api_client

    # === 1. Health Check ===
    print("\n[1/7] Testing health check endpoint...")
    response = await client.get("/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    
    health_data = response.json()
    assert "status" in health_data, "Health response missing 'status'"
    assert health_data["status"] in ("healthy", "degraded", "unhealthy"), "Invalid status value"
    assert "version" in health_data, "Health response missing 'version'"
    assert health_data["version"] == "0.1.0", "Version mismatch"
    assert "index_status" in health_data, "Health response missing 'index_status'"
    assert "zvec" in health_data["index_status"], "index_status missing 'zvec'"
    assert "ticket_count" in health_data["index_status"], "index_status missing 'ticket_count'"
    assert "embedding_provider" in health_data, "Health response missing 'embedding_provider'"
    print(f"  ✓ Health check: status={health_data['status']}, tickets={health_data['index_status']['ticket_count']}")

    # === 2. Doctor Check ===
    print("\n[2/7] Testing doctor endpoint (5 diagnostic checks)...")
    response = await client.get("/doctor")
    assert response.status_code == 200, f"Doctor check failed: {response.text}"
    
    doctor_data = response.json()
    assert "overall" in doctor_data, "Doctor response missing 'overall'"
    assert "checks" in doctor_data, "Doctor response missing 'checks'"
    
    # Verify all 5 checks are present
    check_names = {check["name"] for check in doctor_data["checks"]}
    expected_checks = {"zvec_index", "config_file", "embedding_provider", "file_permissions", "ticket_files"}
    assert check_names == expected_checks, f"Missing checks: {expected_checks - check_names}"
    
    # Verify check structure
    for check in doctor_data["checks"]:
        assert "name" in check, "Check missing 'name'"
        assert "status" in check, f"Check {check['name']} missing 'status'"
        assert check["status"] in ("ok", "warning", "error"), f"Invalid status for {check['name']}"
        assert "message" in check, f"Check {check['name']} missing 'message'"
        # 'fix' field can be null or string
    
    overall = doctor_data["overall"]
    assert overall in ("ok", "warnings", "errors"), f"Invalid overall status: {overall}"
    print(f"  ✓ Doctor check: overall={overall}, checks={len(doctor_data['checks'])}")

    # === 3. Stats with 0 tickets ===
    print("\n[3/7] Testing stats with 0 tickets...")
    response = await client.get("/stats")
    assert response.status_code == 200, f"Stats failed: {response.text}"
    
    stats_data = response.json()
    assert "totals" in stats_data, "Stats missing 'totals'"
    assert stats_data["totals"]["all"] == 0, "Expected 0 total tickets"
    assert stats_data["totals"]["open"] == 0, "Expected 0 open tickets"
    assert stats_data["totals"]["closed"] == 0, "Expected 0 closed tickets"
    assert "by_status" in stats_data, "Stats missing 'by_status'"
    assert "by_severity" in stats_data, "Stats missing 'by_severity'"
    assert "by_category" in stats_data, "Stats missing 'by_category'"
    print(f"  ✓ Stats with 0 tickets: totals={stats_data['totals']}")

    # === 4. Create 20 tickets and verify stats ===
    print("\n[4/7] Creating 20 tickets and verifying stats...")
    created_tickets = []
    categories = [Category.CRASH, Category.FEATURE, Category.HOTFIX, Category.SECURITY, Category.GENERAL]
    severities = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
    statuses = [Status.OPEN, Status.IN_PROGRESS, Status.FIXED]
    
    for i in range(20):
        ticket_data = {
            "title": f"Test Ticket {i+1}",
            "description": f"Description for test ticket {i+1}",
            "repo": f"test/repo{i % 3}",  # Distribute across 3 repos
            "category": categories[i % 5].value,
            "severity": severities[i % 5].value,
            "status": statuses[i % 3].value,
            "tags": [f"tag{i % 4}", "e2e-test"],
        }
        response = await client.post("/tickets", json=ticket_data)
        assert response.status_code == 201, f"Failed to create ticket {i+1}: {response.text}"
        created_tickets.append(response.json()["data"]["id"])
    
    print(f"  ✓ Created 20 tickets: {created_tickets[:5]}...{created_tickets[-1]}")
    
    # Verify stats updated
    response = await client.get("/stats")
    assert response.status_code == 200
    stats_data = response.json()
    
    assert stats_data["totals"]["all"] == 20, f"Expected 20 total tickets, got {stats_data['totals']['all']}"
    # open = open + in_progress, closed = fixed + wont_fix + closed
    # We created: open=7, in_progress=7, fixed=6
    assert stats_data["totals"]["open"] == 14, f"Expected 14 open tickets, got {stats_data['totals']['open']}"
    assert stats_data["totals"]["closed"] == 6, f"Expected 6 closed tickets, got {stats_data['totals']['closed']}"
    
    # Verify by_status breakdown
    assert stats_data["by_status"]["open"] == 7, "Expected 7 open status"
    assert stats_data["by_status"]["in_progress"] == 7, "Expected 7 in_progress status"
    assert stats_data["by_status"]["fixed"] == 6, "Expected 6 fixed status"
    
    print(f"  ✓ Stats updated: totals={stats_data['totals']}")

    # === 5. Reindex and verify ===
    print("\n[5/7] Testing reindex endpoint...")
    response = await client.post("/reindex")
    assert response.status_code == 200, f"Reindex failed: {response.text}"
    
    reindex_data = response.json()
    assert "processed" in reindex_data, "Reindex missing 'processed'"
    assert "skipped" in reindex_data, "Reindex missing 'skipped'"
    assert "failed" in reindex_data, "Reindex missing 'failed'"
    assert "duration_ms" in reindex_data, "Reindex missing 'duration_ms'"
    assert "errors" in reindex_data, "Reindex missing 'errors'"
    
    # All 20 tickets should be processed
    assert reindex_data["processed"] == 20, f"Expected 20 processed, got {reindex_data['processed']}"
    assert reindex_data["failed"] == 0, f"Expected 0 failed, got {reindex_data['failed']}"
    assert reindex_data["duration_ms"] >= 0, "Duration should be non-negative"
    assert isinstance(reindex_data["errors"], list), "Errors should be a list"
    print(f"  ✓ Reindex: processed={reindex_data['processed']}, duration={reindex_data['duration_ms']}ms")

    # === 6. Test Error Responses ===
    print("\n[6/7] Testing error responses...")
    
    # GET /tickets/nonexistent → 404
    response = await client.get("/tickets/NONEXISTENT")
    assert response.status_code == 404, f"Expected 404 for nonexistent ticket, got {response.status_code}"
    error_data = response.json()
    assert "error" in error_data, "404 response missing 'error' object"
    assert error_data["error"]["code"] == "NOT_FOUND", f"Expected NOT_FOUND, got {error_data['error']['code']}"
    print("  ✓ GET /tickets/nonexistent → 404 NOT_FOUND")
    
    # POST /tickets with missing title → 400
    invalid_ticket = {
        "description": "Missing title field",
        "repo": "test/repo"
    }
    response = await client.post("/tickets", json=invalid_ticket)
    assert response.status_code == 400, f"Expected 400 for missing title, got {response.status_code}"
    error_data = response.json()
    assert "error" in error_data, "400 response missing 'error' object"
    assert error_data["error"]["code"] == "VALIDATION_ERROR", f"Expected VALIDATION_ERROR, got {error_data['error']['code']}"
    print("  ✓ POST /tickets (missing title) → 400 VALIDATION_ERROR")
    
    # PATCH /tickets/nonexistent → 404
    response = await client.patch("/tickets/NONEXISTENT", json={"status": "fixed"})
    assert response.status_code == 404, f"Expected 404 for patch nonexistent, got {response.status_code}"
    error_data = response.json()
    assert error_data["error"]["code"] == "NOT_FOUND"
    print("  ✓ PATCH /tickets/nonexistent → 404 NOT_FOUND")
    
    # DELETE /tickets/nonexistent → 404
    response = await client.delete("/tickets/NONEXISTENT")
    assert response.status_code == 404, f"Expected 404 for delete nonexistent, got {response.status_code}"
    error_data = response.json()
    assert error_data["error"]["code"] == "NOT_FOUND"
    print("  ✓ DELETE /tickets/nonexistent → 404 NOT_FOUND")

    # === 7. Verify ErrorResponse Schema ===
    print("\n[7/7] Verifying all error responses match ErrorResponse schema...")
    
    error_test_cases = [
        ("GET /tickets/nonexistent", client.get("/tickets/NONEXISTENT")),
        ("POST /tickets (invalid)", client.post("/tickets", json={"description": "x", "repo": "a/b"})),
        ("PATCH /tickets/nonexistent", client.patch("/tickets/NONEXISTENT", json={"status": "fixed"})),
        ("DELETE /tickets/nonexistent", client.delete("/tickets/NONEXISTENT")),
    ]
    
    for test_name, coro in error_test_cases:
        response = await coro
        error_data = response.json()
        
        # Validate ErrorResponse structure
        assert "error" in error_data, f"{test_name}: Missing 'error' root"
        error_obj = error_data["error"]
        assert "code" in error_obj, f"{test_name}: Missing 'error.code'"
        assert isinstance(error_obj["code"], str), f"{test_name}: 'code' must be string"
        assert "message" in error_obj, f"{test_name}: Missing 'error.message'"
        assert isinstance(error_obj["message"], str), f"{test_name}: 'message' must be string"
        
        # details is optional but must be list if present
        if "details" in error_obj and error_obj["details"] is not None:
            assert isinstance(error_obj["details"], list), f"{test_name}: 'details' must be list"
            for detail in error_obj["details"]:
                assert "message" in detail, f"{test_name}: Detail missing 'message'"
        
        # docs is optional
        if "docs" in error_obj:
            assert error_obj["docs"] is None or isinstance(error_obj["docs"], str), f"{test_name}: 'docs' must be string or null"
    
    print("  ✓ All error responses conform to ErrorResponse schema")
    print("\n" + "="*60)
    print("E2E Case 1: PASSED ✓")
    print("="*60)


# =============================================================================
# E2E Case 2: Concurrent Operations Simulation
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_concurrent_operations_simulation(api_client: AsyncClient) -> None:
    """E2E Case 2: Concurrent Operations Simulation
    
    1. Create 50 tickets rapidly (sequential)
    2. Verify all created (list returns 50)
    3. Search across all 50 — verify pagination works
    4. Update 10 tickets (change status to "fixed")
    5. Search for status=fixed — verify 10 results
    6. Delete 10 tickets
    7. Stats — verify counts updated
    8. Full reindex — verify clean state
    9. Final health check — verify healthy
    """
    client = api_client

    # === 1. Create 50 tickets rapidly ===
    print("\n[1/9] Creating 50 tickets rapidly...")
    created_ids = []
    
    for i in range(50):
        ticket_data = {
            "title": f"Concurrent Test Ticket {i+1}",
            "description": f"Description for concurrent test ticket {i+1}\n\nThis is a longer description to test indexing.",
            "repo": f"concurrent/repo{i % 5}",  # Spread across 5 repos
            "category": ["crash", "hotfix", "feature", "security", "general"][i % 5],
            "severity": ["critical", "high", "medium", "low", "info"][i % 5],
            "status": "open",
            "tags": ["concurrent", f"batch-{i//10}"],
        }
        response = await client.post("/tickets", json=ticket_data)
        assert response.status_code == 201, f"Failed to create ticket {i+1}: {response.text}"
        created_ids.append(response.json()["data"]["id"])
    
    assert len(created_ids) == 50, f"Expected 50 tickets, created {len(created_ids)}"
    print(f"  ✓ Created 50 tickets: {created_ids[0]} to {created_ids[-1]}")

    # === 2. Verify all created (list returns 50) ===
    print("\n[2/9] Verifying all 50 tickets were created...")
    response = await client.get("/tickets?limit=100")
    assert response.status_code == 200
    
    list_data = response.json()
    assert list_data["meta"]["total"] == 50, f"Expected 50 total, got {list_data['meta']['total']}"
    assert len(list_data["data"]) == 50, f"Expected 50 items in data, got {len(list_data['data'])}"
    print(f"  ✓ List returns all 50 tickets")

    # === 3. Search across all 50 — verify pagination works ===
    print("\n[3/9] Testing search with pagination...")
    
    # Test paginated listing
    page1 = await client.get("/tickets?limit=20&offset=0")
    assert page1.status_code == 200
    page1_data = page1.json()
    assert len(page1_data["data"]) == 20
    assert page1_data["meta"]["has_more"] == True
    
    page2 = await client.get("/tickets?limit=20&offset=20")
    assert page2.status_code == 200
    page2_data = page2.json()
    assert len(page2_data["data"]) == 20
    assert page2_data["meta"]["has_more"] == True
    
    page3 = await client.get("/tickets?limit=20&offset=40")
    assert page3.status_code == 200
    page3_data = page3.json()
    assert len(page3_data["data"]) == 10
    assert page3_data["meta"]["has_more"] == False
    
    # Verify no overlap in IDs
    page1_ids = {t["id"] for t in page1_data["data"]}
    page2_ids = {t["id"] for t in page2_data["data"]}
    page3_ids = {t["id"] for t in page3_data["data"]}
    
    assert len(page1_ids & page2_ids) == 0, "Page 1 and 2 overlap"
    assert len(page1_ids & page3_ids) == 0, "Page 1 and 3 overlap"
    assert len(page2_ids & page3_ids) == 0, "Page 2 and 3 overlap"
    
    print(f"  ✓ Pagination works: 20+20+10=50 tickets, no overlap")

    # === 4. Update 10 tickets (change status to "fixed") ===
    print("\n[4/9] Updating 10 tickets to status=fixed...")
    tickets_to_update = created_ids[:10]
    
    for ticket_id in tickets_to_update:
        # First transition: open → in_progress
        response = await client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "in_progress"}
        )
        assert response.status_code == 200, f"Failed to transition to in_progress {ticket_id}: {response.text}"
        
        # Second transition: in_progress → fixed
        response = await client.patch(
            f"/tickets/{ticket_id}",
            json={"status": "fixed", "fix": "Resolved during concurrent test"}
        )
        assert response.status_code == 200, f"Failed to transition to fixed {ticket_id}: {response.text}"
        updated = response.json()["data"]
        assert updated["status"] == "fixed", f"Status not updated for {ticket_id}"
    
    print(f"  ✓ Updated 10 tickets to fixed status (via in_progress)")

    # === 5. Search for status=fixed — verify 10 results ===
    print("\n[5/9] Searching for status=fixed tickets...")
    response = await client.get("/tickets?status=fixed&limit=100")
    assert response.status_code == 200
    
    fixed_data = response.json()
    assert fixed_data["meta"]["total"] == 10, f"Expected 10 fixed tickets, got {fixed_data['meta']['total']}"
    
    for ticket in fixed_data["data"]:
        assert ticket["status"] == "fixed", f"Ticket {ticket['id']} has wrong status"
    
    print(f"  ✓ Found exactly 10 tickets with status=fixed")

    # === 6. Delete 10 tickets (hard delete) ===
    print("\n[6/9] Deleting 10 tickets...")
    tickets_to_delete = created_ids[10:20]  # Different from the ones we updated
    
    for ticket_id in tickets_to_delete:
        response = await client.delete(f"/tickets/{ticket_id}?mode=hard")
        assert response.status_code == 204, f"Failed to delete {ticket_id}: {response.text}"
    
    print(f"  ✓ Deleted 10 tickets (hard)")

    # === 7. Stats — verify counts updated ===
    print("\n[7/9] Verifying stats after operations...")
    response = await client.get("/stats")
    assert response.status_code == 200
    
    stats_data = response.json()
    # 50 created - 10 deleted = 40 remaining
    # 10 fixed (closed), 30 open
    assert stats_data["totals"]["all"] == 40, f"Expected 40 total, got {stats_data['totals']['all']}"
    assert stats_data["totals"]["open"] == 30, f"Expected 30 open, got {stats_data['totals']['open']}"
    assert stats_data["totals"]["closed"] == 10, f"Expected 10 closed, got {stats_data['totals']['closed']}"
    
    # Verify by_status breakdown
    assert stats_data["by_status"]["open"] == 30, f"Expected 30 open status"
    assert stats_data["by_status"]["fixed"] == 10, f"Expected 10 fixed status"
    
    print(f"  ✓ Stats correct: totals={stats_data['totals']}")

    # === 8. Full reindex — verify clean state ===
    print("\n[8/9] Running full reindex...")
    response = await client.post("/reindex")
    assert response.status_code == 200
    
    reindex_data = response.json()
    # After delete, we have 40 tickets remaining
    assert reindex_data["processed"] == 40, f"Expected 40 processed, got {reindex_data['processed']}"
    assert reindex_data["failed"] == 0, f"Expected 0 failed, got {reindex_data['failed']}"
    
    # Verify stats still correct after reindex
    response = await client.get("/stats")
    stats_after = response.json()
    assert stats_after["totals"]["all"] == 40, "Stats inconsistent after reindex"
    
    print(f"  ✓ Reindex complete: processed={reindex_data['processed']}, clean state verified")

    # === 9. Final health check — verify healthy ===
    print("\n[9/9] Final health check...")
    response = await client.get("/health")
    assert response.status_code == 200
    
    health_data = response.json()
    # System can be healthy, degraded (no embeddings), or degraded (unavailable index)
    # The important thing is it's not "unhealthy"
    assert health_data["status"] != "unhealthy", f"System unhealthy: {health_data}"
    assert "version" in health_data, "Health missing version"
    assert "index_status" in health_data, "Health missing index_status"
    
    # Verify final stats are consistent (authoritative source)
    response = await client.get("/stats")
    assert response.status_code == 200
    final_stats = response.json()
    assert final_stats["totals"]["all"] == 40, "Final stats inconsistent after reindex"
    
    print(f"  ✓ Health check: status={health_data['status']}, version={health_data['version']}")
    print(f"  ✓ Final stats verified: {final_stats['totals']}")
    print("\n" + "="*60)
    print("E2E Case 2: PASSED ✓")
    print("="*60)


# =============================================================================
# Test Report Summary
# =============================================================================

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """Print custom test summary."""
    terminalreporter.write("\n" + "="*70 + "\n")
    terminalreporter.write("VTIC E2E TEST SUMMARY\n")
    terminalreporter.write("="*70 + "\n\n")
    
    terminalreporter.write("Test Cases:\n")
    terminalreporter.write("  1. test_e2e_system_operations_and_error_handling\n")
    terminalreporter.write("     - Health check schema validation\n")
    terminalreporter.write("     - Doctor (5 diagnostic checks)\n")
    terminalreporter.write("     - Stats lifecycle (0 → 20 tickets)\n")
    terminalreporter.write("     - Reindex with verification\n")
    terminalreporter.write("     - Error responses (404, 400)\n")
    terminalreporter.write("     - ErrorResponse schema validation\n\n")
    
    terminalreporter.write("  2. test_e2e_concurrent_operations_simulation\n")
    terminalreporter.write("     - Create 50 tickets rapidly\n")
    terminalreporter.write("     - Pagination verification (20+20+10)\n")
    terminalreporter.write("     - Update 10 tickets → status=fixed\n")
    terminalreporter.write("     - Search/filter by status\n")
    terminalreporter.write("     - Delete 10 tickets\n")
    terminalreporter.write("     - Stats verification throughout\n")
    terminalreporter.write("     - Reindex and final health check\n\n")
    
    passed = len(terminalreporter.stats.get("passed", []))
    failed = len(terminalreporter.stats.get("failed", []))
    
    terminalreporter.write(f"Results: {passed} passed, {failed} failed\n")
    terminalreporter.write("="*70 + "\n")
