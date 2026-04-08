"""Coauthdata models for vtic."""

from __future__ import annotations

import re
from datetime import UTC, datetime, timezone
from enum import StrEnum
from typing import Generic, Literal, Self, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .utils import normalize_tags


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

from .constants import CATEGORY_PREFIXES as CATEGORY_PREFIXES_RAW

CATEGORY_PREFIXES: dict[Category, str] = {
    Category(category_name): prefix for category_name, prefix in CATEGORY_PREFIXES_RAW.items()
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
    description: str | None = Field(default=None, max_length=50000)
    fix: str | None = Field(default=None, max_length=20000)
    repo: str = Field(
        ...,
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in 'owner/repo' format",
    )
    owner: str | None = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: str | None = Field(
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
        v = cls._normalize_single_line(v)
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        return cls._normalize_repo(v)

    @field_validator("owner", mode="before")
    @classmethod
    def validate_owner_single_line(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = cls._normalize_single_line(v)
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        return normalize_tags(v)

    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self

    @staticmethod
    def _normalize_single_line(value: str) -> str:
        return " ".join(str(value).splitlines()).strip()

    @classmethod
    def _normalize_repo(cls, value: str) -> str:
        raw = str(value).strip()
        if "/" not in raw:
            raise ValueError(f"Invalid repo format: {raw}. Expected: 'owner/repo'")
        parts = raw.split("/")
        if len(parts) != 2 or not all(parts):
            raise ValueError(f"Invalid repo format: {raw}. Expected: 'owner/repo'")
        if any(part in {".", ".."} for part in parts):
            raise ValueError("Repo path segments cannot be '.' or '..'")
        return raw.lower()

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
        parts = [self.id, self.title, self.description or "", self.file or "", self.fix or "", " ".join(self.tags)]
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
    description: str | None = Field(default=None, max_length=50000)
    fix: str | None = Field(default=None, max_length=20000)
    owner: str | None = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: str | None = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, description="Searchable tags (max 50 items)")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        v = Ticket._normalize_single_line(v)
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("repo", mode="before")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        return Ticket._normalize_repo(v)

    @field_validator("owner", mode="before")
    @classmethod
    def validate_owner_single_line(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = Ticket._normalize_single_line(v)
        return normalized or None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        return normalize_tags(v)


class TicketUpdate(VticBaseModel):
    """Request body for updating an existing ticket."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=50000)
    fix: str | None = Field(default=None, max_length=20000)
    owner: str | None = Field(default=None, max_length=100)
    category: Category | None = Field(default=None)
    severity: Severity | None = Field(default=None)
    status: Status | None = Field(default=None)
    file: str | None = Field(default=None, max_length=500)
    tags: list[str] | None = Field(default=None, description="Searchable tags (max 50 items)")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    @field_validator("title", mode="before")
    @classmethod
    def validate_title_not_empty(cls, v: str | None) -> str | None:
        if v is not None:
            v = Ticket._normalize_single_line(v)
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("owner", mode="before")
    @classmethod
    def validate_owner_single_line(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = Ticket._normalize_single_line(v)
        return normalized or None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return normalize_tags(v)


class TicketResponse(VticBaseModel):
    """API response model for ticket data."""

    id: str
    title: str
    description: str | None = None
    fix: str | None = None
    repo: str
    owner: str | None = None
    category: str
    severity: str
    status: str
    file: str | None = None
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

    severity: list[Severity] | None = Field(
        default=None, description="Filter by severity levels (OR)"
    )
    status: list[Status] | None = Field(default=None, description="Filter by statuses (OR)")
    repo: list[str] | None = Field(default=None, description="Filter by repos (supports wildcards)")
    category: list[Category] | None = Field(default=None, description="Filter by categories (OR)")
    created_after: datetime | None = Field(default=None)
    created_before: datetime | None = Field(default=None)
    updated_after: datetime | None = Field(default=None)
    updated_before: datetime | None = Field(default=None)
    tags: list[str] | None = Field(default=None, description="Filter by tags (AND)")
    has_fix: bool | None = Field(default=None)
    owner: str | None = Field(default=None)

    @field_validator("repo")
    @classmethod
    def normalize_repo_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        normalized = [str(value).strip().lower() for value in v if str(value).strip()]
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tag_filters(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        return normalize_tags(v)

    @field_validator("owner", mode="before")
    @classmethod
    def normalize_owner_filter(cls, v: str | None) -> str | None:
        if v is None:
            return None
        normalized = Ticket._normalize_single_line(v)
        return normalized or None

    @model_validator(mode="after")
    def validate_date_ranges(self) -> Self:
        def _normalize(dt: datetime | None) -> datetime | None:
            if dt is None or dt.tzinfo is not None:
                return dt
            return dt.replace(tzinfo=timezone.utc)

        created_after = _normalize(self.created_after)
        created_before = _normalize(self.created_before)
        updated_after = _normalize(self.updated_after)
        updated_before = _normalize(self.updated_before)

        if created_after is not None and created_before is not None and created_after > created_before:
            raise ValueError("created_after cannot be later than created_before")
        if updated_after is not None and updated_before is not None and updated_after > updated_before:
            raise ValueError("updated_after cannot be later than updated_before")
        return self


class SearchRequest(VticBaseModel):
    """Request body for hybrid search endpoint."""

    query: str = Field(default="", max_length=1000, description="Search query string")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    semantic: bool = Field(default=False, description="Enable semantic search")
    topk: int = Field(default=10, ge=1, le=100, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return v.strip()

    @field_validator("semantic")
    @classmethod
    def validate_semantic_not_supported(cls, v: bool) -> bool:
        if v:
            raise ValueError("Semantic search is not yet implemented")
        return v


class SearchResult(VticBaseModel):
    """Single search result containing ticket data with relevance scores."""

    id: str
    title: str
    repo: str
    category: str
    severity: str
    status: str
    description: str | None = None
    slug: str
    score: float = Field(ge=0.0, le=1.0, description="Final relevance score (0-1)")
    bm25_score: float | None = None
    semantic_score: float | None = None
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

    field: str | None = Field(default=None, description="Field that caused the error")
    message: str = Field(description="Human-readable error message")
    code: str = Field(description="Machine-readable error code")


class ErrorResponse(VticBaseModel):
    """Standard error response for all API errors."""

    error_code: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(default=None)
    request_id: str | None = Field(default=None, description="Request ID for debugging")
    status_code: int = Field(description="HTTP status code")


class HealthResponse(VticBaseModel):
    """Health check response for monitoring endpoints."""

    status: str = Field(pattern=r"^(healthy|degraded|unhealthy)$")
    ticket_count: int = Field(ge=0, description="Total number of tickets")
    index_status: str = Field(pattern=r"^(ready|building|corrupted|missing)$")
    version: str = Field(description="vtic version")
    timestamp: str = Field(description="Response timestamp (ISO 8601)")
    checks: dict[str, bool] = Field(default_factory=dict)
    corrupted_tickets: list[str] = Field(default_factory=list)


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
