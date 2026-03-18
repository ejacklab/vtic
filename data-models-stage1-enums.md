# vtic Data Models - Stage 1: Core Enums

This document defines all core enums for the vtic ticket system. These enums are used across models, API requests, and CLI commands.

> **Canonical Source:** This document is derived from the OpenAPI 3.1.1 specification. In case of discrepancies, the OpenAPI spec is the source of truth.

---

## 1. Category

**Python Code:**
```python
from enum import StrEnum
from typing import Dict


class Category(StrEnum):
    """
    Ticket category with ID prefix mapping.
    
    Categories determine both the storage directory and the ID prefix.
    For example, crash tickets get IDs like C1, C2, C3.
    
    ID Prefix Mapping:
    - crash → C
    - hotfix → H
    - feature → F
    - security → S
    - general → G
    """
    CRASH = "crash"         # Prefix: C
    HOTFIX = "hotfix"       # Prefix: H
    FEATURE = "feature"     # Prefix: F
    SECURITY = "security"   # Prefix: S
    GENERAL = "general"     # Prefix: G

    @classmethod
    def get_prefix(cls, category: "Category | str") -> str:
        """Get the ID prefix for a category."""
        prefix_map: Dict[str, str] = {
            cls.CRASH.value: "C",
            cls.HOTFIX.value: "H",
            cls.FEATURE.value: "F",
            cls.SECURITY.value: "S",
            cls.GENERAL.value: "G",
        }
        value = category.value if isinstance(category, Category) else category
        return prefix_map.get(value, "G")  # Unknown categories get G (general)
```

**Alternative Literal Type:**
```python
from typing import Literal

CategoryLiteral = Literal["crash", "hotfix", "feature", "security", "general"]
```

**Values:**

| Value | ID Prefix | Description |
|-------|-----------|-------------|
| `crash` | C | Application crashes, exceptions, system-breaking issues requiring immediate attention. |
| `hotfix` | H | Urgent fixes that need to be deployed quickly. Critical bugs in production. |
| `feature` | F | New features, enhancements, or improvements to existing functionality. |
| `security` | S | Security vulnerabilities, threats, or hardening. XSS, SQL injection, secrets exposure, etc. |
| `general` | G | General issues, questions, or tasks that don't fit other categories. Default category. |

**Default Value:** `Category.GENERAL`

**Used In:**
- `Ticket.category` - The ticket's category
- `TicketCreate.category` - Category when creating a ticket
- `TicketUpdate.category` - Category when updating a ticket
- `FilterSet.category` - Filter by category
- ID generation: `Category.get_prefix(category) + sequence_number`
- CLI flags: `--category {crash|hotfix|feature|security|general}`

**ID Pattern:** All ticket IDs follow `^[CFGHST]\d+$` pattern (category prefix + number).

---

## 2. Severity

**Python Code:**
```python
from enum import StrEnum


class Severity(StrEnum):
    """Ticket severity levels with weight for sorting."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @property
    def weight(self) -> int:
        """Get numeric weight for sorting (higher = more severe)."""
        weights = {
            self.CRITICAL: 4,
            self.HIGH: 3,
            self.MEDIUM: 2,
            self.LOW: 1,
            self.INFO: 0,
        }
        return weights.get(self, 0)
```

**Alternative Literal Type:**
```python
from typing import Literal

SeverityLiteral = Literal["critical", "high", "medium", "low", "info"]
```

**Values:**

| Value | Weight | Description |
|-------|--------|-------------|
| `critical` | 4 | System-breaking issues requiring immediate attention. Production outages, data loss, security vulnerabilities actively exploited. |
| `high` | 3 | Significant impact on functionality or user experience. Major features broken or security issues with high exploitability. |
| `medium` | 2 | Moderate impact. Workarounds exist, or the issue affects non-core functionality. Performance degradation. |
| `low` | 1 | Minor impact. Cosmetic issues, edge cases, or nice-to-have improvements. No urgency. |
| `info` | 0 | Informational only. No action required. Used for tracking, documentation, or awareness. |

**Default Value:** `Severity.MEDIUM`

**Used In:**
- `Ticket.severity` - The ticket's severity level
- `TicketCreate.severity` - Severity when creating a ticket
- `TicketUpdate.severity` - Severity when updating a ticket
- `FilterSet.severity` - Filter by severity
- CLI flags: `--severity {critical|high|medium|low|info}`

---

## 3. Status

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
- `TicketCreate.status` - Status when creating (default: open)
- `TicketUpdate.status` - Status transitions
- `FilterSet.status` - Filter by status
- CLI flags: `--status {open|in_progress|blocked|fixed|wont_fix|closed}`

---

## 4. EmbeddingProvider

**Python Code:**
```python
from enum import StrEnum


class EmbeddingProvider(StrEnum):
    """Embedding provider for semantic search."""
    LOCAL = "local"
    OPENAI = "openai"
    CUSTOM = "custom"
    NONE = "none"
```

**Alternative Literal Type:**
```python
from typing import Literal

EmbeddingProviderLiteral = Literal["local", "openai", "custom", "none"]
```

**Values:**

| Value | Description |
|-------|-------------|
| `local` | Use local sentence-transformers model. Fully offline, no API key required. Downloads model on first use. |
| `openai` | Use OpenAI's embedding API (text-embedding-3-small or text-embedding-3-large). Requires OPENAI_API_KEY. |
| `custom` | Use a custom embedding provider. Configured via custom endpoint URL and authentication. |
| `none` | Disable semantic search. BM25 keyword search only. No embeddings generated or stored. |

**Default Value:** `EmbeddingProvider.NONE` (zero-config default, pure BM25)

**Used In:**
- `Config.embeddings.provider` - Global embedding provider configuration
- `ReindexRequest.provider` - Override provider for reindex operation
- CLI flags: `--embedding-provider {local|openai|custom|none}`
- API: Search endpoint respects provider config

**Behavior by Provider:**

| Provider | Semantic Search | Requires API Key | Internet Required |
|----------|-----------------|------------------|-------------------|
| `local` | Yes | No | No (after model download) |
| `openai` | Yes | OPENAI_API_KEY | Yes |
| `custom` | Yes | Provider-specific | Provider-specific |
| `none` | No | No | No |

---

## Summary Table

| Enum | Values | Default | Primary Usage |
|------|--------|---------|---------------|
| `Category` | crash, hotfix, feature, security, general | `GENERAL` | Ticket.category, ID prefix |
| `Severity` | critical, high, medium, low, info | `MEDIUM` | Ticket.severity |
| `Status` | open, in_progress, blocked, fixed, wont_fix, closed | `OPEN` | Ticket.status, workflow |
| `EmbeddingProvider` | local, openai, custom, none | `NONE` | Config.embeddings.provider |

---

## Implementation Notes for Coding Agent

1. **StrEnum vs Literal**: Use `StrEnum` for model fields and function parameters. Use `Literal` for type hints where enum class import would cause circular dependencies.

2. **Validation**: All enums should be validated at API boundaries (Pydantic models) and CLI entry points.

3. **Case Sensitivity**: Enums are case-sensitive. Always use lowercase values as defined above.

4. **Serialization**: When serializing to JSON/TOML/YAML, use the string value (e.g., `"critical"` not `Severity.CRITICAL`).

5. **Status Transitions**: Use `Status.can_transition_to(target)` method or check `VALID_STATUS_TRANSITIONS` directly. Implement validation in API/CLI to reject invalid transitions.

6. **Category to ID Prefix**: Use `Category.get_prefix(category)` to get the ID prefix. Only 5 valid categories exist, each with a single-character prefix.

7. **ID Pattern**: Ticket IDs follow pattern `^[CFGHST]\d+$`. Valid prefixes: C (crash), F (feature), G (general), H (hotfix), S (security). Note: T is reserved for testing but not a current category.

8. **Embedding Provider None**: When `NONE`, semantic search endpoints should return a clear error: "Semantic search requires an embedding provider. Set embedding.provider to 'local', 'openai', or 'custom' in vtic.toml."

9. **Severity Sorting**: Use `Severity.weight` property for numeric comparison when sorting by severity. Info has weight 0 (lowest).

10. **Status Display**: Use `Status.display_name` for human-readable labels in CLI output and API responses.
