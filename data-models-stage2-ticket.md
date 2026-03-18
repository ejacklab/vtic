# vtic Data Models - Stage 2: Ticket Models

Comprehensive Pydantic v2 models for the ticket management system.

> **Note:** Stage 1 defines the canonical enums. This stage imports from Stage 1 and extends with ticket models.

## Enums (Imported from Stage 1)

```python
from enum import StrEnum
from datetime import datetime, timezone
from typing import Optional, List, Any, Set, Dict
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class Category(StrEnum):
    """
    Ticket category with ID prefix mapping.
    
    Categories determine both the storage directory and the ID prefix.
    For example, security tickets get IDs like S1, S2, S3.
    """
    SECURITY = "security"       # Prefix: S
    AUTH = "auth"               # Prefix: A
    CODE_QUALITY = "code_quality"  # Prefix: C
    PERFORMANCE = "performance" # Prefix: P
    FRONTEND = "frontend"       # Prefix: F
    BACKEND = "backend"         # Prefix: B
    TESTING = "testing"         # Prefix: T
    DOCUMENTATION = "documentation"  # Prefix: D
    INFRASTRUCTURE = "infrastructure"  # Prefix: I
    CONFIGURATION = "configuration"  # Prefix: G
    API = "api"                 # Prefix: X
    DATA = "data"               # Prefix: D (shared with docs - use context)
    UI = "ui"                   # Prefix: U
    DEPENDENCIES = "dependencies"  # Prefix: E
    BUILD = "build"             # Prefix: L
    OTHER = "other"             # Prefix: O

    @classmethod
    def get_prefix(cls, category: "Category | str") -> str:
        """Get the ID prefix for a category."""
        prefix_map: Dict[str, str] = {
            cls.SECURITY.value: "S",
            cls.AUTH.value: "A",
            cls.CODE_QUALITY.value: "C",
            cls.PERFORMANCE.value: "P",
            cls.FRONTEND.value: "F",
            cls.BACKEND.value: "B",
            cls.TESTING.value: "T",
            cls.DOCUMENTATION.value: "D",
            cls.INFRASTRUCTURE.value: "I",
            cls.CONFIGURATION.value: "G",
            cls.API.value: "X",
            cls.DATA.value: "DA",
            cls.UI.value: "U",
            cls.DEPENDENCIES.value: "E",
            cls.BUILD.value: "L",
            cls.OTHER.value: "O",
        }
        value = category.value if isinstance(category, Category) else category
        return prefix_map.get(value, "X")  # Unknown categories get X


class Severity(StrEnum):
    """Ticket severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def weight(self) -> int:
        """Get numeric weight for sorting (higher = more severe)."""
        weights = {
            self.CRITICAL: 4,
            self.HIGH: 3,
            self.MEDIUM: 2,
            self.LOW: 1,
        }
        return weights.get(self, 0)


class Status(StrEnum):
    """
    Ticket status values with workflow transitions.
    
    Terminal statuses are those that represent a final state (closed, wont_fix).
    Reopening from terminal status is allowed but should be intentional.
    """
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    CLOSED = "closed"

    @property
    def is_terminal(self) -> bool:
        """Check if this is a terminal (completed) status."""
        return self in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)
    
    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        display_map: Dict[Status, str] = {
            Status.OPEN: "Open",
            Status.IN_PROGRESS: "In Progress",
            Status.BLOCKED: "Blocked",
            Status.FIXED: "Fixed",
            Status.WONT_FIX: "Won't Fix",
            Status.CLOSED: "Closed",
        }
        return display_map.get(self, self.value)
    
    def can_transition_to(self, target: "Status") -> bool:
        """Check if transition to target status is valid."""
        return target in VALID_STATUS_TRANSITIONS.get(self, set())


# Valid transitions - defines allowed state changes
# Terminal statuses can only transition back to OPEN (reopening)
VALID_STATUS_TRANSITIONS: Dict[Status, Set[Status]] = {
    Status.OPEN: {Status.IN_PROGRESS, Status.BLOCKED, Status.WONT_FIX, Status.CLOSED},
    Status.IN_PROGRESS: {Status.OPEN, Status.BLOCKED, Status.FIXED, Status.WONT_FIX, Status.CLOSED},
    Status.BLOCKED: {Status.OPEN, Status.IN_PROGRESS, Status.WONT_FIX, Status.CLOSED},
    Status.FIXED: {Status.OPEN, Status.CLOSED, Status.WONT_FIX},
    Status.WONT_FIX: {Status.OPEN, Status.CLOSED},
    Status.CLOSED: {Status.OPEN},  # Reopening only
}

# Terminal statuses - tickets that can't transition further without reopening
TERMINAL_STATUSES: Set[Status] = {Status.CLOSED, Status.WONT_FIX}


## Base Models

```python
class TicketBase(BaseModel):
    """Base ticket fields shared across models."""
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "CORS Wildcard Configuration Issue",
                "description": "API allows wildcard CORS origins in production",
                "repo": "ejacklab/open-dsearch",
                "category": "security",
                "severity": "high",
                "status": "open",
            }
        }
    )
    
    # Required fields
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ticket title - concise summary of the issue",
        examples=["CORS Wildcard Configuration Issue"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the ticket",
        examples=["API allows wildcard CORS origins in production environment"],
    )
    repo: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository identifier in 'owner/repo' format",
        examples=["ejacklab/open-dsearch"],
    )
    
    # Optional fields with defaults
    fix: Optional[str] = Field(
        default=None,
        description="Recommended fix or solution for the issue",
        examples=["Configure specific allowed origins instead of wildcard"],
    )
    category: Category = Field(
        default=Category.OTHER,
        description="Ticket category for organization and ID prefix",
    )
    severity: Severity = Field(
        default=Severity.MEDIUM,
        description="Issue severity level",
    )
    status: Status = Field(
        default=Status.OPEN,
        description="Current ticket status",
    )
    file: Optional[str] = Field(
        default=None,
        pattern=r"^[^:\n]+:\d+$",
        description="Source file reference (e.g., 'backend/main.py:27')",
        examples=["backend/main.py:27"],
    )
    tags: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="List of tags for categorization",
        examples=[["cors", "security", "api"]],
    )
    
    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> List[str]:
        """Validate and normalize tags."""
        if v is None:
            return []
        if isinstance(v, str):
            # Handle comma-separated string
            v = [t.strip() for t in v.split(",") if t.strip()]
        tags = []
        for tag in v:
            tag = str(tag).strip().lower()
            # Remove special characters, keep alphanumeric and hyphens
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 30:
                tags.append(tag)
        # Remove duplicates while preserving order
        seen = set()
        return [t for t in tags if not (t in seen or seen.add(t))]
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Title is required and cannot be empty")
        return v.strip()
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Description is required and cannot be empty")
        return v.strip()


## Core Ticket Model

```python
class Ticket(TicketBase):
    """
    Core ticket data model - represents a complete ticket in the system.
    
    This model is used for internal representation and storage.
    ID and slug are auto-generated based on category and title.
    Timestamps are automatically set on creation.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "S1",
                "slug": "cors-wildcard-configuration-issue",
                "title": "CORS Wildcard Configuration Issue",
                "description": "API allows wildcard CORS origins in production",
                "fix": "Configure specific allowed origins instead of wildcard",
                "repo": "ejacklab/open-dsearch",
                "owner": "ejacklab",
                "category": "security",
                "severity": "high",
                "status": "open",
                "file": "backend/main.py:27",
                "tags": ["cors", "security", "api"],
                "created_at": "2026-03-17T10:00:00Z",
                "updated_at": "2026-03-17T10:00:00Z",
            }
        }
    )
    
    # Auto-generated fields
    id: str = Field(
        ...,
        pattern=r"^[A-Z]{1,2}\d+$",
        description="Unique ticket ID (e.g., C1, S3, P2) - auto-generated from category prefix + sequence",
        examples=["C1", "S3", "P2", "I5", "DA1"],
    )
    slug: str = Field(
        ...,
        pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$",
        min_length=1,
        max_length=100,
        description="URL-safe slug auto-generated from title for filenames",
        examples=["cors-wildcard-configuration-issue"],
    )
    owner: str = Field(
        ...,
        description="Repository owner - extracted from repo field",
        examples=["ejacklab"],
    )
    
    # Timestamps (auto-set)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp (UTC)",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp (UTC)",
    )
    
    @field_validator("owner", mode="before")
    @classmethod
    def extract_owner(cls, v: Any, info: Any) -> str:
        """Extract owner from repo field if not provided."""
        if v and isinstance(v, str) and v.strip():
            return v.strip()
        # Extract from repo field
        data = info.data if hasattr(info, "data") else {}
        repo = data.get("repo", "")
        if repo and "/" in repo:
            return repo.split("/")[0]
        raise ValueError("Cannot extract owner from repo field")
    
    @field_validator("slug", mode="before")
    @classmethod
    def generate_slug(cls, v: Any, info: Any) -> str:
        """Generate slug from title if not provided."""
        if v and isinstance(v, str) and v.strip():
            return v.strip().lower()
        # Generate from title
        data = info.data if hasattr(info, "data") else {}
        title = data.get("title", "")
        if not title:
            raise ValueError("Cannot generate slug: title is required")
        # Convert to URL-safe slug
        slug = title.lower()
        # Replace special chars with hyphens
        import re
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")
        # Limit length
        if len(slug) > 100:
            slug = slug[:100].rsplit("-", 1)[0]
        return slug or "untitled"
    
    @field_validator("id", mode="before")
    @classmethod
    def validate_id_format(cls, v: Any, info: Any) -> str:
        """Validate or generate ticket ID."""
        if v and isinstance(v, str) and v.strip():
            return v.strip().upper()
        # ID generation is typically handled by storage layer
        # This validator ensures format if provided
        raise ValueError("Ticket ID is required")
    
    def update_timestamp(self) -> None:
        """Update the updated_at timestamp to current UTC time."""
        self.updated_at = datetime.now(timezone.utc)
    
    def is_terminal(self) -> bool:
        """Check if ticket is in a terminal status."""
        return self.status.is_terminal
    
    @property
    def id_prefix(self) -> str:
        """Get the category prefix from the ID."""
        return self.id[0] if self.id else "X"


## API Request/Response Models

```python
class TicketCreate(BaseModel):
    """
    Request body for POST /tickets endpoint.
    
    Creates a new ticket with the provided fields.
    ID, slug, owner, and timestamps are auto-generated.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "Memory leak in search indexer",
                "description": "The search indexer process shows increasing memory usage over time",
                "repo": "ejacklab/open-dsearch",
                "category": "backend",
                "severity": "high",
            }
        }
    )
    
    # Required fields
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ticket title - concise summary of the issue",
        examples=["Memory leak in search indexer"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Detailed description of the ticket",
        examples=["The search indexer process shows increasing memory usage over time"],
    )
    
    # Optional fields with defaults
    repo: Optional[str] = Field(
        default=None,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository identifier in 'owner/repo' format (defaults to config default_repo)",
        examples=["ejacklab/open-dsearch"],
    )
    category: Optional[Category] = Field(
        default=None,
        description="Ticket category (defaults to 'other')",
    )
    severity: Optional[Severity] = Field(
        default=None,
        description="Issue severity level (defaults to 'medium')",
    )
    
    # Optional fields (no defaults)
    fix: Optional[str] = Field(
        default=None,
        description="Recommended fix or solution for the issue",
    )
    status: Optional[Status] = Field(
        default=None,
        description="Initial ticket status (defaults to 'open')",
    )
    file: Optional[str] = Field(
        default=None,
        pattern=r"^[^:\n]+:\d+$",
        description="Source file reference (e.g., 'backend/main.py:27')",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="List of tags for categorization",
    )
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Title is required and cannot be empty")
        return v.strip()
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        """Validate description is not empty after stripping."""
        if not v or not v.strip():
            raise ValueError("Description is required and cannot be empty")
        return v.strip()
    
    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> List[str]:
        """Validate and normalize tags."""
        if v is None:
            return []
        if isinstance(v, str):
            v = [t.strip() for t in v.split(",") if t.strip()]
        tags = []
        for tag in v:
            tag = str(tag).strip().lower()
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 30:
                tags.append(tag)
        seen = set()
        return [t for t in tags if not (t in seen or seen.add(t))]
    
    def apply_defaults(self, default_repo: Optional[str] = None) -> "TicketCreateWithDefaults":
        """
        Apply default values for optional fields that weren't provided.
        
        Args:
            default_repo: Default repository from configuration
            
        Returns:
            TicketCreateWithDefaults with all defaults applied
        """
        return TicketCreateWithDefaults(
            title=self.title,
            description=self.description,
            repo=self.repo or default_repo,
            category=self.category or Category.OTHER,
            severity=self.severity or Severity.MEDIUM,
            status=self.status or Status.OPEN,
            fix=self.fix,
            file=self.file,
            tags=self.tags,
        )


class TicketCreateWithDefaults(BaseModel):
    """
    Internal model representing TicketCreate after defaults are applied.
    All fields are now required (no Optional except fix/file).
    """
    
    model_config = ConfigDict(populate_by_name=True)
    
    title: str
    description: str
    repo: str  # Now required (default applied)
    category: Category  # Now required (default applied)
    severity: Severity  # Now required (default applied)
    status: Status  # Now required (default applied)
    fix: Optional[str] = None
    file: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class TicketUpdate(BaseModel):
    """
    Request body for PATCH /tickets/:id endpoint.
    
    Partial update - only provided fields are modified.
    At least one field must be provided for a valid update.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "status": "fixed",
                "fix": "Added memory limit and periodic garbage collection",
            }
        }
    )
    
    # All fields are optional for partial update
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="New ticket title",
    )
    description: Optional[str] = Field(
        default=None,
        min_length=1,
        description="New ticket description",
    )
    fix: Optional[str] = Field(
        default=None,
        description="Updated recommended fix",
    )
    category: Optional[Category] = Field(
        default=None,
        description="New ticket category",
    )
    severity: Optional[Severity] = Field(
        default=None,
        description="New severity level",
    )
    status: Optional[Status] = Field(
        default=None,
        description="New ticket status",
    )
    file: Optional[str] = Field(
        default=None,
        pattern=r"^[^:\n]+:\d+$",
        description="Updated source file reference",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="Replace all tags (None = no change, [] = clear tags)",
    )
    
    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        """Validate title if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title cannot be empty if provided")
        return v
    
    @field_validator("description")
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        """Validate description if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Description cannot be empty if provided")
        return v
    
    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> Optional[List[str]]:
        """Validate and normalize tags if provided."""
        if v is None:
            return None  # No change to tags
        if isinstance(v, str):
            v = [t.strip() for t in v.split(",") if t.strip()]
        tags = []
        for tag in v:
            tag = str(tag).strip().lower()
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 30:
                tags.append(tag)
        seen = set()
        return [t for t in tags if not (t in seen or seen.add(t))]
    
    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "TicketUpdate":
        """Ensure at least one field is being updated."""
        fields_to_check = [
            self.title, self.description, self.fix, self.category,
            self.severity, self.status, self.file, self.tags
        ]
        if all(v is None for v in fields_to_check):
            raise ValueError("At least one field must be provided for update")
        return self
    
    def get_updates(self) -> dict[str, Any]:
        """
        Get a dictionary of fields that have been provided for update.
        
        Returns:
            Dictionary of field names to new values (excluding None values)
        """
        updates = {}
        for field_name, value in self.model_dump(exclude_unset=True).items():
            if value is not None or field_name == "tags":
                # tags can be [] to clear, so we include it even if empty
                updates[field_name] = value
        return updates


class TicketResponse(Ticket):
    """
    API response model for ticket endpoints.
    
    Extends the core Ticket model with all fields included.
    This is the complete representation returned by GET /tickets/:id
    and other endpoints that return full ticket data.
    
    For v0.1, this is identical to Ticket. Future versions may add
    computed fields like related_tickets, search_score, etc.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "S1",
                "slug": "cors-wildcard-configuration-issue",
                "title": "CORS Wildcard Configuration Issue",
                "description": "API allows wildcard CORS origins in production",
                "fix": "Configure specific allowed origins instead of wildcard",
                "repo": "ejacklab/open-dsearch",
                "owner": "ejacklab",
                "category": "security",
                "severity": "high",
                "status": "open",
                "file": "backend/main.py:27",
                "tags": ["cors", "security", "api"],
                "created_at": "2026-03-17T10:00:00Z",
                "updated_at": "2026-03-17T10:00:00Z",
            }
        }
    )
    
    # Inherits all fields from Ticket
    # v0.1: No additional computed fields
    # Future: related_tickets, search_score, comment_count, etc.


## Utility Models

```python
class TicketListResponse(BaseModel):
    """Response model for listing multiple tickets."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    data: List[TicketResponse] = Field(
        default_factory=list,
        description="List of tickets",
    )
    meta: dict = Field(
        default_factory=dict,
        description="Pagination and metadata",
    )


class TicketValidationError(BaseModel):
    """Validation error details for a single field."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    field: str = Field(description="Field name that failed validation")
    message: str = Field(description="Human-readable error message")
    code: str = Field(description="Machine-readable error code")


class TicketValidationResult(BaseModel):
    """Result of validating ticket data."""
    
    model_config = ConfigDict(populate_by_name=True)
    
    is_valid: bool = Field(description="Whether validation passed")
    errors: List[TicketValidationError] = Field(
        default_factory=list,
        description="List of validation errors (empty if valid)",
    )
```

## Model Relationships Summary

```
TicketBase
    └── Ticket (core model with id, slug, owner, timestamps)
            └── TicketResponse (API response - same as Ticket in v0.1)

TicketCreate (POST /tickets request)
    └── TicketCreateWithDefaults (after default values applied)

TicketUpdate (PATCH /tickets/:id request)
```

## Usage Examples

### Creating a Ticket

```python
# From API request
create_data = TicketCreate(
    title="Memory leak in search indexer",
    description="Process memory grows unbounded during indexing",
    repo="ejacklab/open-dsearch",
    category=Category.BACKEND,
    severity=Severity.HIGH,
    tags=["memory", "performance"]
)

# Apply defaults
create_with_defaults = create_data.apply_defaults()

# Generate ticket (storage layer would handle ID generation)
ticket = Ticket(
    id="B1",  # Generated by storage based on category prefix (B = backend)
    slug="memory-leak-in-search-indexer",  # Auto-generated from title
    owner="ejacklab",  # Extracted from repo
    **create_with_defaults.model_dump()
)
```

### Updating a Ticket

```python
# Partial update from API request
update_data = TicketUpdate(status=Status.FIXED, fix="Added garbage collection")

# Get fields to update
updates = update_data.get_updates()
# Result: {"status": "fixed", "fix": "Added garbage collection"}

# Apply to existing ticket
existing_ticket.status = update_data.status or existing_ticket.status
existing_ticket.fix = update_data.fix  # Can be None to clear
existing_ticket.update_timestamp()
```

### API Response

```python
# GET /tickets/B1 returns TicketResponse
response = TicketResponse(
    id="B1",
    slug="memory-leak-in-search-indexer",
    title="Memory leak in search indexer",
    description="Process memory grows unbounded during indexing",
    repo="ejacklab/open-dsearch",
    owner="ejacklab",
    category=Category.BACKEND,
    severity=Severity.HIGH,
    status=Status.FIXED,
    fix="Added garbage collection",
    tags=["memory", "performance"],
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)

# Serialize to JSON
json_response = response.model_dump_json()
```
