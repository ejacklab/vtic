# vtic Data Models - Stage 2: Ticket Models

Comprehensive Pydantic v2 models for the ticket management system.

> **Note:** Stage 1 defines the canonical enums. This stage imports from Stage 1 and extends with ticket models.
>
> **Canonical Source:** This document is derived from the OpenAPI 3.1.1 specification. In case of discrepancies, the OpenAPI spec is the source of truth.

## Enums (Imported from Stage 1)

```python
# Import enums from Stage 1 - DO NOT redefine here
from stage1_enums import Category, Severity, Status
```

> **Important:** The enums `Category`, `Severity`, and `Status` are defined in Stage 1. This document does not redefine them. See `data-models-stage1-enums.md` for full enum definitions.

---

## Core Ticket Model

```python
from datetime import datetime, timezone
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

# Import enums from Stage 1
from stage1_enums import Category, Severity, Status


class Ticket(BaseModel):
    """
    Full ticket representation - the core data model.
    
    This model represents a complete ticket in the system with all fields.
    Used for storage, internal representation, and full API responses.
    
    ID Pattern: ^[CFGHST]\d+$ (category prefix + sequence number)
    Slug Pattern: ^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$ (max 80 chars)
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "C1",
                "slug": "cors-wildcard-issue",
                "title": "CORS Wildcard Issue",
                "description": "The API allows wildcard CORS origins in production...",
                "repo": "ejacklab/open-dsearch",
                "category": "security",
                "severity": "high",
                "status": "open",
                "assignee": "ejack",
                "fix": "Updated Access-Control-Allow-Origin to domain whitelist",
                "tags": ["cors", "security", "api"],
                "references": ["C2", "C3"],
                "created": "2026-03-17T09:00:00Z",
                "updated": "2026-03-17T14:30:00Z",
            }
        }
    )
    
    # === Required Fields ===
    
    id: str = Field(
        ...,
        pattern=r"^[CFGHST]\d+$",
        description="Human-readable ID (e.g., C1, H5, F12, S3, G8)",
        examples=["C1"],
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ticket title",
        examples=["CORS Wildcard Issue"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Full ticket description (markdown supported)",
        examples=["The API allows wildcard CORS origins in production..."],
    )
    repo: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in owner/repo format",
        examples=["ejacklab/open-dsearch"],
    )
    category: Category = Field(
        ...,
        description="Ticket category (crash, hotfix, feature, security, general)",
    )
    severity: Severity = Field(
        ...,
        description="Impact level of the ticket",
    )
    status: Status = Field(
        ...,
        description="Current status in the ticket lifecycle",
    )
    created: datetime = Field(
        ...,
        description="ISO 8601 creation timestamp",
        examples=["2026-03-17T09:00:00Z"],
    )
    updated: datetime = Field(
        ...,
        description="ISO 8601 last update timestamp",
        examples=["2026-03-17T14:30:00Z"],
    )
    
    # === Optional Fields ===
    
    slug: Optional[str] = Field(
        default=None,
        pattern=r"^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$",
        description="URL-safe slug derived from title (max 80 chars)",
        examples=["cors-wildcard-issue"],
    )
    assignee: Optional[str] = Field(
        default=None,
        description="Assigned team member username",
        examples=["ejack"],
    )
    fix: Optional[str] = Field(
        default=None,
        description="Resolution details (set when status becomes fixed)",
        examples=["Updated Access-Control-Allow-Origin to domain whitelist"],
    )
    tags: List[str] = Field(
        default_factory=list,
        max_length=20,
        description="Labels for categorization",
        examples=[["cors", "security", "api"]],
    )
    references: List[str] = Field(
        default_factory=list,
        description="Related ticket IDs",
        examples=[["C2", "C3"]],
    )
    
    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        """Validate tag length and normalize."""
        normalized = []
        for tag in v:
            tag = str(tag).strip().lower()
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 50:
                normalized.append(tag)
        # Remove duplicates while preserving order
        seen = set()
        return [t for t in normalized if not (t in seen or seen.add(t))]
    
    @field_validator("references")
    @classmethod
    def validate_references(cls, v: List[str]) -> List[str]:
        """Validate reference IDs match ticket ID pattern."""
        import re
        pattern = re.compile(r"^[CFGHST]\d+$")
        return [ref for ref in v if pattern.match(ref)]
    
    def update_timestamp(self) -> None:
        """Update the updated timestamp to current UTC time."""
        self.updated = datetime.now(timezone.utc)
    
    def is_terminal(self) -> bool:
        """Check if ticket is in a terminal status."""
        return self.status in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)
    
    @property
    def id_prefix(self) -> str:
        """Get the category prefix from the ID."""
        import re
        match = re.match(r"^([CFGHST])", self.id)
        return match.group(1) if match else "G"
```

---

## API Request Models

### TicketCreate

```python
class TicketCreate(BaseModel):
    """
    Request body for creating a new ticket.
    
    Required fields: title, description, repo
    All other fields are optional with sensible defaults.
    
    ID and timestamps are auto-generated by the system.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "title": "CORS Wildcard Issue",
                "description": "The API allows wildcard CORS origins in production...",
                "repo": "ejacklab/open-dsearch",
                "category": "security",
                "severity": "high",
                "status": "open",
                "assignee": "ejack",
                "tags": ["cors", "security", "api"],
                "references": ["C2"],
            }
        }
    )
    
    # === Required Fields ===
    
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Ticket title",
        examples=["CORS Wildcard Issue"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Full ticket description",
        examples=["The API allows wildcard CORS origins in production..."],
    )
    repo: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$",
        description="Repository in owner/repo format",
        examples=["ejacklab/open-dsearch"],
    )
    
    # === Optional Fields (with defaults applied by system) ===
    
    category: Optional[Category] = Field(
        default=None,
        description="Ticket category (defaults to 'general' if not provided)",
    )
    severity: Optional[Severity] = Field(
        default=None,
        description="Issue severity level (defaults to 'medium' if not provided)",
    )
    status: Optional[Status] = Field(
        default=None,
        description="Initial ticket status (defaults to 'open' if not provided)",
    )
    assignee: Optional[str] = Field(
        default=None,
        description="Assigned team member",
    )
    fix: Optional[str] = Field(
        default=None,
        description="Resolution details (usually set later)",
    )
    tags: List[str] = Field(
        default_factory=list,
        description="Labels for categorization",
    )
    references: List[str] = Field(
        default_factory=list,
        description="Related ticket IDs",
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
        normalized = []
        for tag in v:
            tag = str(tag).strip().lower()
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 50:
                normalized.append(tag)
        seen = set()
        return [t for t in normalized if not (t in seen or seen.add(t))]
    
    @field_validator("references")
    @classmethod
    def validate_references(cls, v: List[str]) -> List[str]:
        """Validate reference IDs match ticket ID pattern."""
        import re
        pattern = re.compile(r"^[CFGHST]\d+$")
        return [ref for ref in v if pattern.match(ref)]
```

### TicketUpdate

```python
class TicketUpdate(BaseModel):
    """
    Request body for PATCH /tickets/:id endpoint.
    
    Partial update - only provided fields are modified.
    At least one field must be provided for a valid update.
    The updated timestamp is automatically refreshed by the system.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "status": "fixed",
                "fix": "Added memory limit and periodic garbage collection",
                "description_append": "\n\n## Update 2026-03-18\nIssue resolved in PR #42.",
            }
        }
    )
    
    # === Optional Fields (partial update) ===
    
    title: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="New title",
    )
    description: Optional[str] = Field(
        default=None,
        description="New description (replaces entire body)",
    )
    description_append: Optional[str] = Field(
        default=None,
        description="Text to append to existing description (does not replace)",
    )
    category: Optional[Category] = Field(
        default=None,
        description="New category",
    )
    severity: Optional[Severity] = Field(
        default=None,
        description="New severity level",
    )
    status: Optional[Status] = Field(
        default=None,
        description="New ticket status",
    )
    assignee: Optional[str] = Field(
        default=None,
        description="New assignee or null to unassign",
    )
    fix: Optional[str] = Field(
        default=None,
        description="Resolution details",
    )
    tags: Optional[List[str]] = Field(
        default=None,
        description="New tag list (replaces existing)",
    )
    references: Optional[List[str]] = Field(
        default=None,
        description="Updated related ticket IDs",
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
    
    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: Any) -> Optional[List[str]]:
        """Validate and normalize tags if provided."""
        if v is None:
            return None  # No change to tags
        if isinstance(v, str):
            v = [t.strip() for t in v.split(",") if t.strip()]
        normalized = []
        for tag in v:
            tag = str(tag).strip().lower()
            tag = "".join(c for c in tag if c.isalnum() or c == "-")
            if tag and len(tag) <= 50:
                normalized.append(tag)
        seen = set()
        return [t for t in normalized if not (t in seen or seen.add(t))]
    
    @field_validator("references")
    @classmethod
    def validate_references(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate reference IDs if provided."""
        if v is None:
            return None
        import re
        pattern = re.compile(r"^[CFGHST]\d+$")
        return [ref for ref in v if pattern.match(ref)]
    
    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "TicketUpdate":
        """Ensure at least one field is being updated."""
        fields_to_check = [
            self.title, self.description, self.description_append,
            self.category, self.severity, self.status,
            self.assignee, self.fix, self.tags, self.references
        ]
        if all(v is None for v in fields_to_check):
            raise ValueError("At least one field must be provided for update")
        return self
    
    def get_updates(self) -> dict[str, Any]:
        """
        Get a dictionary of fields that have been provided for update.
        
        Returns:
            Dictionary of field names to new values (excluding None values,
            except for tags/references which can be empty lists to clear)
        """
        updates = {}
        for field_name, value in self.model_dump(exclude_unset=True).items():
            if value is not None or field_name in ("tags", "references"):
                updates[field_name] = value
        return updates
```

---

## Response Models

### TicketSummary

```python
class TicketSummary(BaseModel):
    """
    Lightweight ticket for list responses.
    
    Contains essential fields for displaying in ticket lists.
    Does not include full description or all optional fields.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "C1",
                "title": "CORS Wildcard Issue",
                "severity": "high",
                "status": "open",
                "repo": "ejacklab/open-dsearch",
                "category": "security",
                "assignee": "ejack",
                "created": "2026-03-17T09:00:00Z",
                "updated": "2026-03-17T14:30:00Z",
            }
        }
    )
    
    # Required fields
    id: str = Field(
        ...,
        description="Ticket ID",
        examples=["C1"],
    )
    title: str = Field(
        ...,
        description="Ticket title",
        examples=["CORS Wildcard Issue"],
    )
    severity: Severity = Field(
        ...,
        description="Ticket severity",
    )
    status: Status = Field(
        ...,
        description="Ticket status",
    )
    repo: str = Field(
        ...,
        description="Repository",
        examples=["ejacklab/open-dsearch"],
    )
    category: Category = Field(
        ...,
        description="Ticket category",
    )
    created: datetime = Field(
        ...,
        description="Creation timestamp",
    )
    
    # Optional fields
    assignee: Optional[str] = Field(
        default=None,
        description="Assigned team member",
    )
    updated: Optional[datetime] = Field(
        default=None,
        description="Last update timestamp",
    )
```

### TicketResponse

```python
class TicketResponse(BaseModel):
    """
    Success envelope for single ticket operations.
    
    Wraps the full Ticket with optional metadata.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "data": {
                    "id": "C1",
                    "slug": "cors-wildcard-issue",
                    "title": "CORS Wildcard Issue",
                    "description": "The API allows wildcard CORS origins...",
                    "repo": "ejacklab/open-dsearch",
                    "category": "security",
                    "severity": "high",
                    "status": "open",
                    "assignee": "ejack",
                    "fix": None,
                    "tags": ["cors", "security", "api"],
                    "references": [],
                    "created": "2026-03-17T09:00:00Z",
                    "updated": "2026-03-17T14:30:00Z",
                },
                "meta": {
                    "request_id": "req_abc123",
                    "warnings": [],
                }
            }
        }
    )
    
    data: Ticket = Field(
        ...,
        description="The ticket data",
    )
    meta: Optional[dict] = Field(
        default=None,
        description="Optional metadata (request_id, warnings, etc.)",
    )
```

### TicketListResponse

```python
class TicketListResponse(BaseModel):
    """
    Paginated list of tickets.
    
    Contains TicketSummary objects (not full Tickets) for efficiency.
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "data": [
                    {
                        "id": "C1",
                        "title": "CORS Wildcard Issue",
                        "severity": "high",
                        "status": "open",
                        "repo": "ejacklab/open-dsearch",
                        "category": "security",
                        "created": "2026-03-17T09:00:00Z",
                    }
                ],
                "meta": {
                    "total": 82,
                    "limit": 20,
                    "offset": 0,
                    "has_more": True,
                    "request_id": "req_abc123",
                }
            }
        }
    )
    
    data: List[TicketSummary] = Field(
        default_factory=list,
        description="List of ticket summaries",
    )
    meta: dict = Field(
        ...,
        description="Pagination and metadata (total, limit, offset, has_more)",
    )
```

---

## Error Models

### ErrorResponse

```python
class ErrorDetail(BaseModel):
    """Details about a specific validation or error field."""
    
    field: Optional[str] = Field(
        default=None,
        description="Field name that caused the error",
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable error message",
    )
    value: Optional[str] = Field(
        default=None,
        description="The invalid value that was provided",
    )


class ErrorBody(BaseModel):
    """Error body structure."""
    
    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND)",
        examples=["VALIDATION_ERROR"],
    )
    message: str = Field(
        ...,
        description="Human-readable error description",
        examples=["Missing required field: title"],
    )
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="List of specific error details",
    )
    docs: Optional[str] = Field(
        default=None,
        description="Link to error documentation",
    )


class ErrorResponse(BaseModel):
    """Error envelope for all error responses."""
    
    error: ErrorBody = Field(
        ...,
        description="Error information",
    )
    meta: Optional[dict] = Field(
        default=None,
        description="Optional metadata (request_id, etc.)",
    )
```

---

## Model Relationships Summary

```
Stage 1 (Enums)
├── Category
├── Severity
├── Status
└── EmbeddingProvider

Stage 2 (Ticket Models)
├── Ticket (full model - all fields)
│   └── used by: TicketResponse.data
├── TicketSummary (lightweight - list view)
│   └── used by: TicketListResponse.data
├── TicketCreate (POST request)
│   └── creates → Ticket
├── TicketUpdate (PATCH request)
│   └── updates → Ticket
├── TicketResponse (single ticket API response)
├── TicketListResponse (list API response)
└── ErrorResponse (error API response)
```

---

## Usage Examples

### Creating a Ticket

```python
# From API request (POST /tickets)
create_data = TicketCreate(
    title="Memory leak in search indexer",
    description="Process memory grows unbounded during indexing",
    repo="ejacklab/open-dsearch",
    category=Category.BACKEND,  # Wait - Category only has: crash, hotfix, feature, security, general
)

# Actually, correct usage:
create_data = TicketCreate(
    title="Memory leak in search indexer",
    description="Process memory grows unbounded during indexing",
    repo="ejacklab/open-dsearch",
    category=Category.CRASH,  # Use appropriate category
    severity=Severity.HIGH,
    tags=["memory", "performance"]
)

# Storage layer generates the full Ticket:
ticket = Ticket(
    id="C1",  # Generated: C = crash prefix + sequence
    slug="memory-leak-in-search-indexer",  # Auto-generated from title
    title=create_data.title,
    description=create_data.description,
    repo=create_data.repo,
    category=create_data.category or Category.GENERAL,
    severity=create_data.severity or Severity.MEDIUM,
    status=create_data.status or Status.OPEN,
    assignee=create_data.assignee,
    fix=create_data.fix,
    tags=create_data.tags,
    references=create_data.references,
    created=datetime.now(timezone.utc),
    updated=datetime.now(timezone.utc),
)
```

### Updating a Ticket

```python
# Partial update from API request (PATCH /tickets/C1)
update_data = TicketUpdate(
    status=Status.FIXED,
    fix="Added garbage collection",
    description_append="\n\n## Resolved\nFixed in PR #42."
)

# Get fields to update
updates = update_data.get_updates()
# Result: {"status": "fixed", "fix": "Added garbage collection", "description_append": "\n\n## Resolved..."}

# Apply to existing ticket
if update_data.status:
    existing_ticket.status = update_data.status
if update_data.fix:
    existing_ticket.fix = update_data.fix
if update_data.description_append:
    existing_ticket.description += update_data.description_append
existing_ticket.update_timestamp()
```

### API Response

```python
# GET /tickets/C1 returns TicketResponse
response = TicketResponse(
    data=Ticket(
        id="C1",
        slug="memory-leak-in-search-indexer",
        title="Memory leak in search indexer",
        description="Process memory grows unbounded...",
        repo="ejacklab/open-dsearch",
        category=Category.CRASH,
        severity=Severity.HIGH,
        status=Status.FIXED,
        fix="Added garbage collection",
        tags=["memory", "performance"],
        references=[],
        created=datetime.now(timezone.utc),
        updated=datetime.now(timezone.utc),
    ),
    meta={"request_id": "req_abc123"}
)

# Serialize to JSON
json_response = response.model_dump_json()
```

---

## Field Reference

### Ticket Field Mapping (OpenAPI → Model)

| OpenAPI Field | Model Field | Type | Required | Notes |
|---------------|-------------|------|----------|-------|
| `id` | `id` | string | Yes | Pattern: `^[CFGHST]\d+$` |
| `slug` | `slug` | string | No | Pattern: `^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$` (80 chars max) |
| `title` | `title` | string | Yes | Min: 1, Max: 200 |
| `description` | `description` | string | Yes | Min: 1 |
| `repo` | `repo` | string | Yes | Pattern: `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` |
| `category` | `category` | Category | Yes | Enum from Stage 1 |
| `severity` | `severity` | Severity | Yes | Enum from Stage 1 |
| `status` | `status` | Status | Yes | Enum from Stage 1 |
| `assignee` | `assignee` | string? | No | Nullable |
| `fix` | `fix` | string? | No | Nullable |
| `tags` | `tags` | string[] | No | Max items: 20, item max: 50 chars |
| `references` | `references` | string[] | No | Items match `^[CFGHST]\d+$` |
| `created` | `created` | datetime | Yes | ISO 8601 format |
| `updated` | `updated` | datetime | Yes | ISO 8601 format |

### TicketCreate Field Mapping

| OpenAPI Field | Model Field | Type | Required | Default |
|---------------|-------------|------|----------|---------|
| `title` | `title` | string | Yes | - |
| `description` | `description` | string | Yes | - |
| `repo` | `repo` | string | Yes | - |
| `category` | `category` | Category? | No | `general` |
| `severity` | `severity` | Severity? | No | `medium` |
| `status` | `status` | Status? | No | `open` |
| `assignee` | `assignee` | string? | No | `null` |
| `fix` | `fix` | string? | No | `null` |
| `tags` | `tags` | string[] | No | `[]` |
| `references` | `references` | string[] | No | `[]` |

### TicketUpdate Field Mapping

| OpenAPI Field | Model Field | Type | Notes |
|---------------|-------------|------|-------|
| `title` | `title` | string? | Replaces title |
| `description` | `description` | string? | Replaces entire description |
| `description_append` | `description_append` | string? | Appends to existing description |
| `category` | `category` | Category? | Updates category |
| `severity` | `severity` | Severity? | Updates severity |
| `status` | `status` | Status? | Updates status (validated for transitions) |
| `assignee` | `assignee` | string? | Updates or clears assignee |
| `fix` | `fix` | string? | Updates resolution details |
| `tags` | `tags` | string[]? | Replaces all tags |
| `references` | `references` | string[]? | Replaces all references |

---

## Implementation Notes

1. **Import Enums from Stage 1**: Never redefine `Category`, `Severity`, or `Status` in Stage 2. Always import from Stage 1.

2. **Timestamp Fields**: Use `created` and `updated` (not `created_at`/`updated_at`). These are ISO 8601 datetime strings.

3. **ID Pattern**: Only valid prefixes are C, F, G, H, S. Pattern: `^[CFGHST]\d+$`

4. **Slug Pattern**: `^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$` - starts and ends with alphanumeric, max 80 chars.

5. **No Owner/File Fields**: These are not in the OpenAPI spec and should not be in the models.

6. **description_append**: This field in TicketUpdate appends text to the existing description rather than replacing it.

7. **Tags Max Length**: Each tag max 50 characters, max 20 tags per ticket.

8. **References**: Must match ticket ID pattern `^[CFGHST]\d+$`.
