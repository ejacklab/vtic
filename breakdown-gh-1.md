# Good to Have (P2) Features - 6-Level Breakdown

27 P2 features broken down to implementation-ready specifications.

---

## Feature 1: Template-Based Creation

### L1: Ticket Lifecycle
### L2: Create
### L3: Template-based creation
### L4: `create_ticket_from_template(template_name: str, args: TemplateArgs, store: TicketStore) -> Ticket`
  - Load template file from `~/.config/vtic/templates/{template_name}.toml`
  - Merge template defaults with CLI-provided overrides
  - Template contains: default field values, required fields, field prompts
  - CLI args override template defaults
  - Validate all required fields present after merge
  - Generate ID and timestamps as normal
  - Persist and return created Ticket

### L5: Spec
```python
@dataclass
class TemplateConfig:
    name: str
    defaults: Dict[str, Any]  # {"category": "security", "severity": "high"}
    required: List[str]  # ["title", "description"]
    prompts: Dict[str, str]  # {"title": "What is the security issue?"}

@dataclass
class TemplateArgs:
    template: str
    title: Optional[str] = None
    description: Optional[str] = None
    overrides: Dict[str, Any] = field(default_factory=dict)

def create_ticket_from_template(template_name: str, args: TemplateArgs, store: TicketStore) -> Ticket:
    """
    Input: template_name="security-issue", 
           args=TemplateArgs(title="XSS in search", overrides={"severity": "critical"})
    Template file ~/.config/vtic/templates/security-issue.toml:
           [defaults]
           category = "security"
           severity = "high"
           tags = ["security", "needs-review"]
    Output: Ticket(id="S5", title="XSS in search", category="security", 
                   severity="critical", tags=["security", "needs-review"], ...)
    
    Input: template_name="nonexistent"
    Error: TemplateNotFoundError(f"Template '{template_name}' not found")
    
    Input: template with required=["description"], args without description
    Error: ValidationError("Template requires field: description")
    """
```

### L6: Test
```python
test_create_ticket_from_template_applies_defaults()
test_create_ticket_from_template_overrides_defaults()
test_create_ticket_from_template_missing_raises()
test_create_ticket_from_template_merges_tags()
test_create_ticket_from_template_nonexistent_raises()
test_create_ticket_from_template_validates_required_fields()
test_create_ticket_from_template_builtin_security()
```

---

## Feature 2: Interactive Creation

### L1: Ticket Lifecycle
### L2: Create
### L3: Interactive creation
### L4: `create_ticket_interactive(prompt_fn: Callable[[str], str], store: TicketStore) -> Ticket`
  - Check if terminal is TTY (sys.stdout.isatty())
  - Prompt for required fields (title, repo) if not provided
  - Offer optional fields with defaults
  - Support multiline input for description (empty line to end)
  - Show preview before confirmation
  - Allow edit loop before final save
  - Return created Ticket

### L5: Spec
```python
def create_ticket_interactive(
    prompt_fn: Callable[[str], str],
    initial: Optional[InteractiveArgs] = None,
    store: TicketStore = None
) -> Ticket:
    """
    Input: prompt_fn returns "Bug in login", "ejacklab/open-dsearch", "medium", ...
           initial=InteractiveArgs(title="Initial Title")
    Prompts shown:
           "Title [Initial Title]: " → user presses enter (keeps initial)
           "Repo: " → "ejacklab/open-dsearch"
           "Description (empty line to end): "
           "Severity [medium]: " → "high"
           "Category [code]: " → enter (uses default)
           "Create ticket? [Y/n]: " → "y"
    Output: Ticket(id="C10", title="Initial Title", repo="ejacklab/open-dsearch",
                   severity="high", ...)
    
    Input: non-TTY terminal
    Error: InteractiveError("Interactive mode requires a TTY. Use --title and --repo flags.")
    
    Input: prompt_fn returns empty title repeatedly
    Error: ValidationError("Title is required")
    """
```

### L6: Test
```python
test_create_ticket_interactive_prompts_for_required()
test_create_ticket_interactive_uses_defaults()
test_create_ticket_interactive_accepts_initial_values()
test_create_ticket_interactive_multiline_description()
test_create_ticket_interactive_shows_preview()
test_create_ticket_interaptive_non_tty_raises()
test_create_ticket_interactive_cancel_aborts()
```

---

## Feature 3: Get by Slug

### L1: Ticket Lifecycle
### L2: Read
### L3: Get by slug
### L4: `get_ticket_by_slug(slug: str, store: TicketStore) -> Optional[Ticket]`
  - Extract slug from ticket filename (e.g., `cors-wildcard` from `C1-cors-wildcard.md`)
  - Build reverse slug-to-id mapping from all ticket files
  - Look up ticket by slug
  - Return Ticket if found, None if not found
  - Case-insensitive slug matching

### L5: Spec
```python
def get_ticket_by_slug(slug: str, store: TicketStore) -> Optional[Ticket]:
    """
    Input: slug="cors-wildcard", store with ticket file C1-cors-wildcard.md
    Output: Ticket(id="C1", title="CORS Wildcard Configuration", ...)
    
    Input: slug="CORS-WILDCARD", store with ticket file C1-cors-wildcard.md
    Output: Ticket(id="C1", ...)  # case-insensitive
    
    Input: slug="nonexistent-slug"
    Output: None
    
    Input: slug=""
    Output: None
    
    Note: Slug extracted from filename pattern: {ID}-{slug}.md
    """
```

### L6: Test
```python
test_get_ticket_by_slug_found()
test_get_ticket_by_slug_case_insensitive()
test_get_ticket_by_slug_not_found_returns_none()
test_get_ticket_by_slug_empty_returns_none()
test_get_ticket_by_slug_with_special_chars()
test_get_ticket_by_slug_normalizes_dashes()
```

---

## Feature 4: Related Tickets

### L1: Ticket Lifecycle
### L2: Read
### L3: Related tickets
### L4: `get_related_tickets(ticket_id: str, store: TicketStore) -> List[TicketSummary]`
  - Parse ticket's `relates_to` field for linked ticket IDs
  - Parse `parent` and `children` relationships
  - Parse `blocked_by` and `blocks` relationships
  - Fetch all referenced tickets
  - Return list of TicketSummary (id, title, status, relationship_type)
  - Handle missing references gracefully (include with status=not_found)

### L5: Spec
```python
@dataclass
class TicketSummary:
    id: str
    title: str
    status: str
    relationship: str  # "relates_to", "parent", "child", "blocked_by", "blocks"

def get_related_tickets(ticket_id: str, store: TicketStore) -> List[TicketSummary]:
    """
    Input: ticket_id="C1", C1 has relates_to=["C2", "C3"], parent="P1"
    Output: [
        TicketSummary(id="C2", title="Related bug", status="open", relationship="relates_to"),
        TicketSummary(id="C3", title="Another issue", status="fixed", relationship="relates_to"),
        TicketSummary(id="P1", title="Parent epic", status="in_progress", relationship="parent")
    ]
    
    Input: ticket_id="C1", C1 has relates_to=["MISSING"]
    Output: [TicketSummary(id="MISSING", title=None, status="not_found", relationship="relates_to")]
    
    Input: ticket_id="C1", C1 has no relationships
    Output: []
    """
```

### L6: Test
```python
test_get_related_tickets_relates_to()
test_get_related_tickets_parent_child()
test_get_related_tickets_blocked_by()
test_get_related_tickets_missing_reference()
test_get_related_tickets_empty_relationships()
test_get_related_tickets_multiple_types()
```

---

## Feature 5: Update History

### L1: Ticket Lifecycle
### L2: Update
### L3: Update history
### L4: `record_update_history(ticket: Ticket, changes: Dict[str, Tuple[Any, Any]], author: Optional[str]) -> Ticket`
  - Append change entry to ticket's internal history field
  - Each entry: timestamp, author, changed_fields with before/after values
  - Store in YAML frontmatter under `history:` key
  - Limit history to last N entries (configurable, default 100)
  - Return updated Ticket

### L5: Spec
```python
@dataclass
class HistoryEntry:
    timestamp: str  # ISO 8601
    author: Optional[str]
    changes: Dict[str, Tuple[Any, Any]]  # {"status": ("open", "fixed")}

def record_update_history(
    ticket: Ticket, 
    changes: Dict[str, Tuple[Any, Any]], 
    author: Optional[str] = None
) -> Ticket:
    """
    Input: ticket with existing history, 
           changes={"status": ("open", "fixed"), "severity": ("medium", "high")},
           author="alice"
    Output: Ticket with appended history entry:
           history:
             - timestamp: "2026-03-17T10:00:00Z"
               author: "alice"
               changes:
                 status: [open, fixed]
                 severity: [medium, high]
    
    Input: ticket with 100 history entries, new change
    Action: Remove oldest entry, append new (FIFO)
    Output: Ticket with exactly 100 entries
    
    Input: changes={} (no actual changes)
    Output: Ticket unchanged (no history entry added)
    """
```

### L6: Test
```python
test_record_update_history_single_field()
test_record_update_history_multiple_fields()
test_record_update_history_author_optional()
test_record_update_history_limits_entries()
test_record_update_history_no_changes_skips()
test_record_update_history_preserves_existing()
```

---

## Feature 6: Audit Log

### L1: Ticket Lifecycle
### L2: Update
### L3: Audit log
### L4: `write_audit_log(entry: AuditEntry, log_path: str) -> None`
  - Append audit entry to centralized `.vtic/audit.log` file
  - Format: JSON lines with timestamp, action, ticket_id, actor, changes, ip
  - Rotate log file when exceeds size limit (default 10MB)
  - Async write to avoid blocking operations
  - Include request_id if available for traceability

### L5: Spec
```python
@dataclass
class AuditEntry:
    timestamp: str
    action: str  # "create", "update", "delete", "restore"
    ticket_id: str
    actor: Optional[str]  # username, api_key_id, or "system"
    changes: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    request_id: Optional[str]

def write_audit_log(entry: AuditEntry, log_path: str = ".vtic/audit.log") -> None:
    """
    Input: AuditEntry(
             timestamp="2026-03-17T10:00:00Z",
             action="update",
             ticket_id="C1",
             actor="alice",
             changes={"status": {"from": "open", "to": "fixed"}},
             ip_address="192.168.1.100",
             request_id="req-123"
           )
    Appends to .vtic/audit.log:
           {"timestamp":"2026-03-17T10:00:00Z","action":"update","ticket_id":"C1",...}
    
    Input: log file at 10MB, new entry
    Action: Rotate to .vtic/audit.log.1, create new audit.log
    
    Note: Rotation keeps max 5 rotated files (.1 through .5)
    """
```

### L6: Test
```python
test_write_audit_log_create_action()
test_write_audit_log_update_action()
test_write_audit_log_delete_action()
test_write_audit_log_rotation()
test_write_audit_log_json_lines_format()
test_write_audit_log_includes_request_id()
```

---

## Feature 7: Vacuum Trash

### L1: Ticket Lifecycle
### L2: Delete
### L3: Vacuum trash
### L4: `vacuum_trash(older_than_days: int, store: TicketStore, dry_run: bool = False) -> VacuumResult`
  - Scan `.trash/` directory for soft-deleted ticket files
  - Filter files older than specified days (based on file mtime)
  - If dry_run=True, return count without deleting
  - If dry_run=False, permanently delete matching files
  - Return VacuumResult with deleted count and list of deleted IDs

### L5: Spec
```python
@dataclass
class VacuumResult:
    deleted_count: int
    deleted_ids: List[str]
    freed_bytes: int
    dry_run: bool

def vacuum_trash(older_than_days: int, store: TicketStore, dry_run: bool = False) -> VacuumResult:
    """
    Input: older_than_days=30, store with .trash/C1.md (45 days old), .trash/C2.md (10 days old)
    Output: VacuumResult(deleted_count=1, deleted_ids=["C1"], freed_bytes=2048, dry_run=False)
    Action: .trash/C1.md permanently deleted, .trash/C2.md kept
    
    Input: older_than_days=30, dry_run=True
    Output: VacuumResult(deleted_count=1, deleted_ids=["C1"], freed_bytes=2048, dry_run=True)
    Action: No files deleted
    
    Input: older_than_days=0
    Action: Delete all files in trash immediately
    
    Input: .trash/ directory empty
    Output: VacuumResult(deleted_count=0, deleted_ids=[], freed_bytes=0, dry_run=False)
    """
```

### L6: Test
```python
test_vacuum_trash_deletes_old_files()
test_vacuum_trash_keeps_recent_files()
test_vacuum_trash_dry_run_no_delete()
test_vacuum_trash_zero_days_deletes_all()
test_vacuum_trash_empty_trash()
test_vacuum_trash_returns_freed_bytes()
```

---

## Feature 8: Status Workflow

### L1: Workflow & Dependencies
### L2: Status
### L3: Status workflow
### L4: `load_workflow_config(config_path: str) -> WorkflowConfig`
  - Parse workflow definition from `vtic.toml` under `[workflow]` section
  - Define valid status transitions as directed graph
  - Define entry points (valid initial statuses)
  - Define terminal statuses (no outgoing transitions by default)
  - Support custom statuses beyond built-in
  - Return WorkflowConfig with transition matrix

### L5: Spec
```python
@dataclass
class WorkflowConfig:
    statuses: List[str]
    initial_statuses: List[str]
    terminal_statuses: List[str]
    transitions: Dict[str, List[str]]  # {"open": ["in_progress", "blocked", "fixed"]}

def load_workflow_config(config_path: str = "vtic.toml") -> WorkflowConfig:
    """
    Input: vtic.toml with:
           [workflow]
           statuses = ["open", "triaging", "in_progress", "blocked", "review", "fixed", "closed"]
           transitions = {open = ["triaging", "in_progress"], triaging = ["in_progress", "wont_fix"]}
    Output: WorkflowConfig(
              statuses=["open", "triaging", "in_progress", "blocked", "review", "fixed", "closed"],
              initial_statuses=["open"],
              terminal_statuses=["fixed", "closed"],
              transitions={"open": ["triaging", "in_progress"], ...}
            )
    
    Input: vtic.toml without [workflow] section
    Output: WorkflowConfig with default built-in workflow
    
    Input: invalid workflow (unreachable status)
    Warning: Log warning about unreachable status, continue with valid transitions
    """
```

### L6: Test
```python
test_load_workflow_config_custom_statuses()
test_load_workflow_config_defaults_when_missing()
test_load_workflow_config_validates_reachability()
test_load_workflow_config_detects_cycles()
test_load_workflow_config_entry_points()
test_load_workflow_config_terminal_statuses()
```

---

## Feature 9: Transition Validation

### L1: Workflow & Dependencies
### L2: Status
### L3: Transition validation
### L4: `validate_transition(current: str, target: str, workflow: WorkflowConfig) -> TransitionResult`
  - Check if target status exists in workflow
  - Check if transition from current to target is allowed
  - Return TransitionResult with is_valid, error_message, allowed_alternatives
  - Support bypass with force flag (for admins)
  - Log blocked transitions for audit

### L5: Spec
```python
@dataclass
class TransitionResult:
    is_valid: bool
    error_message: Optional[str]
    allowed_transitions: List[str]

def validate_transition(
    current: str, 
    target: str, 
    workflow: WorkflowConfig
) -> TransitionResult:
    """
    Input: current="open", target="in_progress", workflow with open→in_progress allowed
    Output: TransitionResult(is_valid=True, error_message=None, allowed_transitions=["in_progress", "blocked", "fixed"])
    
    Input: current="open", target="closed", workflow without open→closed transition
    Output: TransitionResult(
              is_valid=False,
              error_message="Cannot transition from 'open' to 'closed'. Must go through: in_progress, review",
              allowed_transitions=["in_progress", "blocked", "fixed", "wont_fix"]
            )
    
    Input: current="fixed", target="open", workflow terminal status
    Output: TransitionResult(
              is_valid=False,
              error_message="'fixed' is a terminal status. Use 'reopen' action if available.",
              allowed_transitions=[]
            )
    
    Input: current="open", target="invalid_status"
    Output: TransitionResult(is_valid=False, error_message="Unknown status: invalid_status", ...)
    """
```

### L6: Test
```python
test_validate_transition_allowed()
test_validate_transition_blocked()
test_validate_transition_unknown_status()
test_validate_transition_terminal_status()
test_validate_transition_suggests_alternatives()
test_validate_transition_force_bypass()
```

---

## Feature 10: Auto-Transitions

### L1: Workflow & Dependencies
### L2: Status
### L3: Auto-transitions
### L4: `trigger_auto_transition(event: WorkflowEvent, ticket: Ticket, store: TicketStore) -> Optional[Ticket]`
  - Listen for workflow events: pr_merged, commit_pushed, comment_added
  - Match event against configured auto-transition rules
  - Execute status change if rule matches
  - Log auto-transition with trigger reason
  - Return updated Ticket or None if no transition triggered

### L5: Spec
```python
@dataclass
class WorkflowEvent:
    type: str  # "pr_merged", "commit_pushed", "comment_added"
    ticket_id: str
    metadata: Dict[str, Any]  # {"pr_number": 123, "merged_by": "alice"}

# In vtic.toml:
# [workflow.auto_transitions]
# pr_merged = {from = "in_progress", to = "review"}
# comment_added_with_fix = {from = "*", to = "fixed", condition = "contains_fix_reference"}

def trigger_auto_transition(
    event: WorkflowEvent, 
    ticket: Ticket, 
    store: TicketStore
) -> Optional[Ticket]:
    """
    Input: event=WorkflowEvent(type="pr_merged", ticket_id="C1", metadata={"pr_number": 123}),
           ticket with status="in_progress"
    Config: pr_merged = {from = "in_progress", to = "review"}
    Action: Update C1 status to "review", add note "Auto-transitioned due to PR #123 merge"
    Output: Ticket(id="C1", status="review", ...)
    
    Input: event type="pr_merged", ticket status="open"
    Config: pr_merged only applies from "in_progress"
    Output: None  # no transition
    
    Input: event type="unknown"
    Output: None
    
    Note: "*" in from field matches any status
    """
```

### L6: Test
```python
test_trigger_auto_transition_pr_merged()
test_trigger_auto_transition_commit_pushed()
test_trigger_auto_transition_condition_match()
test_trigger_auto_transition_no_match()
test_trigger_auto_transition_wildcard_from()
test_trigger_auto_transition_logs_reason()
```

---

## Feature 11: Blocking Relationships

### L1: Workflow & Dependencies
### L2: Dependencies
### L3: Blocking relationships
### L4: `check_blocking_dependencies(ticket_id: str, store: TicketStore) -> BlockStatus`
  - Parse ticket's `blocked_by` field for blocking ticket IDs
  - Check if any blocking tickets are in non-terminal status
  - Return BlockStatus with is_blocked, blocking_tickets, resolution_hints
  - Support transitive blocking (A blocked by B blocked by C)

### L5: Spec
```python
@dataclass
class BlockingTicket:
    id: str
    title: str
    status: str

@dataclass
class BlockStatus:
    is_blocked: bool
    blocking_tickets: List[BlockingTicket]
    transitively_blocked: List[BlockingTicket]  # indirect blockers

def check_blocking_dependencies(ticket_id: str, store: TicketStore) -> BlockStatus:
    """
    Input: ticket_id="C1", C1 has blocked_by=["C2"], C2 status="open"
    Output: BlockStatus(
              is_blocked=True,
              blocking_tickets=[BlockingTicket(id="C2", title="API bug", status="open")],
              transitively_blocked=[]
            )
    
    Input: ticket_id="C1", C1 has blocked_by=["C2"], C2 status="fixed"
    Output: BlockStatus(is_blocked=False, blocking_tickets=[], transitively_blocked=[])
    
    Input: ticket_id="C1", C1 blocked by C2, C2 blocked by C3 (transitive)
    Output: BlockStatus(
              is_blocked=True,
              blocking_tickets=[BlockingTicket(id="C2", ...)],
              transitively_blocked=[BlockingTicket(id="C3", ...)]
            )
    
    Input: ticket_id="C1", no blocked_by field
    Output: BlockStatus(is_blocked=False, blocking_tickets=[], transitively_blocked=[])
    """
```

### L6: Test
```python
test_check_blocking_dependencies_blocked()
test_check_blocking_dependencies_not_blocked()
test_check_blocking_dependencies_transitive()
test_check_blocking_dependencies_no_blockers()
test_check_blocking_dependencies_missing_ticket()
test_check_blocking_dependencies_circular_detection()
```

---

## Feature 12: Cross-Repo References

### L1: Workflow & Dependencies
### L2: References
### L3: Cross-repo references
### L4: `parse_cross_repo_reference(ref: str) -> CrossRepoRef`
  - Parse reference syntax: `owner/repo#ID` or `repo#ID` (default owner)
  - Support shorthand: `#ID` (same repo as current ticket)
  - Validate repo format and ID format
  - Return CrossRepoRef with owner, repo, ticket_id fields
  - Handle invalid formats gracefully

### L5: Spec
```python
@dataclass
class CrossRepoRef:
    owner: str
    repo: str
    ticket_id: str
    raw: str

def parse_cross_repo_reference(ref: str, default_owner: Optional[str] = None) -> CrossRepoRef:
    """
    Input: ref="ejacklab/infra#C1"
    Output: CrossRepoRef(owner="ejacklab", repo="infra", ticket_id="C1", raw="ejacklab/infra#C1")
    
    Input: ref="open-dsearch#S2", default_owner="ejacklab"
    Output: CrossRepoRef(owner="ejacklab", repo="open-dsearch", ticket_id="S2", raw="open-dsearch#S2")
    
    Input: ref="#C3", current context owner="ejacklab", repo="api"
    Output: CrossRepoRef(owner="ejacklab", repo="api", ticket_id="C3", raw="#C3")
    
    Input: ref="invalid-format"
    Error: ValueError("Invalid cross-repo reference: invalid-format. Expected: owner/repo#ID or repo#ID")
    """
```

### L6: Test
```python
test_parse_cross_repo_reference_full()
test_parse_cross_repo_reference_repo_only()
test_parse_cross_repo_reference_shorthand()
test_parse_cross_repo_reference_invalid_format()
test_parse_cross_repo_reference_with_default_owner()
test_parse_cross_repo_reference_special_chars_in_id()
```

---

## Feature 13: Reference Resolution

### L1: Workflow & Dependencies
### L2: References
### L3: Reference resolution
### L4: `resolve_ticket_references(refs: List[str], store: TicketStore) -> List[ResolvedRef]`
  - Parse each reference (local ID, cross-repo, URL)
  - Fetch referenced ticket data
  - Return ResolvedRef with original ref and ticket data
  - Handle missing references with status indicator
  - Support batch resolution for efficiency

### L5: Spec
```python
@dataclass
class ResolvedRef:
    raw_ref: str
    ticket: Optional[Ticket]
    status: str  # "found", "not_found", "invalid_format"

def resolve_ticket_references(refs: List[str], store: TicketStore) -> List[ResolvedRef]:
    """
    Input: refs=["C1", "ejacklab/infra#C2", "invalid"]
    Output: [
        ResolvedRef(raw_ref="C1", ticket=Ticket(id="C1", title="Local bug"), status="found"),
        ResolvedRef(raw_ref="ejacklab/infra#C2", ticket=Ticket(id="C2", ...), status="found"),
        ResolvedRef(raw_ref="invalid", ticket=None, status="invalid_format")
    ]
    
    Input: refs=["MISSING_ID"]
    Output: [ResolvedRef(raw_ref="MISSING_ID", ticket=None, status="not_found")]
    
    Input: refs=[]
    Output: []
    
    Note: Cross-repo resolution requires multi-repo store access
    """
```

### L6: Test
```python
test_resolve_ticket_references_local()
test_resolve_ticket_references_cross_repo()
test_resolve_ticket_references_not_found()
test_resolve_ticket_references_invalid()
test_resolve_ticket_references_batch()
test_resolve_ticket_references_empty_list()
```

---

## Feature 14: Boolean Operators (Search)

### L1: Search & Query
### L2: BM25 Search
### L3: Boolean operators
### L4: `parse_boolean_query(query: str) -> BooleanQuery`
  - Parse AND, OR, NOT operators (case-insensitive)
  - Support parentheses for grouping: `(auth OR login) AND security`
  - Support shorthand: `-term` for NOT
  - Build AST representation of query
  - Return BooleanQuery tree for search execution

### L5: Spec
```python
@dataclass
class BooleanQuery:
    type: str  # "and", "or", "not", "term"
    children: Optional[List['BooleanQuery']]
    term: Optional[str]

def parse_boolean_query(query: str) -> BooleanQuery:
    """
    Input: "CORS AND security"
    Output: BooleanQuery(type="and", children=[
               BooleanQuery(type="term", term="CORS"),
               BooleanQuery(type="term", term="security")
             ])
    
    Input: "(auth OR login) AND security"
    Output: BooleanQuery(type="and", children=[
               BooleanQuery(type="or", children=[
                 BooleanQuery(type="term", term="auth"),
                 BooleanQuery(type="term", term="login")
               ]),
               BooleanQuery(type="term", term="security")
             ])
    
    Input: "CORS -production"
    Output: BooleanQuery(type="and", children=[
               BooleanQuery(type="term", term="CORS"),
               BooleanQuery(type="not", children=[BooleanQuery(type="term", term="production")])
             ])
    
    Input: "simple term"
    Output: BooleanQuery(type="term", term="simple term")
    """
```

### L6: Test
```python
test_parse_boolean_query_and()
test_parse_boolean_query_or()
test_parse_boolean_query_not()
test_parse_boolean_query_parentheses()
test_parse_boolean_query_shorthand_not()
test_parse_boolean_query_nested()
test_parse_boolean_query_simple_term()
```

---

## Feature 15: Field-Specific Search

### L1: Search & Query
### L2: BM25 Search
### L3: Field-specific search
### L4: `parse_field_query(query: str) -> FieldQuery`
  - Parse field:value syntax: `title:auth description:security`
  - Support quoted values: `title:"exact phrase"`
  - Support wildcard in field names: `*:security` (all fields)
  - Validate field names against ticket schema
  - Return FieldQuery with field-specific terms

### L5: Spec
```python
@dataclass
class FieldTerm:
    field: str
    value: str
    exact: bool  # true if quoted

@dataclass
class FieldQuery:
    terms: List[FieldTerm]
    default_terms: List[str]  # terms without field prefix

def parse_field_query(query: str, valid_fields: List[str]) -> FieldQuery:
    """
    Input: "title:auth severity:critical"
    Output: FieldQuery(
              terms=[
                FieldTerm(field="title", value="auth", exact=False),
                FieldTerm(field="severity", value="critical", exact=False)
              ],
              default_terms=[]
            )
    
    Input: 'title:"CORS wildcard" security'
    Output: FieldQuery(
              terms=[FieldTerm(field="title", value="CORS wildcard", exact=True)],
              default_terms=["security"]
            )
    
    Input: "unknown_field:value"
    Error: ValueError("Unknown field: unknown_field. Valid fields: title, description, severity, ...")
    
    Input: "*:urgent"
    Output: FieldQuery(terms=[FieldTerm(field="*", value="urgent", exact=False)], ...)
    """
```

### L6: Test
```python
test_parse_field_query_single_field()
test_parse_field_query_multiple_fields()
test_parse_field_query_quoted_value()
test_parse_field_query_mixed()
test_parse_field_query_invalid_field()
test_parse_field_query_wildcard_field()
```

---

## Feature 16: Chunked Embedding

### L1: Search & Query
### L2: Semantic Search
### L3: Chunked embedding
### L4: `chunk_ticket_content(ticket: Ticket, max_chunk_tokens: int = 500) -> List[Chunk]`
  - Split long descriptions into semantic chunks
  - Respect sentence/paragraph boundaries
  - Include overlapping context between chunks (sliding window)
  - Tag each chunk with type: title, description, code_block
  - Return list of Chunk objects with content and metadata

### L5: Spec
```python
@dataclass
class Chunk:
    ticket_id: str
    chunk_index: int
    content: str
    chunk_type: str  # "title", "description", "code_block"
    token_count: int
    overlap_with_previous: int  # tokens

def chunk_ticket_content(ticket: Ticket, max_chunk_tokens: int = 500) -> List[Chunk]:
    """
    Input: ticket with description of 1200 tokens
    Output: [
        Chunk(ticket_id="C1", chunk_index=0, content="...", token_count=450, overlap=0),
        Chunk(ticket_id="C1", chunk_index=1, content="...", token_count=450, overlap=50),
        Chunk(ticket_id="C1", chunk_index=2, content="...", token_count=350, overlap=50)
    ]
    
    Input: ticket with short description (< 500 tokens)
    Output: [Chunk(ticket_id="C1", chunk_index=0, content="...", token_count=200, overlap=0)]
    
    Input: ticket with code blocks
    Output: Chunks with chunk_type="code_block" for fenced code sections
    
    Note: Title always gets its own chunk with type="title"
    """
```

### L6: Test
```python
test_chunk_ticket_content_short()
test_chunk_ticket_content_long()
test_chunk_ticket_content_respects_boundaries()
test_chunk_ticket_content_overlap()
test_chunk_ticket_content_code_blocks()
test_chunk_ticket_content_title_separate()
```

---

## Feature 17: Multi-Vector Tickets

### L1: Search & Query
### L2: Semantic Search
### L3: Multi-vector tickets
### L4: `store_multi_vector_embeddings(ticket_id: str, chunks: List[Chunk], embedder: Embedder) -> MultiVectorResult`
  - Generate embedding for each chunk
  - Store multiple vectors per ticket in Zvec index
  - Tag vectors with chunk_type for filtered search
  - Support vector aggregation for ticket-level similarity
  - Return mapping of chunk_index to vector_id

### L5: Spec
```python
@dataclass
class MultiVectorResult:
    ticket_id: str
    vector_ids: List[str]  # one per chunk
    chunk_types: List[str]

def store_multi_vector_embeddings(
    ticket_id: str, 
    chunks: List[Chunk], 
    embedder: Embedder
) -> MultiVectorResult:
    """
    Input: ticket_id="C1", chunks=[Chunk(content="title..."), Chunk(content="desc...")]
    Action: Generate embedding for each chunk, store in Zvec with metadata
    Output: MultiVectorResult(
              ticket_id="C1",
              vector_ids=["vec-C1-0", "vec-C1-1"],
              chunk_types=["title", "description"]
            )
    
    Input: chunks=[]
    Output: MultiVectorResult(ticket_id="C1", vector_ids=[], chunk_types=[])
    
    Note: Search returns best-matching chunk, not just ticket
    """
```

### L6: Test
```python
test_store_multi_vector_embeddings_single()
test_store_multi_vector_embeddings_multiple()
test_store_multi_vector_embeddings_empty()
test_store_multi_vector_embeddings_metadata()
test_retrieve_by_chunk_type()
```

---

## Feature 18: Explain Mode (Search)

### L1: Search & Query
### L2: Hybrid Search
### L3: Explain mode
### L4: `explain_search_result(query: str, ticket: Ticket, index: ZvecIndex) -> Explanation`
  - Show BM25 score breakdown (term frequency, document frequency, field weights)
  - Show semantic similarity score
  - Show hybrid fusion method (RRF weights)
  - Show final score calculation
  - Highlight matched terms in content
  - Return Explanation with score components

### L5: Spec
```python
@dataclass
class ScoreComponent:
    name: str  # "bm25_title", "bm25_description", "semantic_similarity"
    raw_score: float
    weight: float
    weighted_score: float

@dataclass
class Explanation:
    ticket_id: str
    final_score: float
    components: List[ScoreComponent]
    matched_terms: List[str]
    fusion_method: str  # "rrf", "weighted_sum"

def explain_search_result(
    query: str, 
    ticket: Ticket, 
    index: ZvecIndex,
    config: SearchConfig
) -> Explanation:
    """
    Input: query="CORS security", ticket=C1
    Output: Explanation(
              ticket_id="C1",
              final_score=0.85,
              components=[
                ScoreComponent(name="bm25_title", raw_score=3.2, weight=0.4, weighted_score=1.28),
                ScoreComponent(name="bm25_description", raw_score=1.5, weight=0.2, weighted_score=0.3),
                ScoreComponent(name="semantic_similarity", raw_score=0.92, weight=0.4, weighted_score=0.37)
              ],
              matched_terms=["CORS", "security"],
              fusion_method="weighted_sum"
            )
    
    Input: query with no matches in ticket
    Output: Explanation with final_score=0.0, matched_terms=[]
    """
```

### L6: Test
```python
test_explain_search_result_shows_bm25()
test_explain_search_result_shows_semantic()
test_explain_search_result_shows_fusion()
test_explain_search_result_highlights_terms()
test_explain_search_result_no_match()
```

---

## Feature 19: Numeric Comparison Filters

### L1: Search & Query
### L2: Filters
### L3: Numeric comparison
### L4: `parse_numeric_filter(filter_str: str) -> NumericFilter`
  - Parse comparison operators: `>`, `<`, `>=`, `<=`, `=`, `!=`
  - Support field:value format: `priority:>=5`, `age:<30`
  - Handle numeric fields: priority, age (days since created), custom numeric fields
  - Return NumericFilter with field, operator, value

### L5: Spec
```python
@dataclass
class NumericFilter:
    field: str
    operator: str  # "gt", "lt", "gte", "lte", "eq", "neq"
    value: float

def parse_numeric_filter(filter_str: str) -> NumericFilter:
    """
    Input: "priority:>=5"
    Output: NumericFilter(field="priority", operator="gte", value=5.0)
    
    Input: "age:<30"
    Output: NumericFilter(field="age", operator="lt", value=30.0)
    
    Input: "count:=100"
    Output: NumericFilter(field="count", operator="eq", value=100.0)
    
    Input: "priority:invalid"
    Error: ValueError("Invalid numeric filter: priority:invalid")
    
    Note: "age" is computed field (days since created timestamp)
    """
```

### L6: Test
```python
test_parse_numeric_filter_gte()
test_parse_numeric_filter_lt()
test_parse_numeric_filter_eq()
test_parse_numeric_filter_invalid()
test_apply_numeric_filter_priority()
test_apply_numeric_filter_age()
```

---

## Feature 20: OR Filters

### L1: Search & Query
### L2: Filters
### L3: OR filters
### L4: `parse_or_filter(filter_str: str) -> OrFilter`
  - Parse `field:value1 OR value2` syntax
  - Support multiple values: `severity:high OR critical OR blocker`
  - Combine with AND across different fields
  - Return OrFilter with field and allowed values

### L5: Spec
```python
@dataclass
class OrFilter:
    field: str
    values: List[str]

def parse_or_filter(filter_str: str) -> OrFilter:
    """
    Input: "severity:high OR critical"
    Output: OrFilter(field="severity", values=["high", "critical"])
    
    Input: "status:open OR in_progress OR blocked"
    Output: OrFilter(field="status", values=["open", "in_progress", "blocked"])
    
    Input: "severity:critical"  # single value, no OR
    Output: OrFilter(field="severity", values=["critical"])
    
    Note: OR only works within same field. Different fields use AND.
    """
```

### L6: Test
```python
test_parse_or_filter_two_values()
test_parse_or_filter_multiple_values()
test_parse_or_filter_single_value()
test_apply_or_filter_match()
test_apply_or_filter_no_match()
```

---

## Feature 21: NOT Filters

### L1: Search & Query
### L2: Filters
### L3: NOT filters
### L4: `parse_not_filter(filter_str: str) -> NotFilter`
  - Parse `--not-field value` or `field:-value` syntax
  - Exclude tickets matching negated condition
  - Support NOT with OR: `--not-status closed OR wont_fix`
  - Return NotFilter with field and excluded values

### L5: Spec
```python
@dataclass
class NotFilter:
    field: str
    excluded_values: List[str]

def parse_not_filter(filter_str: str) -> NotFilter:
    """
    Input: "--not-status closed"
    Output: NotFilter(field="status", excluded_values=["closed"])
    
    Input: "--not-severity low OR medium"
    Output: NotFilter(field="severity", excluded_values=["low", "medium"])
    
    Input: "status:-wont_fix"
    Output: NotFilter(field="status", excluded_values=["wont_fix"])
    
    Note: NOT filters combine with AND to other filters
    """
```

### L6: Test
```python
test_parse_not_filter_single()
test_parse_not_filter_multiple()
test_parse_not_filter_shorthand()
test_apply_not_filter_exclude()
test_apply_not_filter_include()
```

---

## Feature 22: Faceted Search

### L1: Search & Query
### L2: Filters
### L3: Faceted search
### L4: `compute_facets(tickets: List[Ticket], facet_fields: List[str]) -> Dict[str, FacetCounts]`
  - Count occurrences of each value in specified fields
  - Support multi-value fields (tags)
  - Return FacetCounts with value:count mapping per field
  - Support facet filtering (only compute facets for filtered results)
  - Include "missing" count for null values

### L5: Spec
```python
@dataclass
class FacetCounts:
    field: str
    counts: Dict[str, int]  # {"high": 5, "medium": 10, "low": 3}
    missing_count: int

def compute_facets(
    tickets: List[Ticket], 
    facet_fields: List[str]
) -> Dict[str, FacetCounts]:
    """
    Input: 18 tickets with severities: 5 critical, 8 high, 3 medium, 2 low
           facet_fields=["severity", "status"]
    Output: {
        "severity": FacetCounts(field="severity", counts={"critical": 5, "high": 8, "medium": 3, "low": 2}, missing_count=0),
        "status": FacetCounts(field="status", counts={"open": 10, "fixed": 5, "closed": 3}, missing_count=0)
    }
    
    Input: tickets with tags=["security", "api"], ["security"], ["api", "performance"]
    Output: FacetCounts for tags: {"security": 2, "api": 2, "performance": 1}
    
    Input: empty tickets list
    Output: {}  # empty facets
    """
```

### L6: Test
```python
test_compute_facets_severity()
test_compute_facets_status()
test_compute_facets_tags_multi_value()
test_compute_facets_missing_count()
test_compute_facets_empty_list()
test_compute_facets_filtered_results()
```

---

## Feature 23: Random Sampling

### L1: Search & Query
### L2: Pagination
### L3: Random sampling
### L4: `sample_tickets(tickets: List[Ticket], sample_size: int, seed: Optional[int] = None) -> List[Ticket]`
  - Return random sample of specified size
  - Support reproducible sampling with seed parameter
  - Use reservoir sampling for memory efficiency on large lists
  - Return all tickets if sample_size >= total count
  - Preserve original order option (shuffle vs maintain)

### L5: Spec
```python
def sample_tickets(
    tickets: List[Ticket], 
    sample_size: int, 
    seed: Optional[int] = None,
    shuffle: bool = True
) -> List[Ticket]:
    """
    Input: 100 tickets, sample_size=10, seed=42
    Output: 10 randomly selected tickets (reproducible with same seed)
    
    Input: 5 tickets, sample_size=10
    Output: All 5 tickets (sample_size > available)
    
    Input: 1000 tickets, sample_size=50, seed=None
    Output: 50 random tickets (different each call)
    
    Input: tickets=[], sample_size=10
    Output: []
    
    Note: Reservoir sampling used for O(n) time, O(k) space efficiency
    """
```

### L6: Test
```python
test_sample_tickets_returns_correct_size()
test_sample_tickets_seed_reproducible()
test_sample_tickets_no_seed_varies()
test_sample_tickets_larger_than_available()
test_sample_tickets_empty_list()
test_sample_tickets_reservoir_algorithm()
```

---

## Feature 24: Custom Directory Layout

### L1: Storage & Indexing
### L2: File Storage
### L3: Custom directory layout
### L4: `resolve_ticket_path(ticket: Ticket, layout_config: LayoutConfig) -> str`
  - Parse custom path template from config
  - Support variables: {owner}, {repo}, {category}, {id}, {slug}, {year}, {month}
  - Support conditional segments: `{category?/}` (omit if empty)
  - Validate path doesn't escape tickets root
  - Return resolved absolute path

### L5: Spec
```python
@dataclass
class LayoutConfig:
    path_template: str  # "{owner}/{repo}/{category}/{id}-{slug}.md"
    flatten_limit: Optional[int] = None  # flatten if dirs exceed

def resolve_ticket_path(ticket: Ticket, layout_config: LayoutConfig) -> str:
    """
    Input: ticket with owner="ejacklab", repo="api", category="security", id="S1", slug="xss-bug"
           layout_config.path_template = "{owner}/{repo}/{category}/{id}-{slug}.md"
    Output: "tickets/ejacklab/api/security/S1-xss-bug.md"
    
    Input: layout_config.path_template = "by-date/{year}/{month}/{id}.md"
           ticket created on 2026-03-17
    Output: "tickets/by-date/2026/03/C1.md"
    
    Input: layout_config.path_template = "flat/{id}.md"
    Output: "tickets/flat/C1.md"
    
    Input: layout_config with path_template="../../../etc/passwd"
    Error: SecurityError("Path template escapes tickets root")
    """
```

### L6: Test
```python
test_resolve_ticket_path_standard()
test_resolve_ticket_path_custom()
test_resolve_ticket_path_date_based()
test_resolve_ticket_path_flat()
test_resolve_ticket_path_security_check()
test_resolve_ticket_path_conditional_segments()
```

---

## Feature 25: Multiple Indexes

### L1: Storage & Indexing
### L2: Zvec Index
### L3: Multiple indexes
### L4: `get_index_for_tenant(tenant_id: str, config: MultiIndexConfig) -> ZvecIndex`
  - Maintain separate Zvec index per tenant/project
  - Index stored at `.vtic/{tenant_id}/index/`
  - Route queries to correct index based on tenant context
  - Support cross-tenant search with explicit scope
  - Lazy-load indexes on first access

### L5: Spec
```python
@dataclass
class MultiIndexConfig:
    base_path: str  # ".vtic/"
    tenants: List[str]
    default_tenant: str

def get_index_for_tenant(tenant_id: str, config: MultiIndexConfig) -> ZvecIndex:
    """
    Input: tenant_id="project-alpha", config with base_path=".vtic/"
    Action: Load or create index at .vtic/project-alpha/index/
    Output: ZvecIndex instance for project-alpha
    
    Input: tenant_id="new-project" (not in config.tenants)
    Action: Create new index directory
    Output: ZvecIndex instance for new-project
    
    Input: tenant_id=None
    Output: ZvecIndex for config.default_tenant
    
    Note: Indexes are cached after first load
    """
```

### L6: Test
```python
test_get_index_for_tenant_existing()
test_get_index_for_tenant_new()
test_get_index_for_tenant_default()
test_get_index_for_tenant_isolation()
test_get_index_for_tenant_caching()
test_cross_tenant_search()
```

---

## Feature 26: Index Snapshot

### L1: Storage & Indexing
### L2: Backup
### L3: Index snapshot
### L4: `create_index_snapshot(index: ZvecIndex, snapshot_path: str) -> SnapshotResult`
  - Create point-in-time copy of index files
  - Use hard links for instant snapshots (same filesystem)
  - Fall back to copy for cross-filesystem
  - Include metadata: timestamp, ticket_count, index_version
  - Support incremental snapshots (delta from previous)

### L5: Spec
```python
@dataclass
class SnapshotResult:
    snapshot_id: str
    path: str
    timestamp: str
    ticket_count: int
    size_bytes: int

def create_index_snapshot(
    index: ZvecIndex, 
    snapshot_path: str = ".vtic/snapshots/"
) -> SnapshotResult:
    """
    Input: index with 500 tickets
    Action: Create hard-link snapshot at .vtic/snapshots/snap-20260317-100000/
    Output: SnapshotResult(
              snapshot_id="snap-20260317-100000",
              path=".vtic/snapshots/snap-20260317-100000/",
              timestamp="2026-03-17T10:00:00Z",
              ticket_count=500,
              size_bytes=10240000
            )
    
    Input: snapshot on different filesystem (hard link fails)
    Action: Fall back to file copy
    
    Note: Snapshot is instant with hard links, space-efficient
    """
```

### L6: Test
```python
test_create_index_snapshot_creates_directory()
test_create_index_snapshot_hard_links()
test_create_index_snapshot_fallback_copy()
test_create_index_snapshot_metadata()
test_restore_from_snapshot()
test_list_snapshots()
```

---

## Feature 27: Cloud Backup Sync

### L1: Storage & Indexing
### L2: Backup
### L3: Cloud backup sync
### L4: `sync_to_cloud(config: CloudBackupConfig, local_path: str) -> SyncResult`
  - Sync tickets and index to S3/GCS cloud storage
  - Use incremental sync (only changed files)
  - Support multiple cloud providers (S3, GCS, Azure Blob)
  - Encrypt sensitive data before upload
  - Resume interrupted syncs
  - Return SyncResult with uploaded files and errors

### L5: Spec
```python
@dataclass
class CloudBackupConfig:
    provider: str  # "s3", "gcs", "azure"
    bucket: str
    prefix: str  # "vtic-backups/"
    credentials: Dict[str, str]  # provider-specific

@dataclass
class SyncResult:
    uploaded_count: int
    uploaded_bytes: int
    skipped_count: int
    errors: List[str]
    duration_seconds: float

def sync_to_cloud(config: CloudBackupConfig, local_path: str) -> SyncResult:
    """
    Input: config with provider="s3", bucket="my-backups", prefix="vtic/"
           local_path="tickets/"
    Action: 
      1. List local files
      2. Compare with S3 (by ETag/size)
      3. Upload changed/new files
      4. Delete removed files (if sync_mode="mirror")
    Output: SyncResult(uploaded_count=15, uploaded_bytes=50000, skipped_count=100, errors=[])
    
    Input: interrupted sync (network failure)
    Action: Resume from last checkpoint
    
    Input: invalid credentials
    Error: CloudAuthError("Failed to authenticate with S3: ...")
    
    Note: Uses multipart upload for large files (>5MB)
    """
```

### L6: Test
```python
test_sync_to_cloud_s3_upload()
test_sync_to_cloud_incremental()
test_sync_to_cloud_resume_interrupted()
test_sync_to_cloud_encrypt_sensitive()
test_sync_to_cloud_auth_error()
test_sync_to_cloud_mirror_mode()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | Ticket Lifecycle | Create | Template-based creation | `create_ticket_from_template()` |
| 2 | Ticket Lifecycle | Create | Interactive creation | `create_ticket_interactive()` |
| 3 | Ticket Lifecycle | Read | Get by slug | `get_ticket_by_slug()` |
| 4 | Ticket Lifecycle | Read | Related tickets | `get_related_tickets()` |
| 5 | Ticket Lifecycle | Update | Update history | `record_update_history()` |
| 6 | Ticket Lifecycle | Update | Audit log | `write_audit_log()` |
| 7 | Ticket Lifecycle | Delete | Vacuum trash | `vacuum_trash()` |
| 8 | Workflow & Dependencies | Status | Status workflow | `load_workflow_config()` |
| 9 | Workflow & Dependencies | Status | Transition validation | `validate_transition()` |
| 10 | Workflow & Dependencies | Status | Auto-transitions | `trigger_auto_transition()` |
| 11 | Workflow & Dependencies | Dependencies | Blocking relationships | `check_blocking_dependencies()` |
| 12 | Workflow & Dependencies | References | Cross-repo references | `parse_cross_repo_reference()` |
| 13 | Workflow & Dependencies | References | Reference resolution | `resolve_ticket_references()` |
| 14 | Search & Query | BM25 Search | Boolean operators | `parse_boolean_query()` |
| 15 | Search & Query | BM25 Search | Field-specific search | `parse_field_query()` |
| 16 | Search & Query | Semantic Search | Chunked embedding | `chunk_ticket_content()` |
| 17 | Search & Query | Semantic Search | Multi-vector tickets | `store_multi_vector_embeddings()` |
| 18 | Search & Query | Hybrid Search | Explain mode | `explain_search_result()` |
| 19 | Search & Query | Filters | Numeric comparison | `parse_numeric_filter()` |
| 20 | Search & Query | Filters | OR filters | `parse_or_filter()` |
| 21 | Search & Query | Filters | NOT filters | `parse_not_filter()` |
| 22 | Search & Query | Filters | Faceted search | `compute_facets()` |
| 23 | Search & Query | Pagination | Random sampling | `sample_tickets()` |
| 24 | Storage & Indexing | File Storage | Custom directory layout | `resolve_ticket_path()` |
| 25 | Storage & Indexing | Zvec Index | Multiple indexes | `get_index_for_tenant()` |
| 26 | Storage & Indexing | Backup | Index snapshot | `create_index_snapshot()` |
| 27 | Storage & Indexing | Backup | Cloud backup sync | `sync_to_cloud()` |

---

## Category Distribution

| Category | Count |
|----------|-------|
| Ticket Lifecycle | 7 |
| Workflow & Dependencies | 6 |
| Search & Query | 10 |
| Storage & Indexing | 4 |
| **Total** | **27** |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Callable, Protocol
from datetime import datetime

# Existing structures (from core breakdown)
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
    created: Optional[str] = None
    updated: Optional[str] = None
    # P2 additions
    relates_to: List[str] = field(default_factory=list)
    parent: Optional[str] = None
    blocked_by: List[str] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)

# P2-specific structures
@dataclass
class TemplateConfig:
    name: str
    defaults: Dict[str, Any]
    required: List[str]
    prompts: Dict[str, str]

@dataclass
class WorkflowConfig:
    statuses: List[str]
    initial_statuses: List[str]
    terminal_statuses: List[str]
    transitions: Dict[str, List[str]]

@dataclass
class BooleanQuery:
    type: str
    children: Optional[List['BooleanQuery']]
    term: Optional[str]

@dataclass
class Chunk:
    ticket_id: str
    chunk_index: int
    content: str
    chunk_type: str
    token_count: int
    overlap_with_previous: int

@dataclass
class FacetCounts:
    field: str
    counts: Dict[str, int]
    missing_count: int

@dataclass
class CloudBackupConfig:
    provider: str
    bucket: str
    prefix: str
    credentials: Dict[str, str]
```
