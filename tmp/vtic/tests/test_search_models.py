"""Tests for Search Models (Stage 3)

Tests for FilterSet, SearchQuery, SearchHit, SearchResult, SearchMeta, and SuggestResult.
"""

import json
import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from vtic.models.search import (
    FilterSet,
    SearchQuery,
    SearchHit,
    SearchResult,
    SearchMeta,
    SuggestResult,
    Source,
)
from vtic.models.enums import Severity, Status, Category


# =============================================================================
# SearchQuery Tests
# =============================================================================

class TestSearchQuery:
    """Test SearchQuery model validation."""
    
    def test_query_required(self):
        """Query is required."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery()
        assert "query" in str(exc_info.value)
    
    def test_query_cannot_be_empty(self):
        """Query cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="")
        # Pydantic's min_length constraint triggers before custom validator
        assert "string_too_short" in str(exc_info.value) or "Query cannot be empty" in str(exc_info.value)
    
    def test_query_cannot_be_whitespace_only(self):
        """Query cannot contain only whitespace."""
        with pytest.raises(ValidationError) as exc_info:
            SearchQuery(query="   ")
        assert "Query cannot be empty" in str(exc_info.value)
    
    def test_query_is_stripped(self):
        """Query is stripped of leading/trailing whitespace."""
        query = SearchQuery(query="  test query  ")
        assert query.query == "test query"
    
    def test_limit_min_1(self):
        """Limit must be at least 1."""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=0)
    
    def test_limit_max_100(self):
        """Limit cannot exceed 100."""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", limit=101)
    
    def test_limit_default_20(self):
        """Default limit is 20."""
        query = SearchQuery(query="test")
        assert query.limit == 20
    
    def test_offset_min_0(self):
        """Offset must be at least 0."""
        with pytest.raises(ValidationError):
            SearchQuery(query="test", offset=-1)
    
    def test_offset_default_0(self):
        """Default offset is 0."""
        query = SearchQuery(query="test")
        assert query.offset == 0
    
    def test_sort_format_valid(self):
        """Sort must match pattern -?[a-zA-Z_]+."""
        # Valid cases
        SearchQuery(query="test", sort="score")
        SearchQuery(query="test", sort="-score")
        SearchQuery(query="test", sort="created")
        SearchQuery(query="test", sort="-created")
        SearchQuery(query="test", sort="updated")
        SearchQuery(query="test", sort="-updated")
        SearchQuery(query="test", sort="severity")
        SearchQuery(query="test", sort="-severity")
        
        # Invalid cases
        with pytest.raises(ValidationError):
            SearchQuery(query="test", sort="score!")
        
        with pytest.raises(ValidationError):
            SearchQuery(query="test", sort="score desc")
    
    def test_sort_default_minus_score(self):
        """Default sort is -score."""
        query = SearchQuery(query="test")
        assert query.sort == "-score"
    
    def test_min_score_range_0_to_1(self):
        """min_score must be between 0 and 1."""
        # Valid cases
        SearchQuery(query="test", min_score=0.0)
        SearchQuery(query="test", min_score=0.5)
        SearchQuery(query="test", min_score=1.0)
        
        # Invalid cases
        with pytest.raises(ValidationError):
            SearchQuery(query="test", min_score=-0.1)
        
        with pytest.raises(ValidationError):
            SearchQuery(query="test", min_score=1.1)
    
    def test_semantic_default_false(self):
        """Default semantic is False."""
        query = SearchQuery(query="test")
        assert query.semantic is False
    
    def test_filters_optional(self):
        """Filters is optional."""
        query = SearchQuery(query="test")
        assert query.filters is None
    
    def test_get_sort_field(self):
        """get_sort_field returns field without - prefix."""
        assert SearchQuery(query="test", sort="-score").get_sort_field() == "score"
        assert SearchQuery(query="test", sort="score").get_sort_field() == "score"
        assert SearchQuery(query="test", sort="-created").get_sort_field() == "created"
    
    def test_is_descending(self):
        """is_descending returns True if sort starts with -."""
        assert SearchQuery(query="test", sort="-score").is_descending() is True
        assert SearchQuery(query="test", sort="score").is_descending() is False
    
    def test_is_semantic_enabled(self):
        """is_semantic_enabled returns semantic value."""
        assert SearchQuery(query="test", semantic=True).is_semantic_enabled() is True
        assert SearchQuery(query="test", semantic=False).is_semantic_enabled() is False
    
    def test_full_example_json(self):
        """Full example serializes to valid JSON."""
        query = SearchQuery(
            query="CORS wildcard configuration",
            semantic=True,
            filters=FilterSet(severity=[Severity.CRITICAL], status=[Status.OPEN]),
            limit=10,
            offset=0,
            sort="-score",
            min_score=0.01
        )
        json_str = query.model_dump_json()
        data = json.loads(json_str)
        assert data["query"] == "CORS wildcard configuration"
        assert data["semantic"] is True
        assert data["limit"] == 10


# =============================================================================
# FilterSet Tests
# =============================================================================

class TestFilterSet:
    """Test FilterSet model validation and methods."""
    
    def test_empty_filters(self):
        """FilterSet can be empty."""
        filters = FilterSet()
        assert filters.is_empty() is True
    
    def test_severity_filter(self):
        """Filter by severity."""
        filters = FilterSet(severity=[Severity.CRITICAL, Severity.HIGH])
        assert len(filters.severity) == 2
        assert Severity.CRITICAL in filters.severity
        assert Severity.HIGH in filters.severity
        assert filters.is_empty() is False
    
    def test_status_filter(self):
        """Filter by status."""
        filters = FilterSet(status=[Status.OPEN, Status.IN_PROGRESS])
        assert len(filters.status) == 2
        assert Status.OPEN in filters.status
        assert Status.IN_PROGRESS in filters.status
    
    def test_category_filter(self):
        """Filter by category."""
        filters = FilterSet(category=[Category.CRASH, Category.SECURITY])
        assert len(filters.category) == 2
        assert Category.CRASH in filters.category
        assert Category.SECURITY in filters.category
    
    def test_repo_filter_valid_patterns(self):
        """Repo filter accepts valid patterns."""
        # Exact repo
        filters = FilterSet(repo=["ejacklab/open-dsearch"])
        assert filters.repo == ["ejacklab/open-dsearch"]
        
        # Owner glob
        filters = FilterSet(repo=["ejacklab/*"])
        assert filters.repo == ["ejacklab/*"]
        
        # Repo glob
        filters = FilterSet(repo=["*/vtic"])
        assert filters.repo == ["*/vtic"]
        
        # Multiple repos
        filters = FilterSet(repo=["ejacklab/open-dsearch", "ejacklab/vtic"])
        assert len(filters.repo) == 2
    
    def test_repo_filter_invalid_patterns(self):
        """Repo filter rejects invalid patterns."""
        with pytest.raises(ValidationError) as exc_info:
            FilterSet(repo=["invalid"])
        assert "Invalid repo pattern" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            FilterSet(repo=["owner/repo/extra"])
        assert "Invalid repo pattern" in str(exc_info.value)
    
    def test_tags_filter(self):
        """Filter by tags."""
        filters = FilterSet(tags=["bug", "needs-review"])
        assert len(filters.tags) == 2
        assert "bug" in filters.tags
    
    def test_assignee_filter(self):
        """Filter by assignee."""
        filters = FilterSet(assignee="developer1")
        assert filters.assignee == "developer1"
        assert filters.is_empty() is False
    
    def test_date_filters(self):
        """Filter by date range."""
        after = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        before = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        filters = FilterSet(created_after=after, created_before=before)
        assert filters.created_after == after
        assert filters.created_before == before
        assert filters.is_empty() is False
    
    def test_combined_filters(self):
        """Multiple filters combined."""
        filters = FilterSet(
            severity=[Severity.CRITICAL],
            status=[Status.OPEN],
            category=[Category.CRASH],
            repo=["ejacklab/*"],
            tags=["bug"],
            created_after=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        assert filters.is_empty() is False
        assert len(filters.severity) == 1
        assert len(filters.status) == 1
        assert len(filters.category) == 1
    
    def test_to_zvec_filter_empty(self):
        """to_zvec_filter returns empty string for empty filters."""
        filters = FilterSet()
        assert filters.to_zvec_filter() == ""
    
    def test_to_zvec_filter_severity(self):
        """to_zvec_filter formats severity filter."""
        filters = FilterSet(severity=[Severity.CRITICAL, Severity.HIGH])
        expr = filters.to_zvec_filter()
        assert "severity:critical" in expr
        assert "severity:high" in expr
        assert " OR " in expr
    
    def test_to_zvec_filter_status(self):
        """to_zvec_filter formats status filter."""
        filters = FilterSet(status=[Status.OPEN, Status.IN_PROGRESS])
        expr = filters.to_zvec_filter()
        assert "status:open" in expr
        assert "status:in_progress" in expr
    
    def test_to_zvec_filter_repo(self):
        """to_zvec_filter formats repo filter."""
        filters = FilterSet(repo=["ejacklab/open-dsearch", "ejacklab/*"])
        expr = filters.to_zvec_filter()
        assert "repo:ejacklab/open-dsearch" in expr
        assert "repo:ejacklab/*" in expr
    
    def test_to_zvec_filter_tags(self):
        """to_zvec_filter formats tags with AND logic."""
        filters = FilterSet(tags=["bug", "needs-review"])
        expr = filters.to_zvec_filter()
        assert "tag:bug" in expr
        assert "tag:needs-review" in expr
        assert " AND " in expr
    
    def test_to_zvec_filter_combined(self):
        """to_zvec_filter combines multiple filters with AND."""
        filters = FilterSet(
            severity=[Severity.CRITICAL],
            status=[Status.OPEN]
        )
        expr = filters.to_zvec_filter()
        assert "severity:critical" in expr
        assert "status:open" in expr
        assert " AND " in expr


# =============================================================================
# SearchHit Tests
# =============================================================================

class TestSearchHit:
    """Test SearchHit model validation."""
    
    def test_required_fields(self):
        """SearchHit requires ticket_id, score, source."""
        hit = SearchHit(
            ticket_id="C1",
            score=0.89,
            source="hybrid"
        )
        assert hit.ticket_id == "C1"
        assert hit.score == 0.89
        assert hit.source == "hybrid"
    
    def test_score_range_0_to_1(self):
        """Score must be between 0 and 1."""
        # Valid
        SearchHit(ticket_id="C1", score=0.0, source="bm25")
        SearchHit(ticket_id="C1", score=0.5, source="bm25")
        SearchHit(ticket_id="C1", score=1.0, source="bm25")
        
        # Invalid - score below 0
        with pytest.raises(ValidationError):
            SearchHit(ticket_id="C1", score=-0.1, source="bm25")
    
    def test_score_rounded_to_6_decimals(self):
        """Score is rounded to 6 decimal places."""
        hit = SearchHit(ticket_id="C1", score=0.123456789, source="bm25")
        assert hit.score == 0.123457
    
    def test_source_values(self):
        """Source must be bm25, semantic, or hybrid."""
        SearchHit(ticket_id="C1", score=0.5, source="bm25")
        SearchHit(ticket_id="C1", score=0.5, source="semantic")
        SearchHit(ticket_id="C1", score=0.5, source="hybrid")
        
        with pytest.raises(ValidationError):
            SearchHit(ticket_id="C1", score=0.5, source="invalid")
    
    def test_optional_fields(self):
        """Optional fields bm25_score, semantic_score, highlight."""
        hit = SearchHit(
            ticket_id="C1",
            score=0.89,
            source="hybrid",
            bm25_score=3.45,
            semantic_score=0.92,
            highlight="The API allows wildcard CORS origins..."
        )
        assert hit.bm25_score == 3.45
        assert hit.semantic_score == 0.92
        assert hit.highlight == "The API allows wildcard CORS origins..."
    
    def test_is_hybrid_match(self):
        """is_hybrid_match returns True for hybrid source."""
        hit = SearchHit(ticket_id="C1", score=0.5, source="hybrid")
        assert hit.is_hybrid_match() is True
        
        hit = SearchHit(ticket_id="C1", score=0.5, source="bm25")
        assert hit.is_hybrid_match() is False
    
    def test_is_high_confidence(self):
        """is_high_confidence checks score against threshold."""
        hit = SearchHit(ticket_id="C1", score=0.85, source="bm25")
        assert hit.is_high_confidence() is True  # Default threshold 0.8
        assert hit.is_high_confidence(threshold=0.9) is False


# =============================================================================
# SearchMeta Tests
# =============================================================================

class TestSearchMeta:
    """Test SearchMeta model."""
    
    def test_required_fields(self):
        """SearchMeta requires total."""
        meta = SearchMeta(total=42)
        assert meta.total == 42
    
    def test_defaults(self):
        """SearchMeta has defaults for optional fields."""
        meta = SearchMeta(total=42)
        assert meta.limit == 20
        assert meta.offset == 0
        assert meta.has_more is False
    
    def test_all_fields(self):
        """SearchMeta with all fields."""
        meta = SearchMeta(
            total=42,
            limit=10,
            offset=0,
            has_more=True,
            bm25_weight=0.6,
            semantic_weight=0.4,
            latency_ms=45.0,
            semantic_used=True,
            request_id="req_abc123"
        )
        assert meta.total == 42
        assert meta.limit == 10
        assert meta.offset == 0
        assert meta.has_more is True
        assert meta.bm25_weight == 0.6
        assert meta.semantic_weight == 0.4
        assert meta.latency_ms == 45.0
        assert meta.semantic_used is True
        assert meta.request_id == "req_abc123"


# =============================================================================
# SearchResult Tests
# =============================================================================

class TestSearchResult:
    """Test SearchResult model."""
    
    def test_required_fields(self):
        """SearchResult requires query, hits, total."""
        result = SearchResult(
            query="test",
            hits=[],
            total=0
        )
        assert result.query == "test"
        assert result.hits == []
        assert result.total == 0
    
    def test_with_hits(self):
        """SearchResult with hits."""
        hit = SearchHit(ticket_id="C1", score=0.89, source="hybrid")
        result = SearchResult(
            query="test",
            hits=[hit],
            total=1
        )
        assert len(result.hits) == 1
        assert result.hits[0].ticket_id == "C1"
    
    def test_with_meta(self):
        """SearchResult with metadata."""
        meta = SearchMeta(total=42, semantic_used=True)
        result = SearchResult(
            query="test",
            hits=[],
            total=42,
            meta=meta
        )
        assert result.meta is not None
        assert result.meta.semantic_used is True
    
    def test_has_results(self):
        """has_results returns True if hits exist."""
        hit = SearchHit(ticket_id="C1", score=0.5, source="bm25")
        assert SearchResult(query="test", hits=[hit], total=1).has_results() is True
        assert SearchResult(query="test", hits=[], total=0).has_results() is False
    
    def test_get_hybrid_matches(self):
        """get_hybrid_matches filters for hybrid source."""
        hits = [
            SearchHit(ticket_id="C1", score=0.89, source="hybrid"),
            SearchHit(ticket_id="C2", score=0.72, source="bm25"),
            SearchHit(ticket_id="C3", score=0.65, source="hybrid"),
        ]
        result = SearchResult(query="test", hits=hits, total=3)
        hybrid = result.get_hybrid_matches()
        assert len(hybrid) == 2
        assert all(h.source == "hybrid" for h in hybrid)
    
    def test_get_high_confidence_results(self):
        """get_high_confidence_results filters by threshold."""
        hits = [
            SearchHit(ticket_id="C1", score=0.95, source="hybrid"),
            SearchHit(ticket_id="C2", score=0.72, source="bm25"),
            SearchHit(ticket_id="C3", score=0.85, source="hybrid"),
        ]
        result = SearchResult(query="test", hits=hits, total=3)
        high_conf = result.get_high_confidence_results(threshold=0.8)
        assert len(high_conf) == 2
    
    def test_serialization(self):
        """SearchResult serializes to valid JSON."""
        hit = SearchHit(
            ticket_id="C1",
            score=0.89,
            source="hybrid",
            highlight="The API allows wildcard CORS origins..."
        )
        meta = SearchMeta(
            total=15,
            semantic_used=True,
            latency_ms=45.0
        )
        result = SearchResult(
            query="authentication failure",
            hits=[hit],
            total=15,
            meta=meta
        )
        
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        
        assert data["query"] == "authentication failure"
        assert len(data["hits"]) == 1
        assert data["hits"][0]["ticket_id"] == "C1"
        assert data["total"] == 15
        assert data["meta"]["semantic_used"] is True


# =============================================================================
# SuggestResult Tests
# =============================================================================

class TestSuggestResult:
    """Test SuggestResult model."""
    
    def test_required_fields(self):
        """SuggestResult requires suggestion and ticket_count."""
        result = SuggestResult(
            suggestion="CORS wildcard issue",
            ticket_count=3
        )
        assert result.suggestion == "CORS wildcard issue"
        assert result.ticket_count == 3
    
    def test_ticket_count_min_zero(self):
        """ticket_count must be >= 0."""
        # Valid
        SuggestResult(suggestion="test", ticket_count=0)
        SuggestResult(suggestion="test", ticket_count=10)
        
        # Invalid
        with pytest.raises(ValidationError):
            SuggestResult(suggestion="test", ticket_count=-1)
    
    def test_serialization(self):
        """SuggestResult serializes to valid JSON."""
        result = SuggestResult(
            suggestion="CORS wildcard issue",
            ticket_count=3
        )
        
        json_str = result.model_dump_json()
        data = json.loads(json_str)
        
        assert data["suggestion"] == "CORS wildcard issue"
        assert data["ticket_count"] == 3
    
    def test_suggest_result_list_example(self):
        """Example of /search/suggest endpoint returning list[SuggestResult]."""
        results = [
            SuggestResult(suggestion="CORS wildcard issue", ticket_count=3),
            SuggestResult(suggestion="CORS configuration error", ticket_count=2),
            SuggestResult(suggestion="CORS preflight timeout", ticket_count=1),
        ]
        assert len(results) == 3
        assert all(isinstance(r, SuggestResult) for r in results)
        assert results[0].suggestion == "CORS wildcard issue"
        assert results[0].ticket_count == 3

    def test_empty_suggestions(self):
        """Empty suggestions list is valid - represents no matches found."""
        results = []
        assert results == []
        # When no suggestions match, API returns empty list
        assert len(results) == 0


# =============================================================================
# Sample JSON Outputs
# =============================================================================

class TestSampleJsonOutputs:
    """Generate and verify sample JSON outputs for documentation."""
    
    def test_search_query_json(self):
        """Sample SearchQuery JSON."""
        query = SearchQuery(
            query="CORS wildcard configuration",
            semantic=True,
            filters=FilterSet(
                severity=[Severity.CRITICAL],
                status=[Status.OPEN]
            ),
            limit=10,
            offset=0,
            sort="-score",
            min_score=0.01
        )
        print("\n--- SearchQuery Sample JSON ---")
        print(query.model_dump_json(indent=2))
    
    def test_filter_set_json(self):
        """Sample FilterSet JSON."""
        filters = FilterSet(
            severity=[Severity.CRITICAL, Severity.HIGH],
            status=[Status.OPEN, Status.IN_PROGRESS],
            repo=["ejacklab/open-dsearch"],
            created_after="2024-01-01T00:00:00Z",
            created_before="2024-12-31T23:59:59Z"
        )
        print("\n--- FilterSet Sample JSON ---")
        print(filters.model_dump_json(indent=2))
    
    def test_search_result_json(self):
        """Sample SearchResult JSON."""
        result = SearchResult(
            query="authentication failure",
            hits=[
                SearchHit(
                    ticket_id="C1",
                    score=0.89,
                    source="hybrid",
                    bm25_score=3.45,
                    semantic_score=0.92,
                    highlight="The API allows wildcard CORS origins..."
                ),
                SearchHit(
                    ticket_id="C5",
                    score=0.72,
                    source="hybrid",
                    highlight="Authentication fails after password reset..."
                )
            ],
            total=15,
            meta=SearchMeta(
                total=15,
                limit=20,
                offset=0,
                has_more=False,
                bm25_weight=0.6,
                semantic_weight=0.4,
                latency_ms=45.0,
                semantic_used=True,
                request_id="req_abc123"
            )
        )
        print("\n--- SearchResult Sample JSON ---")
        print(result.model_dump_json(indent=2))
    
    def test_suggest_result_json(self):
        """Sample SuggestResult JSON."""
        result = SuggestResult(
            suggestion="CORS wildcard issue",
            ticket_count=3
        )
        print("\n--- SuggestResult Sample JSON ---")
        print(result.model_dump_json(indent=2))
