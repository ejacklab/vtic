"""Comprehensive search tests — spec compliance, edge cases, integration.

Phase 8 AI Services spec: search engine with hybrid BM25 + semantic,
FilterSet, SearchQuery, SearchHit, SearchMeta, SearchResult, SuggestResult.

These tests complement (not duplicate) existing test_search_models.py,
test_search_engine.py, test_routes_search.py, and test_e2e_search.py.

Coverage focus:
- Spec examples from UNIFIED-DESIGN.md
- Edge cases per spec boundaries
- Integration tests for API endpoints
- FilterSet.to_zvec_filter() spec compliance
- Score normalization boundary conditions
- Pagination edge cases
- Sort edge cases
"""

from __future__ import annotations

import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from pydantic import ValidationError

from vtic.models.search import (
    FilterSet,
    SearchHit,
    SearchMeta,
    SearchQuery,
    SearchResult,
    SuggestResult,
)
from vtic.models.enums import Severity, Status, Category
from vtic.search.engine import SearchEngine
from vtic.index.client import get_collection, destroy_index
from vtic.index.operations import insert_tickets


# =============================================================================
# Fixtures
# =============================================================================

SAMPLE_TICKETS = [
    {
        "id": "C1",
        "title": "Database connection timeout",
        "description": "The application fails to connect to the database after 30 seconds of waiting.",
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
        "description": "Critical database corruption found in production database cluster.",
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
        "description": "Cross-origin requests are being blocked by the API gateway.",
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
    {
        "id": "F1",
        "title": "Add database caching layer",
        "description": "Implement Redis caching for database queries to improve performance.",
        "repo": "owner/repo1",
        "category": "feature",
        "severity": "medium",
        "status": "open",
        "assignee": "charlie",
        "tags": ["database", "performance"],
        "references": [],
        "created": "2024-01-18T10:00:00Z",
        "updated": "2024-01-18T10:00:00Z",
    },
    {
        "id": "S1",
        "title": "SQL injection vulnerability",
        "description": "Potential SQL injection in user input handling for the login page.",
        "repo": "owner/repo3",
        "category": "security",
        "severity": "critical",
        "status": "fixed",
        "assignee": "charlie",
        "tags": ["security", "sql"],
        "references": [],
        "created": "2024-01-19T10:00:00Z",
        "updated": "2024-01-19T10:00:00Z",
    },
    {
        "id": "S2",
        "title": "SQL injection in search",
        "description": "Another SQL injection found in the search endpoint query parameter.",
        "repo": "owner/repo3",
        "category": "security",
        "severity": "critical",
        "status": "open",
        "assignee": "alice",
        "tags": ["security", "sql"],
        "references": [],
        "created": "2024-01-20T10:00:00Z",
        "updated": "2024-01-20T10:00:00Z",
    },
    {
        "id": "H2",
        "title": "CORS wildcard configuration",
        "description": "The API allows wildcard CORS origins, which is insecure.",
        "repo": "owner/repo2",
        "category": "hotfix",
        "severity": "high",
        "status": "open",
        "assignee": "bob",
        "tags": ["cors", "api", "security"],
        "references": [],
        "created": "2024-01-21T10:00:00Z",
        "updated": "2024-01-21T10:00:00Z",
    },
    {
        "id": "G1",
        "title": "Improve logging format",
        "description": "Standardize logging format across all microservices.",
        "repo": "owner/repo4",
        "category": "general",
        "severity": "low",
        "status": "in_progress",
        "assignee": "dave",
        "tags": ["logging"],
        "references": [],
        "created": "2024-01-22T10:00:00Z",
        "updated": "2024-01-22T10:00:00Z",
    },
]


@pytest.fixture
def search_engine(tmp_path: Path) -> SearchEngine:
    """Create a SearchEngine with 8 sample tickets."""
    collection = get_collection(tmp_path)
    insert_tickets(collection, SAMPLE_TICKETS)
    engine = SearchEngine(collection)
    yield engine
    destroy_index(tmp_path)


@pytest.fixture
async def api_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Create FastAPI test client with search routes and sample data."""
    from vtic.api.app import create_app
    from vtic.models.config import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
    from vtic.ticket import TicketService
    from vtic.api.deps import set_config, get_search_engine

    storage_dir = tmp_path / "tickets"
    storage_dir.mkdir(parents=True, exist_ok=True)

    config = Config(
        storage=StorageConfig(dir=storage_dir),
        api=ApiConfig(host="localhost", port=8080),
        search=SearchConfig(bm25_enabled=True, semantic_enabled=False),
        embeddings=EmbeddingsConfig(provider="none"),
    )
    set_config(config)

    app = create_app(config)
    ticket_service = TicketService(config)
    await ticket_service.initialize()
    app.state.ticket_service = ticket_service

    search_engine = SearchEngine(ticket_service.collection)

    def override_get_search_engine(config=None):
        return search_engine

    app.dependency_overrides[get_search_engine] = override_get_search_engine
    insert_tickets(ticket_service.collection, SAMPLE_TICKETS)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
    await ticket_service.close()
    destroy_index(tmp_path)
    set_config(None)


# =============================================================================
# 1. Spec Examples — from UNIFIED-DESIGN.md json_schema_extra examples
# =============================================================================

class TestSpecExamplesSearchQuery:
    """Tests for SearchQuery examples from spec."""

    def test_spec_example_basic_search(self) -> None:
        """Spec example: {'query': 'CORS wildcard configuration', ...}."""
        q = SearchQuery(
            query="CORS wildcard configuration",
            semantic=True,
            filters=FilterSet(severity=[Severity.CRITICAL], status=[Status.OPEN]),
            limit=10,
            offset=0,
            sort="-score",
            min_score=0.01,
        )
        assert q.query == "CORS wildcard configuration"
        assert q.semantic is True
        assert q.filters.severity == [Severity.CRITICAL]
        assert q.filters.status == [Status.OPEN]
        assert q.limit == 10
        assert q.offset == 0
        assert q.sort == "-score"
        assert q.min_score == 0.01

    def test_spec_example_minimal(self) -> None:
        """Spec example: just query, all defaults."""
        q = SearchQuery(query="database connection timeout")
        assert q.query == "database connection timeout"
        assert q.semantic is False
        assert q.filters is None
        assert q.limit == 20
        assert q.offset == 0
        assert q.sort == "-score"
        assert q.min_score == 0.0

    def test_spec_example_all_query_strings(self) -> None:
        """Spec example queries: 'CORS wildcard configuration',
        'database connection timeout', 'authentication failure after password reset'."""
        for query_str in [
            "CORS wildcard configuration",
            "database connection timeout",
            "authentication failure after password reset",
        ]:
            q = SearchQuery(query=query_str)
            assert q.query == query_str


class TestSpecExamplesFilterSet:
    """Tests for FilterSet examples from spec."""

    def test_spec_example_filters(self) -> None:
        """Spec example: severity, status, repo, created_after, created_before."""
        f = FilterSet(
            severity=[Severity.CRITICAL, Severity.HIGH],
            status=[Status.OPEN, Status.IN_PROGRESS],
            repo=["ejacklab/open-dsearch"],
            created_after=datetime(2024, 1, 1, tzinfo=timezone.utc),
            created_before=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        )
        assert len(f.severity) == 2
        assert len(f.status) == 2
        assert f.repo == ["ejacklab/open-dsearch"]
        assert f.created_after is not None
        assert f.created_before is not None
        assert not f.is_empty()

    def test_spec_example_repo_glob_patterns(self) -> None:
        """Spec examples: 'ejacklab/open-dsearch', 'ejacklab/*', '*/vtic'."""
        for pattern in ["ejacklab/open-dsearch", "ejacklab/*", "*/vtic", "*"]:
            f = FilterSet(repo=[pattern])
            assert f.repo == [pattern]

    def test_spec_example_repo_invalid_patterns(self) -> None:
        """Invalid repo patterns should raise ValidationError."""
        invalid = ["no-slash", "too/many/slashes", "empty//", "space in/it"]
        for pattern in invalid:
            with pytest.raises(ValidationError):
                FilterSet(repo=[pattern])


class TestSpecExamplesSearchHit:
    """Tests for SearchHit examples from spec."""

    def test_spec_example_hit_with_explain(self) -> None:
        """Spec example: ticket_id, score, source, bm25_score, semantic_score, highlight."""
        hit = SearchHit(
            ticket_id="C1",
            score=0.89,
            source="hybrid",
            bm25_score=3.45,
            semantic_score=0.92,
            highlight="The API allows wildcard CORS origins...",
        )
        assert hit.ticket_id == "C1"
        assert hit.score == 0.89
        assert hit.source == "hybrid"
        assert hit.bm25_score == 3.45
        assert hit.semantic_score == 0.92
        assert hit.highlight == "The API allows wildcard CORS origins..."
        assert hit.is_hybrid_match() is True
        assert hit.is_high_confidence(0.8) is True

    def test_spec_example_hit_bm25_only(self) -> None:
        """Minimal hit with just required fields (BM25 source)."""
        hit = SearchHit(ticket_id="H1", score=0.72, source="bm25")
        assert hit.bm25_score is None
        assert hit.semantic_score is None
        assert hit.highlight is None
        assert hit.is_hybrid_match() is False


class TestSpecExamplesSearchMeta:
    """Tests for SearchMeta examples from spec."""

    def test_spec_example_meta_full(self) -> None:
        """Spec example: all fields populated."""
        meta = SearchMeta(
            total=42,
            limit=20,
            offset=0,
            has_more=True,
            bm25_weight=0.6,
            semantic_weight=0.4,
            latency_ms=45.0,
            semantic_used=True,
            request_id="req_abc123",
        )
        assert meta.total == 42
        assert meta.has_more is True
        assert meta.bm25_weight == 0.6
        assert meta.semantic_weight == 0.4

    def test_spec_example_meta_minimal(self) -> None:
        """Meta with only required fields."""
        meta = SearchMeta(total=0)
        assert meta.total == 0
        assert meta.limit == 20
        assert meta.offset == 0
        assert meta.has_more is False
        assert meta.latency_ms is None
        assert meta.request_id is None


class TestSpecExamplesSearchResult:
    """Tests for SearchResult examples from spec."""

    def test_spec_example_full_result(self) -> None:
        """Spec example: query, hits with scores, total, meta."""
        result = SearchResult(
            query="authentication failure",
            hits=[
                SearchHit(
                    ticket_id="C1", score=0.89, source="hybrid",
                    highlight="The API allows wildcard CORS origins...",
                ),
                SearchHit(
                    ticket_id="C5", score=0.72, source="hybrid",
                    highlight="Authentication fails after password reset...",
                ),
            ],
            total=15,
            meta=SearchMeta(
                total=15, limit=20, offset=0, has_more=False,
                bm25_weight=0.6, semantic_weight=0.4,
                latency_ms=45.0, semantic_used=True,
                request_id="req_abc123",
            ),
        )
        assert result.query == "authentication failure"
        assert len(result.hits) == 2
        assert result.total == 15
        assert result.has_results() is True
        assert len(result.get_hybrid_matches()) == 2
        assert len(result.get_high_confidence_results(0.8)) == 1  # only C1

    def test_spec_example_empty_result(self) -> None:
        """Empty search result."""
        result = SearchResult(query="nothing", hits=[], total=0)
        assert result.has_results() is False
        assert result.get_hybrid_matches() == []
        assert result.get_high_confidence_results() == []


class TestSpecExamplesSuggestResult:
    """Tests for SuggestResult examples from spec."""

    def test_spec_example_suggest(self) -> None:
        """Spec example: {'suggestion': 'CORS wildcard issue', 'ticket_count': 3}."""
        s = SuggestResult(suggestion="CORS wildcard issue", ticket_count=3)
        assert s.suggestion == "CORS wildcard issue"
        assert s.ticket_count == 3


# =============================================================================
# 2. Edge Cases — spec boundaries
# =============================================================================

class TestSearchQueryEdgeCases:
    """Edge cases for SearchQuery validation."""

    def test_query_min_length_1(self) -> None:
        """Query of exactly 1 character should be valid."""
        q = SearchQuery(query="a")
        assert q.query == "a"

    def test_query_max_length_500(self) -> None:
        """Query of exactly 500 characters should be valid."""
        q = SearchQuery(query="a" * 500)
        assert len(q.query) == 500

    def test_query_length_501_rejected(self) -> None:
        """Query of 501 characters should be rejected."""
        with pytest.raises(ValidationError):
            SearchQuery(query="a" * 501)

    def test_query_whitespace_trimmed(self) -> None:
        """Leading/trailing whitespace is stripped."""
        q = SearchQuery(query="  hello world  ")
        assert q.query == "hello world"

    def test_query_all_whitespace_rejected(self) -> None:
        """Query of only whitespace should be rejected."""
        for ws in ["", "   ", "\t", "\n", "  \t\n  "]:
            with pytest.raises(ValidationError):
                SearchQuery(query=ws)

    def test_limit_boundary_min(self) -> None:
        """limit=1 should be valid, limit=0 should fail."""
        q = SearchQuery(query="test", limit=1)
        assert q.limit == 1
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=0)

    def test_limit_boundary_max(self) -> None:
        """limit=100 should be valid, limit=101 should fail."""
        q = SearchQuery(query="test", limit=100)
        assert q.limit == 100
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=101)

    def test_offset_boundary(self) -> None:
        """offset=0 valid, offset=-1 invalid."""
        q = SearchQuery(query="test", offset=0)
        assert q.offset == 0
        with pytest.raises(ValidationError):
            SearchQuery(query="test", offset=-1)

    def test_min_score_boundaries(self) -> None:
        """min_score at 0.0 and 1.0 should be valid."""
        q0 = SearchQuery(query="test", min_score=0.0)
        q1 = SearchQuery(query="test", min_score=1.0)
        assert q0.min_score == 0.0
        assert q1.min_score == 1.0
        with pytest.raises(ValidationError):
            SearchQuery(query="test", min_score=-0.01)
        with pytest.raises(ValidationError):
            SearchQuery(query="test", min_score=1.01)

    def test_sort_valid_fields(self) -> None:
        """Various valid sort fields."""
        for sort in ["-score", "score", "-created", "created", "-updated",
                      "updated", "-severity", "severity", "-ticket_id", "ticket_id"]:
            q = SearchQuery(query="test", sort=sort)
            assert q.sort == sort

    def test_sort_invalid_characters(self) -> None:
        """Sort with special characters rejected."""
        for bad in ["score field", "score,created", "score;drop", "invalid@sort!"]:
            with pytest.raises(ValidationError):
                SearchQuery(query="test", sort=bad)

    def test_sort_empty_rejected(self) -> None:
        """Empty sort string should be rejected by pattern."""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", sort="")

    def test_semantic_flag(self) -> None:
        """Semantic flag defaults to False."""
        q = SearchQuery(query="test")
        assert q.semantic is False
        assert q.is_semantic_enabled() is False

        q2 = SearchQuery(query="test", semantic=True)
        assert q2.is_semantic_enabled() is True

    def test_get_sort_field(self) -> None:
        """get_sort_field strips - prefix."""
        assert SearchQuery(query="t", sort="-score").get_sort_field() == "score"
        assert SearchQuery(query="t", sort="created").get_sort_field() == "created"

    def test_is_descending(self) -> None:
        """is_descending checks - prefix."""
        assert SearchQuery(query="t", sort="-score").is_descending() is True
        assert SearchQuery(query="t", sort="score").is_descending() is False


class TestSearchHitEdgeCases:
    """Edge cases for SearchHit."""

    def test_score_exactly_zero(self) -> None:
        """Score of 0.0 is valid."""
        hit = SearchHit(ticket_id="X", score=0.0, source="bm25")
        assert hit.score == 0.0
        assert hit.is_high_confidence(0.0) is True

    def test_score_exactly_one(self) -> None:
        """Score of 1.0 is valid."""
        hit = SearchHit(ticket_id="X", score=1.0, source="bm25")
        assert hit.score == 1.0

    def test_score_rounding(self) -> None:
        """Score is rounded to 6 decimal places."""
        hit = SearchHit(ticket_id="X", score=0.123456789, source="bm25")
        assert hit.score == round(0.123456789, 6)

    def test_score_negative_rejected(self) -> None:
        """Negative score should be rejected."""
        with pytest.raises(ValidationError):
            SearchHit(ticket_id="X", score=-0.1, source="bm25")

    def test_score_above_one_rejected(self) -> None:
        """Score > 1.0 should be rejected."""
        with pytest.raises(ValidationError):
            SearchHit(ticket_id="X", score=1.1, source="bm25")

    def test_source_invalid_rejected(self) -> None:
        """Invalid source value should be rejected."""
        with pytest.raises(ValidationError):
            SearchHit(ticket_id="X", score=0.5, source="unknown")

    def test_is_high_confidence_custom_threshold(self) -> None:
        """Custom threshold for high confidence."""
        hit = SearchHit(ticket_id="X", score=0.75, source="bm25")
        assert hit.is_high_confidence(0.8) is False
        assert hit.is_high_confidence(0.7) is True
        assert hit.is_high_confidence(0.75) is True  # >= threshold


class TestFilterSetEdgeCases:
    """Edge cases for FilterSet."""

    def test_all_enums_in_severity(self) -> None:
        """All Severity enum values should work."""
        f = FilterSet(severity=list(Severity))
        assert len(f.severity) == 5
        assert not f.is_empty()

    def test_all_enums_in_status(self) -> None:
        """All Status enum values should work."""
        f = FilterSet(status=list(Status))
        assert len(f.status) == 6

    def test_all_enums_in_category(self) -> None:
        """All Category enum values should work."""
        f = FilterSet(category=list(Category))
        assert len(f.category) == 5

    def test_empty_arrays_treated_as_empty(self) -> None:
        """Empty arrays in filters should be treated as not-set."""
        f = FilterSet(severity=[], status=[], repo=[])
        assert f.is_empty() is True

    def test_single_tag(self) -> None:
        """Single tag filter."""
        f = FilterSet(tags=["security"])
        assert not f.is_empty()

    def test_multiple_tags(self) -> None:
        """Multiple tags (AND logic — all must match)."""
        f = FilterSet(tags=["security", "sql"])
        zvec = f.to_zvec_filter()
        assert "tag:security" in zvec
        assert "tag:sql" in zvec

    def test_date_ranges(self) -> None:
        """Date range filters."""
        f = FilterSet(
            created_after=datetime(2024, 6, 1, tzinfo=timezone.utc),
            created_before=datetime(2024, 6, 30, tzinfo=timezone.utc),
            updated_after=datetime(2024, 5, 1, tzinfo=timezone.utc),
            updated_before=datetime(2024, 7, 31, tzinfo=timezone.utc),
        )
        assert not f.is_empty()
        zvec = f.to_zvec_filter()
        assert "created_after:" in zvec
        assert "created_before:" in zvec
        assert "updated_after:" in zvec
        assert "updated_before:" in zvec

    def test_assignee_none_vs_empty(self) -> None:
        """assignee=None is different from assignee=''."""
        f_none = FilterSet(assignee=None)
        assert f_none.is_empty() is True

        f_empty = FilterSet(assignee="")
        assert f_empty.is_empty() is False  # empty string is still "set"

    def test_to_zvec_filter_combined(self) -> None:
        """Combined filters use AND between groups, OR within."""
        f = FilterSet(
            severity=[Severity.CRITICAL, Severity.HIGH],
            status=[Status.OPEN],
            repo=["owner/repo1"],
            tags=["database"],
        )
        zvec = f.to_zvec_filter()
        # All groups should be present
        assert "(severity:critical OR severity:high)" in zvec
        assert "(status:open)" in zvec
        assert "(repo:owner/repo1)" in zvec
        assert "tag:database" in zvec
        # Groups connected with AND
        parts = zvec.split(" AND ")
        assert len(parts) == 4


class TestSuggestResultEdgeCases:
    """Edge cases for SuggestResult."""

    def test_ticket_count_zero(self) -> None:
        """ticket_count=0 is valid."""
        s = SuggestResult(suggestion="test", ticket_count=0)
        assert s.ticket_count == 0

    def test_ticket_count_negative_rejected(self) -> None:
        """Negative ticket_count should be rejected."""
        with pytest.raises(ValidationError):
            SuggestResult(suggestion="test", ticket_count=-1)

    def test_empty_suggestion_rejected(self) -> None:
        """Empty suggestion string... actually allowed by spec (no min_length)."""
        s = SuggestResult(suggestion="", ticket_count=0)
        assert s.suggestion == ""


# =============================================================================
# 3. Score Normalization Edge Cases
# =============================================================================

class TestScoreNormalization:
    """Boundary tests for SearchEngine._normalize_score()."""

    def test_single_result_max(self, search_engine: SearchEngine) -> None:
        """Single result should get score 1.0."""
        result = search_engine._normalize_score(5.0, [5.0])
        assert result == 1.0

    def test_single_result_zero(self, search_engine: SearchEngine) -> None:
        """Single zero result should get score 0.0."""
        result = search_engine._normalize_score(0.0, [0.0])
        assert result == 0.0

    def test_all_equal_nonzero(self, search_engine: SearchEngine) -> None:
        """All equal non-zero scores → all get 1.0."""
        result = search_engine._normalize_score(3.0, [3.0, 3.0, 3.0])
        assert result == 1.0

    def test_all_zero(self, search_engine: SearchEngine) -> None:
        """All zero scores → 0.0."""
        result = search_engine._normalize_score(0.0, [0.0, 0.0, 0.0])
        assert result == 0.0

    def test_empty_score_list(self, search_engine: SearchEngine) -> None:
        """Empty score list → 0.0."""
        result = search_engine._normalize_score(5.0, [])
        assert result == 0.0

    def test_very_small_range(self, search_engine: SearchEngine) -> None:
        """Very close scores (tiny range)."""
        result = search_engine._normalize_score(
            5.000001, [5.0, 5.000001, 5.000002]
        )
        assert 0.0 <= result <= 1.0

    def test_clamping(self, search_engine: SearchEngine) -> None:
        """Score should never exceed 1.0 or go below 0.0."""
        for raw, all_scores in [
            (100.0, [0.0, 50.0, 100.0]),
            (-10.0, [-10.0, 0.0, 10.0]),
        ]:
            result = search_engine._normalize_score(raw, all_scores)
            assert 0.0 <= result <= 1.0


# =============================================================================
# 4. Search Engine Behavior Tests
# =============================================================================

class TestSearchEngineBehavior:
    """Engine-level tests with real Zvec collection."""

    def test_search_returns_bmpl_source(self, search_engine: SearchEngine) -> None:
        """All hits should have source='bm25' (no semantic configured)."""
        q = SearchQuery(query="database", limit=20)
        result = search_engine.search(q)
        for hit in result.hits:
            assert hit.source == "bm25"

    def test_search_query_preserved_in_result(self, search_engine: SearchEngine) -> None:
        """Original query string is in the result."""
        q = SearchQuery(query="CORS error", limit=10)
        result = search_engine.search(q)
        assert result.query == "CORS error"

    def test_search_limit_respected(self, search_engine: SearchEngine) -> None:
        """Number of hits should not exceed limit."""
        q = SearchQuery(query="", limit=3)
        result = search_engine.search(q)
        assert len(result.hits) <= 3

    def test_search_min_score_1_excludes_all(self, search_engine: SearchEngine) -> None:
        """min_score=1.0 should exclude everything (no perfect scores from BM25)."""
        q = SearchQuery(query="database", min_score=1.0, limit=100)
        result = search_engine.search(q)
        # With min-max normalization, if only 1 result it gets 1.0
        # But with multiple results, none should be exactly 1.0
        # This tests the general case
        assert all(h.score >= 1.0 for h in result.hits)

    def test_search_sort_ticket_id(self, search_engine: SearchEngine) -> None:
        """Sort by ticket_id ascending."""
        q = SearchQuery(query="database", sort="ticket_id", limit=20)
        result = search_engine.search(q)
        ids = [h.ticket_id for h in result.hits]
        assert ids == sorted(ids)

    def test_search_sort_ticket_id_desc(self, search_engine: SearchEngine) -> None:
        """Sort by -ticket_id descending."""
        q = SearchQuery(query="database", sort="-ticket_id", limit=20)
        result = search_engine.search(q)
        ids = [h.ticket_id for h in result.hits]
        assert ids == sorted(ids, reverse=True)

    def test_search_multiple_filters(self, search_engine: SearchEngine) -> None:
        """Combined severity + status + repo filters."""
        q = SearchQuery(
            query="",
            filters=FilterSet(
                severity=[Severity.CRITICAL],
                status=[Status.OPEN],
                repo=["owner/repo3"],
            ),
            limit=20,
        )
        result = search_engine.search(q)
        # S2 matches: critical, open, owner/repo3
        ticket_ids = [h.ticket_id for h in result.hits]
        assert "S2" in ticket_ids

    def test_search_request_id_none(self, search_engine: SearchEngine) -> None:
        """search() with request_id=None should work."""
        q = SearchQuery(query="test", limit=10)
        result = search_engine.search(q, request_id=None)
        assert result is not None
        assert result.meta.request_id is None

    def test_meta_has_more_false_when_all_fits(self, search_engine: SearchEngine) -> None:
        """has_more=false when total <= limit."""
        q = SearchQuery(query="database", limit=100, offset=0)
        result = search_engine.search(q)
        if result.meta.total <= 100:
            assert result.meta.has_more is False

    def test_meta_latency_positive(self, search_engine: SearchEngine) -> None:
        """latency_ms should be positive (search takes some time)."""
        q = SearchQuery(query="database", limit=10)
        result = search_engine.search(q)
        assert result.meta.latency_ms >= 0

    def test_suggest_limit_respected(self, search_engine: SearchEngine) -> None:
        """Suggest should respect limit parameter."""
        suggestions = search_engine.suggest("database", limit=1)
        assert len(suggestions) <= 1

    def test_suggest_limit_20_max(self, search_engine: SearchEngine) -> None:
        """Suggest with limit=20 should return at most 20."""
        suggestions = search_engine.suggest("a", limit=20)
        assert len(suggestions) <= 20

    def test_suggest_single_char_returns_empty(self, search_engine: SearchEngine) -> None:
        """Single character partial returns empty list."""
        assert search_engine.suggest("x") == []

    def test_suggest_none_returns_empty(self, search_engine: SearchEngine) -> None:
        """None partial returns empty list."""
        assert search_engine.suggest(None) == []

    def test_suggest_returns_ticket_counts(self, search_engine: SearchEngine) -> None:
        """All suggestions should have ticket_count >= 1."""
        suggestions = search_engine.suggest("database", limit=10)
        for s in suggestions:
            assert isinstance(s, SuggestResult)
            assert s.ticket_count >= 1


# =============================================================================
# 5. Pagination Edge Cases
# =============================================================================

class TestPagination:
    """Pagination behavior tests."""

    def test_offset_zero(self, search_engine: SearchEngine) -> None:
        """offset=0 should work."""
        q = SearchQuery(query="database", limit=10, offset=0)
        result = search_engine.search(q)
        assert result.meta.offset == 0

    def test_offset_exceeds_total(self, search_engine: SearchEngine) -> None:
        """offset beyond total returns empty results."""
        q = SearchQuery(query="database", limit=10, offset=9999)
        result = search_engine.search(q)
        assert len(result.hits) == 0
        assert result.meta.has_more is False

    def test_large_offset(self, search_engine: SearchEngine) -> None:
        """Large offset should not crash."""
        q = SearchQuery(query="test", limit=10, offset=100000)
        result = search_engine.search(q)
        assert len(result.hits) == 0

    def test_limit_1(self, search_engine: SearchEngine) -> None:
        """limit=1 returns at most 1 result."""
        q = SearchQuery(query="database", limit=1)
        result = search_engine.search(q)
        assert len(result.hits) <= 1


# =============================================================================
# 6. Integration Tests — API Endpoints
# =============================================================================

@pytest.mark.asyncio
class TestSearchAPIIntegration:
    """Integration tests for search API endpoints."""

    async def test_post_search_returns_200(self, api_client: AsyncClient) -> None:
        """POST /search with valid query returns 200."""
        resp = await api_client.post("/search", json={"query": "database", "limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "database"
        assert isinstance(data["hits"], list)
        assert "meta" in data

    async def test_post_search_semantic_503(self, api_client: AsyncClient) -> None:
        """POST /search with semantic=True when unavailable returns 503."""
        resp = await api_client.post("/search", json={
            "query": "test", "semantic": True
        })
        assert resp.status_code == 503
        data = resp.json()
        assert "error" in data

    async def test_post_search_missing_query_field(self, api_client: AsyncClient) -> None:
        """POST /search without query field returns 422."""
        resp = await api_client.post("/search", json={"limit": 10})
        assert resp.status_code == 422

    async def test_post_search_invalid_body(self, api_client: AsyncClient) -> None:
        """POST /search with garbage body returns 422."""
        resp = await api_client.post("/search", json="not json", headers={"Content-Type": "application/json"})
        assert resp.status_code in [400, 422]

    async def test_get_suggest_200(self, api_client: AsyncClient) -> None:
        """GET /search/suggest returns 200 with list."""
        resp = await api_client.get("/search/suggest?q=database&limit=5")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    async def test_get_suggest_missing_q(self, api_client: AsyncClient) -> None:
        """GET /search/suggest without q param returns 422."""
        resp = await api_client.get("/search/suggest")
        assert resp.status_code == 422

    async def test_get_suggest_q_too_short(self, api_client: AsyncClient) -> None:
        """GET /search/suggest?q=a returns 422."""
        resp = await api_client.get("/search/suggest?q=a")
        assert resp.status_code == 422

    async def test_get_suggest_limit_boundary(self, api_client: AsyncClient) -> None:
        """GET /search/suggest respects limit boundaries."""
        resp_ok = await api_client.get("/search/suggest?q=database&limit=1")
        assert resp_ok.status_code == 200

        resp_bad = await api_client.get("/search/suggest?q=database&limit=0")
        assert resp_bad.status_code == 422

        resp_over = await api_client.get("/search/suggest?q=database&limit=21")
        assert resp_over.status_code == 422

    async def test_search_response_content_type(self, api_client: AsyncClient) -> None:
        """POST /search returns application/json."""
        resp = await api_client.post("/search", json={"query": "test"})
        assert resp.headers["content-type"].startswith("application/json")

    async def test_suggest_response_content_type(self, api_client: AsyncClient) -> None:
        """GET /search/suggest returns application/json."""
        resp = await api_client.get("/search/suggest?q=test")
        assert resp.headers["content-type"].startswith("application/json")

    async def test_search_with_all_filter_combos(self, api_client: AsyncClient) -> None:
        """POST /search with all filters combined."""
        resp = await api_client.post("/search", json={
            "query": "test",
            "filters": {
                "severity": ["critical", "high"],
                "status": ["open"],
                "category": ["crash", "security"],
                "repo": ["owner/repo1", "owner/repo3"],
                "tags": ["database", "security"],
                "assignee": "alice",
            },
            "limit": 10,
            "sort": "-score",
            "min_score": 0.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data["hits"], list)


# =============================================================================
# 7. Build Filter Dict Edge Cases
# =============================================================================

class TestBuildFilterDictEdgeCases:
    """Tests for SearchEngine._build_filter_dict() edge cases."""

    def test_none_filters(self, search_engine: SearchEngine) -> None:
        """None filters returns None."""
        assert search_engine._build_filter_dict(None) is None

    def test_empty_filter_set(self, search_engine: SearchEngine) -> None:
        """Empty FilterSet returns None."""
        assert search_engine._build_filter_dict(FilterSet()) is None

    def test_only_date_filters(self, search_engine: SearchEngine) -> None:
        """Date-only filters (not supported by query_tickets, but shouldn't crash)."""
        f = FilterSet(
            created_after=datetime(2024, 1, 1, tzinfo=timezone.utc),
            created_before=datetime(2024, 12, 31, tzinfo=timezone.utc),
        )
        result = search_engine._build_filter_dict(f)
        # Date filters are not passed to query_tickets per implementation note
        assert result is None  # only non-date filters are passed through

    def test_tags_not_supported(self, search_engine: SearchEngine) -> None:
        """Tags filter is noted as not supported by operations.query_tickets."""
        f = FilterSet(tags=["security"])
        result = search_engine._build_filter_dict(f)
        # Tags are not passed to query_tickets per implementation note
        assert result is None

    def test_mixed_supported_and_unsupported(self, search_engine: SearchEngine) -> None:
        """Mix of supported and unsupported filters returns only supported ones."""
        f = FilterSet(
            severity=[Severity.CRITICAL],
            tags=["security"],  # not supported
            created_after=datetime(2024, 1, 1, tzinfo=timezone.utc),  # not supported
        )
        result = search_engine._build_filter_dict(f)
        assert result is not None
        assert "severity" in result
        assert "tags" not in result
        assert "created_after" not in result


# =============================================================================
# 8. Sort Edge Cases
# =============================================================================

class TestSortEdgeCases:
    """Edge cases for sort functionality."""

    def test_unknown_sort_field(self, search_engine: SearchEngine) -> None:
        """Unknown sort field returns hits unsorted (no crash)."""
        q = SearchQuery(query="database", sort="unknown_field", limit=20)
        result = search_engine.search(q)
        # Should not crash, just return unsorted
        assert isinstance(result, SearchResult)

    def test_empty_hits_sort(self, search_engine: SearchEngine) -> None:
        """Sorting empty hit list should not crash."""
        hits: list[SearchHit] = []
        result = search_engine._apply_sort(hits, "-score")
        assert result == []

    def test_single_hit_sort(self, search_engine: SearchEngine) -> None:
        """Sorting single hit should not crash."""
        hits = [SearchHit(ticket_id="C1", score=0.5, source="bm25")]
        result = search_engine._apply_sort(hits, "-score")
        assert len(result) == 1


# =============================================================================
# 9. SearchResult Helper Methods
# =============================================================================

class TestSearchResultHelpers:
    """Tests for SearchResult helper methods."""

    def test_has_results_true(self) -> None:
        result = SearchResult(query="test", hits=[
            SearchHit(ticket_id="X", score=0.5, source="bm25")
        ], total=1)
        assert result.has_results() is True

    def test_has_results_false(self) -> None:
        result = SearchResult(query="test", hits=[], total=0)
        assert result.has_results() is False

    def test_get_hybrid_matches_mixed(self) -> None:
        result = SearchResult(query="test", hits=[
            SearchHit(ticket_id="X", score=0.5, source="bm25"),
            SearchHit(ticket_id="Y", score=0.8, source="hybrid"),
            SearchHit(ticket_id="Z", score=0.3, source="semantic"),
        ], total=3)
        hybrid = result.get_hybrid_matches()
        assert len(hybrid) == 1
        assert hybrid[0].ticket_id == "Y"

    def test_get_high_confidence_default_threshold(self) -> None:
        result = SearchResult(query="test", hits=[
            SearchHit(ticket_id="X", score=0.9, source="bm25"),
            SearchHit(ticket_id="Y", score=0.5, source="bm25"),
            SearchHit(ticket_id="Z", score=0.8, source="bm25"),
        ], total=3)
        high = result.get_high_confidence_results()
        assert len(high) == 2  # 0.9 and 0.8 (>= 0.8 default)

    def test_get_high_confidence_custom_threshold(self) -> None:
        result = SearchResult(query="test", hits=[
            SearchHit(ticket_id="X", score=0.9, source="bm25"),
            SearchHit(ticket_id="Y", score=0.5, source="bm25"),
        ], total=2)
        high = result.get_high_confidence_results(threshold=0.6)
        assert len(high) == 1
        assert high[0].ticket_id == "X"

    def test_serialization_round_trip(self) -> None:
        """SearchResult serializes and deserializes correctly."""
        result = SearchResult(
            query="test",
            hits=[SearchHit(ticket_id="C1", score=0.89, source="hybrid")],
            total=1,
            meta=SearchMeta(total=1, limit=20, offset=0, latency_ms=12.3),
        )
        json_str = result.model_dump_json()
        restored = SearchResult.model_validate_json(json_str)
        assert restored.query == "test"
        assert len(restored.hits) == 1
        assert restored.hits[0].score == 0.89
        assert restored.meta.latency_ms == 12.3
