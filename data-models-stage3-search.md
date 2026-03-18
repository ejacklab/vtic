# vtic — Search Data Models (Stage 3)

Pydantic v2 models for hybrid BM25 + semantic search API.

> **Important:** This module imports enums from Stage 1 (canonical definitions). Do not redefine enums here.

---

## Imports

```python
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import canonical enums from Stage 1
# In actual implementation:
# from .enums import Severity, Status, Category
```

---

## Enums (Imported from Stage 1)

These enums are defined in `data-models-stage1-enums.md` and imported here.

```python
# Re-exported from stage1 for convenience
from .enums import (
    Severity,      # critical, high, medium, low, info
    Status,        # open, in_progress, blocked, fixed, wont_fix, closed
    Category,      # crash, hotfix, feature, security, general
)

# Literal types for source (not an enum, use Literal)
Source = Literal["bm25", "semantic", "hybrid"]
```

---

## 1. FilterSet

Structured filters for refining search queries. Uses arrays for multi-select fields.

```python
class FilterSet(BaseModel):
    """
    Query filters applied post-search.
    
    All filters are optional. When multiple filters are provided,
    they are combined with AND logic. Multi-select fields (severity, status,
    category, repo, tags) use arrays to allow OR logic within each field.
    
    Supported filter types (per OpenAPI spec):
    - Multi-select filters: severity[], status[], category[], repo[], tags[]
    - Repo glob patterns: supports '*' wildcard (e.g., 'ejacklab/*', '*/vtic')
    - Date range filters: created_after/before, updated_after/before
    - Single-select: assignee
    
    Examples:
        >>> # Filter by multiple severities (OR within field)
        >>> FilterSet(severity=[Severity.CRITICAL, Severity.HIGH])
        
        >>> # Filter by repo glob patterns
        >>> FilterSet(repo=["ejacklab/*"])
        
        >>> # Combined date range filter
        >>> FilterSet(
        ...     created_after="2024-01-01T00:00:00Z",
        ...     created_before="2024-12-31T23:59:59Z"
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "severity": ["critical", "high"],
                "status": ["open", "in_progress"],
                "repo": ["ejacklab/open-dsearch"],
                "created_after": "2024-01-01T00:00:00Z",
                "created_before": "2024-12-31T23:59:59Z"
            }
        }
    )
    
    # -- Multi-select equality filters (arrays) --
    severity: Optional[list[Severity]] = Field(
        default=None,
        description="Filter by severity levels (OR logic within this field)"
    )
    status: Optional[list[Status]] = Field(
        default=None,
        description="Filter by status values (OR logic within this field)"
    )
    category: Optional[list[Category]] = Field(
        default=None,
        description="Filter by category (OR logic within this field)"
    )
    
    # -- Repo glob patterns (array) --
    repo: Optional[list[str]] = Field(
        default=None,
        description="Filter by repo. Supports globs: 'owner/*' matches all repos under owner, "
                    "'*/repo' for repo in any owner",
        examples=[["ejacklab/open-dsearch"], ["ejacklab/*"], ["*/vtic"]]
    )
    
    # -- Tags filter (array) --
    tags: Optional[list[str]] = Field(
        default=None,
        description="Filter by tags (ticket must have ALL specified tags)"
    )
    
    # -- Single-select filters --
    assignee: Optional[str] = Field(
        default=None,
        description="Filter by assignee username"
    )
    
    # -- Date range filters (created) --
    created_after: Optional[datetime] = Field(
        default=None,
        description="Only include tickets created after this timestamp"
    )
    created_before: Optional[datetime] = Field(
        default=None,
        description="Only include tickets created before this timestamp"
    )
    
    # -- Date range filters (updated) --
    updated_after: Optional[datetime] = Field(
        default=None,
        description="Only include tickets updated after this timestamp"
    )
    
    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_patterns(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """
        Validate repository pattern formats.
        
        Rules:
        - Each pattern must be in 'owner/repo' format (exactly one '/')
        - Supports '*' as wildcard for glob matching
        """
        if v is None:
            return v
            
        validated = []
        for pattern in v:
            # Allow simple glob patterns
            if pattern == "*":
                validated.append(pattern)
                continue
                
            # Split by '/' - should have exactly 2 parts
            parts = pattern.split("/")
            if len(parts) != 2:
                raise ValueError(
                    f"Invalid repo pattern '{pattern}'. Must be in 'owner/repo' format. "
                    "Examples: 'ejacklab/open-dsearch', 'ejacklab/*', '*/vtic'"
                )
            validated.append(pattern)
        
        return validated
    
    def is_empty(self) -> bool:
        """Check if any filter is set."""
        return all([
            self.severity is None or len(self.severity) == 0,
            self.status is None or len(self.status) == 0,
            self.category is None or len(self.category) == 0,
            self.repo is None or len(self.repo) == 0,
            self.tags is None or len(self.tags) == 0,
            self.assignee is None,
            self.created_after is None,
            self.created_before is None,
            self.updated_after is None,
        ])
```

---

## 2. SearchQuery

POST /search request body.

```python
class SearchQuery(BaseModel):
    """
    Search request with hybrid BM25 + semantic options.
    
    Validation:
    - query: required, 1-500 characters
    - limit: 1-100 (default: 20)
    - offset: 0+ (default: 0)
    - sort: field name with optional '-' prefix for descending (default: -score)
    - min_score: 0.0-1.0 (default: 0.0)
    
    Examples:
        >>> # Simple keyword search
        >>> SearchQuery(query="CORS authentication error")
        
        >>> # Semantic search with filters
        >>> SearchQuery(
        ...     query="database connection timeout",
        ...     semantic=True,
        ...     filters=FilterSet(severity=[Severity.HIGH]),
        ...     limit=20
        ... )
        
        >>> # Search with sorting and pagination
        >>> SearchQuery(
        ...     query="memory leak",
        ...     sort="-created",
        ...     limit=50,
        ...     offset=100
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "CORS wildcard configuration",
                "semantic": True,
                "filters": {
                    "severity": ["critical"],
                    "status": ["open"]
                },
                "limit": 10,
                "offset": 0,
                "sort": "-score",
                "min_score": 0.01
            }
        }
    )
    
    # -- Required --
    query: str = Field(
        ...,  # required
        min_length=1,
        max_length=500,
        description="Search query string",
        examples=[
            "CORS wildcard configuration",
            "database connection timeout",
            "authentication failure after password reset",
        ]
    )
    
    # -- Optional with defaults --
    semantic: bool = Field(
        default=False,
        description="Enable semantic (vector) search in addition to BM25"
    )
    filters: Optional[FilterSet] = Field(
        default=None,
        description="Structured filters to narrow search results"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return. Default: 20."
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset. Default: 0."
    )
    sort: str = Field(
        default="-score",
        pattern=r"^-?[a-zA-Z_]+$",
        description="Sort field. Prefix with - for descending. "
                    "Default: -score (relevance). Use created, updated, severity for non-search lists."
    )
    min_score: Optional[float] = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold (0-1). Results below are excluded."
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """
        Validate and normalize search query.
        
        Rules:
        - Strip leading/trailing whitespace
        - Reject queries that are only whitespace
        """
        v = v.strip()
        
        if not v:
            raise ValueError("Query cannot be empty or contain only whitespace")
        
        return v
    
    @field_validator("sort")
    @classmethod
    def validate_sort(cls, v: str) -> str:
        """Normalize sort field."""
        return v.strip()
    
    def get_sort_field(self) -> str:
        """Get the field name without the - prefix."""
        return self.sort.lstrip("-")
    
    def is_descending(self) -> bool:
        """Check if sort is descending (starts with -)."""
        return self.sort.startswith("-")
    
    def is_semantic_enabled(self) -> bool:
        """Check if this request has semantic search enabled."""
        return self.semantic
```

---

## 3. SearchHit

Single search result representing one matching ticket.

```python
# Type alias for source (not an enum, uses Literal)
Source = Literal["bm25", "semantic", "hybrid"]


class SearchHit(BaseModel):
    """
    A single search result.
    
    Score Type and Range:
    - Type: float (double)
    - Range: 0.0 to 1.0 (inclusive)
    - 0.0 = no relevance, higher = better match
    - For hybrid search, score is normalized fusion score from BM25 + semantic
    
    The `source` indicates which search method(s) produced this result:
    - "bm25": Matched via BM25 keyword search only
    - "semantic": Matched via dense embedding (semantic) search only  
    - "hybrid": Matched via both BM25 and semantic search
    
    Examples:
        >>> SearchHit(
        ...     ticket_id="C1",
        ...     score=0.89,
        ...     source="hybrid",
        ...     highlight="The API allows wildcard CORS origins..."
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "ticket_id": "C1",
                "score": 0.89,
                "source": "hybrid",
                "bm25_score": 3.45,
                "semantic_score": 0.92,
                "highlight": "The API allows wildcard CORS origins..."
            }
        }
    )
    
    ticket_id: str = Field(
        ...,  # required
        description="Matching ticket ID",
        examples=["C1", "S42", "F12"]
    )
    score: float = Field(
        ...,  # required
        ge=0.0,
        description="Fused relevance score (higher = more relevant)"
    )
    source: Source = Field(
        ...,  # required
        description="Which search method produced this ranking"
    )
    bm25_score: Optional[float] = Field(
        default=None,
        description="BM25 score component (only in explain mode)"
    )
    semantic_score: Optional[float] = Field(
        default=None,
        description="Cosine similarity score (only in explain mode)"
    )
    highlight: Optional[str] = Field(
        default=None,
        description="Best matching snippet from ticket content",
        examples=["The API allows wildcard CORS origins..."]
    )
    
    @field_validator("score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Round score to avoid floating point noise."""
        return round(v, 6)
    
    def is_hybrid_match(self) -> bool:
        """Check if this result was found by both search methods."""
        return self.source == "hybrid"
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if this result has high confidence (score >= threshold)."""
        return self.score >= threshold
```

---

## 4. SearchMeta

Metadata about the search execution.

```python
class SearchMeta(BaseModel):
    """
    Search execution metadata.
    
    Provides information about how the search was executed,
    including weights used for fusion, timing, and request tracing.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bm25_weight": 0.6,
                "semantic_weight": 0.4,
                "latency_ms": 45,
                "semantic_used": True,
                "request_id": "req_abc123"
            }
        }
    )
    
    bm25_weight: Optional[float] = Field(
        default=None,
        description="BM25 weight used in fusion",
        examples=[0.6]
    )
    semantic_weight: Optional[float] = Field(
        default=None,
        description="Semantic weight used in fusion",
        examples=[0.4]
    )
    latency_ms: Optional[int] = Field(
        default=None,
        description="Search execution time in milliseconds"
    )
    semantic_used: Optional[bool] = Field(
        default=None,
        description="Whether semantic search was active"
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracing",
        examples=["req_abc123"]
    )
```

---

## 5. SearchResult

Full search response returned by POST /search.

```python
class SearchResult(BaseModel):
    """
    Search response with hits and metadata.
    
    Contains the matching results, total count, and metadata about the query
    execution.
    
    Examples:
        >>> # Successful search with results
        >>> SearchResult(
        ...     query="CORS error",
        ...     hits=[hit1, hit2],
        ...     total=42,
        ...     meta=SearchMeta(
        ...         bm25_weight=0.6,
        ...         semantic_weight=0.4,
        ...         latency_ms=45,
        ...         semantic_used=True
        ...     )
        ... )
        
        >>> # Empty search results
        >>> SearchResult(
        ...     query="xyznonexistent",
        ...     hits=[],
        ...     total=0,
        ...     meta=SearchMeta(semantic_used=False, latency_ms=12)
        ... )
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "authentication failure",
                "hits": [
                    {
                        "ticket_id": "C1",
                        "score": 0.89,
                        "source": "hybrid",
                        "highlight": "The API allows wildcard CORS origins..."
                    },
                    {
                        "ticket_id": "C5",
                        "score": 0.72,
                        "source": "hybrid",
                        "highlight": "Authentication fails after password reset..."
                    }
                ],
                "total": 15,
                "meta": {
                    "bm25_weight": 0.6,
                    "semantic_weight": 0.4,
                    "latency_ms": 45,
                    "semantic_used": True
                }
            }
        }
    )
    
    query: str = Field(
        ...,  # required
        description="The original query string"
    )
    hits: list[SearchHit] = Field(
        default_factory=list,
        description="Matching tickets ranked by relevance"
    )
    total: int = Field(
        ...,  # required
        ge=0,
        description="Total matching tickets (before limit/offset)"
    )
    meta: Optional[SearchMeta] = Field(
        default=None,
        description="Search execution metadata"
    )
    
    def has_results(self) -> bool:
        """Check if any results were returned."""
        return len(self.hits) > 0
    
    def get_hybrid_matches(self) -> list[SearchHit]:
        """Get only results that matched via hybrid search."""
        return [h for h in self.hits if h.is_hybrid_match()]
    
    def get_high_confidence_results(self, threshold: float = 0.8) -> list[SearchHit]:
        """Get results with score >= threshold."""
        return [h for h in self.hits if h.is_high_confidence(threshold)]
```

---

## 6. SuggestResult

Response for `/search/suggest` endpoint.

```python
class SuggestResult(BaseModel):
    """
    Autocomplete suggestion result.
    
    Used for typeahead suggestions based on partial query input.
    Returns matching ticket titles or phrases with counts.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "suggestion": "CORS wildcard issue",
                "ticket_count": 3
            }
        }
    )
    
    suggestion: str = Field(
        ...,  # required
        description="Suggested ticket title or phrase"
    )
    ticket_count: int = Field(
        ...,  # required
        ge=0,
        description="Number of tickets matching this suggestion"
    )


# The /search/suggest endpoint returns a list of SuggestResult
# GET /search/suggest?q=cors&limit=5
# Response: list[SuggestResult]
```

---

## Complete Model Summary

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `FilterSet` | Structured filters | severity[], status[], category[], repo[], tags[], assignee, created_*, updated_* |
| `SearchQuery` | POST /search body | query, semantic, filters, limit, offset, sort, min_score |
| `SearchHit` | Single hit | ticket_id (string), score, source (not match_type), highlight |
| `SearchMeta` | Execution metadata | bm25_weight, semantic_weight, latency_ms, semantic_used, request_id |
| `SearchResult` | Full response | query, hits[], total, meta |
| `SuggestResult` | Autocomplete | suggestion, ticket_count |

---

## Cross-Reference with Stage 2 (Ticket Models)

Key shared types:

| Stage 1 Type | Used In Stage 3 |
|--------------|-----------------|
| `Severity` | `FilterSet.severity[]` |
| `Status` | `FilterSet.status[]` |
| `Category` | `FilterSet.category[]` |

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
    "query": "CORS error authentication",
    "hits": [
        {
            "ticket_id": "C1",
            "score": 0.89,
            "source": "bm25",
            "highlight": "The API allows wildcard CORS origins..."
        }
    ],
    "total": 15,
    "meta": {
        "latency_ms": 23,
        "semantic_used": false
    }
}
```

### Example 2: Semantic search with filters
```python
# POST /search
{
    "query": "database connection timeout issues",
    "semantic": true,
    "filters": {
        "severity": ["critical", "high"],
        "status": ["open"],
        "repo": ["ejacklab/*"]
    },
    "limit": 20,
    "offset": 0,
    "min_score": 0.1
}
```

### Example 3: Sorting and pagination
```python
# POST /search
{
    "query": "performance regression",
    "filters": {
        "created_after": "2024-01-01T00:00:00Z",
        "created_before": "2024-06-30T23:59:59Z",
        "category": ["performance"]
    },
    "sort": "-created",
    "limit": 50,
    "offset": 100
}
```

### Example 4: Autocomplete suggestions
```python
# GET /search/suggest?q=cors&limit=5

# Response (list of SuggestResult)
[
    {"suggestion": "CORS wildcard issue", "ticket_count": 3},
    {"suggestion": "CORS configuration error", "ticket_count": 2},
    {"suggestion": "CORS preflight timeout", "ticket_count": 1}
]
```

---

## Validation Error Examples

```python
# Invalid repo pattern
FilterSet(repo=["invalid"])  # ValueError: Must be in 'owner/repo' format

# Empty query
SearchQuery(query="   ")  # ValueError: Query cannot be empty

# limit out of range  
SearchQuery(query="test", limit=200)  # ValidationError: limit <= 100

# Invalid sort pattern
SearchQuery(query="test", sort="score!")  # ValidationError: must match pattern
```

---

## Key Changes from Previous Version

### Breaking Changes:
1. **`SearchRequest` → `SearchQuery`**: Model renamed to match OpenAPI spec
2. **`topk` → `limit`**: Renamed, default changed from 10 to 20
3. **`offset` added**: New pagination field (default: 0)
4. **`sort_by`/`sort_order` → `sort`**: Combined into single string with `-` prefix
5. **`min_score` added**: New threshold field (default: 0.0)
6. **`SearchResult` (hit) → `SearchHit`**: Renamed, uses `ticket_id` string instead of `ticket` object
7. **`match_type` → `source`**: Field renamed
8. **`results` → `hits`**: Field renamed in SearchResult response
9. **`FilterSet` arrays**: Multi-select fields now use arrays instead of single values
10. **`SuggestResult` added**: New model for autocomplete endpoint

---

## Implementation Notes

1. **Enum Imports**: All enums are imported from Stage 1 (`enums.py`). Do not redefine them here.

2. **Source as Literal**: `source` uses `Literal["bm25", "semantic", "hybrid"]` rather than an enum.

3. **Score Normalization**: Hybrid search scores are normalized to 0.0-1.0 using Reciprocal Rank Fusion (RRF).

4. **Sort Format**: Sort field uses `-` prefix for descending (e.g., `-score`, `-created`, `updated`).

5. **FilterSet Arrays**: All multi-select filters (severity, status, category, repo, tags) use arrays.

6. **SearchMeta**: New nested object for execution metadata (weights, latency, request_id).
