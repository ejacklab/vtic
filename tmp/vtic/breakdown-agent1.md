# Ticket Lifecycle - 6-Level Breakdown

13 Core features broken down to implementation-ready specifications.

---

## Feature 1: CLI Ticket Creation

### L1: Ticket Lifecycle
### L2: Create
### L3: CLI ticket creation
### L4: `create_ticket_from_cli(args: CreateArgs) -> Ticket`
  - Parse CLI arguments from argparse Namespace into validated ticket data
  - Extract title, description, repo, category, severity, status, tags, file_refs
  - Validate required fields are present (title, repo)
  - Call ID generator for auto-generated ID
  - Call timestamp generator for created/updated fields
  - Delegate to storage layer for persistence
  - Return created Ticket dataclass

### L5: Spec
```python
@dataclass
class CreateArgs:
    title: str
    repo: str
    description: Optional[str] = None
    category: str = "code"
    severity: str = "medium"
    status: str = "open"
    tags: List[str] = field(default_factory=list)
    file_refs: List[str] = field(default_factory=list)

def create_ticket_from_cli(args: CreateArgs, store: TicketStore) -> Ticket:
    """
    Input: CreateArgs with title="CORS Bug", repo="ejacklab/open-dsearch", severity="critical"
    Output: Ticket(id="C1", title="CORS Bug", repo="ejacklab/open-dsearch", 
                   severity="critical", status="open", category="code",
                   created="2026-03-17T10:00:00Z", updated="2026-03-17T10:00:00Z")
    Error: ValueError if title is empty or missing
           ValueError if repo is empty or missing
           ValueError if repo format invalid (not "owner/repo")
    """
```

### L6: Test
```python
test_create_ticket_from_cli_valid_minimal()
test_create_ticket_from_cli_valid_all_fields()
test_create_ticket_from_cli_missing_title_raises_value_error()
test_create_ticket_from_cli_empty_title_raises_value_error()
test_create_ticket_from_cli_missing_repo_raises_value_error()
test_create_ticket_from_cli_invalid_repo_format_raises_value_error()
test_create_ticket_from_cli_default_values_applied()
```

---

## Feature 2: Auto-Generated IDs

### L1: Ticket Lifecycle
### L2: Create
### L3: Auto-generated IDs
### L4: `generate_ticket_id(category: str, existing_ids: Set[str]) -> str`
  - Generate unique human-readable ID based on category prefix
  - Category prefixes: C (code), S (security), H (hotfix), M (maintenance), D (docs), I (infra)
  - Format: `{PREFIX}{NUMBER}` (e.g., C1, S2, H3)
  - Increment number until unique ID found (not in existing_ids)
  - Thread-safe: handle concurrent creation with atomic ID assignment

### L5: Spec
```python
CATEGORY_PREFIXES = {
    "code": "C",
    "security": "S",
    "hotfix": "H",
    "maintenance": "M",
    "docs": "D",
    "infra": "I",
}

def generate_ticket_id(category: str, existing_ids: Set[str]) -> str:
    """
    Input: category="security", existing_ids={"S1", "S2", "S3"}
    Output: "S4"
    
    Input: category="code", existing_ids={"C1", "C3"}  # gap in sequence
    Output: "C2"  # fills lowest gap
    
    Input: category="unknown", existing_ids=set()
    Output: "X1"  # unknown categories get "X" prefix
    
    Error: ValueError if category is None or empty (use "X" prefix instead)
    """
```

### L6: Test
```python
test_generate_ticket_id_first_in_category()
test_generate_ticket_id_sequential()
test_generate_ticket_id_fills_gaps()
test_generate_ticket_id_unknown_category_uses_x_prefix()
test_generate_ticket_id_empty_category_uses_x_prefix()
test_generate_ticket_id_concurrent_creation_no_collision()
test_generate_ticket_id_all_category_prefixes()
```

---

## Feature 3: Timestamp Auto-Fill

### L1: Ticket Lifecycle
### L2: Create
### L3: Timestamp auto-fill
### L4: `auto_fill_timestamps(ticket: Ticket, now: Optional[datetime] = None) -> Ticket`
  - Set `created` timestamp to current UTC time if not provided
  - Set `updated` timestamp to same as `created` on new tickets
  - Accept optional `now` parameter for deterministic testing
  - Use ISO 8601 format: `YYYY-MM-DDTHH:MM:SSZ`

### L5: Spec
```python
def auto_fill_timestamps(ticket: Ticket, now: Optional[datetime] = None) -> Ticket:
    """
    Input: Ticket(id="C1", title="Bug", created=None, updated=None)
           now=datetime(2026, 3, 17, 10, 0, 0, tzinfo=timezone.utc)
    Output: Ticket(id="C1", title="Bug", 
                   created="2026-03-17T10:00:00Z", 
                   updated="2026-03-17T10:00:00Z")
    
    Input: Ticket(id="C1", title="Bug", created="2026-03-15T09:00:00Z", updated=None)
    Output: Ticket(..., created="2026-03-15T09:00:00Z", updated="2026-03-15T09:00:00Z")
    
    Note: This is for creation. Update operations should only modify `updated`.
    """
```

### L6: Test
```python
test_auto_fill_timestamps_sets_both_on_new_ticket()
test_auto_fill_timestamps_preserves_existing_created()
test_auto_fill_timestamps_uses_provided_now_parameter()
test_auto_fill_timestamps_uses_utc_timezone()
test_auto_fill_timestamps_iso8601_format()
```

---

## Feature 4: Required Field Validation

### L1: Ticket Lifecycle
### L2: Create
### L3: Required field validation
### L4: `validate_ticket_required_fields(ticket: Ticket) -> ValidationResult`
  - Validate `title` is non-empty string after stripping whitespace
  - Validate `repo` is non-empty and matches `owner/repo` format
  - Return ValidationResult with `is_valid: bool` and `errors: List[ValidationError]`
  - Each ValidationError has `field: str`, `message: str`, `code: str`

### L5: Spec
```python
@dataclass
class ValidationError:
    field: str
    message: str
    code: str

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]

def validate_ticket_required_fields(ticket: Ticket) -> ValidationResult:
    """
    Input: Ticket(id="C1", title="Valid Title", repo="owner/repo")
    Output: ValidationResult(is_valid=True, errors=[])
    
    Input: Ticket(id="C1", title="", repo="owner/repo")
    Output: ValidationResult(is_valid=False, 
                             errors=[ValidationError(field="title", 
                                                     message="Title is required", 
                                                     code="REQUIRED_FIELD_EMPTY")])
    
    Input: Ticket(id="C1", title="Title", repo="invalid-format")
    Output: ValidationResult(is_valid=False,
                             errors=[ValidationError(field="repo",
                                                     message="Repo must be in format 'owner/repo'",
                                                     code="INVALID_REPO_FORMAT")])
    
    Input: Ticket(id="C1", title="", repo="")
    Output: ValidationResult(is_valid=False, errors=[...])  # Both errors
    """
```

### L6: Test
```python
test_validate_ticket_required_fields_valid()
test_validate_ticket_required_fields_empty_title()
test_validate_ticket_required_fields_whitespace_only_title()
test_validate_ticket_required_fields_missing_repo()
test_validate_ticket_required_fields_invalid_repo_format()
test_validate_ticket_required_fields_multiple_errors()
test_validate_ticket_required_fields_repo_with_spaces_invalid()
```

---

## Feature 5: Get Ticket by ID

### L1: Ticket Lifecycle
### L2: Read
### L3: Get by ID
### L4: `get_ticket_by_id(ticket_id: str, store: TicketStore) -> Optional[Ticket]`
  - Look up ticket by ID in storage layer
  - Return Ticket dataclass if found
  - Return None if not found (no exception)
  - Case-insensitive ID matching (C1 == c1)

### L5: Spec
```python
def get_ticket_by_id(ticket_id: str, store: TicketStore) -> Optional[Ticket]:
    """
    Input: ticket_id="C1", store with ticket C1 exists
    Output: Ticket(id="C1", title="...", ...)
    
    Input: ticket_id="c1", store with ticket C1 exists (lowercase query)
    Output: Ticket(id="C1", title="...", ...)  # case-insensitive match
    
    Input: ticket_id="NONEXISTENT", store with ticket does not exist
    Output: None
    
    Input: ticket_id="", store
    Output: None  # empty ID returns None, no error
    """
```

### L6: Test
```python
test_get_ticket_by_id_exists()
test_get_ticket_by_id_not_found_returns_none()
test_get_ticket_by_id_case_insensitive()
test_get_ticket_by_id_empty_string_returns_none()
test_get_ticket_by_id_whitespace_trimmed()
```

---

## Feature 6: CLI Get Command Output

### L1: Ticket Lifecycle
### L2: Read
### L3: CLI get command
### L4: `cli_get_ticket(ticket_id: str, store: TicketStore, format: str = "table") -> int`
  - Fetch ticket by ID using get_ticket_by_id
  - Format output based on format parameter (table, json, markdown)
  - Print formatted output to stdout
  - Return exit code: 0 for success, 1 for not found, 2 for error

### L5: Spec
```python
def cli_get_ticket(ticket_id: str, store: TicketStore, format: str = "table") -> int:
    """
    Input: ticket_id="C1", store with C1 exists, format="table"
    Output (stdout): Formatted table with ticket fields
    Return: 0
    
    Input: ticket_id="C1", store with C1 exists, format="json"
    Output (stdout): {"id": "C1", "title": "...", ...}
    Return: 0
    
    Input: ticket_id="NONEXISTENT", store
    Output (stderr): "Ticket NONEXISTENT not found"
    Return: 1
    
    Input: format="invalid"
    Output (stderr): "Unknown format: invalid. Use: table, json, markdown"
    Return: 2
    """
```

### L6: Test
```python
test_cli_get_ticket_table_format()
test_cli_get_ticket_json_format()
test_cli_get_ticket_markdown_format()
test_cli_get_ticket_not_found_exit_code_1()
test_cli_get_ticket_invalid_format_exit_code_2()
test_cli_get_ticket_json_output_is_valid_json()
```

---

## Feature 7: Field-Level Updates (CLI)

### L1: Ticket Lifecycle
### L2: Update
### L3: Field-level updates (CLI)
### L4: `update_ticket_fields(ticket_id: str, updates: Dict[str, Any], store: TicketStore) -> Ticket`
  - Fetch existing ticket by ID
  - Apply only specified field updates (partial update)
  - Validate new field values if they have constraints
  - Auto-update `updated` timestamp to current time
  - Preserve unmodified fields
  - Persist updated ticket
  - Return updated Ticket

### L5: Spec
```python
def update_ticket_fields(ticket_id: str, updates: Dict[str, Any], store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", 
           updates={"status": "fixed", "severity": "critical"},
           store with C1 existing
    Output: Ticket(id="C1", status="fixed", severity="critical", 
                   updated="2026-03-17T11:30:00Z", ...)  # other fields preserved
    
    Input: ticket_id="C1", updates={}, store
    Output: Ticket(...)  # unchanged except updated timestamp
    
    Input: ticket_id="NONEXISTENT", updates={...}
    Error: TicketNotFoundError(f"Ticket {ticket_id} not found")
    
    Input: ticket_id="C1", updates={"status": "invalid_status"}
    Error: ValidationError("Invalid status: invalid_status")
    
    Allowed update fields: title, description, status, severity, category, tags, file_refs, fix
    Disallowed update fields: id, created, repo (immutable after creation)
    """
```

### L6: Test
```python
test_update_ticket_fields_single_field()
test_update_ticket_fields_multiple_fields()
test_update_ticket_fields_preserves_unmodified()
test_update_ticket_fields_updates_timestamp()
test_update_ticket_fields_empty_updates_only_timestamp()
test_update_ticket_fields_ticket_not_found_raises()
test_update_ticket_fields_invalid_status_raises()
test_update_ticket_fields_immutable_field_ignored_or_raises()
```

---

## Feature 8: CLI Update Command

### L1: Ticket Lifecycle
### L2: Update
### L3: CLI update command
### L4: `cli_update_ticket(args: UpdateArgs, store: TicketStore) -> int`
  - Parse CLI arguments into field update dictionary
  - Handle `--set field=value` syntax for arbitrary fields
  - Handle specific flags like `--status`, `--severity`, `--title`
  - Call update_ticket_fields with parsed updates
  - Print confirmation message or error
  - Return exit code: 0 success, 1 not found, 2 validation error

### L5: Spec
```python
@dataclass
class UpdateArgs:
    ticket_id: str
    title: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    set_fields: List[str] = field(default_factory=list)  # ["field=value", ...]

def cli_update_ticket(args: UpdateArgs, store: TicketStore) -> int:
    """
    Input: UpdateArgs(ticket_id="C1", status="fixed")
    Output (stdout): "Updated C1: status=fixed"
    Return: 0
    
    Input: UpdateArgs(ticket_id="C1", set_fields=["custom_field=custom_value"])
    Output (stdout): "Updated C1: custom_field=custom_value"
    Return: 0
    
    Input: UpdateArgs(ticket_id="NONEXISTENT", status="fixed")
    Output (stderr): "Ticket NONEXISTENT not found"
    Return: 1
    
    Input: UpdateArgs(ticket_id="C1", status="invalid")
    Output (stderr): "Invalid status: invalid. Valid values: open, in_progress, blocked, fixed, wont_fix, closed"
    Return: 2
    """
```

### L6: Test
```python
test_cli_update_ticket_status_flag()
test_cli_update_ticket_set_syntax()
test_cli_update_ticket_multiple_flags()
test_cli_update_ticket_not_found_exit_code_1()
test_cli_update_ticket_validation_error_exit_code_2()
test_cli_update_ticket_combines_flags_and_set_syntax()
```

---

## Feature 9: Delete Ticket (CLI)

### L1: Ticket Lifecycle
### L2: Delete
### L3: Delete ticket (CLI)
### L4: `delete_ticket(ticket_id: str, store: TicketStore, force: bool = False) -> bool`
  - Remove ticket file from storage
  - Remove ticket from Zvec index
  - If force=False, move to .trash/ instead of permanent delete (soft delete)
  - If force=True, permanently delete file and index entry
  - Return True if deleted, False if not found

### L5: Spec
```python
def delete_ticket(ticket_id: str, store: TicketStore, force: bool = False) -> bool:
    """
    Input: ticket_id="C1", store with C1, force=False
    Action: Move tickets/owner/repo/code/C1.md to .trash/C1.md
            Remove C1 from Zvec index
    Output: True
    
    Input: ticket_id="C1", store with C1, force=True
    Action: Permanently delete tickets/owner/repo/code/C1.md
            Remove C1 from Zvec index
    Output: True
    
    Input: ticket_id="NONEXISTENT", store
    Output: False  # no exception, just return False
    
    Note: .trash/ directory created if it doesn't exist
    """
```

### L6: Test
```python
test_delete_ticket_soft_delete_moves_to_trash()
test_delete_ticket_force_permanently_removes()
test_delete_ticket_not_found_returns_false()
test_delete_ticket_removes_from_index()
test_delete_ticket_trash_directory_created_if_missing()
test_delete_ticket_soft_delete_preserves_file_content()
```

---

## Feature 10: CLI Delete Command

### L1: Ticket Lifecycle
### L2: Delete
### L3: CLI delete command
### L4: `cli_delete_ticket(args: DeleteArgs, store: TicketStore) -> int`
  - Parse ticket_id and force flag from CLI args
  - Prompt for confirmation unless --yes flag provided
  - Call delete_ticket with appropriate force setting
  - Print confirmation or error message
  - Return exit code: 0 success, 1 not found, 2 cancelled

### L5: Spec
```python
@dataclass
class DeleteArgs:
    ticket_id: str
    force: bool = False
    yes: bool = False  # skip confirmation

def cli_delete_ticket(args: DeleteArgs, store: TicketStore, input_fn=input) -> int:
    """
    Input: DeleteArgs(ticket_id="C1", force=False, yes=True), store with C1
    Action: Delete C1 (soft), no prompt
    Output (stdout): "Deleted C1 (moved to trash)"
    Return: 0
    
    Input: DeleteArgs(ticket_id="C1", force=True, yes=True), store with C1
    Action: Delete C1 (permanent), no prompt
    Output (stdout): "Permanently deleted C1"
    Return: 0
    
    Input: DeleteArgs(ticket_id="C1", yes=False), store with C1, input_fn returns "n"
    Output (stdout): "Cancelled"
    Return: 2
    
    Input: DeleteArgs(ticket_id="NONEXISTENT", yes=True)
    Output (stderr): "Ticket NONEXISTENT not found"
    Return: 1
    """
```

### L6: Test
```python
test_cli_delete_ticket_soft_with_yes_flag()
test_cli_delete_ticket_force_with_yes_flag()
test_cli_delete_ticket_prompts_without_yes()
test_cli_delete_ticket_cancelled_returns_2()
test_cli_delete_ticket_not_found_returns_1()
test_cli_delete_ticket_confirmed_proceeds()
```

---

## Feature 11: Built-in Status: Open

### L1: Ticket Lifecycle
### L2: Status
### L3: Built-in status: open
### L4: `validate_status_transition(current: str, new: str) -> bool`
  - Define "open" as valid initial status for new tickets
  - Allow transitions FROM open TO: in_progress, blocked, fixed, wont_fix, closed
  - Disallow transitions FROM open TO: open (no-op allowed but no transition)

### L5: Spec
```python
VALID_STATUSES = ["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"]

OPEN_TRANSITIONS = ["in_progress", "blocked", "fixed", "wont_fix", "closed"]

def validate_status_transition(current: Optional[str], new: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if status transition is allowed.
    
    Input: current=None, new="open"  # new ticket
    Output: (True, None)
    
    Input: current="open", new="in_progress"
    Output: (True, None)
    
    Input: current="open", new="invalid"
    Output: (False, "Invalid status: invalid. Valid: open, in_progress, blocked, fixed, wont_fix, closed")
    
    Input: current="open", new="open"
    Output: (True, None)  # no-op allowed
    
    Note: v0.1 allows all transitions; workflow enforcement is P2
    """
```

### L6: Test
```python
test_validate_status_open_valid_initial()
test_validate_status_open_to_in_progress()
test_validate_status_open_to_blocked()
test_validate_status_open_to_fixed()
test_validate_status_open_to_wont_fix()
test_validate_status_open_to_closed()
test_validate_status_invalid_status_rejected()
```

---

## Feature 12: Built-in Status: In Progress / Blocked

### L1: Ticket Lifecycle
### L2: Status
### L3: Built-in statuses: in_progress, blocked
### L4: `get_status_metadata(status: str) -> StatusMetadata`
  - Define "in_progress" as active work state
  - Define "blocked" as waiting on external dependency
  - Provide metadata: display_name, description, color (for CLI output)
  - v0.1: No transition restrictions (any status can transition to any other)

### L5: Spec
```python
@dataclass
class StatusMetadata:
    name: str
    display_name: str
    description: str
    color: str  # ANSI color code

STATUS_METADATA = {
    "in_progress": StatusMetadata(
        name="in_progress",
        display_name="In Progress",
        description="Currently being worked on",
        color="yellow"
    ),
    "blocked": StatusMetadata(
        name="blocked",
        display_name="Blocked",
        description="Waiting on external dependency",
        color="red"
    ),
}

def get_status_metadata(status: str) -> Optional[StatusMetadata]:
    """
    Input: status="in_progress"
    Output: StatusMetadata(name="in_progress", display_name="In Progress", ...)
    
    Input: status="blocked"
    Output: StatusMetadata(name="blocked", display_name="Blocked", ...)
    
    Input: status="unknown"
    Output: None
    """
```

### L6: Test
```python
test_get_status_metadata_in_progress()
test_get_status_metadata_blocked()
test_get_status_metadata_unknown_returns_none()
test_status_metadata_display_name_capitalized()
test_status_metadata_has_color()
```

---

## Feature 13: Built-in Status: Fixed / Wont Fix / Closed

### L1: Ticket Lifecycle
### L2: Status
### L3: Built-in statuses: fixed, wont_fix, closed
### L4: `is_terminal_status(status: str) -> bool`
  - Define "fixed" as successfully resolved
  - Define "wont_fix" as will not be resolved
  - Define "closed" as generic closed state
  - Mark fixed, wont_fix, closed as terminal statuses (ticket work complete)
  - Terminal statuses can still be reopened (v0.1 allows all transitions)

### L5: Spec
```python
TERMINAL_STATUSES = ["fixed", "wont_fix", "closed"]

def is_terminal_status(status: str) -> bool:
    """
    Check if status is terminal (work completed).
    
    Input: status="fixed"
    Output: True
    
    Input: status="wont_fix"
    Output: True
    
    Input: status="closed"
    Output: True
    
    Input: status="open"
    Output: False
    
    Input: status="in_progress"
    Output: False
    """

def get_status_metadata(status: str) -> Optional[StatusMetadata]:
    """
    Extended with terminal statuses:
    
    "fixed": StatusMetadata(name="fixed", display_name="Fixed", 
                            description="Issue resolved", color="green")
    "wont_fix": StatusMetadata(name="wont_fix", display_name="Won't Fix",
                               description="Will not be resolved", color="gray")
    "closed": StatusMetadata(name="closed", display_name="Closed",
                             description="Ticket closed", color="blue")
    """
```

### L6: Test
```python
test_is_terminal_status_fixed()
test_is_terminal_status_wont_fix()
test_is_terminal_status_closed()
test_is_terminal_status_open_false()
test_is_terminal_status_in_progress_false()
test_is_terminal_status_blocked_false()
test_terminal_status_metadata_has_distinct_colors()
test_all_terminal_statuses_in_terminal_statuses_list()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | Ticket Lifecycle | Create | CLI ticket creation | `create_ticket_from_cli()` |
| 2 | Ticket Lifecycle | Create | Auto-generated IDs | `generate_ticket_id()` |
| 3 | Ticket Lifecycle | Create | Timestamp auto-fill | `auto_fill_timestamps()` |
| 4 | Ticket Lifecycle | Create | Required field validation | `validate_ticket_required_fields()` |
| 5 | Ticket Lifecycle | Read | Get by ID | `get_ticket_by_id()` |
| 6 | Ticket Lifecycle | Read | CLI get command | `cli_get_ticket()` |
| 7 | Ticket Lifecycle | Update | Field-level updates (CLI) | `update_ticket_fields()` |
| 8 | Ticket Lifecycle | Update | CLI update command | `cli_update_ticket()` |
| 9 | Ticket Lifecycle | Delete | Delete ticket (CLI) | `delete_ticket()` |
| 10 | Ticket Lifecycle | Delete | CLI delete command | `cli_delete_ticket()` |
| 11 | Ticket Lifecycle | Status | Built-in status: open | `validate_status_transition()` |
| 12 | Ticket Lifecycle | Status | Built-in statuses: in_progress, blocked | `get_status_metadata()` |
| 13 | Ticket Lifecycle | Status | Built-in statuses: fixed, wont_fix, closed | `is_terminal_status()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime

@dataclass
class Ticket:
    id: str
    title: str
    repo: str
    description: Optional[str] = None
    category: str = "code"
    severity: str = "medium"
    status: str = "open"
    tags: List[str] = field(default_factory=list)
    file_refs: List[str] = field(default_factory=list)
    fix: Optional[str] = None
    created: Optional[str] = None  # ISO 8601
    updated: Optional[str] = None  # ISO 8601

@dataclass
class ValidationError:
    field: str
    message: str
    code: str

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ValidationError]

@dataclass
class StatusMetadata:
    name: str
    display_name: str
    description: str
    color: str

class TicketStore(Protocol):
    def get(self, ticket_id: str) -> Optional[Ticket]: ...
    def save(self, ticket: Ticket) -> None: ...
    def delete(self, ticket_id: str) -> bool: ...
    def move_to_trash(self, ticket_id: str) -> bool: ...
    def list_ids(self) -> Set[str]: ...
```
