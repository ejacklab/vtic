"""Core data models for vtic."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Generic, Literal, Optional, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Severity(StrEnum):
    """Ticket severity levels indicating impact and urgency."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Status(StrEnum):
    """Ticket lifecycle statuses."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    CLOSED = "closed"


class Category(StrEnum):
    """Ticket categorization for organization and routing."""

    SECURITY = "security"
    AUTH = "auth"
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    FRONTEND = "frontend"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    CONFIGURATION = "configuration"
    API = "api"
    DATA = "data"
    UI = "ui"
    DEPENDENCIES = "dependencies"
    BUILD = "build"
    OTHER = "other"


SeverityLiteral = Literal["critical", "high", "medium", "low"]
StatusLiteral = Literal["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"]
CategoryLiteral = Literal[
    "security",
    "auth",
    "code_quality",
    "performance",
    "frontend",
    "testing",
    "documentation",
    "infrastructure",
    "configuration",
    "api",
    "data",
    "ui",
    "dependencies",
    "build",
    "other",
]

CATEGORY_PREFIXES: dict[Category, str] = {
    Category.CODE_QUALITY: "C",
    Category.SECURITY: "S",
    Category.AUTH: "A",
    Category.INFRASTRUCTURE: "I",
    Category.DOCUMENTATION: "D",
    Category.TESTING: "T",
    Category.PERFORMANCE: "P",
    Category.FRONTEND: "F",
    Category.CONFIGURATION: "N",
    Category.API: "X",
    Category.DATA: "M",
    Category.UI: "U",
    Category.DEPENDENCIES: "Y",
    Category.BUILD: "B",
    Category.OTHER: "O",
}


class VticBaseModel(BaseModel):
    """Base model with common configuration for all vtic models."""

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",
    )


class Ticket(VticBaseModel):
    """Core ticket entity representing a single issue or task."""

    id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z]\d+$",
        description="Unique ticket ID (e.g., C1, S2, A3)",
    )
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    repo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in 'owner/repo' format",
    )
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: Optional[str] = Field(
        default=None,
        max_length=500,
        pattern=r"^[^:]+(:\d+(-\d+)?)?$",
        description="File reference (path:line or path:start-end).",
    )
    tags: list[str] = Field(default_factory=list, description="Searchable tags (validator enforces max 50 items)")
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe slug for filename",
    )

    @field_validator("id", mode="before")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        v = v.upper()
        if not re.match(r"^[A-Z]\d+$", v):
            raise ValueError(f"Invalid ID format: {v}. Expected: prefix + digits (e.g., C1, S2)")
        return v

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        parts = v.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        return v.lower()

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 tags")
        normalized: list[str] = []
        seen: set[str] = set()
        for tag in v:
            clean = tag.lower().strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self

    @staticmethod
    def _slugify(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", text.lower())
        slug = slug.strip("-")
        slug = re.sub(r"-+", "-", slug)
        return slug[:100]

    @property
    def is_terminal(self) -> bool:
        return self.status in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)

    @property
    def filename(self) -> str:
        return f"{self.id}-{self.slug}.md"

    @property
    def filepath(self) -> str:
        return f"{self.repo}/{self.category.value}/{self.filename}"

    @property
    def search_text(self) -> str:
        parts = [self.title, self.description or "", self.fix or "", " ".join(self.tags)]
        return " ".join(parts)


class TicketCreate(VticBaseModel):
    """Request body for creating a new ticket."""

    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    repo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in 'owner/repo' format",
    )
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: Optional[str] = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, description="Searchable tags (max 50 items)")

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        return v.lower()


class TicketUpdate(VticBaseModel):
    """Request body for updating an existing ticket."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Optional[Category] = Field(default=None)
    severity: Optional[Severity] = Field(default=None)
    status: Optional[Status] = Field(default=None)
    file: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[list[str]] = Field(default=None, description="Searchable tags (max 50 items)")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v if v else v


class TicketResponse(VticBaseModel):
    """API response model for ticket data."""

    id: str
    title: str
    description: Optional[str] = None
    fix: Optional[str] = None
    repo: str
    owner: Optional[str] = None
    category: str
    severity: str
    status: str
    file: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    slug: str
    is_terminal: bool
    filename: str
    filepath: str

    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse":
        return cls(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            fix=ticket.fix,
            repo=ticket.repo,
            owner=ticket.owner,
            category=ticket.category.value,
            severity=ticket.severity.value,
            status=ticket.status.value,
            file=ticket.file,
            tags=ticket.tags,
            created_at=ticket.created_at.isoformat(),
            updated_at=ticket.updated_at.isoformat(),
            slug=ticket.slug,
            is_terminal=ticket.is_terminal,
            filename=ticket.filename,
            filepath=ticket.filepath,
        )


class SearchFilters(VticBaseModel):
    """Filter parameters for ticket search."""

    severity: Optional[list[Severity]] = Field(default=None, description="Filter by severity levels (OR)")
    status: Optional[list[Status]] = Field(default=None, description="Filter by statuses (OR)")
    repo: Optional[list[str]] = Field(default=None, description="Filter by repos (supports wildcards)")
    category: Optional[list[Category]] = Field(default=None, description="Filter by categories (OR)")
    created_after: Optional[datetime] = Field(default=None)
    created_before: Optional[datetime] = Field(default=None)
    updated_after: Optional[datetime] = Field(default=None)
    updated_before: Optional[datetime] = Field(default=None)
    tags: Optional[list[str]] = Field(default=None, description="Filter by tags (AND)")
    has_fix: Optional[bool] = Field(default=None)
    owner: Optional[str] = Field(default=None)


class SearchRequest(VticBaseModel):
    """Request body for hybrid search endpoint."""

    query: str = Field(default="", max_length=1000, description="Search query string")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    semantic: bool = Field(default=False, description="Enable semantic search")
    topk: int = Field(default=10, ge=1, le=100, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    sort_by: str = Field(default="relevance", pattern=r"^(relevance|created_at|updated_at|severity|status)$")
    sort_order: str = Field(default="desc", pattern=r"^(asc|desc)$")

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return v.strip()


class SearchResult(VticBaseModel):
    """Single search result containing ticket data with relevance scores."""

    id: str
    title: str
    repo: str
    category: str
    severity: str
    status: str
    description: Optional[str] = None
    slug: str
    score: float = Field(ge=0.0, le=1.0, description="Final relevance score (0-1)")
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None
    highlights: list[str] = Field(default_factory=list)


class SearchResponse(VticBaseModel):
    """Response model for search endpoint."""

    results: list[SearchResult] = Field(default_factory=list)
    total: int = Field(ge=0, description="Total matching tickets")
    query: str = Field(description="Normalized search query")
    semantic: bool = Field(description="Whether semantic search was used")
    limit: int = Field(ge=1, description="Results limit (page size)")
    offset: int = Field(ge=0, description="Results offset")
    has_more: bool = Field(description="Whether more results are available")
    took_ms: int = Field(ge=0, description="Search execution time in milliseconds")


T = TypeVar("T")


class PaginatedResponse(VticBaseModel, Generic[T]):
    """Generic paginated response wrapper for list endpoints."""

    data: list[T] = Field(default_factory=list, description="Page of results")
    total: int = Field(ge=0, description="Total number of items matching the query")
    limit: int = Field(ge=1, description="Page size (limit)")
    offset: int = Field(ge=0, description="Number of items skipped")
    has_more: bool = Field(description="Whether additional pages exist")

    @classmethod
    def create(cls, data: list[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        return cls(
            data=data,
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(data)) < total,
        )


class ErrorDetail(VticBaseModel):
    """Detailed error information for field-level validation errors."""

    field: Optional[str] = Field(default=None, description="Field that caused the error")
    message: str = Field(description="Human-readable error message")
    code: str = Field(description="Machine-readable error code")


class ErrorResponse(VticBaseModel):
    """Standard error response for all API errors."""

    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: Optional[list[ErrorDetail]] = Field(default=None)
    request_id: Optional[str] = Field(default=None, description="Request ID for debugging")
    status_code: int = Field(description="HTTP status code")


class HealthResponse(VticBaseModel):
    """Health check response for monitoring endpoints."""

    status: str = Field(pattern=r"^(healthy|degraded|unhealthy)$")
    ticket_count: int = Field(ge=0, description="Total number of tickets")
    index_status: str = Field(pattern=r"^(ready|building|corrupted|missing)$")
    version: str = Field(description="vtic version")
    timestamp: str = Field(description="Response timestamp (ISO 8601)")
    checks: dict[str, bool] = Field(default_factory=dict)


class CountByField(VticBaseModel):
    """Count aggregation by a specific field value."""

    value: str = Field(description="Field value")
    count: int = Field(ge=0, description="Number of tickets")


class StatsResponse(VticBaseModel):
    """System statistics response."""

    total: int = Field(ge=0, description="Total number of tickets")
    by_severity: list[CountByField] = Field(default_factory=list)
    by_status: list[CountByField] = Field(default_factory=list)
    by_category: list[CountByField] = Field(default_factory=list)
    by_repo: list[CountByField] = Field(default_factory=list)
    open_by_severity: list[CountByField] = Field(default_factory=list)
    recently_created: int = Field(default=0, ge=0, description="Tickets created in last 7 days")
    recently_updated: int = Field(default=0, ge=0, description="Tickets updated in last 7 days")
    timestamp: str = Field(description="Stats generation timestamp (ISO 8601)")
