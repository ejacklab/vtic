# Breakdown Agent 4 - Configuration & Security Features

## Feature 1: Configuration - Sensible Defaults

### L1: Configuration
### L2: Defaults & Profiles
### L3: Sensible defaults

### L4: Implementation Units

#### Unit 4.1: `load_config(config_path: Path | None = None) -> Config`
- Load from project `./vtic.toml` if exists
- Fall back to `~/.config/vtic/config.toml` if exists
- Fall back to hardcoded defaults
- Merge with env vars (VTIC_* overrides)

#### Unit 4.2: `Config` dataclass
```python
@dataclass
class Config:
    tickets_dir: Path = Path("./tickets")
    index_dir: Path = Path("./.vtic")
    search_bm25_enabled: bool = True
    search_semantic_enabled: bool = False
    embedding_provider: str = "none"  # "none" | "openai" | "local"
    embedding_model: str = ""
    openai_api_key: str = ""
    default_severity: str = "medium"
    default_status: str = "open"
    api_host: str = "127.0.0.1"
    api_port: int = 3000
```

#### Unit 4.3: `get_default_config() -> Config`
- Return hardcoded defaults
- No file I/O, pure function
- Used as base for merging

#### Unit 4.4: `merge_config(base: Config, override: dict) -> Config`
- Deep merge override dict into base config
- Handle None values (don't override with None)
- Return new Config instance

#### Unit 4.5: `load_env_overrides() -> dict`
- Scan `os.environ` for `VTIC_*` variables
- Convert `VTIC_TICKETS_DIR` → `tickets_dir`
- Parse values (strings, bools, ints)
- Return dict for merging

### L5: Specs

#### Unit 4.1: `load_config`
```
Input: config_path=None (no config file exists)
Output: Config(
  tickets_dir=Path("./tickets"),
  index_dir=Path("./.vtic"),
  search_bm25_enabled=True,
  search_semantic_enabled=False,
  embedding_provider="none",
  ...
)

Input: config_path=Path("/project/vtic.toml") (file exists)
Output: Config with values from file merged with defaults
```

#### Unit 4.2: `Config`
```
Input: Config()  # No args
Output: Config with all default values set
```

#### Unit 4.3: `get_default_config`
```
Input: (no parameters)
Output: Config instance with all hardcoded defaults
```

#### Unit 4.4: `merge_config`
```
Input: 
  base=Config(tickets_dir=Path("./tickets"), search_bm25_enabled=True)
  override={"tickets_dir": "/custom/tickets", "search_semantic_enabled": True}
Output: Config(
  tickets_dir=Path("/custom/tickets"),
  search_bm25_enabled=True,
  search_semantic_enabled=True
)
```

#### Unit 4.5: `load_env_overrides`
```
Input: os.environ = {"VTIC_TICKETS_DIR": "/env/tickets", "VTIC_API_PORT": "8080"}
Output: {"tickets_dir": "/env/tickets", "api_port": 8080}
```

### L6: Tests

#### Unit 4.1
- `test_load_config_no_file_returns_defaults()` - No config file exists, returns defaults
- `test_load_config_project_file_overrides_global()` - Project config takes precedence
- `test_load_config_env_var_overrides_file()` - Env vars override file values
- `test_load_config_missing_optional_fields_use_defaults()` - Partial config fills in missing fields

#### Unit 4.2
- `test_config_dataclass_defaults()` - All fields have correct default values
- `test_config_immutable()` - Config is frozen/immutable

#### Unit 4.3
- `test_get_default_config_returns_valid_config()` - Returns Config with all defaults
- `test_get_default_config_no_side_effects()` - Multiple calls return same values

#### Unit 4.4
- `test_merge_config_override_replaces_base()` - Override values replace base
- `test_merge_config_none_does_not_override()` - None values in override are ignored
- `test_merge_config_deep_merge()` - Nested dicts merge correctly

#### Unit 4.5
- `test_load_env_overrides_extracts_vtic_vars()` - Only VTIC_* vars extracted
- `test_load_env_overrides_converts_types()` - Strings converted to bools/ints
- `test_load_env_overrides_snake_case_conversion()` - VTIC_API_KEY → api_key

---

## Feature 2: Security - Input Validation

### L1: Security
### L2: Data Security
### L3: Input validation

### L4: Implementation Units

#### Unit 4.6: `validate_ticket_id(id: str) -> str`
- Validate ticket ID format (e.g., "C1", "H5", "M12")
- Pattern: `[A-Z][0-9]+`
- Raise `ValidationError` if invalid
- Return normalized ID

#### Unit 4.7: `validate_ticket_fields(fields: dict) -> dict`
- Validate required fields (title, repo)
- Validate field types (string, int, enum)
- Validate field lengths (title max 200 chars)
- Validate enum values (severity: low|medium|high|critical)
- Sanitize string fields (trim whitespace, remove control chars)
- Return validated and sanitized dict

#### Unit 4.8: `validate_search_query(query: str) -> str`
- Enforce max query length (1000 chars)
- Remove/sanitize dangerous characters
- Prevent injection patterns (even though no SQL)
- Return sanitized query

#### Unit 4.9: `validate_filter_value(field: str, value: Any) -> Any`
- Validate filter field is allowed (severity, status, repo, etc.)
- Validate filter value type matches field
- Convert string values to appropriate types
- Return validated value

#### Unit 4.10: `ValidationError` exception class
```python
class ValidationError(Exception):
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")
```

### L5: Specs

#### Unit 4.6: `validate_ticket_id`
```
Input: "C1"
Output: "C1"

Input: "invalid"
Output: raises ValidationError(field="id", message="Invalid ID format. Expected: LETTER+NUMBER (e.g., C1, H5)")

Input: "c1"
Output: raises ValidationError (lowercase not allowed)
```

#### Unit 4.7: `validate_ticket_fields`
```
Input: {"title": "Bug in auth", "repo": "ejacklab/vtic"}
Output: {"title": "Bug in auth", "repo": "ejacklab/vtic"}  # Passes through

Input: {"title": "   Bug   ", "repo": "vtic"}
Output: {"title": "Bug", "repo": "vtic"}  # Trimmed

Input: {"title": "", "repo": "vtic"}
Output: raises ValidationError(field="title", message="Required field cannot be empty")

Input: {"title": "Bug", "severity": "urgent"}
Output: raises ValidationError(field="severity", message="Invalid value. Expected: low|medium|high|critical")
```

#### Unit 4.8: `validate_search_query`
```
Input: "CORS wildcard issue"
Output: "CORS wildcard issue"

Input: "a" * 1001
Output: raises ValidationError(field="query", message="Query exceeds maximum length of 1000 characters")

Input: "test\x00null"
Output: "testnull"  # Null byte removed
```

#### Unit 4.9: `validate_filter_value`
```
Input: ("severity", "high")
Output: "high"

Input: ("severity", 123)
Output: raises ValidationError(field="severity", message="Expected string value")

Input: ("created_after", "2024-01-01")
Output: datetime.date(2024, 1, 1)  # Converted to date
```

#### Unit 4.10: `ValidationError`
```
Input: ValidationError("title", "Cannot be empty", "")
Output: Exception with message "title: Cannot be empty"
        .field = "title"
        .message = "Cannot be empty"
        .value = ""
```

### L6: Tests

#### Unit 4.6
- `test_validate_ticket_id_valid()` - Valid IDs pass
- `test_validate_ticket_id_invalid_format()` - Invalid format raises error
- `test_validate_ticket_id_lowercase_rejected()` - Lowercase rejected

#### Unit 4.7
- `test_validate_ticket_fields_required_present()` - Valid fields pass
- `test_validate_ticket_fields_missing_required()` - Missing title raises error
- `test_validate_ticket_fields_invalid_severity()` - Invalid enum raises error
- `test_validate_ticket_fields_trims_whitespace()` - Whitespace trimmed
- `test_validate_ticket_fields_removes_control_chars()` - Control chars removed
- `test_validate_ticket_fields_enforces_max_length()` - Long title raises error

#### Unit 4.8
- `test_validate_search_query_normal_passes()` - Normal query passes
- `test_validate_search_query_max_length_enforced()` - Long query raises error
- `test_validate_search_query_removes_null_bytes()` - Null bytes removed
- `test_validate_search_query_removes_control_chars()` - Control chars removed

#### Unit 4.9
- `test_validate_filter_value_valid_string()` - Valid string filter passes
- `test_validate_filter_value_converts_date()` - Date strings converted
- `test_validate_filter_value_invalid_field()` - Unknown field raises error
- `test_validate_filter_value_type_mismatch()` - Wrong type raises error

#### Unit 4.10
- `test_validation_error_attributes()` - All attributes accessible
- `test_validation_error_message_format()` - Message formatted correctly

---

## Dependency Graph (Configuration + Security)

```
[4.3: get_default_config] ──┐
                             ├──> [4.4: merge_config] ──> [4.1: load_config]
[4.5: load_env_overrides] ──┘                                      │
                                                                   │
[4.2: Config dataclass] <──────────────────────────────────────────┘

[4.10: ValidationError] <──┬─── [4.6: validate_ticket_id]
                           ├─── [4.7: validate_ticket_fields]
                           ├─── [4.8: validate_search_query]
                           └─── [4.9: validate_filter_value]
```

---

## Size Estimates (This Agent)

| Unit | Description | Size |
|------|-------------|------|
| 4.1 | load_config | tiny |
| 4.2 | Config dataclass | tiny |
| 4.3 | get_default_config | tiny |
| 4.4 | merge_config | tiny |
| 4.5 | load_env_overrides | small (env parsing) |
| 4.6 | validate_ticket_id | tiny |
| 4.7 | validate_ticket_fields | small (multiple fields) |
| 4.8 | validate_search_query | tiny |
| 4.9 | validate_filter_value | small (type conversions) |
| 4.10 | ValidationError | tiny |

**Total: 4 tiny + 3 small = ~1 day of work**

---

# MASTER TASK LIST

## Overview

**Total Implementation Units:** 43  
**Breakdown Sources:** Agent 1 (Lifecycle), Agent 2 (Search/Storage), Agent 3 (API/CLI), Agent 4 (Config/Security)

## Build Order (Dependencies First)

### Phase 1: Foundation (Core Data & Config) - MUST BE FIRST

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 1 | Config dataclass | Core configuration structure | tiny | None | Config |
| 2 | get_default_config | Hardcoded defaults | tiny | #1 | Config |
| 3 | ValidationError | Base validation exception | tiny | None | Security |
| 4 | merge_config | Config merging logic | tiny | #1 | Config |
| 5 | load_env_overrides | Parse VTIC_* env vars | small | None | Config |
| 6 | load_config | Full config loading chain | tiny | #1, #2, #4, #5 | Config |
| 7 | Ticket dataclass | Core ticket structure (from Agent 1) | tiny | None | Lifecycle |

**Phase 1 Total:** 3 tiny + 2 small = ~0.5 day

---

### Phase 2: Storage Layer - REQUIRED FOR LIFECYCLE

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 8 | TicketPathResolver | Path ↔ ticket ID conversion | small | #7 | Storage |
| 9 | serialize_ticket_to_markdown | Ticket → markdown | small | #7 | Storage |
| 10 | parse_markdown_to_ticket | Markdown → Ticket | small | #7 | Storage |
| 11 | AtomicFileWriter | Atomic file writes | small | None | Storage |
| 12 | GitCompatibleStorage | Git-friendly file ops | tiny | #11 | Storage |
| 13 | TicketStore (Protocol) | Storage interface (from Agent 1) | tiny | #7, #8 | Storage |

**Phase 2 Total:** 1 tiny + 5 small = ~1 day

---

### Phase 3: Validation Layer - SECURITY FIRST

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 14 | validate_ticket_id | ID format validation | tiny | #3, #7 | Security |
| 15 | validate_ticket_fields | Field-level validation | small | #3, #7 | Security |
| 16 | validate_search_query | Query sanitization | tiny | #3 | Security |
| 17 | validate_filter_value | Filter validation | small | #3 | Security |
| 18 | validate_ticket_required_fields | Required fields (from Agent 1) | small | #3, #7 | Lifecycle |
| 19 | validate_status_transition | Status workflow | tiny | #7 | Lifecycle |

**Phase 3 Total:** 4 tiny + 3 small = ~0.75 day

---

### Phase 4: Ticket Lifecycle - CORE BUSINESS LOGIC

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 20 | generate_ticket_id | Unique ID generation | small | #7, #14 | Lifecycle |
| 21 | auto_fill_timestamps | Timestamp management | tiny | #7 | Lifecycle |
| 22 | get_ticket_by_id | Fetch single ticket | tiny | #7, #13 | Lifecycle |
| 23 | create_ticket_from_cli | CLI create command | small | #7, #13, #18, #20, #21 | Lifecycle |
| 24 | update_ticket_fields | Partial field updates | small | #7, #13, #19 | Lifecycle |
| 25 | delete_ticket | Delete (soft/hard) | small | #7, #13 | Lifecycle |
| 26 | cli_get_ticket | CLI get command | small | #13, #22 | Lifecycle |
| 27 | cli_update_ticket | CLI update command | small | #13, #24 | Lifecycle |
| 28 | cli_delete_ticket | CLI delete command | small | #13, #25 | Lifecycle |
| 29 | get_status_metadata | Status display info | tiny | #7 | Lifecycle |
| 30 | is_terminal_status | Terminal status check | tiny | #7 | Lifecycle |

**Phase 4 Total:** 4 tiny + 7 small = ~1.5 days

---

### Phase 5: Search & Index - QUERY ENGINE

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 31 | TicketIndex | In-process Zvec index | small | #6 | Storage |
| 32 | IndexRebuilder.rebuild | Full index rebuild | small | #31 | Storage |
| 33 | build_filter_expression | Filter dict → expression | tiny | #17 | Search |
| 34 | apply_equality_filters | Filter execution | small | #31, #33 | Search |
| 35 | bm25_search | BM25 full-text search | small | #31 | Search |
| 36 | SortSpec + parse_sort_spec | Sort specification | tiny | None | Search |
| 37 | sort_tickets_by_field | Field-based sorting | tiny | #36 | Search |
| 38 | sort_by_relevance | Score-based sorting | tiny | None | Search |
| 39 | search_with_relevance_sort | Search with sort | tiny | #35, #38 | Search |
| 40 | PaginatedResult + paginate_results | Pagination | tiny | #7 | Search |
| 41 | parse_repo_glob | Repo glob patterns | tiny | None | Search |
| 42 | filter_by_repo_glob | Glob filter execution | tiny | #31, #41 | Search |

**Phase 5 Total:** 9 tiny + 4 small = ~1 day

---

### Phase 6: API Layer - HTTP INTERFACE

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 43 | json_response | JSON serialization helper | tiny | None | API |
| 44 | ApiError + error envelope | Error response structure | tiny | #43, #3 | API |
| 45 | handle_health_check | GET /health endpoint | tiny | #13, #31, #44 | API |
| 46 | handle_search | POST /search endpoint | medium | #31, #35, #39, #44 | API |

**Phase 6 Total:** 3 tiny + 1 medium = ~0.5 day

---

### Phase 7: CLI Layer - USER INTERFACE

| # | Unit | Description | Size | Dependencies | Category |
|---|------|-------------|------|--------------|----------|
| 47 | configure_color_output | Color mode setup | tiny | None | CLI |
| 48 | format_status + format_severity | Color formatting | tiny | #47 | CLI |
| 49 | format_output + print_output | Output formatting | small | #47 | CLI |
| 50 | setup_logging | Debug mode logging | small | None | CLI |
| 51 | Cli struct + run_command | Command dispatcher | medium | #6, #23, #26, #27, #28, all search units | CLI |

**Phase 7 Total:** 3 tiny + 1 small + 1 medium = ~1 day

---

## Summary by Category

| Category | Units | Tiny | Small | Medium | Est. Time |
|----------|-------|------|-------|--------|-----------|
| Configuration | 6 | 4 | 2 | 0 | 0.5 day |
| Security | 4 | 1 | 3 | 0 | 0.5 day |
| Storage | 6 | 1 | 5 | 0 | 1 day |
| Lifecycle | 11 | 5 | 6 | 0 | 1.5 days |
| Search | 12 | 9 | 3 | 0 | 1 day |
| API | 4 | 3 | 0 | 1 | 0.5 day |
| CLI | 5 | 3 | 1 | 1 | 1 day |
| **TOTAL** | **48** | **26** | **20** | **2** | **6 days** |

---

## Critical Path

```
Config (#1-6) → Storage (#8-13) → Validation (#14-19) → Lifecycle (#20-30)
                                     ↓
                                 Search (#31-42)
                                     ↓
                                  API (#43-46)
                                     ↓
                                  CLI (#47-51)
```

**Minimum Viable Product (v0.1):**
- Must complete: Phases 1-5 (Config, Storage, Validation, Lifecycle, Search)
- Then: Phase 6 OR Phase 7 (API or CLI, not both)
- Total for MVP: ~4.5 days

**Full v0.1 (API + CLI):** ~6 days

---

## Parallelization Opportunities

**Can be built in parallel:**
- Phase 3 (Validation) while Phase 2 (Storage) is in progress
- Phase 5 (Search) units 36-42 while unit 31-35 are in progress
- Phase 7 (CLI) while Phase 6 (API) is in progress

**MUST be sequential:**
- Phase 1 → Phase 2 (Storage needs Config)
- Phase 2 → Phase 4 (Lifecycle needs Storage)
- Phase 3 → Phase 4 (Lifecycle needs Validation)
- Phase 5 → Phase 6 (API needs Search)

---

## Risk Areas (Medium Complexity)

| Unit | Why Medium? | Mitigation |
|------|-------------|------------|
| #46 handle_search | Integrates validation, search, pagination, error handling | Build search first, then wrap in API |
| #51 run_command | Orchestrates ALL commands, error handling, exit codes | Build all commands first, then dispatcher |

---

## Notes

1. **Config is Foundation:** Everything depends on Config, build it first
2. **Validation is Security-Critical:** Block Lifecycle until Validation done
3. **Search is Independent:** Can be built in parallel with Lifecycle once Storage ready
4. **API and CLI are Parallel:** Once Search is done, API and CLI can be built simultaneously
5. **Test as You Go:** Each unit has test cases defined - write tests alongside implementation

---

**Generated by:** Breakdown Agent 4  
**Based on:** breakdown-agent1.md, breakdown-agent2.md, breakdown-agent3.md, breakdown-agent4.md  
**Total Features:** 43 Core features across 13 categories
