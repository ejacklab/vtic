# vtic Data Models - Stage 1: Core Enums

This document defines all core enums for the vtic ticket system. These enums are used across models, API requests, and CLI commands.

---

## 1. Severity

**Python Code:**
```python
from enum import StrEnum


class Severity(StrEnum):
    """Ticket severity levels with weight for sorting."""
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
```

**Alternative Literal Type:**
```python
from typing import Literal

SeverityLiteral = Literal["critical", "high", "medium", "low"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `critical` | System-breaking issues requiring immediate attention. Production outages, data loss, security vulnerabilities actively exploited. |
| `high` | Significant impact on functionality or user experience. Major features broken or security issues with high exploitability. |
| `medium` | Moderate impact. Workarounds exist, or the issue affects non-core functionality. Performance degradation. |
| `low` | Minor impact. Cosmetic issues, edge cases, or nice-to-have improvements. No urgency. |

**Default Value:** `Severity.MEDIUM`

**Used In:**
- `Ticket.severity` - The ticket's severity level
- `TicketCreateRequest.severity` - Severity when creating a ticket
- `TicketUpdateRequest.severity` - Severity when updating a ticket
- `SearchQuery.severity` - Filter by severity
- CLI flags: `--severity {critical|high|medium|low}`

---

## 2. Status

**Python Code:**
```python
from enum import StrEnum
from typing import Dict, Set


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
```

**Alternative Literal Type:**
```python
from typing import Literal

StatusLiteral = Literal["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `open` | Ticket is newly created, acknowledged but work has not started. Ready for assignment. |
| `in_progress` | Work is actively being done on this ticket. Assigned to someone. |
| `blocked` | Work is stalled due to external dependency, waiting on another ticket, or unmet prerequisites. |
| `fixed` | The issue has been resolved (code merged, fix deployed) but not yet verified/closed. |
| `wont_fix` | A deliberate decision not to address this issue. Could be "won't fix", "can't reproduce", or "by design". |
| `closed` | Ticket is complete and verified. Issue is resolved or decision is final. |

**Valid Transitions:**

```
open ──────┬──→ in_progress ───┬──→ fixed ──┬──→ closed
           │                   │            │
           ├──→ blocked ───────┤            ├──→ wont_fix
           │                   │            │
           ├──→ wont_fix ←─────┘            │
           │                                │
           └──→ closed ←────────────────────┘
                                      ↑
                                      └── reopen

Terminal statuses: closed, wont_fix
```

**Default Value:** `Status.OPEN`

**Used In:**
- `Ticket.status` - Current status of the ticket
- `TicketCreateRequest.status` - Status when creating (default: open)
- `TicketUpdateRequest.status` - Status transitions
- `SearchQuery.status` - Filter by status
- `SearchQuery.not_status` - Exclude by status
- CLI flags: `--status {open|in_progress|blocked|fixed|wont_fix|closed}`

---

## 3. Category

**Python Code:**
```python
from enum import StrEnum
from typing import Dict, Set


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
    DATA = "data"               # Prefix: DA (two chars to distinguish from docs)
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
        return prefix_map.get(value, "X")
```

**Alternative Literal Type:**
```python
from typing import Literal

CategoryLiteral = Literal[
    "security", "auth", "code_quality", "performance",
    "frontend", "backend", "testing", "documentation",
    "infrastructure", "configuration", "api", "data",
    "ui", "dependencies", "build", "other"
]
```

**Values:**

| Value | ID Prefix | Description |
|-------|-----------|-------------|
| `security` | S | Security vulnerabilities, threats, or hardening. XSS, SQL injection, secrets exposure, etc. |
| `auth` | A | Authentication and authorization issues. Login, logout, permissions, roles, sessions. |
| `code_quality` | C | Code maintainability, readability, technical debt, refactoring needs. |
| `performance` | P | Speed, efficiency, resource usage, optimization opportunities. |
| `frontend` | F | Client-side code, browser compatibility, JavaScript/CSS/HTML issues. |
| `backend` | B | Server-side logic, business rules, data processing, internal services. |
| `testing` | T | Unit tests, integration tests, test coverage, test infrastructure. |
| `documentation` | D | README, API docs, inline comments, wiki pages, user guides. |
| `infrastructure` | I | Cloud resources, networking, load balancers, monitoring, logging. |
| `configuration` | G | Config files, environment variables, feature flags, settings. |
| `api` | X | External API design, REST endpoints, GraphQL, API contracts, versioning. |
| `data` | DA | Database design, migrations, data integrity, data models, schemas. |
| `ui` | U | User interface design, UX, visual polish, component behavior. |
| `dependencies` | E | Third-party libraries, package updates, dependency conflicts, licenses. |
| `build` | L | Build scripts, CI/CD pipelines, compilation, bundling, deployment. |
| `other` | O | Catch-all for anything that doesn't fit the above categories. |

**Default Value:** `Category.OTHER`

**ID Prefix Usage:**

```python
# Example: Generate ticket ID
category = Category.SECURITY
prefix = Category.get_prefix(category)  # "S"
ticket_id = f"{prefix}{sequence_number}"  # "S1", "S2", etc.
```

**Used In:**
- `Ticket.category` - The ticket's category
- `TicketCreateRequest.category` - Category when creating a ticket
- `TicketUpdateRequest.category` - Category when updating a ticket
- `SearchQuery.category` - Filter by category
- `SearchQuery.categories` - Filter by multiple categories (OR)
- ID generation: `Category.get_prefix(category) + sequence_number`
- CLI flags: `--category {security|auth|...|other}`

---

## 4. SortField

**Python Code:**
```python
from enum import StrEnum

class SortField(StrEnum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    SEVERITY = "severity"
    STATUS = "status"
    RELEVANCE = "relevance"
    TITLE = "title"
```

**Alternative Literal Type:**
```python
from typing import Literal

SortFieldLiteral = Literal[
    "created_at", "updated_at", "severity", "status", "relevance", "title"
]
```

**Values:**

| Value | Description |
|-------|-------------|
| `created_at` | Sort by ticket creation timestamp (chronological order). |
| `updated_at` | Sort by last modification timestamp (most recently updated first/last). |
| `severity` | Sort by severity level (critical > high > medium > low). |
| `status` | Sort by status (alphabetical by status name). |
| `relevance` | Sort by search relevance score (BM25 + semantic fusion). Only applicable when search query provided. |
| `title` | Sort alphabetically by ticket title. |

**Default Value:** `SortField.CREATED_AT` (or `SortField.RELEVANCE` when a search query is provided)

**Used In:**
- `SearchQuery.sort_field` - Primary sort field
- `SearchQuery.sort` - Combined sort specification (e.g., "-created_at,severity")
- `ListTicketsRequest.sort_field` - Sorting for list operations
- CLI flags: `--sort {created_at|updated_at|severity|status|relevance|title}` or `--sort -severity` for descending

---

## 5. SortOrder

**Python Code:**
```python
from enum import StrEnum

class SortOrder(StrEnum):
    ASC = "asc"
    DESC = "desc"
```

**Alternative Literal Type:**
```python
from typing import Literal

SortOrderLiteral = Literal["asc", "desc"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `asc` | Ascending order (A-Z, 0-9, oldest-newest for timestamps, low-high for severity). |
| `desc` | Descending order (Z-A, 9-0, newest-oldest for timestamps, high-low for severity). |

**Default Value:** `SortOrder.DESC` for timestamps and relevance, `SortOrder.ASC` for title and status

**Used In:**
- `SearchQuery.sort_order` - Direction of sort
- `ListTicketsRequest.sort_order` - Direction of sort
- CLI flags: `--order {asc|desc}` or prefix sort field with `-` for descending (e.g., `--sort -created_at`)

---

## 6. EmbeddingProvider

**Python Code:**
```python
from enum import StrEnum

class EmbeddingProvider(StrEnum):
    OPENAI = "openai"
    LOCAL = "local"
    NONE = "none"
```

**Alternative Literal Type:**
```python
from typing import Literal

EmbeddingProviderLiteral = Literal["openai", "local", "none"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `openai` | Use OpenAI's embedding API (text-embedding-3-small or text-embedding-3-large). Requires OPENAI_API_KEY. |
| `local` | Use local sentence-transformers model. Fully offline, no API key required. Downloads model on first use. |
| `none` | Disable semantic search. BM25 keyword search only. No embeddings generated or stored. |

**Default Value:** `EmbeddingProvider.NONE` (zero-config default, pure BM25)

**Used In:**
- `Config.embedding.provider` - Global embedding provider configuration
- `Config.embedding_provider` - Shorthand config field
- `IndexConfig.embedding_provider` - Per-index embedding provider
- CLI flags: `--embedding-provider {openai|local|none}`
- API: Search endpoint respects provider config

**Behavior by Provider:**

| Provider | Semantic Search | Requires API Key | Internet Required |
|----------|-----------------|------------------|-------------------|
| `openai` | Yes | OPENAI_API_KEY | Yes |
| `local` | Yes | No | No (after model download) |
| `none` | No | No | No |

---

## 7. DeleteMode

**Python Code:**
```python
from enum import StrEnum

class DeleteMode(StrEnum):
    SOFT = "soft"
    HARD = "hard"
```

**Alternative Literal Type:**
```python
from typing import Literal

DeleteModeLiteral = Literal["soft", "hard"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `soft` | Move ticket to trash (`.trash/` directory) or mark with `status: deleted`. Recoverable via `vtic restore`. |
| `hard` | Permanently delete the ticket file and remove from index. Irreversible. Requires `--force` flag in CLI. |

**Default Value:** `DeleteMode.SOFT` (safe default to prevent accidental data loss)

**Used In:**
- `DeleteTicketRequest.mode` - API delete mode
- `DeleteTicketsBulkRequest.mode` - Bulk delete mode
- `TrashConfig.default_mode` - Default trash behavior
- CLI flags: `--force` implies `hard`, default is `soft`
- CLI trash commands: `vtic trash list`, `vtic trash restore`, `vtic trash clean`

**Soft Delete Behavior:**
- Move file to `.trash/{owner}/{repo}/{category}/{ticket_id}_{timestamp}.md`
- Update index to mark as deleted (exclude from searches by default)
- Preserve git history if tickets are versioned
- Restorable via `vtic restore <id>`

**Hard Delete Behavior:**
- Permanently remove markdown file
- Remove from Zvec index
- Cannot be recovered
- Requires explicit opt-in via `--force`

---

## Summary Table

| Enum | Values | Default | Primary Usage |
|------|--------|---------|---------------|
| `Severity` | critical, high, medium, low | `MEDIUM` | Ticket.severity |
| `Status` | open, in_progress, blocked, fixed, wont_fix, closed | `OPEN` | Ticket.status, workflow |
| `Category` | 16 values (see table) | `OTHER` | Ticket.category, ID prefix, storage path |
| `SortField` | created_at, updated_at, severity, status, relevance, title | `CREATED_AT` | Search/list sorting |
| `SortOrder` | asc, desc | `DESC` (timestamps) | Sort direction |
| `EmbeddingProvider` | openai, local, none | `NONE` | Config.embedding.provider |
| `DeleteMode` | soft, hard | `SOFT` | Ticket deletion behavior |

---

## Implementation Notes for Coding Agent

1. **StrEnum vs Literal**: Use `StrEnum` for model fields and function parameters. Use `Literal` for type hints where enum class import would cause circular dependencies.

2. **Validation**: All enums should be validated at API boundaries (Pydantic models) and CLI entry points.

3. **Case Sensitivity**: Enums are case-sensitive. Always use lowercase values as defined above.

4. **Serialization**: When serializing to JSON/TOML/YAML, use the string value (e.g., `"critical"` not `Severity.CRITICAL`).

5. **Status Transitions**: Use `Status.can_transition_to(target)` method or check `VALID_STATUS_TRANSITIONS` directly. Implement validation in API/CLI to reject invalid transitions.

6. **Category to ID Prefix**: Use `Category.get_prefix(category)` to get the ID prefix. Some categories use two-character prefixes (e.g., `data` → `DA`) to avoid collisions.

7. **Embedding Provider None**: When `NONE`, semantic search endpoints should return a clear error: "Semantic search requires an embedding provider. Set embedding.provider to 'openai' or 'local' in vtic.toml."

8. **Delete Mode Soft Default**: Always default to soft delete in UI/CLI to prevent accidental data loss. Require explicit `--force` for hard delete.

9. **Severity Sorting**: Use `Severity.weight` property for numeric comparison when sorting by severity.

10. **Status Display**: Use `Status.display_name` for human-readable labels in CLI output and API responses.
