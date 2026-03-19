"""SearchEngine for vtic ticket search.

Provides a higher-level search interface wrapping index operations.
"""

from __future__ import annotations

import time
from collections import Counter
from typing import Any

from zvec import Collection

from vtic.models.search import (
    FilterSet,
    SearchHit,
    SearchMeta,
    SearchQuery,
    SearchResult,
    SuggestResult,
)
from vtic.index.operations import query_tickets


class SearchEngine:
    """
    Higher-level search interface wrapping index operations.
    
    Responsibilities:
    - Convert SearchQuery model → zvec query parameters
    - Build filter expressions from FilterSet
    - Format results into SearchHit + SearchMeta
    - Track latency_ms timing
    
    Thread-safe: Each instance holds no mutable state beyond the Collection reference.
    """
    
    def __init__(self, collection: Collection) -> None:
        """
        Initialize search engine with a Zvec collection.
        
        Args:
            collection: Zvec collection for ticket search.
        """
        self._collection = collection
    
    def search(
        self,
        query: SearchQuery,
        request_id: str | None = None,
    ) -> SearchResult:
        """
        Execute a search query.
        
        Args:
            query: SearchQuery model with all parameters.
            request_id: Optional request ID for tracing.
            
        Returns:
            SearchResult with hits, total, and metadata.
            
        Notes:
            - Calls operations.query_tickets() internally
            - Applies min_score filtering post-search
            - Handles sort field normalization
            - Calculates latency_ms in metadata
        """
        # Start timer
        start_time = time.perf_counter()
        
        # Build filter dict from FilterSet
        filters = self._build_filter_dict(query.filters)
        
        # Call operations.query_tickets
        raw_results = query_tickets(
            collection=self._collection,
            query=query.query,
            filters=filters,
            limit=query.limit,
            offset=query.offset,
        )
        
        # Calculate latency
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Get all raw scores for normalization
        all_raw_scores = [r.get("score", 0.0) for r in raw_results]
        
        # Build SearchHit list with normalized scores
        hits: list[SearchHit] = []
        for result in raw_results:
            raw_score = result.get("score", 0.0)
            normalized_score = self._normalize_score(raw_score, all_raw_scores)
            
            # Skip if below min_score
            if normalized_score < query.min_score:
                continue
            
            hit = SearchHit(
                ticket_id=result.get("id", ""),
                score=round(normalized_score, 6),
                source="bm25",
            )
            hits.append(hit)
        
        # Apply sort if not default (-score, which is what BM25 returns)
        if query.sort != "-score":
            hits = self._apply_sort(hits, query.sort)
        
        # Calculate total (before limit/offset, but after min_score filter)
        total = len(hits)
        
        # Build SearchMeta
        meta = SearchMeta(
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=total > query.offset + query.limit,
            latency_ms=round(latency_ms, 3),
            request_id=request_id,
        )
        
        # Return SearchResult
        return SearchResult(
            query=query.query,
            hits=hits,
            total=total,
            meta=meta,
        )
    
    def suggest(
        self,
        partial: str,
        limit: int = 5,
    ) -> list[SuggestResult]:
        """
        Get autocomplete suggestions for partial query.
        
        Args:
            partial: Partial query string (min 2 chars).
            limit: Maximum suggestions to return (1-20, default 5).
            
        Returns:
            List of SuggestResult with matching ticket titles/phrases.
            
        Notes:
            - Uses BM25 prefix matching on ticket titles
            - Groups by title, counts occurrences
        """
        if not partial or len(partial) < 2:
            return []
        
        # Query index with partial string (as a prefix search)
        # We fetch more results to get better grouping
        results = query_tickets(
            collection=self._collection,
            query=partial,
            filters=None,
            limit=50,  # Fetch more for better grouping
            offset=0,
        )
        
        # Group by title prefix and count occurrences
        title_counter: Counter[str] = Counter()
        
        for result in results:
            title = result.get("title", "")
            if title:
                # Use title as the suggestion
                title_counter[title] += 1
        
        # Get top N suggestions by count
        top_titles = title_counter.most_common(limit)
        
        # Build SuggestResult list
        suggestions: list[SuggestResult] = []
        for title, count in top_titles:
            suggestions.append(
                SuggestResult(
                    suggestion=title,
                    ticket_count=count,
                )
            )
        
        return suggestions
    
    def _build_filter_dict(self, filters: FilterSet | None) -> dict[str, Any] | None:
        """
        Convert FilterSet to dict for operations.query_tickets().
        
        Args:
            filters: FilterSet model or None.
            
        Returns:
            Dict suitable for operations.query_tickets() or None.
        """
        if filters is None or filters.is_empty():
            return None
        
        filter_dict: dict[str, Any] = {}
        
        # Multi-value filters (arrays)
        if filters.severity:
            filter_dict["severity"] = [s.value for s in filters.severity]
        
        if filters.status:
            filter_dict["status"] = [s.value for s in filters.status]
        
        if filters.category:
            filter_dict["category"] = [c.value for c in filters.category]
        
        if filters.repo:
            filter_dict["repo"] = filters.repo
        
        # Single-value filters
        if filters.assignee:
            filter_dict["assignee"] = filters.assignee
        
        # Note: tags and date range filters are not directly supported
        # by operations.query_tickets(). They would need post-filtering
        # or additional index support.
        
        return filter_dict if filter_dict else None
    
    def _normalize_score(self, raw_score: float, all_scores: list[float]) -> float:
        """
        Normalize BM25 score to 0.0-1.0 range using min-max scaling.
        
        Args:
            raw_score: The raw BM25 score to normalize.
            all_scores: List of all raw scores in the result set.
            
        Returns:
            Normalized score between 0.0 and 1.0.
        """
        if not all_scores:
            return 0.0
        
        min_score = min(all_scores)
        max_score = max(all_scores)
        
        # Handle edge cases
        if max_score == min_score:
            return 1.0 if raw_score > 0 else 0.0
        
        # Min-max normalization
        normalized = (raw_score - min_score) / (max_score - min_score)
        
        # Clamp to [0.0, 1.0] to handle any floating point issues
        return max(0.0, min(1.0, normalized))
    
    def _apply_sort(
        self,
        hits: list[SearchHit],
        sort: str,
    ) -> list[SearchHit]:
        """
        Sort hits by field with - prefix for descending.
        
        Args:
            hits: List of SearchHit objects.
            sort: Sort field. Prefix with - for descending.
            
        Returns:
            Sorted list of SearchHit objects.
        """
        if not hits:
            return hits
        
        # Determine sort direction
        descending = sort.startswith("-")
        field = sort.lstrip("-")
        
        # Currently, SearchHit only has ticket_id and score fields
        # Other sort fields would require fetching additional ticket data
        # For now, support sorting by score (default) and ticket_id
        
        if field == "score":
            reverse = descending  # -score means descending
            return sorted(hits, key=lambda h: h.score, reverse=reverse)
        elif field == "ticket_id":
            reverse = descending
            return sorted(hits, key=lambda h: h.ticket_id, reverse=reverse)
        
        # For other fields (created, updated, severity), we'd need to fetch
        # the full ticket data. For now, return as-is.
        return hits
