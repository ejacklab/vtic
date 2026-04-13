# vtic Data Models

> Complete data model specification for vtic ticket system. This document serves as the contract between design and implementation.

---

## 1. Core Enums

All enums implemented as `StrEnum` for Python 3.11+ compatibility with string comparison support.

```python
from enum import StrEnum
from typing import Literal


class Severity(StrEnum):
    """Ticket severity levels indicating impact and urgency."""
    CRITICAL = "critical"    # Production outage, security breach, data loss
    HIGH = "high"            # Significant impact, workaround exists
    MEDIUM = "medium"        # Moderate impact, standard priority
    LOW = "low"              # Minor issue, cosmetic, nice-to-have


class Status(StrEnum):
    """Ticket lifecycle statuses."""
    OPEN = "open"                    # New ticket, not yet started
    IN_PROGRESS = "in_progress"      # Actively being worked on
    BLOCKED = "blocked"              # Waiting on external dependency
    FIXED = "fixed"                  # Issue resolved, pending verification
    WONT_FIX = "wont_fix"            # Will not be resolved (intentional, obsolete)
    CLOSED = "closed"                # Ticket closed (resolved, duplicate, etc.)


class Category(StrEnum):
    """Ticket categorization for organization and routing."""
    SECURITY = "security"            # Security vulnerabilities, CVEs
    AUTH="auth"                    # Authentication, authorization issues
    CODE_QUALITY = "code_quality"    # Refactoring, tech debt, linting
    PERFORMANCE = "performance"      # Speed, memory, optimization
    FRONTEND = "frontend"            # UI/UX, browser, CSS, JS
    TESTING = "testing"              # Tests, coverage, test infra
    DOCUMENTATION = "documentation"  # Docs, README, comments
    INFRASTRUCTURE = "infrastructure" # CI/CD, deployment, servers
    CONFIGURATION = "configuration"  # Config files, env vars, settings
    API = "api"                      # API design, endpoints, contracts
    DATA = "data"                    # Database, migrations, schema
    UI = "ui"                        # Visual design, components
    DEPENDENCIES = "dependencies"    # Packages, versions, upgrades
    BUILD = "build"                  # Compilation, bundling, artifacts
    OTHER = "other"                  # Uncategorized


# Type aliases for Literal type usage in Pydantic models
SeverityLiteral = Literal["critical", "high", "medium", "low"]
StatusLiteral = Literal["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"]
CategoryLiteral = Literal[
    "security", "auth", "code_quality", "performance", "frontend",
    "testing", "documentation", "infrastructure", "configuration",
    "api", "data", "ui", "dependencies", "build", "other"
]
```

### Category ID Prefix Mapping

> **Note:** Category values in this spec (e.g., `code_quality`) supersede simplified names
> in breakdown docs (e.g., `code`). The detailed taxonomy provides better organization.

```python
CATEGORY_PREFIXES: dict[Category, str] = {
    Category.CODE_QUALITY: "C",
    Category.SECURITY: "S",
    Category.AUTH: "A",
    Category.INFRASTRUCTURE: "I",
    Category.DOCUMENTATION: "D",
    Category.TESTING: "T",
    Category.PERFORMANCE: "P",
    Category.FRONTEND: "F",
    Category.CONFIGURATION: "N",  # CoNfiguration
    Category.API: "X",            # API/extension
    Category.DATA: "M",           # Data/Migrations
    Category.UI: "U",
    Category.DEPENDENCIES: "Y",   # deplY
    Category.BUILD: "B",
    Category.OTHER: "O",
}
```

---

## 2. Core Data Models (Pydantic BaseModel)

All models use Pydantic v2 with strict validation.

```python
from datetime import datetime
from typing import Any, Generic, Optional, TypeVar, Self
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
import re


# =============================================================================
# Base Configuration
# =============================================================================

class VticBaseModel(BaseModel):
    """Base model with common configuration for all vtic models."""
    model_config = ConfigDict(
        populate_by_name=True,           # Allow field alias usage
        str_strip_whitespace=True,       # Auto-strip whitespace on strings
        validate_assignment=True,        # Validate on field assignment
        extra="ignore",                  # Ignore extra fields (forward compatibility)
    )


# =============================================================================
# Ticket Model
# =============================================================================

class Ticket(VticBaseModel):
    """
    Core ticket entity representing a single issue or task.
    
    This is the primary data structure stored as markdown files on disk.
    All fields map directly to YAML frontmatter or markdown sections.
    """
    
    # Identity
    id: str = Field(
        ...,  # Required
        min_length=1,
        max_length=20,
        pattern=r"^[A-Z]\d+$",
        description="Unique ticket ID (e.g., C1, S2, A3)",
    )
    
    # Content
    title: str = Field(
        ...,  # Required
        min_length=1,
        max_length=200,
        description="Ticket title",
    )
    description: Optional[str] = Field(
        default=None,
        max_length=50000,
        description="Detailed description (markdown supported)",
    )
    fix: Optional[str] = Field(
        default=None,
        max_length=20000,
        description="Proposed or actual fix (markdown supported)",
    )
    
    # Metadata
    repo: str = Field(
        ...,  # Required
        min_length=3,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in 'owner/repo' format",
    )
    owner: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Ticket owner/assignee",
    )
    category: Category = Field(
        default=Category.CODE_QUALITY,
        description="Ticket category",
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="Issue severity level",
    )
    status: Status = Field(
        default=Status.OPEN,
        description="Current status",
    )
    
    # References
    file: Optional[str] = Field(
        default=None,
        max_length=500,
        pattern=r"^[^:]+(:\d+(-\d+)?)?$",
        description="File reference (path:line or path:start-end). "
                    "Note: Single reference; use tags for multiple file references.",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Searchable tags (validator enforces max 50 items)",
    )
    
    # Timestamps
    created_at: datetime = Field(..., description="Creation timestamp (UTC)")
    updated_at: datetime = Field(..., description="Last update timestamp (UTC)")
    
    # Derived
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="URL-safe slug for filename",
    )
    
    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    
    @field_validator("id")
    @classmethod
    def validate_id_format(cls, v: str) -> str:
        """Ensure ID follows prefix + number format."""
        if not re.match(r"^[A-Z]\d+$", v):
            raise ValueError(f"Invalid ID format: {v}. Expected: prefix + digits (e.g., C1, S2)")
        return v.upper()
    
    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @field_validator("repo")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        """Ensure repo follows owner/repo format."""
        if "/" not in v:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        parts = v.split("/")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        return v.lower()
    
    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, v: list[str]) -> list[str]:
        """Normalize tags: lowercase, strip, remove empty, deduplicate, max 50."""
        if len(v) > 50:
            raise ValueError("Cannot have more than 50 tags")
        normalized = []
        seen = set()
        for tag in v:
            clean = tag.lower().strip()
            if clean and clean not in seen:
                normalized.append(clean)
                seen.add(clean)
        return normalized
    
    @model_validator(mode="after")
    def validate_timestamps(self) -> Self:
        """Ensure updated_at >= created_at."""
        if self.updated_at < self.created_at:
            raise ValueError("updated_at cannot be earlier than created_at")
        return self
    
    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to URL-safe slug."""
        slug = re.sub(r'[^a-z0-9]+', '-', text.lower())
        slug = slug.strip('-')
        slug = re.sub(r'-+', '-', slug)
        return slug[:100]
    
    @property
    def is_terminal(self) -> bool:
        """Check if ticket is in a terminal (completed) status."""
        return self.status in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)
    
    @property
    def filename(self) -> str:
        """Generate filename from ID and slug."""
        return f"{self.id}-{self.slug}.md"
    
    @property
    def filepath(self) -> str:
        """Generate relative filepath: owner/repo/category/filename."""
        return f"{self.repo}/{self.category.value}/{self.filename}"
    
    @property
    def search_text(self) -> str:
        """Generate searchable text combining all content fields."""
        parts = [self.title, self.description or "", self.fix or "", " ".join(self.tags)]
        return " ".join(parts)


class TicketCreate(VticBaseModel):
    """
    Request body for creating a new ticket.
    
    Required fields: title, repo
    Optional fields: description, fix, owner, category, severity, status, file, tags
    ID, slug, and timestamps are auto-generated by the server.
    """
    
    # Required
    title: str = Field(..., min_length=1, max_length=200, description="Ticket title")
    repo: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in 'owner/repo' format",
    )
    
    # Optional
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: Optional[str] = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list, description="Searchable tags (max 50 items)")
    
    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @field_validator("repo")
    @classmethod
    def validate_repo_format(cls, v: str) -> str:
        if "/" not in v:
            raise ValueError(f"Invalid repo format: {v}. Expected: 'owner/repo'")
        return v.lower()


class TicketUpdate(VticBaseModel):
    """
    Request body for updating an existing ticket.
    
    All fields are optional (Partial[Ticket]). Only provided fields are updated.
    The updated_at timestamp is automatically refreshed on any modification.
    """
    
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
        extra="forbid",  # Reject unknown fields in updates
    )
    
    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip() if v else v


class TicketResponse(VticBaseModel):
    """
    API response model for ticket data.
    
    Includes all Ticket fields plus computed/derived fields for API consumers.
    """
    
    # All Ticket fields
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
    created_at: str  # ISO 8601 string
    updated_at: str  # ISO 8601 string
    slug: str
    
    # Computed fields
    is_terminal: bool
    filename: str
    filepath: str
    
    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse":
        """Create response from Ticket model."""
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


# =============================================================================
# Search Models
# =============================================================================

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
    """
    Request body for the current search endpoint.
    Today this is keyword-only (BM25-style) search with filters and pagination.
    Semantic search and alternate sort modes are planned but not implemented yet.
    """
    
    query: str = Field(default="", max_length=1000, description="Search query string")
    filters: SearchFilters = Field(default_factory=SearchFilters)
    semantic: bool = Field(
        default=False,
        description="Reserved for future semantic search support; true is currently rejected",
    )
    topk: int = Field(default=10, ge=1, le=100, description="Max results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    # TODO: Planned fields not yet implemented by the current codebase:
    # sort_by: Literal["relevance", "created_at", "updated_at", "severity", "status"]
    # sort_order: Literal["asc", "desc"]
    
    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str) -> str:
        return v.strip()


class SearchResult(VticBaseModel):
    """Single search result containing ticket data with relevance scores."""
    
    # Ticket data (subset for list view)
    id: str
    title: str
    repo: str
    category: str
    severity: str
    status: str
    description: Optional[str] = None  # Snippet
    slug: str
    
    # Scoring
    score: float = Field(ge=0.0, le=1.0, description="Final relevance score (0-1)")
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None
    
    # Highlights
    highlights: list[str] = Field(default_factory=list)


class SearchResponse(VticBaseModel):
    """Response model for search endpoint."""
    
    results: list[SearchResult] = Field(default_factory=list)
    total: int = Field(ge=0, description="Total matching tickets")
    query: str = Field(description="Normalized search query")
    semantic: bool = Field(description="Whether semantic search was used; currently always false")
    limit: int = Field(ge=1, description="Results limit (page size)")
    offset: int = Field(ge=0, description="Results offset")
    has_more: bool = Field(description="Whether more results are available")
    took_ms: int = Field(ge=0, description="Search execution time in milliseconds")


# =============================================================================
# Generic Response Models
# =============================================================================

T = TypeVar("T")


class PaginatedResponse(VticBaseModel, Generic[T]):
    """
    Generic paginated response wrapper for list endpoints.
    Type parameter T is the item type in the data list.
    """
    
    data: list[T] = Field(default_factory=list, description="Page of results")
    total: int = Field(ge=0, description="Total number of items matching the query")
    limit: int = Field(ge=1, description="Page size (limit)")
    offset: int = Field(ge=0, description="Number of items skipped")
    has_more: bool = Field(description="Whether additional pages exist")
    
    @classmethod
    def create(cls, data: list[T], total: int, limit: int, offset: int) -> "PaginatedResponse[T]":
        """Factory method to create paginated response."""
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
    """
    Standard error response for all API errors.
    Follows RFC 7807 Problem Details format (adapted for JSON).
    """
    
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
    """
    System statistics response.
    Provides ticket counts aggregated by various dimensions.
    """
    
    total: int = Field(ge=0, description="Total number of tickets")
    by_severity: list[CountByField] = Field(default_factory=list)
    by_status: list[CountByField] = Field(default_factory=list)
    by_category: list[CountByField] = Field(default_factory=list)
    by_repo: list[CountByField] = Field(default_factory=list)
    open_by_severity: list[CountByField] = Field(default_factory=list)
    recently_created: int = Field(default=0, ge=0, description="Tickets created in last 7 days")
    recently_updated: int = Field(default=0, ge=0, description="Tickets updated in last 7 days")
    timestamp: str = Field(description="Stats generation timestamp (ISO 8601)")

---

## 3. Config Schema

Configuration file `vtic.toml` structure with types and defaults:

```toml
[tickets]
dir = "./tickets"                    # string: Ticket storage directory path

[server]
host = "127.0.0.1"                   # string: API server bind address
port = 8900                          # int: API server port (1-65535)

[search]
bm25_enabled = true                  # bool: Enable BM25 keyword search
semantic_enabled = false             # bool: Enable semantic (dense) search
embedding_provider = "openai"        # string: "openai" | "local" | "none"
embedding_model = "text-embedding-3-small"  # string: Model identifier
embedding_dimensions = 1536          # int: Vector dimensions (384-4096)
hybrid_weights_bm25 = 0.7            # float: BM25 weight for hybrid scoring (0-1)
hybrid_weights_semantic = 0.3        # float: Semantic weight for hybrid scoring (0-1)
```

### Python Config Model

```python
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Optional, Self
from pathlib import Path


class TicketsConfig(BaseModel):
    """Ticket storage configuration."""
    
    dir: Path = Field(
        default=Path("./tickets"),
        description="Ticket storage directory path",
    )
    
    @field_validator("dir")
    @classmethod
    def validate_dir(cls, v: Path) -> Path:
        return v.expanduser().resolve()


class ServerConfig(BaseModel):
    """API server configuration."""
    
    host: str = Field(default="127.0.0.1", description="Bind address")
    port: int = Field(
        default=8900,
        ge=1,
        le=65535,
        description="Server port",
    )


class SearchConfig(BaseModel):
    """Search configuration."""
    
    bm25_enabled: bool = Field(default=True)
    semantic_enabled: bool = Field(default=False)
    embedding_provider: Literal["openai", "local", "none"] = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536, ge=384, le=4096)
    hybrid_weights_bm25: float = Field(default=0.7, ge=0.0, le=1.0)
    hybrid_weights_semantic: float = Field(default=0.3, ge=0.0, le=1.0)
    
    @model_validator(mode="after")
    def validate_semantic_config(self) -> Self:
        """Ensure semantic config is valid when enabled."""
        if self.semantic_enabled and self.embedding_provider == "none":
            raise ValueError("Cannot enable semantic search with provider='none'")
        return self

    @model_validator(mode="after")
    def validate_weights_sum(self) -> Self:
        """Ensure hybrid weights sum to 1.0 when both search types enabled."""
        if self.bm25_enabled and self.semantic_enabled:
            total = self.hybrid_weights_bm25 + self.hybrid_weights_semantic
            if abs(total - 1.0) > 0.001:
                raise ValueError(f"Hybrid weights must sum to 1.0, got {total}")
        return self


class VticConfig(BaseModel):
    """Complete vtic configuration."""
    
    tickets: TicketsConfig = Field(default_factory=TicketsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    
    @classmethod
    def from_toml(cls, path: Path) -> "VticConfig":
        """Load configuration from TOML file."""
        import tomllib
        with open(path, "rb") as f:
            data = tomllib.load(f)
        return cls(**data)
    
    @classmethod
    def from_env(cls) -> "VticConfig":
        """Load configuration from environment variables."""
        import os
        
        config = cls()
        
        # Tickets
        if tickets_dir := os.getenv("VTIC_TICKETS_DIR"):
            config.tickets.dir = Path(tickets_dir)
        
        # Server
        if host := os.getenv("VTIC_SERVER_HOST"):
            config.server.host = host
        if port := os.getenv("VTIC_SERVER_PORT"):
            config.server.port = int(port)
        
        # Search
        if bm25 := os.getenv("VTIC_SEARCH_BM25_ENABLED"):
            config.search.bm25_enabled = bm25.lower() in ("true", "1", "yes")
        if semantic := os.getenv("VTIC_SEARCH_SEMANTIC_ENABLED"):
            config.search.semantic_enabled = semantic.lower() in ("true", "1", "yes")
        if provider := os.getenv("VTIC_SEARCH_EMBEDDING_PROVIDER"):
            config.search.embedding_provider = provider
        if model := os.getenv("VTIC_SEARCH_EMBEDDING_MODEL"):
            config.search.embedding_model = model
        if dims := os.getenv("VTIC_SEARCH_EMBEDDING_DIMENSIONS"):
            config.search.embedding_dimensions = int(dims)
        
        return config

---

## 4. Error Catalog

Every error the system can produce:

| Error Code | HTTP Status | Message | When |
|------------|-------------|---------|------|
| TICKET_NOT_FOUND | 404 | Ticket {id} not found | Requested ticket ID does not exist |
| INVALID_TICKET_ID | 400 | Invalid ticket ID format: {id} | ID does not match pattern `^[A-Z]\d+$` |
| MISSING_REQUIRED_FIELD | 400 | Required field '{field}' is missing | Create/update missing required field |
| INVALID_STATUS | 400 | Invalid status: {status}. Valid: open, in_progress, blocked, fixed, wont_fix, closed | Invalid status value provided |
| INVALID_SEVERITY | 400 | Invalid severity: {severity}. Valid: critical, high, medium, low | Invalid severity value provided |
| INVALID_CATEGORY | 400 | Invalid category: {category} | Invalid category value provided |
| INVALID_REPO_FORMAT | 400 | Invalid repo format: {repo}. Expected: 'owner/repo' | Repo doesn't match `owner/repo` pattern |
| INVALID_FILE_REFERENCE | 400 | Invalid file reference: {file} | File ref doesn't match `path:line` or `path:start-end` |
| INVALID_DATE_RANGE | 400 | Invalid date range: {message} | Date range filters are inconsistent |
| SEARCH_INDEX_ERROR | 500 | Search index error: {details} | Zvec index operation failed |
| EMBEDDING_ERROR | 500 | Embedding generation failed: {details} | Embedding provider API error |
| CONFIG_ERROR | 500 | Configuration error: {details} | Invalid or missing configuration |
| CONFIG_NOT_FOUND | 404 | Configuration file not found: {path} | Config file doesn't exist |
| TICKET_ALREADY_EXISTS | 409 | Ticket {id} already exists | Attempting to create duplicate ticket ID |
| TICKET_WRITE_ERROR | 500 | Failed to write ticket {id}: {details} | File system error writing ticket |
| TICKET_READ_ERROR | 500 | Failed to read ticket {id}: {details} | File system error reading ticket |
| TICKET_DELETE_ERROR | 500 | Failed to delete ticket {id}: {details} | File system error deleting ticket |
| VALIDATION_ERROR | 400 | Validation failed: {details} | Pydantic validation failure |
| INVALID_REQUEST | 400 | Invalid request: {details} | Malformed request body/parameters |
| RATE_LIMIT_EXCEEDED | 429 | Rate limit exceeded. Retry after {seconds}s | Too many requests |
| INTERNAL_ERROR | 500 | Internal server error: {details} | Unexpected server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily unavailable | Server overloaded or maintenance mode |
| SEMANTIC_SEARCH_DISABLED | 400 | Semantic search is disabled | Requested semantic search when disabled |
| EMBEDDING_PROVIDER_ERROR | 502 | Embedding provider error: {details} | External embedding service failure |
| INVALID_SORT_FIELD | 400 | Invalid sort field: {field} | Sort field not in allowed list |
| INVALID_FILTER_VALUE | 400 | Invalid filter value for {field}: {value} | Filter value validation failed |
| BULK_OPERATION_ERROR | 400 | Bulk operation failed for {count} items | Partial bulk operation failure |
| INDEX_CORRUPTED | 500 | Search index corrupted: {details} | Zvec index corruption detected |
| INDEX_REBUILD_REQUIRED | 503 | Search index rebuild required | Index is missing or incompatible |

### Error Classes (Python)

```python
class VticError(Exception):
    """Base exception for all vtic errors."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: Optional[list[ErrorDetail]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)
    
    def to_response(self) -> ErrorResponse:
        return ErrorResponse(
            error_code=self.error_code,
            message=self.message,
            details=self.details,
            status_code=self.status_code,
        )


class TicketNotFoundError(VticError):
    """Raised when a requested ticket does not exist."""
    
    def __init__(self, ticket_id: str):
        super().__init__(
            error_code="TICKET_NOT_FOUND",
            message=f"Ticket {ticket_id} not found",
            status_code=404,
        )


class ValidationError(VticError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, details: Optional[list[ErrorDetail]] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class ConfigError(VticError):
    """Raised when configuration is invalid."""
    
    def __init__(self, message: str):
        super().__init__(
            error_code="CONFIG_ERROR",
            message=message,
            status_code=500,
        )


class SearchIndexError(VticError):
    """Raised when Zvec index operations fail."""
    
    def __init__(self, message: str):
        super().__init__(
            error_code="SEARCH_INDEX_ERROR",
            message=f"Search index error: {message}",
            status_code=500,
        )


class EmbeddingError(VticError):
    """Raised when embedding generation fails."""
    
    def __init__(self, message: str):
        super().__init__(
            error_code="EMBEDDING_ERROR",
            message=f"Embedding generation failed: {message}",
            status_code=500,
        )


class TicketAlreadyExistsError(VticError):
    """Raised when attempting to create a ticket with existing ID."""

    def __init__(self, ticket_id: str):
        super().__init__(
            error_code="TICKET_ALREADY_EXISTS",
            message=f"Ticket {ticket_id} already exists",
            status_code=409,
        )


class TicketWriteError(VticError):
    """Raised when file system write fails."""

    def __init__(self, ticket_id: str, details: str):
        super().__init__(
            error_code="TICKET_WRITE_ERROR",
            message=f"Failed to write ticket {ticket_id}: {details}",
            status_code=500,
        )


class TicketReadError(VticError):
    """Raised when file system read fails."""

    def __init__(self, ticket_id: str, details: str):
        super().__init__(
            error_code="TICKET_READ_ERROR",
            message=f"Failed to read ticket {ticket_id}: {details}",
            status_code=500,
        )
```

---

## 5. Module Map

Directory structure and file organization:

```
src/vtic/
├── __init__.py           # Package exports and version
├── models.py             # All Pydantic models and enums
├── config.py             # Config loading and validation (VticConfig classes)
├── errors.py             # Error classes and catalog (VticError hierarchy)
├── store.py              # Markdown file read/write (TicketStore class)
├── index.py              # Zvec index operations (ZvecIndex class)
├── search.py             # Search engine (BM25 + hybrid) (SearchEngine class)
├── ticket.py             # Ticket CRUD orchestration (TicketService class)
├── constants.py          # CATEGORY_PREFIXES, VALID_STATUSES, etc.
└── utils.py              # slugify, timestamp helpers
│
├── api/
│   ├── __init__.py
│   ├── app.py            # FastAPI app factory (create_app)
│   ├── deps.py           # Dependencies (get_store, get_index, get_config)
│   └── routes/
│       ├── __init__.py
│       ├── tickets.py    # Ticket CRUD endpoints
│       └── search.py     # Search endpoints
│
├── cli/
│   ├── __init__.py
│   └── main.py           # Typer CLI commands
│
└── embeddings/
    ├── __init__.py
    ├── base.py           # EmbeddingProvider interface
    ├── openai.py         # OpenAIEmbeddingProvider
    └── local.py          # LocalEmbeddingProvider (sentence-transformers)
```

### Key Classes/Functions by Module

#### `models.py`
- **Enums:** `Severity`, `Status`, `Category`
- **Core Models:** `Ticket`, `TicketCreate`, `TicketUpdate`, `TicketResponse`
- **Search Models:** `SearchFilters`, `SearchRequest`, `SearchResult`, `SearchResponse`
- **Response Models:** `PaginatedResponse[T]`, `ErrorResponse`, `HealthResponse`, `StatsResponse`

#### `config.py`
- **Classes:** `TicketsConfig`, `ServerConfig`, `SearchConfig`, `VticConfig`
- **Functions:** `load_config()`, `get_config()`

#### `errors.py`
- **Base:** `VticError`
- **Specific:** `TicketNotFoundError`, `ValidationError`, `ConfigError`, `SearchIndexError`, `EmbeddingError`, `TicketAlreadyExistsError`, `TicketWriteError`, `TicketReadError`

#### `store.py`
- **Class:** `TicketStore`
- **Methods:** `get()`, `save()`, `delete()`, `list()`, `exists()`

#### `index.py`
- **Class:** `ZvecIndex`
- **Methods:** `add()`, `remove()`, `search_bm25()`, `search_semantic()`, `search_hybrid()`, `rebuild()`

#### `search.py`
- **Class:** `SearchEngine`
- **Methods:** `search()`, `index_ticket()`, `remove_ticket()`, `reindex_all()`

#### `ticket.py`
- **Class:** `TicketService`
- **Methods:** `create()`, `get()`, `update()`, `delete()`, `list()`, `search()`

#### `api/app.py`
- **Function:** `create_app() -> FastAPI`

#### `api/deps.py`
- **Functions:** `get_config()`, `get_store()`, `get_index()`, `get_ticket_service()`, `get_search_engine()`

#### `cli/main.py`
- **Commands:** `init`, `create`, `get`, `update`, `delete`, `list`, `search`, `serve`, `reindex`

#### `embeddings/base.py`
- **Class:** `EmbeddingProvider` (abstract)
- **Methods:** `embed()`, `embed_batch()`

#### `embeddings/openai.py`
- **Class:** `OpenAIEmbeddingProvider`

#### `embeddings/local.py`
- **Class:** `LocalEmbeddingProvider`
