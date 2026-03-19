"""VTIC Search Models (Stage 3)

Pydantic v2 models for hybrid BM25 + semantic search API.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict

# Import canonical enums from Stage 1
from .enums import Severity, Status, Category

# Type alias for source (not an enum, use Literal)
Source = Literal["bm25", "semantic", "hybrid"]


# -----------------------------------------------------------------------------
# FilterSet
# -----------------------------------------------------------------------------

class FilterSet(BaseModel):
    """
    Query filters applied post-search.
    
    All filters are optional. When multiple filters are provided,
    they are combined with AND logic. Multi-select fields (severity, status,
    category, repo, tags) use arrays to allow OR logic within each field.
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
    updated_before: Optional[datetime] = Field(
        default=None,
        description="Only include tickets updated before this timestamp"
    )
    
    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_patterns(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        """Validate repository pattern formats."""
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
            self.updated_before is None,
        ])
    
    def to_zvec_filter(self) -> str:
        """
        Build a Zvec filter expression from the filters.
        
        Returns a filter string in Zvec format.
        """
        if self.is_empty():
            return ""
        
        parts = []
        
        # Multi-select filters with OR logic within
        if self.severity:
            sev_values = " OR ".join(f"severity:{s.value}" for s in self.severity)
            parts.append(f"({sev_values})")
        
        if self.status:
            stat_values = " OR ".join(f"status:{s.value}" for s in self.status)
            parts.append(f"({stat_values})")
        
        if self.category:
            cat_values = " OR ".join(f"category:{c.value}" for c in self.category)
            parts.append(f"({cat_values})")
        
        if self.repo:
            repo_values = " OR ".join(f"repo:{r}" for r in self.repo)
            parts.append(f"({repo_values})")
        
        if self.tags:
            # Tags require ALL (AND logic)
            for tag in self.tags:
                parts.append(f"tag:{tag}")
        
        if self.assignee:
            parts.append(f"assignee:{self.assignee}")
        
        # Date range filters
        if self.created_after:
            parts.append(f"created_after:{self.created_after.isoformat()}")
        
        if self.created_before:
            parts.append(f"created_before:{self.created_before.isoformat()}")
        
        if self.updated_after:
            parts.append(f"updated_after:{self.updated_after.isoformat()}")
        
        if self.updated_before:
            parts.append(f"updated_before:{self.updated_before.isoformat()}")
        
        # Combine all with AND
        return " AND ".join(parts)


# -----------------------------------------------------------------------------
# SearchQuery
# -----------------------------------------------------------------------------

class SearchQuery(BaseModel):
    """
    Search request with hybrid BM25 + semantic options.
    
    Validation:
    - query: required, 1-500 characters
    - limit: 1-100 (default: 20)
    - offset: 0+ (default: 0)
    - sort: field name with optional '-' prefix for descending (default: -score)
    - min_score: 0.0-1.0 (default: 0.0)
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
        ...,
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
    min_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score threshold (0-1). Results below are excluded."
    )
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Validate and normalize search query."""
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


# -----------------------------------------------------------------------------
# SearchHit
# -----------------------------------------------------------------------------

class SearchHit(BaseModel):
    """
    A single search result.
    
    Score Type and Range:
    - Type: float (double)
    - Range: 0.0 to 1.0 (inclusive)
    - 0.0 = no relevance, higher = better match
    - For hybrid search, score is normalized fusion score from BM25 + semantic
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
        ...,
        description="Matching ticket ID",
        examples=["C1", "S42", "F12"]
    )
    score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fused relevance score (higher = more relevant)"
    )
    source: Source = Field(
        ...,
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


# -----------------------------------------------------------------------------
# SearchMeta
# -----------------------------------------------------------------------------

class SearchMeta(BaseModel):
    """
    Search execution metadata.
    
    Provides information about how the search was executed,
    including weights used for fusion, timing, and request tracing.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 42,
                "limit": 20,
                "offset": 0,
                "has_more": True,
                "bm25_weight": 0.6,
                "semantic_weight": 0.4,
                "latency_ms": 45.0,
                "semantic_used": True,
                "request_id": "req_abc123"
            }
        }
    )
    
    total: int = Field(
        ...,
        ge=0,
        description="Total matching tickets (before limit/offset)"
    )
    limit: int = Field(
        default=20,
        ge=1,
        description="Maximum number of results per page"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Pagination offset"
    )
    has_more: bool = Field(
        default=False,
        description="Whether more results are available"
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
    latency_ms: Optional[float] = Field(
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


# -----------------------------------------------------------------------------
# SearchResult
# -----------------------------------------------------------------------------

class SearchResult(BaseModel):
    """
    Search response with hits and metadata.
    
    Contains the matching results, total count, and metadata about the query
    execution.
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
                    "total": 15,
                    "limit": 20,
                    "offset": 0,
                    "has_more": False,
                    "bm25_weight": 0.6,
                    "semantic_weight": 0.4,
                    "latency_ms": 45.0,
                    "semantic_used": True,
                    "request_id": "req_abc123"
                }
            }
        }
    )
    
    query: str = Field(
        ...,
        description="The original query string"
    )
    hits: list[SearchHit] = Field(
        default_factory=list,
        description="Matching tickets ranked by relevance"
    )
    total: int = Field(
        ...,
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


# -----------------------------------------------------------------------------
# SuggestResult
# -----------------------------------------------------------------------------

class SuggestResult(BaseModel):
    """
    Autocomplete suggestion result.
    
    Used for typeahead suggestions based on partial query input.
    Returns matching ticket titles or phrases with counts.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "cor",
                "suggestions": [
                    "CORS wildcard issue",
                    "CORS configuration error",
                    "core dump analysis"
                ]
            }
        }
    )
    
    query: str = Field(
        ...,
        description="The original query string"
    )
    suggestions: list[str] = Field(
        default_factory=list,
        description="List of suggested completions"
    )
