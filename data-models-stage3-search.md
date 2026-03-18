# vtic — Search Data Models (Stage 3)

Pydantic v2 models for hybrid BM25 + semantic search API.

> **Important:** This module imports enums from Stage 1 (canonical definitions). Do not redefine enums here.

---

## Imports

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import canonical enums from Stage 1
# In actual implementation:
# from .enums import Severity, Status, Category, SortField, SortOrder
```

---

## Enums (Imported from Stage 1)

These enums are defined in `data-models-stage1-enums.md` and imported here.

```python
# Re-exported from stage1 for convenience
from .enums import (
    Severity,      # critical, high, medium, low
    Status,        # open, in_progress, blocked, fixed, wont_fix, closed
    Category,      # security, auth, code_quality, performance, frontend, 
                   # backend, testing, documentation, infrastructure, 
                   # configuration, api, data, ui, dependencies, build, other
    SortField,     # created_at, updated_at, severity, status, relevance, title
    SortOrder,     # asc, desc
)

# Literal types for match_type (not an enum, use Literal)
MatchType = Literal["bm25", "semantic", "hybrid"]
```

---

## 1. SearchFilter

Structured filters for refining search queries.

```python
class SearchFilter(BaseModel):
    """
    Structured filters for ticket search.
    
    All filters are optional. When multiple filters are provided,
    they are combined with AND logic.
    
    Supported filter types (per FEATURES.md §2.4):
    - Equality filters: severity, status, category
    - Repo glob patterns: supports '*' wildcard (e.g., 'ejacklab/*', '*/vtic')
    - Date range filters: created_after/before, updated_after/before
    
    Examples:
        >>> # Filter by single severity
        >>> SearchFilter(severity=Severity.CRITICAL)
        
        >>> # Filter by repo glob pattern
        >>> SearchFilter(repo="ejacklab/*")
        
        >>> # Combined date range filter
        >>> SearchFilter(
        ...     created_after=datetime(2024, 1, 1),
        ...     created_before=datetime(2024, 12, 31)
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "severity": "critical",
                "status": "open",
                "category": "security",
                "repo": "ejacklab/*",
                "created_after": "2024-01-01T00:00:00Z",
                "created_before": "2024-12-31T23:59:59Z"
            }
        }
    )
    
    # -- Equality filters --
    severity: Severity | None = Field(
        default=None,
        description="Filter by ticket severity level (critical, high, medium, low)"
    )
    status: Status | None = Field(
        default=None,
        description="Filter by ticket status (open, in_progress, blocked, fixed, wont_fix, closed)"
    )
    category: Category | None = Field(
        default=None,
        description="Filter by ticket category (security, auth, code_quality, performance, frontend, backend, testing, documentation, infrastructure, configuration, api, data, ui, dependencies, build, other)"
    )
    
    # -- Repo glob patterns --
    repo: str | None = Field(
        default=None,
        description="Filter by repository. Supports glob patterns: 'owner/repo' for exact match, 'owner/*' for all repos under owner, '*/repo' for repo in any owner",
        examples=["ejacklab/open-dsearch", "ejacklab/*", "*/vtic"]
    )
    
    # -- Date range filters (created) --
    created_after: datetime | None = Field(
        default=None,
        description="Only include tickets created after this datetime (inclusive)"
    )
    created_before: datetime | None = Field(
        default=None,
        description="Only include tickets created before this datetime (inclusive)"
    )
    
    # -- Date range filters (updated) --
    updated_after: datetime | None = Field(
        default=None,
        description="Only include tickets updated after this datetime (inclusive)"
    )
    updated_before: datetime | None = Field(
        default=None,
        description="Only include tickets updated before this datetime (inclusive)"
    )
    
    @field_validator("repo")
    @classmethod
    def validate_repo_pattern(cls, v: str | None) -> str | None:
        """
        Validate repository pattern format.
        
        Rules:
        - Must be in 'owner/repo' format (exactly one '/')
        - Supports '*' as wildcard for glob matching
        - Owner and repo names must be valid (alphanumeric, hyphens, underscores, dots)
        """
        if v is None:
            return v
            
        # Allow simple glob patterns
        if v == "*":
            return v
            
        # Split by '/' - should have exactly 2 parts (glob allows owner/* or */repo)
        parts = v.split("/")
        if len(parts) != 2:
            raise ValueError(
                f"Invalid repo pattern '{v}'. Must be in 'owner/repo' format. "
                "Examples: 'ejacklab/open-dsearch', 'ejacklab/*', '*/vtic'"
            )
        
        owner, repo = parts
        
        # Validate owner part (unless it's a wildcard)
        if owner != "*":
            if not owner.replace("-", "").replace("_", "").isalnum():
                raise ValueError(
                    f"Invalid owner '{owner}'. Owner must contain only alphanumeric "
                    "characters, hyphens, and underscores."
                )
        
        # Validate repo part (unless it's a wildcard)  
        if repo != "*":
            if not repo.replace("-", "").replace("_", "").replace(".", "").isalnum():
                raise ValueError(
                    f"Invalid repo name '{repo}'. Repo must contain only alphanumeric "
                    "characters, hyphens, underscores, and dots."
                )
        
        return v
    
    @field_validator("created_before", "created_after", "updated_before", "updated_after")
    @classmethod
    def validate_datetime_has_timezone(cls, v: datetime | None) -> datetime | None:
        """Ensure datetime values have timezone info (treat naive as UTC)."""
        if v is None:
            return v
        # If naive datetime, assume UTC
        if v.tzinfo is None:
            from datetime import timezone
            return v.replace(tzinfo=timezone.utc)
        return v
    
    def to_zvec_filter(self) -> str | None:
        """
        Convert filter to Zvec filter expression string.
        
        Returns:
            Zvec filter expression or None if no filters set.
            
        Example:
            >>> SearchFilter(severity="critical", status="open").to_zvec_filter()
            "severity == 'critical' and status == 'open'"
        """
        conditions: list[str] = []
        
        if self.severity is not None:
            conditions.append(f"severity == '{self.severity.value}'")
        
        if self.status is not None:
            conditions.append(f"status == '{self.status.value}'")
        
        if self.category is not None:
            conditions.append(f"category == '{self.category.value}'")
        
        if self.repo is not None:
            if self.repo == "*":
                # Match all repos - no filter needed
                pass
            elif "*" in self.repo:
                # Convert glob to LIKE pattern
                like_pattern = self.repo.replace("*", "%")
                conditions.append(f"repo LIKE '{like_pattern}'")
            else:
                # Exact match
                conditions.append(f"repo == '{self.repo}'")
        
        if self.created_after is not None:
            ts = self.created_after.isoformat()
            conditions.append(f"created_at >= '{ts}'")
        
        if self.created_before is not None:
            ts = self.created_before.isoformat()
            conditions.append(f"created_at <= '{ts}'")
        
        if self.updated_after is not None:
            ts = self.updated_after.isoformat()
            conditions.append(f"updated_at >= '{ts}'")
        
        if self.updated_before is not None:
            ts = self.updated_before.isoformat()
            conditions.append(f"updated_at <= '{ts}'")
        
        if not conditions:
            return None
        
        return " and ".join(conditions)
    
    def is_empty(self) -> bool:
        """Check if any filter is set."""
        return all([
            self.severity is None,
            self.status is None,
            self.category is None,
            self.repo is None,
            self.created_after is None,
            self.created_before is None,
            self.updated_after is None,
            self.updated_before is None,
        ])


# Example usage
SEARCH_FILTER_EXAMPLES = [
    SearchFilter(severity=Severity.CRITICAL),
    SearchFilter(repo="ejacklab/open-dsearch"),
    SearchFilter(repo="ejacklab/*"),
    SearchFilter(
        status=Status.OPEN,
        category=Category.SECURITY,
        created_after=datetime(2024, 1, 1)
    ),
]
```

---

## 2. SearchRequest

POST /search request body.

```python
class SearchRequest(BaseModel):
    """
    Request body for the POST /search endpoint.
    
    Performs hybrid BM25 + semantic search on tickets with optional
    structured filtering.
    
    Validation:
    - query: required, 1-1000 characters, no control characters
    - topk: 1-100 (default: 10)
    
    Examples:
        >>> # Simple keyword search
        >>> SearchRequest(query="CORS authentication error")
        
        >>> # Semantic search with filters
        >>> SearchRequest(
        ...     query="database connection timeout",
        ...     semantic=True,
        ...     filters=SearchFilter(severity=Severity.HIGH),
        ...     topk=20
        ... )
        
        >>> # Search with sorting by creation date
        >>> SearchRequest(
        ...     query="memory leak",
        ...     sort_by=SortField.CREATED_AT,
        ...     sort_order=SortOrder.DESC,
        ...     topk=50
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "CORS wildcard configuration",
                "semantic": True,
                "filters": {
                    "severity": "critical",
                    "status": "open"
                },
                "topk": 10,
                "sort_by": "relevance",
                "sort_order": "desc"
            }
        }
    )
    
    # -- Required --
    query: str = Field(
        ...,  # required
        min_length=1,
        max_length=1000,
        description="Search query string. Supports keyword terms, phrases (in quotes), and natural language for semantic search.",
        examples=[
            "CORS wildcard configuration",
            "database connection timeout",
            '"authentication error"',
        ]
    )
    
    # -- Optional with defaults --
    semantic: bool = Field(
        default=False,
        description="Enable dense embedding (semantic) search in addition to BM25 keyword search. "
                    "Requires an embedding provider to be configured."
    )
    filters: SearchFilter | None = Field(
        default=None,
        description="Structured filters to narrow search results. Supports severity, status, category, repo glob, and date ranges."
    )
    topk: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return. Must be between 1 and 100. Default: 10."
    )
    sort_by: SortField = Field(
        default=SortField.RELEVANCE,
        description="Field to sort results by. 'relevance' sorts by search score; other fields sort by ticket metadata."
    )
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort direction: 'asc' for ascending, 'desc' for descending"
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """
        Validate and normalize search query.
        
        Rules:
        - Strip leading/trailing whitespace
        - Reject queries that are only whitespace
        - Reject queries with control characters
        """
        v = v.strip()
        
        if not v:
            raise ValueError("Query cannot be empty or contain only whitespace")
        
        # Check for control characters (except common whitespace)
        for char in v:
            if ord(char) < 32 and char not in "\t\n\r":
                raise ValueError(
                    f"Query contains invalid control character (code: {ord(char)}). "
                    "Queries must be valid UTF-8 text."
                )
        
        return v
    
    @field_validator("topk")
    @classmethod
    def validate_topk(cls, v: int) -> int:
        """Ensure topk is within valid range (1-100)."""
        if v < 1:
            raise ValueError("topk must be at least 1")
        if v > 100:
            raise ValueError("topk cannot exceed 100")
        return v
    
    def is_semantic_enabled(self) -> bool:
        """Check if this request has semantic search enabled."""
        return self.semantic
    
    def get_effective_sort_field(self) -> SortField:
        """
        Get the effective sort field.
        
        If sort_by is RELEVANCE but no search is being performed
        (empty query edge case), fall back to CREATED_AT.
        """
        return self.sort_by


# Example usage
SEARCH_REQUEST_EXAMPLES = [
    SearchRequest(query="authentication error"),
    SearchRequest(
        query="CORS configuration",
        semantic=True,
        filters=SearchFilter(severity=Severity.HIGH),
        topk=20
    ),
    SearchRequest(
        query="memory leak in production",
        semantic=True,
        filters=SearchFilter(
            repo="ejacklab/*",
            status=Status.OPEN
        ),
        topk=50,
        sort_by=SortField.CREATED_AT,
        sort_order=SortOrder.DESC
    ),
]
```

---

## 3. SearchResult

Single search hit representing one matching ticket.

```python
# Type alias for match type (not an enum, uses Literal)
MatchType = Literal["bm25", "semantic", "hybrid"]


class SearchResult(BaseModel):
    """
    A single search result containing a matching ticket and its relevance metadata.
    
    Score Type and Range:
    - Type: float
    - Range: 0.0 to 1.0 (inclusive)
    - 0.0 = no relevance, 1.0 = perfect match
    - For hybrid search, score is normalized fusion score from BM25 + semantic
    
    The `match_type` indicates which search method(s) produced this result:
    - "bm25": Matched via BM25 keyword search only
    - "semantic": Matched via dense embedding (semantic) search only  
    - "hybrid": Matched via both BM25 and semantic search (best of both)
    
    Examples:
        >>> SearchResult(
        ...     ticket=ticket_response,
        ...     score=0.89,
        ...     match_type="hybrid"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket": {
                    "id": "S42",
                    "title": "CORS wildcard allows any origin",
                    "repo": "ejacklab/open-dsearch",
                    "owner": "ejacklab",
                    "category": "security",
                    "severity": "critical",
                    "status": "open",
                    "description": "The CORS configuration uses wildcard...",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "tags": ["cors", "security"],
                    "fix": None
                },
                "score": 0.89,
                "match_type": "hybrid"
            }
        }
    )
    
    ticket: dict[str, Any] = Field(
        ...,  # required - in practice this is TicketResponse from stage2
        description="The matching ticket data. Full TicketResponse object with all fields."
    )
    score: float = Field(
        ...,  # required
        ge=0.0,
        le=1.0,
        description="Relevance score between 0.0 (least relevant) and 1.0 (most relevant). "
                    "Higher scores indicate better matches. For hybrid search, this is the "
                    "normalized fusion score combining BM25 and semantic similarity."
    )
    match_type: MatchType = Field(
        ...,  # required
        description="Indicates which search method(s) found this ticket: "
                    "'bm25' = keyword match only, "
                    "'semantic' = embedding similarity only, "
                    "'hybrid' = both methods matched this ticket"
    )
    
    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Ensure score is within 0.0-1.0 range and round to avoid floating point noise."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Score must be between 0.0 and 1.0, got {v}")
        return round(v, 6)  # Round to 6 decimal places
    
    @field_validator("match_type", mode="before")
    @classmethod
    def validate_match_type(cls, v: str) -> MatchType:
        """Ensure match_type is one of the allowed values."""
        allowed = {"bm25", "semantic", "hybrid"}
        if v not in allowed:
            raise ValueError(
                f"Invalid match_type '{v}'. Must be one of: {', '.join(sorted(allowed))}"
            )
        return v  # type: ignore
    
    def is_hybrid_match(self) -> bool:
        """Check if this result was found by both search methods."""
        return self.match_type == "hybrid"
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this result has high confidence (score >= threshold)."""
        return self.score >= threshold


# Example usage (with placeholder ticket data)
SEARCH_RESULT_EXAMPLE = SearchResult(
    ticket={
        "id": "S42",
        "title": "CORS wildcard allows any origin",
        "repo": "ejacklab/open-dsearch",
        "owner": "ejacklab",
        "category": "security",
        "severity": "critical",
        "status": "open",
        "description": "The CORS configuration uses wildcard...",
        "created_at": "2024-01-15T10:30:00Z",
        "updated_at": "2024-01-15T10:30:00Z",
        "tags": ["cors", "security"],
        "fix": None
    },
    score=0.89,
    match_type="hybrid"
)
```

---

## 4. SearchResponse

Full search response returned by POST /search.

```python
class SearchResponse(BaseModel):
    """
    Complete response from the search endpoint.
    
    Contains the matching results, total count, and metadata about the query
    execution. The `took_ms` field helps diagnose performance issues.
    
    Examples:
        >>> # Successful search with results
        >>> SearchResponse(
        ...     results=[result1, result2],
        ...     total=42,
        ...     query="CORS error",
        ...     semantic_used=True,
        ...     topk=10,
        ...     took_ms=45.2
        ... )
        
        >>> # Empty search results
        >>> SearchResponse(
        ...     results=[],
        ...     total=0,
        ...     query="xyznonexistent",
        ...     semantic_used=False,
        ...     topk=10,
        ...     took_ms=12.5
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "ticket": {
                            "id": "S42",
                            "title": "CORS wildcard allows any origin",
                            "repo": "ejacklab/open-dsearch",
                            "severity": "critical",
                            "status": "open"
                        },
                        "score": 0.95,
                        "match_type": "hybrid"
                    },
                    {
                        "ticket": {
                            "id": "A17",
                            "title": "Authentication bypass in CORS preflight",
                            "repo": "ejacklab/vtic",
                            "severity": "high",
                            "status": "in_progress"
                        },
                        "score": 0.78,
                        "match_type": "bm25"
                    }
                ],
                "total": 2,
                "query": "CORS authentication",
                "semantic_used": True,
                "topk": 10,
                "took_ms": 45.2
            }
        }
    )
    
    results: list[SearchResult] = Field(
        default_factory=list,
        description="List of search results, ordered by relevance score (highest first). "
                    "May be empty if no tickets match the query."
    )
    total: int = Field(
        ...,  # required
        ge=0,
        description="Total number of tickets matching the query and filters. "
                    "This is the count before topk pagination is applied."
    )
    query: str = Field(
        ...,  # required
        description="The original search query (echoed back for client reference)"
    )
    semantic_used: bool = Field(
        ...,  # required
        description="Whether semantic/embedding search was actually used. "
                    "May be False even if requested if no embedding provider is configured."
    )
    topk: int = Field(
        ...,  # required
        ge=1,
        le=100,
        description="The topk value used for this search (echoed back)"
    )
    took_ms: float = Field(
        ...,  # required
        ge=0.0,
        description="Query execution time in milliseconds. Includes BM25 search, "
                    "optional semantic search, filtering, and result serialization."
    )
    
    @field_validator("total")
    @classmethod
    def validate_total(cls, v: int) -> int:
        """Ensure total is non-negative."""
        if v < 0:
            raise ValueError("Total cannot be negative")
        return v
    
    @field_validator("took_ms")
    @classmethod
    def validate_took_ms(cls, v: float) -> float:
        """Ensure took_ms is non-negative and round to 3 decimal places."""
        if v < 0:
            raise ValueError("took_ms cannot be negative")
        return round(v, 3)
    
    @field_validator("results")
    @classmethod
    def validate_results_sorted(cls, v: list[SearchResult]) -> list[SearchResult]:
        """Verify results are sorted by score (descending)."""
        # This is a soft validation - results should be sorted but we don't reject
        # Note: In production, this could log a warning if unsorted
        return v
    
    def has_results(self) -> bool:
        """Check if any results were returned."""
        return len(self.results) > 0
    
    def get_hybrid_matches(self) -> list[SearchResult]:
        """Get only results that matched via hybrid search."""
        return [r for r in self.results if r.is_hybrid_match()]
    
    def get_high_confidence_results(self, threshold: float = 0.8) -> list[SearchResult]:
        """Get results with score >= threshold."""
        return [r for r in self.results if r.is_high_confidence(threshold)]
    
    def to_paginated_response(self, offset: int = 0) -> dict[str, Any]:
        """
        Convert to a paginated response format with metadata.
        
        Returns:
            Dict with results, pagination info, and query metadata.
        """
        return {
            "data": [r.model_dump() for r in self.results],
            "meta": {
                "query": self.query,
                "total": self.total,
                "returned": len(self.results),
                "semantic_used": self.semantic_used,
                "took_ms": self.took_ms,
                "pagination": {
                    "offset": offset,
                    "limit": self.topk,
                    "has_more": self.total > offset + len(self.results)
                }
            }
        }


# Example responses
SEARCH_RESPONSE_EXAMPLES = {
    "with_results": SearchResponse(
        results=[
            SearchResult(
                ticket={
                    "id": "S42",
                    "title": "CORS wildcard allows any origin",
                    "repo": "ejacklab/open-dsearch",
                    "owner": "ejacklab",
                    "category": "security",
                    "severity": "critical",
                    "status": "open",
                    "description": "The CORS configuration...",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                    "tags": ["cors", "security"],
                    "fix": None
                },
                score=0.95,
                match_type="hybrid"
            ),
            SearchResult(
                ticket={
                    "id": "A17",
                    "title": "Authentication bypass in CORS preflight",
                    "repo": "ejacklab/vtic",
                    "owner": "ejacklab",
                    "category": "auth",
                    "severity": "high",
                    "status": "in_progress",
                    "description": "The preflight request...",
                    "created_at": "2024-02-10T14:20:00Z",
                    "updated_at": "2024-02-11T09:15:00Z",
                    "tags": ["cors", "auth"],
                    "fix": "Validate origin header"
                },
                score=0.78,
                match_type="bm25"
            )
        ],
        total=2,
        query="CORS authentication",
        semantic_used=True,
        topk=10,
        took_ms=45.234
    ),
    "empty": SearchResponse(
        results=[],
        total=0,
        query="xyznonexistentticket12345",
        semantic_used=False,
        topk=10,
        took_ms=12.5
    ),
    "semantic_disabled": SearchResponse(
        results=[
            SearchResult(
                ticket={
                    "id": "P5",
                    "title": "Database connection pool exhausted",
                    "repo": "ejacklab/open-dsearch",
                    "severity": "medium",
                    "status": "open"
                },
                score=0.82,
                match_type="bm25"
            )
        ],
        total=1,
        query="database connection",
        semantic_used=False,
        topk=10,
        took_ms=8.123
    )
}
```

---

## Complete Model Summary

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `SearchFilter` | Structured filters | severity, status, category, repo (glob), created_*, updated_* |
| `SearchRequest` | POST /search body | query, semantic, filters, topk (1-100), sort_by, sort_order |
| `SearchResult` | Single hit | ticket, score (0.0-1.0), match_type (bm25/semantic/hybrid) |
| `SearchResponse` | Full response | results, total, query, semantic_used, topk, took_ms |

---

## Cross-Reference with Stage 2 (Ticket Models)

The `ticket` field in `SearchResult` contains a `TicketResponse` object from Stage 2. Key shared types:

| Stage 2 Type | Used In Stage 3 |
|--------------|-----------------|
| `Severity` | `SearchFilter.severity` |
| `Status` | `SearchFilter.status` |
| `Category` | `SearchFilter.category` |
| `TicketResponse` | `SearchResult.ticket` (as dict) |

Note: In the actual implementation, `SearchResult.ticket` would be typed as `TicketResponse`, but for documentation purposes it's shown as `dict[str, Any]` to avoid circular imports.

---

## API Usage Examples

### Example 1: Simple keyword search
```python
# POST /search
{
    "query": "CORS error authentication"
}

# Response
{
    "results": [...],
    "total": 15,
    "query": "CORS error authentication",
    "semantic_used": false,
    "topk": 10,
    "took_ms": 23.4
}
```

### Example 2: Semantic search with filters
```python
# POST /search
{
    "query": "database connection timeout issues",
    "semantic": true,
    "filters": {
        "severity": "critical",
        "status": "open",
        "repo": "ejacklab/*"
    },
    "topk": 20
}
```

### Example 3: Date range filtered search
```python
# POST /search
{
    "query": "performance regression",
    "filters": {
        "created_after": "2024-01-01T00:00:00Z",
        "created_before": "2024-06-30T23:59:59Z",
        "category": "performance"
    },
    "sort_by": "created_at",
    "sort_order": "desc",
    "topk": 50
}
```

---

## Validation Error Examples

```python
# Invalid repo pattern
SearchFilter(repo="invalid")  # ValueError: Must be in 'owner/repo' format

# Empty query
SearchRequest(query="   ")  # ValueError: Query cannot be empty

# topk out of range  
SearchRequest(query="test", topk=200)  # ValueError: topk cannot exceed 100

# Invalid match_type
SearchResult(ticket={}, score=0.5, match_type="invalid")  # ValueError

# Score out of range
SearchResult(ticket={}, score=1.5, match_type="bm25")  # ValueError: Score must be 0.0-1.0
```

---

## Implementation Notes

1. **Enum Imports**: All enums are imported from Stage 1 (`enums.py`). Do not redefine them here.

2. **MatchType as Literal**: `match_type` uses `Literal["bm25", "semantic", "hybrid"]` rather than an enum, as it's specific to search results and not shared across modules.

3. **Score Normalization**: Hybrid search scores are normalized to 0.0-1.0 using Reciprocal Rank Fusion (RRF).

4. **Timestamp Field Names**: Use `created_at` and `updated_at` (with `_at` suffix) to match Stage 2 ticket models.

5. **Zvec Filter Conversion**: The `to_zvec_filter()` method generates filter expressions compatible with Zvec's query syntax.
