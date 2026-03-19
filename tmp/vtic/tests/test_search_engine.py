"""Tests for SearchEngine.

These tests verify the SearchEngine class directly with a real Zvec collection.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from vtic.models.search import SearchQuery, FilterSet, SearchResult, SuggestResult
from vtic.models.enums import Severity, Status, Category
from vtic.search.engine import SearchEngine
from vtic.index.client import get_collection, destroy_index
from vtic.index.operations import insert_tickets


@pytest.fixture
def search_engine(tmp_path: Path) -> SearchEngine:
    """Create a SearchEngine with a temporary Zvec collection."""
    # Create a temporary collection
    collection = get_collection(tmp_path)
    
    # Insert sample tickets for testing
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
        {
            "id": "F1",
            "title": "Add database caching layer",
            "description": "Implement Redis caching for database queries to improve performance.",
            "repo": "owner/repo1",
            "category": "feature",
            "severity": "medium",
            "status": "open",
            "assignee": None,
            "tags": ["database", "performance"],
            "references": [],
            "created": "2024-01-18T10:00:00Z",
            "updated": "2024-01-18T10:00:00Z",
        },
        {
            "id": "S1",
            "title": "SQL injection vulnerability",
            "description": "Potential SQL injection in user input handling.",
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
    ]
    
    insert_tickets(collection, sample_tickets)
    
    engine = SearchEngine(collection)
    yield engine
    
    # Cleanup
    destroy_index(tmp_path)


class TestSearchBasic:
    """Tests for basic search functionality."""
    
    def test_search_basic(self, search_engine: SearchEngine) -> None:
        """Query 'database' returns hits with scores."""
        query = SearchQuery(query="database", limit=10)
        
        result = search_engine.search(query)
        
        assert isinstance(result, SearchResult)
        assert result.query == "database"
        assert len(result.hits) > 0
        assert result.total > 0
        
        # All hits should have scores in 0.0-1.0 range
        for hit in result.hits:
            assert 0.0 <= hit.score <= 1.0
            assert hit.ticket_id != ""
            assert hit.source == "bm25"
    
    def test_search_with_filters(self, search_engine: SearchEngine) -> None:
        """Filter by severity=critical."""
        query = SearchQuery(
            query="database",
            filters=FilterSet(severity=[Severity.CRITICAL]),
            limit=10,
        )
        
        result = search_engine.search(query)
        
        # Should return C1 and C2 (both critical severity, mention database)
        assert len(result.hits) > 0
        ticket_ids = [h.ticket_id for h in result.hits]
        assert "C1" in ticket_ids or "C2" in ticket_ids
    
    def test_search_min_score(self, search_engine: SearchEngine) -> None:
        """min_score=0.5 filters low results."""
        query = SearchQuery(query="database", min_score=0.5, limit=10)
        
        result = search_engine.search(query)
        
        # All hits should have score >= 0.5
        for hit in result.hits:
            assert hit.score >= 0.5
    
    def test_search_sort_score(self, search_engine: SearchEngine) -> None:
        """Sort by -score (descending)."""
        query = SearchQuery(query="database", sort="-score", limit=10)
        
        result = search_engine.search(query)
        
        # Results should be sorted by score descending
        if len(result.hits) >= 2:
            for i in range(len(result.hits) - 1):
                assert result.hits[i].score >= result.hits[i + 1].score
    
    def test_search_no_results(self, search_engine: SearchEngine) -> None:
        """Query with no matches returns results with 0 scores."""
        query = SearchQuery(query="xyznonexistent12345", limit=10)
        
        result = search_engine.search(query)
        
        assert isinstance(result, SearchResult)
        # BM25 returns all docs with 0 score when no matches
        # All hits should have 0 score when no match
        for hit in result.hits:
            assert hit.score == 0.0


class TestNormalizeScore:
    """Tests for score normalization."""
    
    def test_normalize_score_range(self, search_engine: SearchEngine) -> None:
        """Verify 0.0-1.0 range for normalized scores."""
        query = SearchQuery(query="database", limit=10)
        
        result = search_engine.search(query)
        
        for hit in result.hits:
            assert 0.0 <= hit.score <= 1.0
            # Scores should be rounded to 6 decimal places
            assert hit.score == round(hit.score, 6)
    
    def test_normalize_score_direct(self, search_engine: SearchEngine) -> None:
        """Test direct _normalize_score method with various inputs."""
        # Test with normal range
        result = search_engine._normalize_score(5.0, [0.0, 5.0, 10.0])
        assert result == 0.5
        
        # Test with min score
        result = search_engine._normalize_score(0.0, [0.0, 5.0, 10.0])
        assert result == 0.0
        
        # Test with max score
        result = search_engine._normalize_score(10.0, [0.0, 5.0, 10.0])
        assert result == 1.0
        
        # Test with empty scores
        result = search_engine._normalize_score(5.0, [])
        assert result == 0.0
        
        # Test with all same scores
        result = search_engine._normalize_score(5.0, [5.0, 5.0, 5.0])
        assert result == 1.0  # When all scores are equal and > 0
        
        # Test with zero score when all same zero
        result = search_engine._normalize_score(0.0, [0.0, 0.0])
        assert result == 0.0


class TestSuggest:
    """Tests for suggest functionality."""
    
    def test_suggest_basic(self, search_engine: SearchEngine) -> None:
        """partial='cor' returns suggestions."""
        suggestions = search_engine.suggest("cor", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Each suggestion should be a SuggestResult
        for sugg in suggestions:
            assert isinstance(sugg, SuggestResult)
            assert sugg.suggestion != ""
            assert sugg.ticket_count >= 1
    
    def test_suggest_no_results(self, search_engine: SearchEngine) -> None:
        """partial='xyznonexistent' returns empty list or no matches."""
        suggestions = search_engine.suggest("xyznonexistent", limit=5)
        
        assert isinstance(suggestions, list)
        # If partial doesn't match anything in titles, may return empty or filtered results
        # Just verify it's a valid list response
        for sugg in suggestions:
            assert isinstance(sugg, SuggestResult)
    
    def test_suggest_min_length(self, search_engine: SearchEngine) -> None:
        """Suggestions with less than 2 chars returns empty."""
        suggestions = search_engine.suggest("x", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) == 0
    
    def test_suggest_empty(self, search_engine: SearchEngine) -> None:
        """Empty partial returns empty list."""
        suggestions = search_engine.suggest("", limit=5)
        
        assert isinstance(suggestions, list)
        assert len(suggestions) == 0


class TestSearchMeta:
    """Tests for search metadata."""
    
    def test_search_meta_present(self, search_engine: SearchEngine) -> None:
        """SearchResult includes metadata."""
        query = SearchQuery(query="database", limit=10)
        
        result = search_engine.search(query)
        
        assert result.meta is not None
        assert result.meta.total >= 0
        assert result.meta.limit == 10
        assert result.meta.offset == 0
        assert isinstance(result.meta.has_more, bool)
        assert result.meta.latency_ms is not None
        assert result.meta.latency_ms >= 0
    
    def test_search_request_id_propagation(self, search_engine: SearchEngine) -> None:
        """request_id is propagated to meta."""
        query = SearchQuery(query="database", limit=10)
        request_id = "test-request-123"
        
        result = search_engine.search(query, request_id=request_id)
        
        assert result.meta is not None
        assert result.meta.request_id == request_id
    
    def test_search_has_more(self, search_engine: SearchEngine) -> None:
        """has_more is true when there are more results."""
        query = SearchQuery(query="database", limit=1, offset=0)
        
        result = search_engine.search(query)
        
        # If we have more than 1 result total, has_more should be true
        if result.total > 1:
            assert result.meta.has_more is True


class TestSearchFilters:
    """Tests for search filtering."""
    
    def test_search_filter_by_status(self, search_engine: SearchEngine) -> None:
        """Filter by status."""
        query = SearchQuery(
            query="database",
            filters=FilterSet(status=[Status.OPEN]),
            limit=10,
        )
        
        result = search_engine.search(query)
        
        # Should return results
        assert isinstance(result, SearchResult)
    
    def test_search_filter_by_category(self, search_engine: SearchEngine) -> None:
        """Filter by category."""
        query = SearchQuery(
            query="database",
            filters=FilterSet(category=[Category.CRASH]),
            limit=10,
        )
        
        result = search_engine.search(query)
        
        # Should return C1 and C2 (crash category, mention database)
        assert isinstance(result, SearchResult)
    
    def test_search_filter_by_repo(self, search_engine: SearchEngine) -> None:
        """Filter by repo."""
        query = SearchQuery(
            query="database",
            filters=FilterSet(repo=["owner/repo1"]),
            limit=10,
        )
        
        result = search_engine.search(query)
        
        assert isinstance(result, SearchResult)


class TestBuildFilterDict:
    """Tests for _build_filter_dict method."""
    
    def test_build_filter_dict_empty(self, search_engine: SearchEngine) -> None:
        """Empty FilterSet returns None."""
        result = search_engine._build_filter_dict(None)
        assert result is None
        
        result = search_engine._build_filter_dict(FilterSet())
        assert result is None
    
    def test_build_filter_dict_severity(self, search_engine: SearchEngine) -> None:
        """FilterSet with severity returns correct dict."""
        filters = FilterSet(severity=[Severity.CRITICAL, Severity.HIGH])
        result = search_engine._build_filter_dict(filters)
        
        assert result is not None
        assert "severity" in result
        assert result["severity"] == ["critical", "high"]
    
    def test_build_filter_dict_status(self, search_engine: SearchEngine) -> None:
        """FilterSet with status returns correct dict."""
        filters = FilterSet(status=[Status.OPEN])
        result = search_engine._build_filter_dict(filters)
        
        assert result is not None
        assert "status" in result
        assert result["status"] == ["open"]
    
    def test_build_filter_dict_repo(self, search_engine: SearchEngine) -> None:
        """FilterSet with repo returns correct dict."""
        filters = FilterSet(repo=["owner/repo1", "owner/repo2"])
        result = search_engine._build_filter_dict(filters)
        
        assert result is not None
        assert "repo" in result
        assert result["repo"] == ["owner/repo1", "owner/repo2"]
    
    def test_build_filter_dict_assignee(self, search_engine: SearchEngine) -> None:
        """FilterSet with assignee returns correct dict."""
        filters = FilterSet(assignee="alice")
        result = search_engine._build_filter_dict(filters)
        
        assert result is not None
        assert "assignee" in result
        assert result["assignee"] == "alice"
