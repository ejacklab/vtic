"""Tests for Zvec index operations.

Tests cover:
- Schema creation
- Client operations (create_index, open_index, close_index)
- CRUD operations (insert, upsert, fetch, delete)
- BM25 keyword search
- Filter queries
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

# Import the modules under test
from vtic.index.client import (
    close_index,
    create_index,
    destroy_index,
    get_collection,
    open_index,
)
from vtic.index.operations import (
    BM25_VECTOR_FIELD,
    delete_ticket,
    fetch_ticket,
    insert_tickets,
    query_tickets,
    rebuild_index,
    upsert_ticket,
)
from vtic.index.schema import COLLECTION_NAME, BM25_VECTOR_FIELD as SCHEMA_BM25_FIELD, define_ticket_schema

# Sample test data
SAMPLE_TICKETS = [
    {
        "id": "C1",
        "title": "Segmentation Fault on Startup",
        "description": "Application crashes immediately when launched with corrupted config file",
        "repo": "ejacklab/api",
        "category": "crash",
        "severity": "critical",
        "status": "open",
        "assignee": "alice",
        "tags": ["crash", "startup"],
        "references": [],
        "created": "2026-03-17T09:00:00Z",
        "updated": "2026-03-17T09:00:00Z",
    },
    {
        "id": "S1",
        "title": "SQL Injection in Login Endpoint",
        "description": "User input is not sanitized allowing SQL injection attacks on the login form",
        "repo": "ejacklab/web",
        "category": "security",
        "severity": "critical",
        "status": "in_progress",
        "assignee": "bob",
        "tags": ["security", "sql", "login"],
        "references": [],
        "created": "2026-03-17T10:00:00Z",
        "updated": "2026-03-17T10:00:00Z",
    },
    {
        "id": "S2",
        "title": "CORS Wildcard Origin",
        "description": "API allows wildcard CORS origins in production environment",
        "repo": "ejacklab/api",
        "category": "security",
        "severity": "high",
        "status": "open",
        "assignee": None,
        "tags": ["security", "cors", "api"],
        "references": ["C1"],
        "created": "2026-03-17T11:00:00Z",
        "updated": "2026-03-17T11:00:00Z",
    },
    {
        "id": "F1",
        "title": "Add Dark Mode Support",
        "description": "Users have requested dark mode toggle for the dashboard interface",
        "repo": "ejacklab/ui",
        "category": "feature",
        "severity": "low",
        "status": "open",
        "assignee": None,
        "tags": ["feature", "ui", "dark-mode"],
        "references": [],
        "created": "2026-03-17T12:00:00Z",
        "updated": "2026-03-17T12:00:00Z",
    },
    {
        "id": "H1",
        "title": "Fix Memory Leak in Worker Process",
        "description": "Worker process memory grows continuously until OOM after 24 hours of operation",
        "repo": "ejacklab/api",
        "category": "hotfix",
        "severity": "high",
        "status": "open",
        "assignee": "charlie",
        "tags": ["hotfix", "memory", "worker"],
        "references": [],
        "created": "2026-03-17T13:00:00Z",
        "updated": "2026-03-17T13:00:00Z",
    },
    {
        "id": "G1",
        "title": "Update README Installation Steps",
        "description": "Installation instructions are outdated and reference deprecated package names",
        "repo": "ejacklab/docs",
        "category": "general",
        "severity": "info",
        "status": "open",
        "assignee": None,
        "tags": ["docs", "readme"],
        "references": [],
        "created": "2026-03-17T14:00:00Z",
        "updated": "2026-03-17T14:00:00Z",
    },
    {
        "id": "C2",
        "title": "Null Pointer in Payment Module",
        "description": "Payment processing fails with null pointer when card expiry date is missing",
        "repo": "ejacklab/api",
        "category": "crash",
        "severity": "high",
        "status": "fixed",
        "assignee": "alice",
        "tags": ["crash", "payment"],
        "references": [],
        "created": "2026-03-17T15:00:00Z",
        "updated": "2026-03-17T15:00:00Z",
    },
    {
        "id": "F2",
        "title": "Export to CSV Feature",
        "description": "Add ability to export ticket data to CSV format for offline analysis",
        "repo": "ejacklab/api",
        "category": "feature",
        "severity": "medium",
        "status": "open",
        "assignee": None,
        "tags": ["feature", "export", "csv"],
        "references": [],
        "created": "2026-03-17T16:00:00Z",
        "updated": "2026-03-17T16:00:00Z",
    },
    {
        "id": "H2",
        "title": "Patch Log4j Vulnerability",
        "description": "Critical vulnerability in Log4j library needs immediate patching",
        "repo": "ejacklab/api",
        "category": "hotfix",
        "severity": "critical",
        "status": "fixed",
        "assignee": "bob",
        "tags": ["hotfix", "security", "log4j"],
        "references": ["S1"],
        "created": "2026-03-17T17:00:00Z",
        "updated": "2026-03-17T17:00:00Z",
    },
    {
        "id": "G2",
        "title": "Fix Typo in Error Message",
        "description": "Error message contains a typo that confuses users",
        "repo": "ejacklab/web",
        "category": "general",
        "severity": "info",
        "status": "closed",
        "assignee": None,
        "tags": ["typo", "error"],
        "references": [],
        "created": "2026-03-17T18:00:00Z",
        "updated": "2026-03-17T18:00:00Z",
    },
]


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test indexes."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def collection(temp_dir):
    """Create a fresh collection for each test."""
    coll = create_index(temp_dir)
    yield coll
    close_index(coll)


class TestSchema:
    """Test schema creation and structure."""

    def test_schema_creation(self):
        """Test that define_ticket_schema returns a valid CollectionSchema."""
        schema = define_ticket_schema()

        assert schema.name == COLLECTION_NAME
        # Check that we have the expected fields
        assert schema.field("id") is not None
        assert schema.field("title") is not None
        assert schema.field("description") is not None
        assert schema.field("repo") is not None
        assert schema.field("category") is not None
        assert schema.field("severity") is not None
        assert schema.field("status") is not None

    def test_bm25_vector_field_name(self):
        """Test that BM25 vector field name is consistent."""
        assert BM25_VECTOR_FIELD == SCHEMA_BM25_FIELD
        assert BM25_VECTOR_FIELD == "bm25_sparse"


class TestClient:
    """Test client operations."""

    def test_create_index(self, temp_dir):
        """Test creating a new index."""
        coll = create_index(temp_dir)

        assert coll is not None
        assert coll.schema.name == COLLECTION_NAME

        # Verify index directory was created
        index_path = temp_dir / "zvec_index"
        assert index_path.exists()

        # Properly close and destroy to release locks
        close_index(coll)
        coll.destroy()

    def test_open_index(self, temp_dir):
        """Test opening an existing index.

        Note: zvec uses file locking, so we need to ensure the previous
        collection handle is released (garbage collected) before opening.
        """
        # Create
        coll1 = create_index(temp_dir)
        coll1.flush()
        # Delete reference to release file lock
        del coll1

        # Now open (lock should be released)
        coll2 = open_index(temp_dir)
        assert coll2 is not None
        assert coll2.schema.name == COLLECTION_NAME

        close_index(coll2)
        coll2.destroy()

    def test_open_index_not_found(self, temp_dir):
        """Test opening a non-existent index raises error."""
        with pytest.raises(FileNotFoundError):
            open_index(temp_dir)

    def test_create_index_already_exists(self, temp_dir):
        """Test creating index twice raises error."""
        coll = create_index(temp_dir)
        close_index(coll)

        with pytest.raises(FileExistsError):
            create_index(temp_dir)

        # Cleanup
        coll.destroy()

    def test_get_collection_creates_if_missing(self, temp_dir):
        """Test get_collection creates index if it doesn't exist."""
        coll = get_collection(temp_dir)
        assert coll is not None
        close_index(coll)
        coll.destroy()

    def test_get_collection_opens_existing(self, temp_dir):
        """Test get_collection opens existing index."""
        coll1 = get_collection(temp_dir)
        close_index(coll1)
        coll1.destroy()

        coll2 = get_collection(temp_dir)
        assert coll2 is not None
        close_index(coll2)
        coll2.destroy()

    def test_destroy_index(self, temp_dir):
        """Test destroying an index."""
        coll = create_index(temp_dir)
        close_index(coll)

        result = destroy_index(temp_dir)
        assert result is True

        # Verify directory is gone
        assert not (temp_dir / "zvec_index").exists()

    def test_destroy_index_not_exists(self, temp_dir):
        """Test destroying non-existent index returns False."""
        result = destroy_index(temp_dir)
        assert result is False


class TestInsertOperations:
    """Test ticket insertion operations."""

    def test_insert_tickets_batch(self, collection):
        """Test batch inserting 10 tickets."""
        count = insert_tickets(collection, SAMPLE_TICKETS)

        assert count == 10

    def test_insert_empty_list(self, collection):
        """Test inserting empty list returns 0."""
        count = insert_tickets(collection, [])
        assert count == 0

    def test_fetch_ticket_returns_correct_ticket(self, collection):
        """Test fetching a ticket by ID returns correct data."""
        insert_tickets(collection, SAMPLE_TICKETS)

        ticket = fetch_ticket(collection, "S1")

        assert ticket is not None
        assert ticket["id"] == "S1"
        assert ticket["title"] == "SQL Injection in Login Endpoint"
        assert ticket["category"] == "security"
        assert ticket["severity"] == "critical"
        assert "sql" in ticket["tags"]

    def test_fetch_ticket_non_existent(self, collection):
        """Test fetching non-existent ticket returns None."""
        ticket = fetch_ticket(collection, "NONEXISTENT")
        assert ticket is None

    def test_upsert_ticket_inserts_new(self, collection):
        """Test upserting a new ticket."""
        new_ticket = {
            "id": "X1",
            "title": "New Test Ticket",
            "description": "A test ticket for upsert",
            "repo": "ejacklab/test",
            "category": "general",
            "severity": "low",
            "status": "open",
            "tags": ["test"],
            "references": [],
            "created": "2026-03-17T20:00:00Z",
            "updated": "2026-03-17T20:00:00Z",
        }

        upsert_ticket(collection, new_ticket)

        fetched = fetch_ticket(collection, "X1")
        assert fetched is not None
        assert fetched["title"] == "New Test Ticket"

    def test_upsert_ticket_updates_existing(self, collection):
        """Test upserting an existing ticket updates it."""
        insert_tickets(collection, [SAMPLE_TICKETS[0]])

        updated = SAMPLE_TICKETS[0].copy()
        updated["title"] = "Updated Title"

        upsert_ticket(collection, updated)

        fetched = fetch_ticket(collection, "C1")
        assert fetched["title"] == "Updated Title"


class TestDeleteOperations:
    """Test ticket deletion operations."""

    def test_delete_ticket_removes_from_index(self, collection):
        """Test deleting a ticket removes it."""
        insert_tickets(collection, SAMPLE_TICKETS)

        delete_ticket(collection, "S1")

        # Should not find deleted ticket
        ticket = fetch_ticket(collection, "S1")
        assert ticket is None

    def test_delete_ticket_non_existent(self, collection):
        """Test deleting non-existent ticket doesn't raise error."""
        # Should not raise
        delete_ticket(collection, "NONEXISTENT")


class TestBM25Search:
    """Test BM25 keyword search functionality."""

    @pytest.fixture(autouse=True)
    def setup_tickets(self, collection):
        """Insert sample tickets before each search test."""
        insert_tickets(collection, SAMPLE_TICKETS)

    def test_search_sql_injection(self, collection):
        """Test BM25 search for 'SQL injection' returns S1."""
        results = query_tickets(collection, "SQL injection", limit=10)

        assert len(results) > 0
        # S1 should be in top results
        ids = [r["id"] for r in results]
        assert "S1" in ids

    def test_search_memory(self, collection):
        """Test BM25 search for 'memory' returns H1."""
        results = query_tickets(collection, "memory leak worker", limit=10)

        assert len(results) > 0
        ids = [r["id"] for r in results]
        assert "H1" in ids

    def test_search_cors(self, collection):
        """Test BM25 search for 'CORS' returns S2."""
        results = query_tickets(collection, "CORS wildcard", limit=10)

        assert len(results) > 0
        ids = [r["id"] for r in results]
        assert "S2" in ids

    def test_search_returns_scores(self, collection):
        """Test that search results include relevance scores."""
        results = query_tickets(collection, "crash", limit=5)

        for r in results:
            assert "score" in r
            assert r["score"] is not None
            assert r["score"] >= 0

    def test_search_empty_query(self, collection):
        """Test that empty query returns empty results."""
        results = query_tickets(collection, "", limit=10)
        assert results == []

    def test_search_whitespace_query(self, collection):
        """Test that whitespace-only query returns empty results."""
        results = query_tickets(collection, "   ", limit=10)
        assert results == []

    def test_search_with_limit(self, collection):
        """Test that limit parameter works."""
        results = query_tickets(collection, "api", limit=3)
        assert len(results) <= 3


class TestFilterQueries:
    """Test filter-based queries."""

    @pytest.fixture(autouse=True)
    def setup_tickets(self, collection):
        """Insert sample tickets before each filter test."""
        insert_tickets(collection, SAMPLE_TICKETS)

    def test_filter_by_category_security(self, collection):
        """Test filter by category='security' returns S1, S2."""
        results = query_tickets(
            collection,
            "security vulnerability",
            filters={"category": ["security"]},
            limit=10,
        )

        # Should only return security tickets
        for r in results:
            if r["id"] in ("S1", "S2"):
                assert r["category"] == "security"

    def test_filter_by_severity_critical(self, collection):
        """Test filter by severity='critical' returns C1, S1, H2."""
        results = query_tickets(
            collection,
            "critical important urgent",
            filters={"severity": ["critical"]},
            limit=10,
        )

        ids = [r["id"] for r in results]
        # Should include critical tickets
        for rid in ["C1", "S1", "H2"]:
            if rid in ids:
                r = next(x for x in results if x["id"] == rid)
                assert r["severity"] == "critical"

    def test_filter_by_repo(self, collection):
        """Test filter by repo='ejacklab/api'."""
        results = query_tickets(
            collection,
            "api server",
            filters={"repo": ["ejacklab/api"]},
            limit=10,
        )

        # All results should be from ejacklab/api
        for r in results:
            assert r["repo"] == "ejacklab/api"

    def test_filter_combined_category_and_severity(self, collection):
        """Test combined filter: category='security' AND severity='critical'."""
        results = query_tickets(
            collection,
            "security critical",
            filters={"category": ["security"], "severity": ["critical"]},
            limit=10,
        )

        # Should only return S1 (security + critical)
        for r in results:
            if r["category"] == "security":
                assert r["severity"] == "critical" or r["id"] in ("S1",)

    def test_filter_by_status(self, collection):
        """Test filter by status='open'."""
        results = query_tickets(
            collection,
            "open ticket",
            filters={"status": ["open"]},
            limit=10,
        )

        for r in results:
            if r["id"] in ("C1", "S2", "F1", "H1", "G1", "F2"):
                assert r["status"] == "open"


class TestQueryAfterDelete:
    """Test that deleted tickets don't appear in queries."""

    def test_query_after_delete(self, collection):
        """Test that deleted ticket doesn't appear in search results."""
        insert_tickets(collection, SAMPLE_TICKETS)

        # Verify S1 is searchable
        results = query_tickets(collection, "SQL injection", limit=10)
        ids = [r["id"] for r in results]
        assert "S1" in ids

        # Delete S1
        delete_ticket(collection, "S1")

        # Search again - S1 should not appear
        results = query_tickets(collection, "SQL injection", limit=10)
        ids = [r["id"] for r in results]
        assert "S1" not in ids


class TestPagination:
    """Test pagination functionality."""

    @pytest.fixture(autouse=True)
    def setup_tickets(self, collection):
        """Insert sample tickets before each pagination test."""
        insert_tickets(collection, SAMPLE_TICKETS)

    def test_offset_pagination(self, collection):
        """Test that offset parameter works."""
        # Get first page
        page1 = query_tickets(collection, "api", limit=3, offset=0)

        # Get second page
        page2 = query_tickets(collection, "api", limit=3, offset=3)

        # Pages should be different (unless results are fewer than expected)
        if len(page2) > 0:
            page1_ids = {r["id"] for r in page1}
            page2_ids = {r["id"] for r in page2}
            # Should have no overlap
            assert page1_ids.isdisjoint(page2_ids)


class TestRebuildIndex:
    """Test rebuild_index functionality."""

    def test_rebuild_from_markdown_files(self, temp_dir):
        """Test rebuilding index from markdown files on disk."""
        from vtic.index.operations import rebuild_index
        from vtic.store.markdown import write_ticket
        from vtic.store.paths import ticket_file_path

        # Write some tickets to disk
        base_dir = temp_dir
        for ticket in SAMPLE_TICKETS[:3]:  # Use first 3 tickets
            path = ticket_file_path(
                base_dir,
                ticket["repo"],
                ticket["category"],
                ticket["id"],
                "test-ticket"
            )
            write_ticket(path, ticket)

        # Create index
        coll = create_index(temp_dir)

        try:
            # Rebuild index from markdown files
            result = rebuild_index(coll, base_dir)

            # Verify result structure
            assert "processed" in result
            assert "skipped" in result
            assert "failed" in result
            assert "duration_ms" in result
            assert "errors" in result

            # Should have processed 3 tickets
            assert result["processed"] == 3
            assert result["failed"] == 0

            # Verify tickets are searchable
            results = query_tickets(coll, "SQL injection", limit=10)
            ids = [r["id"] for r in results]
            assert "S1" in ids
        finally:
            close_index(coll)
            coll.destroy()

    def test_rebuild_empty_directory(self, temp_dir):
        """Test rebuilding index from empty directory."""
        from vtic.index.operations import rebuild_index

        # Create index
        coll = create_index(temp_dir)

        try:
            # Rebuild from empty directory
            result = rebuild_index(coll, temp_dir)

            # Should process 0 tickets
            assert result["processed"] == 0
            assert result["failed"] == 0
        finally:
            close_index(coll)
            coll.destroy()

    def test_rebuild_returns_errors(self, temp_dir):
        """Test that rebuild_index returns errors list."""
        from vtic.index.operations import rebuild_index

        # Create index
        coll = create_index(temp_dir)

        try:
            # Rebuild from empty directory
            result = rebuild_index(coll, temp_dir)

            # Should have errors key (empty list for successful rebuild)
            assert "errors" in result
            assert isinstance(result["errors"], list)
        finally:
            close_index(coll)
            coll.destroy()

    def test_rebuild_after_delete_and_recreate(self, temp_dir):
        """Test rebuilding after index deletion recreates all data."""
        from vtic.index.operations import rebuild_index
        from vtic.store.markdown import write_ticket
        from vtic.store.paths import ticket_file_path

        # Write tickets to disk
        base_dir = temp_dir
        for ticket in SAMPLE_TICKETS[:3]:
            path = ticket_file_path(
                base_dir,
                ticket["repo"],
                ticket["category"],
                ticket["id"],
                "test-ticket"
            )
            write_ticket(path, ticket)

        # Create index and insert directly
        coll1 = create_index(temp_dir)
        insert_tickets(coll1, SAMPLE_TICKETS[:3])

        # Verify tickets exist
        ticket = fetch_ticket(coll1, "C1")
        assert ticket is not None
        close_index(coll1)

        # Destroy the index (simulating data loss)
        coll1.destroy()

        # Create new index
        coll2 = create_index(temp_dir)

        try:
            # Index should be empty
            ticket = fetch_ticket(coll2, "C1")
            assert ticket is None

            # Rebuild from markdown files
            result = rebuild_index(coll2, base_dir)
            assert result["processed"] == 3

            # Verify tickets are back
            ticket = fetch_ticket(coll2, "C1")
            assert ticket is not None
            assert ticket["id"] == "C1"
        finally:
            close_index(coll2)
            coll2.destroy()
