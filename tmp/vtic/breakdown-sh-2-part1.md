# Utility & Bulk Operations - 6-Level Breakdown

12 "Should Have" features broken down to implementation-ready specifications.

---

## Feature 1: Config Command

### L1: CLI
### L2: Management Commands
### L3: config command
### L4: `cli_config(args: ConfigArgs, config_manager: ConfigManager) -> int`
  - Parse CLI arguments for config subcommand (show, set, init, get)
  - `show`: Display current merged configuration (global + project + env)
  - `set`: Update a configuration value in appropriate config file
  - `init`: Create new vtic.toml with sensible defaults in current directory
  - `get`: Retrieve single config value by key path
  - Handle global vs project config scope (--global flag)
  - Output in specified format (table, json, toml)
  - Return exit code: 0 success, 1 key not found (for get), 2 validation error

### L5: Spec
```python
@dataclass
class ConfigArgs:
    subcommand: str  # "show", "set", "init", "get"
    key: Optional[str] = None  # e.g., "search.embedding_provider"
    value: Optional[str] = None  # for set
    global_scope: bool = False  # --global flag
    format: str = "table"  # table, json, toml

def cli_config(args: ConfigArgs, config_manager: ConfigManager) -> int:
    """
    # show subcommand
    Input: ConfigArgs(subcommand="show", format="json")
    Output (stdout): {"tickets_dir": "./tickets", "search": {"provider": "openai", ...}, ...}
    Return: 0
    
    # set subcommand
    Input: ConfigArgs(subcommand="set", key="search.embedding_model", value="text-embedding-3-large")
    Action: Update ./vtic.toml with embedding_model = "text-embedding-3-large"
    Output (stdout): "Updated search.embedding_model = text-embedding-3-large"
    Return: 0
    
    # set with --global
    Input: ConfigArgs(subcommand="set", key="defaults.category", value="security", global_scope=True)
    Action: Update ~/.config/vtic/config.toml
    Output (stdout): "Updated defaults.category = security (global)"
    Return: 0
    
    # init subcommand
    Input: ConfigArgs(subcommand="init")
    Action: Create ./vtic.toml with default configuration
    Output (stdout): "Created vtic.toml in /path/to/project"
    Return: 0
    
    # init when file exists
    Input: ConfigArgs(subcommand="init"), vtic.toml already exists
    Output (stderr): "vtic.toml already exists. Use --force to overwrite."
    Return: 1
    
    # get subcommand
    Input: ConfigArgs(subcommand="get", key="search.provider")
    Output (stdout): "openai"
    Return: 0
    
    # get non-existent key
    Input: ConfigArgs(subcommand="get", key="nonexistent.key")
    Output (stderr): "Configuration key not found: nonexistent.key"
    Return: 1
    
    # invalid key format
    Input: ConfigArgs(subcommand="set", key="invalid", value="test")
    Error: ValueError("Invalid configuration key format. Use dot notation: section.key")
    """
```

### L6: Test
```python
test_cli_config_show_outputs_merged_config()
test_cli_config_show_json_format()
test_cli_config_show_toml_format()
test_cli_config_set_updates_project_config()
test_cli_config_set_global_updates_global_config()
test_cli_config_set_creates_missing_sections()
test_cli_config_init_creates_vtic_toml()
test_cli_config_init_fails_if_file_exists()
test_cli_config_init_force_overwrites_existing()
test_cli_config_get_returns_single_value()
test_cli_config_get_nonexistent_key_returns_1()
test_cli_config_set_validates_value_type()
test_cli_config_invalid_key_format_raises()
```

---

## Feature 2: Stats Command

### L1: CLI
### L2: Management Commands
### L3: stats command
### L4: `cli_stats(args: StatsArgs, store: TicketStore) -> int`
  - Aggregate ticket statistics from store
  - Count tickets by status, severity, category, repo
  - Calculate percentages and totals
  - Support --by-repo, --by-category, --by-severity, --by-status flags
  - Support --json, --table output formats
  - Include counts for: total, open, in_progress, blocked, fixed, wont_fix, closed
  - Return exit code: 0 success, 1 no tickets found, 2 error

### L5: Spec
```python
@dataclass
class StatsArgs:
    by_repo: bool = False
    by_category: bool = False
    by_severity: bool = False
    by_status: bool = False
    repo: Optional[str] = None  # filter to specific repo
    format: str = "table"

@dataclass
class TicketStats:
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    by_repo: Dict[str, int]

def cli_stats(args: StatsArgs, store: TicketStore) -> int:
    """
    # default stats (all breakdowns)
    Input: StatsArgs()
    Output (stdout):
    ┌─────────────┬───────┬─────────┐
    │ Status      │ Count │ Percent │
    ├─────────────┼───────┼─────────┤
    │ open        │    45 │   45.0% │
    │ in_progress │    20 │   20.0% │
    │ blocked     │     5 │    5.0% │
    │ fixed       │    25 │   25.0% │
    │ wont_fix    │     3 │    3.0% │
    │ closed      │     2 │    2.0% │
    ├─────────────┼───────┼─────────┤
    │ TOTAL       │   100 │  100.0% │
    └─────────────┴───────┴─────────┘
    
    [Similar tables for severity, category, repo]
    Return: 0
    
    # --by-repo only
    Input: StatsArgs(by_repo=True)
    Output (stdout):
    ┌──────────────────────────┬───────┬─────────┐
    │ Repo                     │ Count │ Percent │
    ├──────────────────────────┼───────┼─────────┤
    │ ejacklab/open-dsearch    │    60 │   60.0% │
    │ ejacklab/other-repo      │    40 │   40.0% │
    └──────────────────────────┴───────┴─────────┘
    Return: 0
    
    # --repo filter
    Input: StatsArgs(repo="ejacklab/open-dsearch")
    Output: Stats for only ejacklab/open-dsearch tickets
    Return: 0
    
    # JSON format
    Input: StatsArgs(format="json")
    Output (stdout):
    {
      "total": 100,
      "by_status": {"open": 45, "in_progress": 20, ...},
      "by_severity": {"critical": 10, "high": 25, ...},
      "by_category": {"code": 60, "security": 15, ...},
      "by_repo": {"ejacklab/open-dsearch": 60, ...}
    }
    Return: 0
    
    # no tickets
    Input: StatsArgs(), empty store
    Output (stdout): "No tickets found"
    Return: 1
    """
```

### L6: Test
```python
test_cli_stats_shows_all_breakdowns()
test_cli_stats_by_repo_only()
test_cli_stats_by_category_only()
test_cli_stats_by_severity_only()
test_cli_stats_by_status_only()
test_cli_stats_repo_filter()
test_cli_stats_json_format()
test_cli_stats_empty_store_returns_1()
test_cli_stats_calculates_percentages_correctly()
test_cli_stats_includes_total_row()
test_cli_stats_handles_multiple_repos()
```

---

## Feature 3: Validate Command

### L1: CLI
### L2: Management Commands
### L3: validate command
### L4: `cli_validate(args: ValidateArgs, store: TicketStore) -> int`
  - Scan all ticket files in storage
  - Validate YAML frontmatter syntax
  - Validate required fields present (id, title, repo)
  - Validate field values against constraints (enum values, formats)
  - Validate file naming convention matches ID
  - Validate directory structure matches repo/category
  - Report errors with file path, line number, and description
  - Support --fix flag to auto-correct fixable issues
  - Return exit code: 0 all valid, 1 validation errors found, 2 system error

### L5: Spec
```python
@dataclass
class ValidateArgs:
    fix: bool = False  # auto-fix issues where possible
    strict: bool = False  # warn on non-critical issues
    format: str = "table"  # table, json

@dataclass
class ValidationError:
    file_path: str
    line: Optional[int]
    field: Optional[str]
    message: str
    severity: str  # "error", "warning"
    fixable: bool

def cli_validate(args: ValidateArgs, store: TicketStore) -> int:
    """
    # all valid
    Input: ValidateArgs(), store with 10 valid tickets
    Output (stdout): "✓ All 10 ticket files are valid"
    Return: 0
    
    # validation errors
    Input: ValidateArgs(), store with errors
    Output (stdout):
    ┌────────────────────────────────────┬──────┬─────────┬───────────────────────────────┬──────────┐
    │ File                               │ Line │ Field   │ Error                         │ Fixable  │
    ├────────────────────────────────────┼──────┼─────────┼───────────────────────────────┼──────────┤
    │ tickets/ejacklab/repo/code/C1.md   │ 3    │ title   │ Required field missing        │ No       │
    │ tickets/ejacklab/repo/code/C2.md   │ 5    │ status  │ Invalid value: unknown_status │ Yes      │
    │ tickets/ejacklab/repo/code/C3.md   │ -    │ -       │ YAML parse error at line 8    │ No       │
    └────────────────────────────────────┴──────┴─────────┴───────────────────────────────┴──────────┘
    
    Found 3 errors in 3 files
    Return: 1
    
    # --fix flag
    Input: ValidateArgs(fix=True), store with fixable errors
    Output (stdout):
    Fixed 2 issues:
      - C2.md: status changed from 'unknown_status' to 'open'
      - C4.md: added missing created timestamp
    
    Remaining 1 error (not fixable):
      - C1.md: Required field 'title' missing
    Return: 1
    
    # JSON format
    Input: ValidateArgs(format="json")
    Output (stdout):
    {
      "valid": false,
      "total_files": 10,
      "errors": [
        {"file": "tickets/.../C1.md", "line": 3, "field": "title", "message": "...", "fixable": false}
      ],
      "warnings": []
    }
    Return: 1
    
    # --strict mode (warnings)
    Input: ValidateArgs(strict=True)
    Output: Includes warnings for non-critical issues (e.g., missing optional fields, unusual values)
    """
```

### L6: Test
```python
test_cli_validate_all_valid_returns_0()
test_cli_validate_missing_required_field()
test_cli_validate_invalid_status_value()
test_cli_validate_invalid_severity_value()
test_cli_validate_yaml_syntax_error()
test_cli_validate_fix_auto_corrects_issues()
test_cli_validate_fix_reports_unfixable()
test_cli_validate_strict_mode_shows_warnings()
test_cli_validate_json_format()
test_cli_validate_file_naming_mismatch()
test_cli_validate_directory_structure_mismatch()
test_cli_validate_multiple_errors_in_one_file()
```

---

## Feature 4: Doctor Command

### L1: CLI
### L2: Management Commands
### L3: doctor command
### L4: `cli_doctor(args: DoctorArgs, config_manager: ConfigManager, store: TicketStore) -> int`
  - Run diagnostic checks for common issues
  - Check 1: Config file exists and is valid TOML
  - Check 2: Tickets directory exists and is accessible
  - Check 3: Zvec index exists and is not corrupted
  - Check 4: Index is in sync with ticket files (no orphan entries, no missing tickets)
  - Check 5: Embedding provider is configured and accessible (if semantic search enabled)
  - Check 6: API keys are set (if using remote embedding provider)
  - Check 7: File permissions allow read/write
  - Report status for each check (✓ pass, ✗ fail, ⚠ warning)
  - Provide actionable suggestions for failed checks
  - Return exit code: 0 all pass, 1 some failures, 2 critical failure

### L5: Spec
```python
@dataclass
class DoctorArgs:
    fix: bool = False  # attempt auto-fix where possible
    check: Optional[str] = None  # run specific check only

@dataclass
class DiagnosticResult:
    check_name: str
    status: str  # "pass", "fail", "warning"
    message: str
    suggestion: Optional[str]
    auto_fixable: bool

def cli_doctor(args: DoctorArgs, config_manager: ConfigManager, store: TicketStore) -> int:
    """
    # all checks pass
    Input: DoctorArgs()
    Output (stdout):
    Running diagnostics...
    
    ✓ Config file: Valid (./vtic.toml)
    ✓ Tickets directory: Exists and accessible (./tickets)
    ✓ Zvec index: Valid and synced (142 tickets indexed)
    ✓ Embedding provider: OpenAI configured
    ✓ API key: OPENAI_API_KEY is set
    ✓ File permissions: Read/write access confirmed
    
    All checks passed!
    Return: 0
    
    # some failures
    Input: DoctorArgs()
    Output (stdout):
    Running diagnostics...
    
    ✓ Config file: Valid (./vtic.toml)
    ✗ Tickets directory: Not found (./tickets)
      → Suggestion: Run 'vtic init' to create tickets directory
    ✗ Zvec index: Not found (.vtic/index)
      → Suggestion: Run 'vtic reindex' to build index
    ⚠ Embedding provider: No provider configured
      → Suggestion: Set search.embedding_provider in vtic.toml (or use BM25 only)
    ✓ API key: N/A (no remote provider configured)
    ✓ File permissions: Read/write access confirmed
    
    2 failures, 1 warning
    Return: 1
    
    # --fix flag
    Input: DoctorArgs(fix=True)
    Action: Auto-create missing directories, reindex if needed
    Output (stdout):
    Running diagnostics with auto-fix...
    
    ✗ Tickets directory: Not found
      → Fixed: Created ./tickets
    ✗ Zvec index: Not found
      → Fixed: Running reindex... Indexed 0 tickets
    ⚠ Embedding provider: No provider configured
      → Cannot auto-fix: Manual configuration required
    
    Fixed 2 issues. 1 warning remains.
    Return: 1
    
    # specific check only
    Input: DoctorArgs(check="index")
    Output (stdout):
    ✓ Zvec index: Valid and synced (142 tickets indexed)
    Return: 0
    """
```

### L6: Test
```python
test_cli_doctor_all_checks_pass()
test_cli_doctor_missing_config_file()
test_cli_doctor_invalid_config_toml()
test_cli_doctor_missing_tickets_directory()
test_cli_doctor_missing_index()
test_cli_doctor_index_out_of_sync()
test_cli_doctor_embedding_provider_not_configured()
test_cli_doctor_missing_api_key()
test_cli_doctor_file_permission_issues()
test_cli_doctor_fix_creates_missing_directories()
test_cli_doctor_fix_reindexes_if_needed()
test_cli_doctor_specific_check_only()
test_cli_doctor_reports_suggestions()
```

---

## Feature 5: Trash Command

### L1: CLI
### L2: Management Commands
### L3: trash command
### L4: `cli_trash(args: TrashArgs, store: TicketStore) -> int`
  - Manage soft-deleted tickets in .trash/ directory
  - `list`: Show all trashed tickets with deletion date
  - `restore`: Move ticket from .trash/ back to active tickets
  - `clean`: Permanently delete old trashed tickets (--older-than)
  - `show`: Display contents of a trashed ticket
  - Support --format for list output (table, json)
  - Return exit code: 0 success, 1 not found, 2 error

### L5: Spec
```python
@dataclass
class TrashArgs:
    subcommand: str  # "list", "restore", "clean", "show"
    ticket_id: Optional[str] = None
    older_than: Optional[str] = None  # e.g., "30d", "1w"
    format: str = "table"
    force: bool = False  # skip confirmation for clean

@dataclass
class TrashedTicket:
    id: str
    original_path: str
    deleted_at: str  # ISO 8601
    metadata: Dict[str, Any]

def cli_trash(args: TrashArgs, store: TicketStore) -> int:
    """
    # list subcommand
    Input: TrashArgs(subcommand="list")
    Output (stdout):
    ┌──────┬────────────────────────────┬─────────────────────────┬──────────────────────────┐
    │ ID   │ Title                      │ Original Path           │ Deleted At               │
    ├──────┼────────────────────────────┼─────────────────────────┼──────────────────────────┤
    │ C5   │ Fix login bug              │ ejacklab/repo/code/C5   │ 2026-03-15T10:30:00Z     │
    │ S2   │ Security vulnerability     │ ejacklab/repo/security  │ 2026-03-10T08:15:00Z     │
    └──────┴────────────────────────────┴─────────────────────────┴──────────────────────────┘
    
    2 trashed tickets
    Return: 0
    
    # restore subcommand
    Input: TrashArgs(subcommand="restore", ticket_id="C5")
    Action: Move .trash/C5.md back to tickets/ejacklab/repo/code/C5.md
            Re-add to Zvec index
    Output (stdout): "Restored C5 to tickets/ejacklab/repo/code/C5.md"
    Return: 0
    
    # restore non-existent
    Input: TrashArgs(subcommand="restore", ticket_id="NONEXISTENT")
    Output (stderr): "Ticket NONEXISTENT not found in trash"
    Return: 1
    
    # show subcommand
    Input: TrashArgs(subcommand="show", ticket_id="C5")
    Output (stdout): Full ticket content (markdown + frontmatter)
    Return: 0
    
    # clean subcommand
    Input: TrashArgs(subcommand="clean", older_than="30d")
    Action: Permanently delete tickets trashed more than 30 days ago
    Output (stdout): "Permanently deleted 3 tickets older than 30 days"
    Return: 0
    
    # clean with confirmation
    Input: TrashArgs(subcommand="clean", older_than="7d", force=False)
    Output (stdout): "Delete 5 tickets older than 7 days? [y/N]: "
    # If user enters 'y': proceed with deletion
    # If user enters 'n': "Cancelled"
    Return: 0 or 2 (if cancelled)
    
    # clean --force (no confirmation)
    Input: TrashArgs(subcommand="clean", older_than="7d", force=True)
    Output (stdout): "Permanently deleted 5 tickets older than 7 days"
    Return: 0
    
    # empty trash
    Input: TrashArgs(subcommand="list"), empty trash
    Output (stdout): "No trashed tickets"
    Return: 0
    """
```

### L6: Test
```python
test_cli_trash_list_shows_trashed_tickets()
test_cli_trash_list_empty_trash()
test_cli_trash_list_json_format()
test_cli_trash_restore_moves_back_to_active()
test_cli_trash_restore_reindexes()
test_cli_trash_restore_nonexistent_returns_1()
test_cli_trash_show_displays_content()
test_cli_trash_clean_deletes_old_tickets()
test_cli_trash_clean_older_than_days()
test_cli_trash_clean_older_than_weeks()
test_cli_trash_clean_prompts_without_force()
test_cli_trash_clean_force_skips_prompt()
test_cli_trash_clean_no_matching_tickets()
test_cli_trash_restore_preserves_original_path()
```

---

## Feature 6: Bulk Create CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk create CLI
### L4: `cli_bulk_create(args: BulkCreateArgs, store: TicketStore) -> int`
  - Read tickets from JSON/JSONL file specified by --from
  - Parse and validate each ticket object
  - Generate IDs for tickets without specified ID
  - Create all tickets in batch with progress indicator
  - Report success/failure count with details
  - Support --dry-run to preview without creating
  - Support --on-error (stop, continue, rollback)
  - Return exit code: 0 all success, 1 partial failure, 2 all failed

### L5: Spec
```python
@dataclass
class BulkCreateArgs:
    from_file: str  # --from, path to JSON/JSONL file
    dry_run: bool = False
    on_error: str = "stop"  # "stop", "continue", "rollback"
    format: str = "table"

@dataclass
class BulkCreateResult:
    total: int
    created: int
    failed: int
    errors: List[Tuple[int, str, str]]  # (index, ticket_id_or_title, error_message)
    created_ids: List[str]

def cli_bulk_create(args: BulkCreateArgs, store: TicketStore) -> int:
    """
    # successful bulk create
    Input: BulkCreateArgs(from_file="tickets.json"), file contains:
    [
      {"title": "Bug 1", "repo": "owner/repo", "severity": "high"},
      {"title": "Bug 2", "repo": "owner/repo", "severity": "medium"},
      {"title": "Bug 3", "repo": "owner/repo", "severity": "low"}
    ]
    Output (stdout):
    Creating tickets from tickets.json...
    ████████████████████████████████████ 100% | 3/3
    
    ✓ Created 3 tickets: C10, C11, C12
    Return: 0
    
    # with validation errors (on_error=stop)
    Input: BulkCreateArgs(from_file="tickets.json", on_error="stop"), file contains:
    [
      {"title": "Valid", "repo": "owner/repo"},
      {"title": "", "repo": "owner/repo"},  # invalid: empty title
      {"title": "Also Valid", "repo": "owner/repo"}
    ]
    Output (stdout):
    Creating tickets from tickets.json...
    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 6% | 1/3
    
    ✗ Error at index 1: Title is required
    Stopped on error (use --on-error=continue to skip)
    
    Created: 1
    Failed: 1
    Remaining: 1 (not processed)
    Return: 1
    
    # with validation errors (on_error=continue)
    Input: BulkCreateArgs(from_file="tickets.json", on_error="continue")
    Output (stdout):
    Creating tickets from tickets.json...
    ████████████████████████████████████ 100% | 3/3
    
    ✓ Created 2 tickets: C10, C12
    ✗ Failed 1 ticket:
      - Index 1: Title is required
    
    Created: 2 | Failed: 1
    Return: 1
    
    # --dry-run
    Input: BulkCreateArgs(from_file="tickets.json", dry_run=True)
    Output (stdout):
    Dry run: validating 3 tickets...
    ✓ All 3 tickets valid
    Would create: C10, C11, C12
    No tickets created (dry run)
    Return: 0
    
    # on_error=rollback
    Input: BulkCreateArgs(from_file="tickets.json", on_error="rollback")
    Action: If any error occurs, delete all created tickets in this batch
    Output (stdout):
    Creating tickets from tickets.json...
    Error at index 2. Rolling back 1 created ticket...
    Rolled back C10
    No tickets created (rolled back due to error)
    Return: 2
    
    # JSONL format
    Input: BulkCreateArgs(from_file="tickets.jsonl"), file contains:
    {"title": "Bug 1", "repo": "owner/repo"}
    {"title": "Bug 2", "repo": "owner/repo"}
    Output: Same behavior, reads line-delimited JSON
    Return: 0
    
    # file not found
    Input: BulkCreateArgs(from_file="nonexistent.json")
    Output (stderr): "File not found: nonexistent.json"
    Return: 2
    
    # invalid JSON
    Input: BulkCreateArgs(from_file="invalid.json")
    Output (stderr): "Failed to parse JSON: Expecting ',' delimiter at line 5"
    Return: 2
    """
```

### L6: Test
```python
test_cli_bulk_create_from_json()
test_cli_bulk_create_from_jsonl()
test_cli_bulk_create_generates_ids()
test_cli_bulk_create_preserves_specified_ids()
test_cli_bulk_create_dry_run()
test_cli_bulk_create_on_error_stop()
test_cli_bulk_create_on_error_continue()
test_cli_bulk_create_on_error_rollback()
test_cli_bulk_create_shows_progress()
test_cli_bulk_create_file_not_found()
test_cli_bulk_create_invalid_json()
test_cli_bulk_create_validation_error()
test_cli_bulk_create_all_fail_returns_2()
test_cli_bulk_create_large_batch()
```

---

## Feature 7: Bulk Update CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk update CLI
### L4: `cli_bulk_update(args: BulkUpdateArgs, store: TicketStore) -> int`
  - Filter tickets matching --filter criteria (status, severity, category, repo, etc.)
  - Apply field updates specified by --set flags
  - Support multiple --set flags (e.g., --set status=fixed --set severity=low)
  - Show preview of affected tickets before update
  - Require --yes flag to skip confirmation
  - Support --dry-run to preview without updating
  - Update `updated` timestamp on all modified tickets
  - Report count of updated tickets
  - Return exit code: 0 success, 1 no matches, 2 error

### L5: Spec
```python
@dataclass
class BulkUpdateArgs:
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None  # supports glob patterns
    set_fields: List[str] = field(default_factory=list)  # ["status=fixed", "severity=low"]
    dry_run: bool = False
    yes: bool = False
    limit: Optional[int] = None  # max tickets to update

def cli_bulk_update(args: BulkUpdateArgs, store: TicketStore) -> int:
    """
    # basic bulk update
    Input: BulkUpdateArgs(filter_status="open", set_fields=["status=reviewing"], yes=True)
    Output (stdout):
    Updating tickets with status=open to status=reviewing...
    ████████████████████████████████████ 100% | 15/15
    
    ✓ Updated 15 tickets
    Return: 0
    
    # multiple field updates
    Input: BulkUpdateArgs(
        filter_status="fixed",
        set_fields=["status=closed", "severity=low"],
        yes=True
    )
    Output (stdout):
    Updating tickets with status=fixed...
      - status: fixed → closed
      - severity: <varies> → low
    
    ████████████████████████████████████ 100% | 8/8
    ✓ Updated 8 tickets
    Return: 0
    
    # with confirmation
    Input: BulkUpdateArgs(filter_severity="critical", set_fields=["severity=high"], yes=False)
    Output (stdout):
    Found 5 tickets matching filter:
      - C1: CORS Bug (severity: critical → high)
      - C3: Auth issue (severity: critical → high)
      - C5: Memory leak (severity: critical → high)
      - S1: SQL injection (severity: critical → high)
      - S2: XSS vulnerability (severity: critical → high)
    
    Update these 5 tickets? [y/N]: _
    # If 'y': proceed with update
    # If 'n': "Cancelled"
    Return: 0 or 2
    
    # --dry-run
    Input: BulkUpdateArgs(
        filter_repo="ejacklab/*",
        set_fields=["category=security"],
        dry_run=True
    )
    Output (stdout):
    Dry run: would update 20 tickets in ejacklab/*
      - All would have category set to 'security'
    No tickets updated (dry run)
    Return: 0
    
    # no matches
    Input: BulkUpdateArgs(filter_status="nonexistent", set_fields=["status=fixed"])
    Output (stdout): "No tickets match the specified filters"
    Return: 1
    
    # with --limit
    Input: BulkUpdateArgs(filter_status="open", set_fields=["status=in_progress"], limit=10, yes=True)
    Output (stdout):
    Updating first 10 tickets with status=open to status=in_progress...
    ✓ Updated 10 tickets (45 remaining matches not updated)
    Return: 0
    
    # invalid field name
    Input: BulkUpdateArgs(set_fields=["invalid_field=value"])
    Output (stderr): "Unknown field: invalid_field. Allowed fields: status, severity, category, tags, ..."
    Return: 2
    
    # repo glob pattern
    Input: BulkUpdateArgs(filter_repo="ejacklab/*", set_fields=["category=infra"], yes=True)
    Action: Match all repos starting with "ejacklab/"
    Output (stdout): "✓ Updated 30 tickets across 3 repos"
    Return: 0
    """
```

### L6: Test
```python
test_cli_bulk_update_by_status()
test_cli_bulk_update_by_severity()
test_cli_bulk_update_by_category()
test_cli_bulk_update_by_repo()
test_cli_bulk_update_by_repo_glob()
test_cli_bulk_update_multiple_fields()
test_cli_bulk_update_confirmation_prompt()
test_cli_bulk_update_yes_skips_prompt()
test_cli_bulk_update_dry_run()
test_cli_bulk_update_no_matches()
test_cli_bulk_update_with_limit()
test_cli_bulk_update_invalid_field()
test_cli_bulk_update_updates_timestamp()
test_cli_bulk_update_combined_filters()
```

---

## Feature 8: Bulk Delete CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk delete CLI
### L4: `cli_bulk_delete(args: BulkDeleteArgs, store: TicketStore) -> int`
  - Filter tickets matching --filter criteria
  - Require --all flag to confirm bulk deletion
  - Require --yes flag to skip confirmation prompt
  - Support --force for hard delete (default is soft delete to trash)
  - Show preview of affected tickets
  - Report count of deleted tickets
  - Support --dry-run to preview without deleting
  - Return exit code: 0 success, 1 no matches, 2 cancelled/error

### L5: Spec
```python
@dataclass
class BulkDeleteArgs:
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None
    all: bool = False  # required to confirm bulk delete
    force: bool = False  # hard delete instead of trash
    yes: bool = False  # skip confirmation
    dry_run: bool = False
    limit: Optional[int] = None

def cli_bulk_delete(args: BulkDeleteArgs, store: TicketStore) -> int:
    """
    # basic bulk delete (soft)
    Input: BulkDeleteArgs(filter_status="wont_fix", all=True, yes=True)
    Action: Move all wont_fix tickets to .trash/
    Output (stdout):
    Deleting tickets with status=wont_fix...
    ████████████████████████████████████ 100% | 5/5
    
    ✓ Deleted 5 tickets (moved to trash)
    Return: 0
    
    # hard delete (--force)
    Input: BulkDeleteArgs(filter_status="closed", all=True, force=True, yes=True)
    Action: Permanently delete all closed tickets
    Output (stdout):
    Permanently deleting tickets with status=closed...
    ████████████████████████████████████ 100% | 12/12
    
    ⚠ Permanently deleted 12 tickets
    Return: 0
    
    # with confirmation
    Input: BulkDeleteArgs(filter_category="test", all=True, yes=False)
    Output (stdout):
    ⚠ WARNING: This will delete 8 tickets!
    
    Tickets to be deleted:
      - C20: Test ticket 1
      - C21: Test ticket 2
      ...
    
    Move 8 tickets to trash? [y/N]: _
    # If 'y': proceed
    # If 'n': "Cancelled", return 2
    Return: 0 or 2
    
    # missing --all flag
    Input: BulkDeleteArgs(filter_status="closed")
    Output (stderr): "Bulk delete requires --all flag for safety"
    Return: 2
    
    # --dry-run
    Input: BulkDeleteArgs(filter_repo="test/*", all=True, dry_run=True)
    Output (stdout):
    Dry run: would delete 15 tickets in test/*
      - C30: Old feature
      - C31: Deprecated API
      ...
    No tickets deleted (dry run)
    Return: 0
    
    # no matches
    Input: BulkDeleteArgs(filter_status="nonexistent", all=True)
    Output (stdout): "No tickets match the specified filters"
    Return: 1
    
    # with --limit
    Input: BulkDeleteArgs(filter_status="closed", all=True, limit=10, yes=True)
    Output (stdout):
    Deleting first 10 tickets with status=closed...
    ✓ Deleted 10 tickets (25 remaining matches not deleted)
    Return: 0
    
    # combined filters
    Input: BulkDeleteArgs(
        filter_repo="old-org/*",
        filter_status="closed",
        all=True,
        yes=True
    )
    Output (stdout):
    Deleting tickets with repo=old-org/* AND status=closed...
    ✓ Deleted 20 tickets
    Return: 0
    """
```

### L6: Test
```python
test_cli_bulk_delete_by_status()
test_cli_bulk_delete_by_category()
test_cli_bulk_delete_by_repo()
test_cli_bulk_delete_by_repo_glob()
test_cli_bulk_delete_soft_delete_to_trash()
test_cli_bulk_delete_hard_delete_with_force()
test_cli_bulk_delete_requires_all_flag()
test_cli_bulk_delete_confirmation_prompt()
test_cli_bulk_delete_yes_skips_prompt()
test_cli_bulk_delete_dry_run()
test_cli_bulk_delete_no_matches()
test_cli_bulk_delete_with_limit()
test_cli_bulk_delete_combined_filters()
test_cli_bulk_delete_cancellable()
```

---

## Feature 9: Export CLI

### L1: CLI
### L2: Bulk Operations
### L3: Export CLI
### L4: `cli_export(args: ExportArgs, store: TicketStore) -> int`
  - Export tickets to specified format (json, jsonl, csv, markdown, tar.gz)
  - Support --output to specify output file (default: stdout for text formats)
  - Support --filter to export subset of tickets
  - Support --fields to export only specific fields
  - Support --include-deleted to include trashed tickets
  - For tar.gz: create archive with all markdown files and index metadata
  - Report count of exported tickets
  - Return exit code: 0 success, 1 no tickets, 2 error

### L5: Spec
```python
@dataclass
class ExportArgs:
    format: str  # json, jsonl, csv, markdown, tar.gz
    output: Optional[str] = None  # file path, defaults to stdout
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None
    fields: Optional[List[str]] = None  # --fields id,title,status
    include_deleted: bool = False
    pretty: bool = False  # for JSON, pretty-print

def cli_export(args: ExportArgs, store: TicketStore) -> int:
    """
    # JSON export to stdout
    Input: ExportArgs(format="json")
    Output (stdout):
    [
      {"id": "C1", "title": "CORS Bug", "repo": "owner/repo", ...},
      {"id": "C2", "title": "Auth issue", "repo": "owner/repo", ...}
    ]
    Return: 0
    
    # JSON export to file
    Input: ExportArgs(format="json", output="tickets.json")
    Action: Write JSON to tickets.json
    Output (stdout): "Exported 50 tickets to tickets.json"
    Return: 0
    
    # JSON with --pretty
    Input: ExportArgs(format="json", pretty=True)
    Output (stdout): Pretty-printed JSON with indentation
    
    # JSONL export (line-delimited)
    Input: ExportArgs(format="jsonl")
    Output (stdout):
    {"id": "C1", "title": "CORS Bug", ...}
    {"id": "C2", "title": "Auth issue", ...}
    Return: 0
    
    # CSV export
    Input: ExportArgs(format="csv", output="tickets.csv")
    Action: Write CSV to tickets.csv with header row
    Output (stdout): "Exported 50 tickets to tickets.csv"
    CSV format:
    id,title,repo,category,severity,status,created,updated
    C1,CORS Bug,owner/repo,code,critical,open,2026-03-15T10:00:00Z,2026-03-15T10:00:00Z
    C2,Auth issue,owner/repo,security,high,in_progress,2026-03-14T09:00:00Z,2026-03-16T11:00:00Z
    
    # CSV with --fields
    Input: ExportArgs(format="csv", fields=["id", "title", "status"])
    Output (stdout):
    id,title,status
    C1,CORS Bug,open
    C2,Auth issue,in_progress
    
    # Markdown export
    Input: ExportArgs(format="markdown", output="tickets.md")
    Action: Concatenate all ticket markdown files
    Output (stdout): "Exported 50 tickets to tickets.md"
    
    # tar.gz archive
    Input: ExportArgs(format="tar.gz", output="backup.tar.gz")
    Action: Create tar.gz with:
      - All markdown files preserving directory structure
      - .vtic/index metadata
      - manifest.json with export metadata
    Output (stdout): "Created backup.tar.gz with 50 tickets (2.3 MB)"
    Return: 0
    
    # with filter
    Input: ExportArgs(format="json", filter_status="open")
    Output (stdout): JSON array with only open tickets
    Output (stderr): "Exported 15 tickets (filtered by status=open)"
    Return: 0
    
    # include deleted
    Input: ExportArgs(format="json", include_deleted=True)
    Action: Include tickets from .trash/ in export
    Output (stdout): JSON with active and trashed tickets
    Return: 0
    
    # no tickets
    Input: ExportArgs(format="json"), empty store
    Output (stdout): "No tickets to export"
    Return: 1
    
    # invalid format
    Input: ExportArgs(format="invalid")
    Output (stderr): "Unknown format: invalid. Supported: json, jsonl, csv, markdown, tar.gz"
    Return: 2
    """
```

### L6: Test
```python
test_cli_export_json_to_stdout()
test_cli_export_json_to_file()
test_cli_export_json_pretty()
test_cli_export_jsonl()
test_cli_export_csv()
test_cli_export_csv_with_fields()
test_cli_export_markdown()
test_cli_export_tar_gz()
test_cli_export_with_filter_status()
test_cli_export_with_filter_repo()
test_cli_export_include_deleted()
test_cli_export_no_tickets()
test_cli_export_invalid_format()
test_cli_export_tar_gz_preserves_structure()
test_cli_export_csv_handles_special_chars()
```

---

## Feature 10: Import CLI

### L1: CLI
### L2: Bulk Operations
### L3: Import CLI
### L4: `cli_import(args: ImportArgs, store: TicketStore) -> int`
  - Import tickets from JSON, JSONL, CSV, or tar.gz archive
  - Detect format from file extension or --format flag
  - For tar.gz: extract and import markdown files
  - Handle duplicate IDs: skip, error, or rename (--on-duplicate)
  - Generate new IDs for tickets without IDs
  - Support --id-map to export mapping of old→new IDs
  - Support --dry-run to validate without importing
  - Validate all tickets before import
  - Report success/failure with details
  - Return exit code: 0 success, 1 partial failure, 2 all failed

### L5: Spec
```python
@dataclass
class ImportArgs:
    file: str  # path to import file
    format: Optional[str] = None  # auto-detect from file extension if not specified
    on_duplicate: str = "error"  # "skip", "error", "rename"
    dry_run: bool = False
    id_map: Optional[str] = None  # --id-map file to write ID mappings
    validate_only: bool = False  # validate but don't import

@dataclass
class ImportResult:
    total: int
    imported: int
    skipped: int
    errors: List[Tuple[int, str, str]]  # (index, id, error)
    id_mappings: Dict[str, str]  # old_id -> new_id

def cli_import(args: ImportArgs, store: TicketStore) -> int:
    """
    # JSON import
    Input: ImportArgs(file="tickets.json"), file contains valid tickets
    Output (stdout):
    Importing from tickets.json...
    ████████████████████████████████████ 100% | 20/20
    
    ✓ Imported 20 tickets
    Return: 0
    
    # JSONL import
    Input: ImportArgs(file="tickets.jsonl")
    Action: Read line-delimited JSON
    Output (stdout): "✓ Imported 15 tickets"
    Return: 0
    
    # CSV import
    Input: ImportArgs(file="tickets.csv")
    Action: Parse CSV with header row, map columns to ticket fields
    Output (stdout): "✓ Imported 30 tickets from CSV"
    Return: 0
    
    # CSV with column mapping
    Input: ImportArgs(file="jira-export.csv"), columns are "Issue Key", "Summary", "Status"
    Action: Auto-detect common column names, or use --column-map
    Output (stdout): 
    Detected column mapping:
      Issue Key → id
      Summary → title
      Status → status
    ✓ Imported 50 tickets
    Return: 0
    
    # tar.gz import
    Input: ImportArgs(file="backup.tar.gz")
    Action: Extract archive, import markdown files preserving structure
    Output (stdout):
    Extracting backup.tar.gz...
    Importing 45 ticket files...
    ✓ Imported 45 tickets from archive
    Return: 0
    
    # duplicate handling: error (default)
    Input: ImportArgs(file="tickets.json", on_duplicate="error")
           File contains ticket with id="C1", C1 already exists
    Output (stdout):
    Importing from tickets.json...
    ✗ Error at index 5: Duplicate ID 'C1' already exists
    Stopped on error (use --on-duplicate=skip or --on-duplicate=rename)
    Imported: 4 | Failed: 1
    Return: 1
    
    # duplicate handling: skip
    Input: ImportArgs(file="tickets.json", on_duplicate="skip")
    Output (stdout):
    Importing from tickets.json...
    ⚠ Skipped 3 duplicate IDs: C1, C5, S2
    ✓ Imported 17 new tickets
    Return: 0
    
    # duplicate handling: rename
    Input: ImportArgs(file="tickets.json", on_duplicate="rename")
    Output (stdout):
    Importing from tickets.json...
    ⚠ Renamed 3 duplicate IDs:
      - C1 → C20
      - C5 → C21
      - S2 → S10
    ✓ Imported 20 tickets
    Return: 0
    
    # --id-map
    Input: ImportArgs(file="tickets.json", on_duplicate="rename", id_map="id-mapping.json")
    Action: Write mapping file
    Output (stdout): "✓ Imported 20 tickets, ID mapping written to id-mapping.json"
    id-mapping.json content: {"C1": "C20", "C5": "C21", "S2": "S10"}
    Return: 0
    
    # --dry-run
    Input: ImportArgs(file="tickets.json", dry_run=True)
    Output (stdout):
    Dry run: validating 20 tickets...
    ✓ All 20 tickets valid
    Would import: C1, C2, C3, ...
    No tickets imported (dry run)
    Return: 0
    
    # validation error
    Input: ImportArgs(file="tickets.json")
           File contains ticket with empty title
    Output (stdout):
    Importing from tickets.json...
    ✗ Validation error at index 7: Title is required
    Imported: 6 | Failed: 1
    Return: 1
    
    # file not found
    Input: ImportArgs(file="nonexistent.json")
    Output (stderr): "File not found: nonexistent.json"
    Return: 2
    
    # invalid JSON
    Input: ImportArgs(file="invalid.json")
    Output (stderr): "Failed to parse JSON: Expecting ',' delimiter at line 5"
    Return: 2
    """
```

### L6: Test
```python
test_cli_import_from_json()
test_cli_import_from_jsonl()
test_cli_import_from_csv()
test_cli_import_from_csv_with_column_mapping()
test_cli_import_from_tar_gz()
test_cli_import_duplicate_error()
test_cli_import_duplicate_skip()
test_cli_import_duplicate_rename()
test_cli_import_id_map()
test_cli_import_dry_run()
test_cli_import_validation_error()
test_cli_import_file_not_found()
test_cli_import_invalid_json()
test_cli_import_generates_missing_ids()
test_cli_import_preserves_existing_ids()
test_cli_import_csv_handles_quotes()
```

---

## Feature 11: Markdown Output

### L1: CLI
### L2: Output Formats
### L3: Markdown output
### L4: `format_markdown(tickets: Union[Ticket, List[Ticket]], mode: str = "single") -> str`
  - Format single ticket or list of tickets as Markdown
  - Single ticket mode: full markdown with frontmatter and content
  - List mode: summary table with links/details
  - Support --template for custom markdown templates
  - Include all ticket fields in structured format
  - Generate clickable links for repo, file_refs
  - Format tags as markdown links or badges
  - Support syntax highlighting for code in description/fix

### L5: Spec
```python
@dataclass
class MarkdownFormatOptions:
    mode: str = "single"  # "single", "list", "summary"
    template: Optional[str] = None  # path to custom template
    include_frontmatter: bool = True
    include_content: bool = True
    syntax_highlight: bool = True

def format_markdown(
    tickets: Union[Ticket, List[Ticket]], 
    options: MarkdownFormatOptions = MarkdownFormatOptions()
) -> str:
    """
    # single ticket (default)
    Input: Ticket(id="C1", title="CORS Bug", repo="owner/repo", 
                  description="The API returns `Access-Control-Allow-Origin: *`",
                  severity="critical", status="open", category="code",
                  tags=["security", "api"], created="2026-03-15T10:00:00Z")
    Output:
    ---
    id: C1
    title: CORS Bug
    repo: owner/repo
    category: code
    severity: critical
    status: open
    tags:
      - security
      - api
    created: "2026-03-15T10:00:00Z"
    updated: "2026-03-15T10:00:00Z"
    ---
    
    # CORS Bug
    
    The API returns `Access-Control-Allow-Origin: *`
    
    **Severity:** critical  
    **Status:** open  
    **Repo:** [owner/repo](https://github.com/owner/repo)
    
    **Tags:** `security` `api`
    
    # list mode
    Input: List of 3 tickets, options.mode="list"
    Output:
    # Tickets (3)
    
    | ID | Title | Status | Severity | Repo |
|----|-------|--------|----------|------|
    | C1 | CORS Bug | open | critical | owner/repo |
    | C2 | Auth issue | in_progress | high | owner/repo |
    | S1 | SQL injection | fixed | critical | owner/repo |
    
    # summary mode (detailed list)
    Input: List of tickets, options.mode="summary"
    Output:
    # Open Tickets (2)
    
    ## C1: CORS Bug
    
    - **Status:** open
    - **Severity:** critical
    - **Category:** code
    - **Repo:** owner/repo
    - **Created:** 2026-03-15
    
    The API returns `Access-Control-Allow-Origin: *`
    
    ---
    
    ## C2: Auth issue
    
    - **Status:** in_progress
    - **Severity:** high
    - **Category:** security
    - **Repo:** owner/repo
    - **Created:** 2026-03-14
    
    Authentication bypass in login endpoint.
    
    ---
    
    # with code blocks
    Input: Ticket with fix field containing code
    Output: Includes syntax-highlighted code block
    
    **Fix:**
    ```python
    # Fixed in commit abc123
    response.headers['Access-Control-Allow-Origin'] = 'https://example.com'
    ```
    
    # custom template
    Input: options.template="custom.md"
    Action: Load template with placeholders like {{id}}, {{title}}, {{description}}
    Output: Formatted according to template
    
    # without frontmatter
    Input: options.include_frontmatter=False
    Output: Pure markdown without YAML block
    """
```

### L6: Test
```python
test_format_markdown_single_ticket()
test_format_markdown_single_with_all_fields()
test_format_markdown_list_mode()
test_format_markdown_summary_mode()
test_format_markdown_with_frontmatter()
test_format_markdown_without_frontmatter()
test_format_markdown_with_code_blocks()
test_format_markdown_syntax_highlighting()
test_format_markdown_tags_as_badges()
test_format_markdown_repo_links()
test_format_markdown_file_ref_links()
test_format_markdown_custom_template()
test_format_markdown_empty_list()
test_format_markdown_special_characters_escaped()
```

---

## Feature 12: CSV Output

### L1: CLI
### L2: Output Formats
### L3: CSV output
### L4: `format_csv(tickets: List[Ticket], options: CSVFormatOptions) -> str`
  - Format list of tickets as CSV with header row
  - Support --fields to select specific columns
  - Support --delimiter for custom delimiter (default: comma)
  - Handle special characters (quotes, commas, newlines) with proper escaping
  - Support --no-header to omit header row
  - Flatten complex fields (tags as semicolon-separated)
  - Include all standard fields by default
  - Support custom column names via --column-names

### L5: Spec
```python
@dataclass
class CSVFormatOptions:
    fields: Optional[List[str]] = None  # specific fields to include
    delimiter: str = ","
    quote_char: str = '"'
    include_header: bool = True
    column_names: Optional[Dict[str, str]] = None  # field -> column name mapping
    flatten_arrays: str = ";"  # delimiter for array fields like tags

def format_csv(tickets: List[Ticket], options: CSVFormatOptions = CSVFormatOptions()) -> str:
    """
    # default CSV output
    Input: List of 2 tickets
    Output:
    id,title,repo,category,severity,status,description,tags,created,updated
    C1,CORS Bug,owner/repo,code,critical,open,"The API returns *",security;api,2026-03-15T10:00:00Z,2026-03-15T10:00:00Z
    C2,Auth issue,owner/repo,security,high,in_progress,"Auth bypass in login",security,2026-03-14T09:00:00Z,2026-03-16T11:00:00Z
    
    # with --fields
    Input: options.fields=["id", "title", "status"]
    Output:
    id,title,status
    C1,CORS Bug,open
    C2,Auth issue,in_progress
    
    # custom delimiter (tab-separated)
    Input: options.delimiter="\t"
    Output:
    id	title	repo	category	...
    C1	CORS Bug	owner/repo	code	...
    
    # with special characters (quoting)
    Input: Ticket with title='Bug: "quotes", commas, and
    lines'
    Output:
    id,title,...
    C1,"Bug: ""quotes"", commas, and
    lines",...
    
    # flatten array fields
    Input: Ticket with tags=["security", "api", "cors"]
    Output (tags column):
    security;api;cors
    
    # custom column names
    Input: options.column_names={"id": "Ticket ID", "title": "Summary", "status": "State"}
    Output:
    Ticket ID,Summary,State,...
    C1,CORS Bug,open,...
    
    # --no-header
    Input: options.include_header=False
    Output:
    C1,CORS Bug,owner/repo,code,critical,open,...
    C2,Auth issue,owner/repo,security,high,in_progress,...
    
    # empty list
    Input: Empty list
    Output: (header only)
    id,title,repo,category,severity,status,description,tags,created,updated
    
    # all standard fields (default order)
    Default fields: id, title, repo, category, severity, status, description, 
                    tags, file_refs, fix, created, updated
    """
```

### L6: Test
```python
test_format_csv_default()
test_format_csv_with_fields()
test_format_csv_custom_delimiter()
test_format_csv_tab_separated()
test_format_csv_quotes_escaping()
test_format_csv_comma_in_value()
test_format_csv_newline_in_value()
test_format_csv_flatten_tags()
test_format_csv_flatten_file_refs()
test_format_csv_custom_column_names()
test_format_csv_no_header()
test_format_csv_empty_list()
test_format_csv_all_fields()
test_format_csv_unicode_handling()
test_format_csv_empty_optional_fields()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | CLI | Management Commands | config command | `cli_config()` |
| 2 | CLI | Management Commands | stats command | `cli_stats()` |
| 3 | CLI | Management Commands | validate command | `cli_validate()` |
| 4 | CLI | Management Commands | doctor command | `cli_doctor()` |
| 5 | CLI | Management Commands | trash command | `cli_trash()` |
| 6 | CLI | Bulk Operations | Bulk create CLI | `cli_bulk_create()` |
| 7 | CLI | Bulk Operations | Bulk update CLI | `cli_bulk_update()` |
| 8 | CLI | Bulk Operations | Bulk delete CLI | `cli_bulk_delete()` |
| 9 | CLI | Bulk Operations | Export CLI | `cli_export()` |
| 10 | CLI | Bulk Operations | Import CLI | `cli_import()` |
| 11 | CLI | Output Formats | Markdown output | `format_markdown()` |
| 12 | CLI | Output Formats | CSV output | `format_csv()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union, Tuple
from datetime import datetime

# Re-use from agent1 breakdown
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

# Configuration Management
class ConfigManager(Protocol):
    def load(self) -> Dict[str, Any]: ...
    def get(self, key: str) -> Optional[Any]: ...
    def set(self, key: str, value: Any, global_scope: bool = False) -> None: ...
    def validate(self) -> List[str]: ...  # return list of validation errors

# Storage Protocol (extended)
class TicketStore(Protocol):
    def get(self, ticket_id: str) -> Optional[Ticket]: ...
    def save(self, ticket: Ticket) -> None: ...
    def delete(self, ticket_id: str, force: bool = False) -> bool: ...
    def move_to_trash(self, ticket_id: str) -> bool: ...
    def restore_from_trash(self, ticket_id: str) -> bool: ...
    def list_trash(self) -> List[Ticket]: ...
    def clean_trash(self, older_than_days: int) -> int: ...
    def list_ids(self) -> set: ...
    def list_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Ticket]: ...
    def bulk_create(self, tickets: List[Ticket]) -> Tuple[int, List[Tuple[int, str, str]]]: ...
    def bulk_update(self, filters: Dict[str, Any], updates: Dict[str, Any], limit: Optional[int] = None) -> int: ...
    def bulk_delete(self, filters: Dict[str, Any], force: bool = False, limit: Optional[int] = None) -> int: ...

# Validation
@dataclass
class ValidationError:
    file_path: str
    line: Optional[int]
    field: Optional[str]
    message: str
    severity: str  # "error", "warning"
    fixable: bool

# Diagnostics
@dataclass
class DiagnosticResult:
    check_name: str
    status: str  # "pass", "fail", "warning"
    message: str
    suggestion: Optional[str]
    auto_fixable: bool

# Import/Export
@dataclass
class BulkCreateResult:
    total: int
    created: int
    failed: int
    errors: List[Tuple[int, str, str]]
    created_ids: List[str]

@dataclass
class ImportResult:
    total: int
    imported: int
    skipped: int
    errors: List[Tuple[int, str, str]]
    id_mappings: Dict[str, str]
```

---

## Implementation Notes

### Progress Indicators
- Use tqdm or rich library for progress bars
- Progress to stderr, data to stdout
- Support --silent to disable progress

### Error Handling
- All functions return exit codes for CLI integration
- Structured errors with actionable messages
- Partial success allowed for bulk operations

### File Formats
- JSON: Array of objects or line-delimited (JSONL)
- CSV: RFC 4180 compliant with proper quoting
- Markdown: YAML frontmatter + GitHub-flavored markdown
- tar.gz: Preserve directory structure

### Performance
- Stream large imports/exports to avoid memory issues
- Batch database operations for bulk commands
- Use generators where possible for large datasets

### Safety
- Bulk delete requires --all flag
- Destructive operations require confirmation (or --yes)
- Dry-run mode available for preview
