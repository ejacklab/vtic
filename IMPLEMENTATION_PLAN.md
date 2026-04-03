# Implementation Plan: Core Ticket Lifecycle CRUD

> **Branch:** `feat/ticket-lifecycle-core`
> **Scope:** P0 features from FEATURES.md §1 (Ticket Lifecycle), §2.1 (BM25 Search), §3.1 (Markdown Files), §4.1 (REST Endpoints), §5.1 (Core CLI Commands), §6.1 (Config Files)

---

## 1. Assessment: What's Already Done

The codebase is **substantially complete** for P0 Core Ticket Lifecycle CRUD. All core modules exist with 99 passing tests.

### Implemented (✅)

| Module | File | Status |
|--------|------|--------|
| **Enums** | `src/vtic/models.py` L15-52 | ✅ Severity, Status, Category as StrEnum |
| **Data Models** | `src/vtic/models.py` L92-495 | ✅ Ticket, TicketCreate, TicketUpdate, TicketResponse, SearchFilters, SearchRequest, SearchResult, SearchResponse, PaginatedResponse, ErrorResponse, HealthResponse, StatsResponse |
| **Constants** | `src/vtic/constants.py` | ✅ CATEGORY_PREFIXES, VALID_STATUSES, TERMINAL_STATUSES, STATUS_METADATA |
| **Errors** | `src/vtic/errors.py` | ✅ VticError hierarchy (6 error classes) |
| **Config** | `src/vtic/config.py` | ✅ VticConfig, TicketsConfig, ServerConfig, SearchConfig, load_config(), from_toml(), from_env(), resolve_config_path() |
| **Storage** | `src/vtic/storage.py` | ✅ TicketStore with create(), create_ticket(), get(), list(), count(), update(), delete(), next_id(), markdown read/write, YAML frontmatter, atomic writes, file locking |
| **Search** | `src/vtic/search.py` | ✅ TicketSearch with BM25 via rank_bm25, build_index(), search(), filters, pagination, highlights, TF fallback |
| **API** | `src/vtic/api.py` | ✅ FastAPI app: POST/GET/PATCH/DELETE /tickets, POST /search, GET /health, error handlers |
| **CLI** | `src/vtic/cli/main.py` | ✅ Typer CLI: init, create, get, list, search, update, delete, serve |
| **Utils** | `src/vtic/utils.py` | ✅ slugify, utc_now, isoformat_z, parse_repo, normalize_tags, ticket_path |
| **Tests** | `tests/` | ✅ 99 tests: models (21), config (9), storage (26), search (13), api (7), integration (1), cli stubs |

### P0 Feature Checklist (from FEATURES.md)

| # | Feature | Spec Ref | Status |
|---|---------|----------|--------|
| 1 | CLI ticket creation | §1.1 | ✅ `vtic create` with all flags |
| 2 | API ticket creation | §1.1 | ✅ `POST /tickets` |
| 3 | Auto-generated IDs | §1.1 | ✅ `next_id()` in TicketStore |
| 4 | ID slug from title | §1.1 | ✅ `slugify()` in utils |
| 5 | Timestamp auto-fill | §1.1 | ✅ `utc_now()` on create/update |
| 6 | Required field validation | §1.1 | ✅ Pydantic validators + Field constraints |
| 7 | Get by ID | §1.2 | ✅ CLI `get` + API `GET /tickets/:id` |
| 8 | Output formats | §1.2 | ⚠️ Partial — table only, missing `--format json` |
| 9 | Field-level updates | §1.3 | ✅ CLI `update` + API `PATCH` |
| 10 | API PATCH endpoint | §1.3 | ✅ `PATCH /tickets/:id` |
| 11 | Auto timestamp on update | §1.3 | ✅ `utc_now()` in `store.update()` |
| 12 | Soft delete | §1.4 | ❌ Missing — `delete()` is hard-only |
| 13 | Hard delete | §1.4 | ✅ `store.delete()` + CLI `--yes` |
| 14 | Confirmation prompt | §1.4 | ✅ `typer.confirm()` in CLI |
| 15 | Built-in statuses | §1.5 | ✅ 6 statuses in Status enum |
| 16 | BM25 full-text search | §2.1 | ✅ `TicketSearch` with rank_bm25 |
| 17 | Markdown file storage | §3.1 | ✅ YAML frontmatter + body sections |
| 18 | Hierarchical dirs | §3.1 | ✅ `{owner}/{repo}/{category}/{id}-{slug}.md` |
| 19 | Atomic writes | §3.1 | ✅ temp file + os.replace in update |
| 20 | REST CRUD endpoints | §4.1 | ✅ POST/GET/PATCH/DELETE /tickets |
| 21 | REST search endpoint | §4.1 | ✅ `POST /search` |
| 22 | REST health check | §4.1 | ✅ `GET /health` |
| 23 | JSON responses | §4.2 | ✅ ErrorResponse, TicketResponse |
| 24 | HTTP status codes | §4.3 | ✅ 201, 404, 422, 204 |
| 25 | Offset pagination | §4.4 | ✅ limit/offset on list + search |
| 26 | CLI init | §5.1 | ✅ `vtic init` |
| 27 | CLI list | §5.1 | ✅ `vtic list` with filters |
| 28 | CLI search | §5.1 | ✅ `vtic search` with filters |
| 29 | CLI serve | §5.1 | ✅ `vtic serve` |
| 30 | Project config | §6.1 | ✅ `vtic.toml` loading |
| 31 | Global config | §6.1 | ✅ `~/.config/vtic/config.toml` |
| 32 | Config precedence | §6.1 | ✅ TOML → env overrides |
| 33 | Config validation | §6.1 | ✅ Pydantic models validate |
| 34 | Env overrides | §6.2 | ✅ `VTIC_TICKETS_DIR` etc. |
| 35 | Sensible defaults | §6.3 | ✅ Zero-config works |
| 36 | CI-friendly CLI | §9.3 | ✅ Exit codes, error messages |

---

## 2. Gaps Identified (P0 Only)

### Gap 1: Soft Delete (§1.4 — P0)

**Spec:** "Move deleted tickets to `.trash/` or mark as `status: deleted`" and "Hard delete option with `--force` flag"

**Current:** `TicketStore.delete()` (storage.py L143-150) permanently unlinks the file. CLI `delete` (cli/main.py L258-273) has `--yes` but no `--force` flag. No `.trash/` directory support.

**What's needed:**
- Add `move_to_trash()` method to `TicketStore`
- Add `--force` flag to CLI `delete` command
- Default behavior: move to `.trash/{owner}/{repo}/{category}/{id}-{slug}.md`
- `--force`: permanent delete (current behavior)
- Trash directory: `{tickets_dir}/.trash/`
- Ensure `list()` and `search()` skip `.trash/` contents

### Gap 2: CLI Output Formats (§1.2 + §5.4 — P0)

**Spec:** "Support `--format json|markdown|yaml|table` for CLI output" (P0 for json+table)

**Current:** CLI `get` only outputs Rich panels. `list`/`search` only output Rich tables. No `--format` option.

**What's needed:**
- Add `--format` option to `get`, `list`, and `search` CLI commands
- `table` (default): current Rich output
- `json`: `TicketResponse.model_dump_json()` for get, list of `TicketResponse` for list/search
- No yaml/csv needed at P0 (P1/P2)

### Gap 3: CLI `--format json` for Automation (§5.4 + §9.3 — P0)

**Spec:** "CI-friendly CLI: Exit codes, JSON output for automation" + "JSON output: `--format json` for machine-readable output"

**This is the same as Gap 2** but specifically calling out the CI/automation use case. JSON output must go to stdout, errors to stderr.

### Gap 4: API Delete Response (§4.1 vs OpenAPI spec)

**Current:** `DELETE /tickets/:id` returns 204 No Content. OpenAPI stage2-crud.yaml says it should return 200 with the deleted TicketResponse body.

**Decision needed:** The current 204 pattern is more RESTful. Keep 204 unless there's a reason to change. **Recommendation: keep 204.**

### Gap 5: Sorting on List (§2.5 — P0)

**Spec:** "Sort by field" with `--sort` flag, default sort by relevance when query provided.

**Current:** `TicketStore.list()` sorts by ticket ID only. No `--sort` option on CLI `list`. API `GET /tickets` has no sort parameter.

**What's needed:**
- Add `--sort` option to CLI `list` command (e.g., `--sort severity`, `--sort -created`)
- Add `sort_by` parameter to `TicketStore.list()`
- Supported fields: severity, status, created_at, updated_at, title
- Prefix `-` for descending

---

## 3. Breakdown-agent1.md Feature Coverage

All 13 features from breakdown-agent1.md are **fully implemented**:

| # | Feature | Function | Status |
|---|---------|----------|--------|
| 1 | CLI ticket creation | `store.create_ticket()` | ✅ |
| 2 | Auto-generated IDs | `store.next_id()` | ✅ |
| 3 | Timestamp auto-fill | `utc_now()` in create_ticket/update | ✅ |
| 4 | Required field validation | Pydantic validators | ✅ |
| 5 | Get by ID | `store.get()` | ✅ |
| 6 | CLI get command | CLI `get` | ✅ (needs --format) |
| 7 | Field-level updates | `store.update()` | ✅ |
| 8 | CLI update command | CLI `update` | ✅ |
| 9 | Delete ticket | `store.delete()` | ✅ (needs soft delete) |
| 10 | CLI delete command | CLI `delete` | ✅ (needs --force) |
| 11 | Built-in status: open | Status.OPEN enum | ✅ |
| 12 | Statuses: in_progress, blocked | StatusMetadata dict | ✅ |
| 13 | Statuses: fixed, wont_fix, closed | is_terminal property | ✅ |

---

## 4. Improvements Needed

### 4.1 Category Enum Has `***` Value

**File:** `src/vtic/models.py` L39

```python
AUTH="***"   # Bug — should be AUTH="auth"
```

This is clearly a placeholder/scrub error from the spec (DATA_MODELS.md L37 has the same `***`). Must be fixed to `AUTH = "auth"`.

### 4.2 `search.py` Has Truncated Lines

**File:** `src/vtic/search.py` L15, L46

Line 15 shows: `_TOKEN_SPLIT_RE=re.com...]+")`
Line 46 shows: `self._tokenized_documents=[self....et)) for ticket in corpus]`

These appear truncated in the file listing but may be display artifacts. **Verify** the actual file content is correct:
```python
_TOKEN_SPLIT_RE = re.compile(r"[^a-zA-Z0-9]+")
self._tokenized_documents = [self._tokenize(self._get_document(ticket)) for ticket in corpus]
```

### 4.3 Missing `--owner` Flag on CLI `create`

**File:** `src/vtic/cli/main.py` L70-102

The CLI `create` command doesn't expose `--owner` as a flag. It auto-derives owner from `--repo`. The API allows explicit owner. The CLI should too for cases where the owner differs from the repo owner.

### 4.4 Missing `--status` on CLI `create`

**File:** `src/vtic/cli/main.py` L70-102

The `create` command hardcodes `status=Status.OPEN` (L93). The spec and API allow setting status on creation. Should add `--status` option.

### 4.5 CLI `update` Doesn't Validate Status Transitions

**File:** `src/vtic/cli/main.py` L197-238

The breakdown spec (Feature 11) says v0.1 allows all transitions. But the constants define `TERMINAL_STATUSES` and `STATUS_METADATA`. While no enforcement is needed at P0, the update should at least validate the status value is in `VALID_STATUSES` (currently handled by Pydantic).

### 4.6 Missing `reindex` CLI Command

**File:** `src/vtic/cli/main.py`

The spec lists `vtic reindex` as P0 (§5.1, §3.2). The BM25 index is built on-demand in `TicketSearch._ensure_index()`, so it's implicitly rebuilt. But the explicit `reindex` command is missing. For BM25-only mode this is low priority since the index rebuilds automatically, but it should exist for consistency.

### 4.7 `pyproject.toml` Missing `tomli` / `pyyaml` Dependencies

**File:** `pyproject.toml`

The code imports `yaml` (PyYAML) and `tomllib` (stdlib in 3.11+). PyYAML is used but not listed in dependencies. This works because it's likely installed transitively, but should be explicit:
```toml
dependencies = [
    "pydantic>=2.0",
    "typer>=0.9",
    "rich>=13.0",
    "rank-bm25>=0.2",
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
    "pyyaml>=6.0",  # Missing
]
```

---

## 5. Implementation Order

Work items ordered by dependency and priority:

```
Phase 1 — Bug Fixes (no dependencies)
  ├─ [1] Fix AUTH="***" → AUTH="auth" in models.py
  ├─ [2] Verify/fix truncated lines in search.py
  └─ [3] Add pyyaml to pyproject.toml dependencies

Phase 2 — Soft Delete (depends on nothing, self-contained)
  ├─ [4] Add TicketStore.move_to_trash() method
  ├─ [5] Add TicketStore.restore_from_trash() method (P1 prep)
  ├─ [6] Modify TicketStore.delete() to default to soft delete
  ├─ [7] Update TicketStore.list() to skip .trash/ directory
  ├─ [8] Update TicketStore._find_ticket_path() to NOT search .trash/
  ├─ [9] Add --force flag to CLI delete command
  └─ [10] Tests for soft delete, hard delete, trash isolation

Phase 3 — CLI Output Formats (depends on nothing)
  ├─ [11] Add --format option to CLI get command (table|json)
  ├─ [12] Add --format option to CLI list command (table|json)
  ├─ [13] Add --format option to CLI search command (table|json)
  └─ [14] Tests for JSON output format on all commands

Phase 4 — CLI Missing Flags (depends on nothing)
  ├─ [15] Add --owner flag to CLI create command
  ├─ [16] Add --status flag to CLI create command
  └─ [17] Tests for new create flags

Phase 5 — List Sorting (depends on nothing)
  ├─ [18] Add sort_by parameter to TicketStore.list()
  ├─ [19] Add --sort option to CLI list command
  └─ [20] Tests for sorted list output

Phase 6 — Reindex Command (low priority, nice-to-have)
  └─ [21] Add CLI reindex command (no-op for BM25, placeholder for semantic)
```

---

## 6. File Changes

### Phase 1: Bug Fixes

| File | Change |
|------|--------|
| `src/vtic/models.py` L39 | Change `AUTH="***"` to `AUTH = "auth"` |
| `src/vtic/search.py` L15, L46 | Verify/fix truncated regex and list comprehension |
| `pyproject.toml` L18 | Add `"pyyaml>=6.0"` to dependencies |

### Phase 2: Soft Delete

| File | Change |
|------|--------|
| `src/vtic/storage.py` | Add `move_to_trash(self, ticket_id: str) -> Path` method |
| `src/vtic/storage.py` | Add `restore_from_trash(self, ticket_id: str) -> Ticket` method |
| `src/vtic/storage.py` | Modify `delete()` — add `force=False` param, default to soft delete |
| `src/vtic/storage.py` | Update `list()` — exclude `.trash/` from rglob scan |
| `src/vtic/storage.py` | Update `_find_ticket_path()` — exclude `.trash/` from scan |
| `src/vtic/cli/main.py` | Add `--force` flag to `delete` command |
| `tests/test_storage.py` | Add tests: soft delete, force delete, trash path, list skips trash |

### Phase 3: CLI Output Formats

| File | Change |
|------|--------|
| `src/vtic/cli/main.py` | Add `--format` option (table|json) to `get` command |
| `src/vtic/cli/main.py` | Add `--format` option (table|json) to `list_tickets` command |
| `src/vtic/cli/main.py` | Add `--format` option (table|json) to `search` command |
| `src/vtic/cli/main.py` | Add `_format_ticket_json()` helper for JSON output |
| `src/vtic/cli/main.py` | Add `_format_list_json()` helper for list JSON output |
| `tests/test_cli.py` | Add tests: get --format json, list --format json, search --format json |

### Phase 4: Missing CLI Flags

| File | Change |
|------|--------|
| `src/vtic/cli/main.py` | Add `--owner` option to `create` command (default: auto from repo) |
| `src/vtic/cli/main.py` | Add `--status` option to `create` command (default: open) |
| `tests/test_cli.py` | Add tests: create --owner, create --status |

### Phase 5: List Sorting

| File | Change |
|------|--------|
| `src/vtic/storage.py` | Add `sort_by: str | None = None` param to `list()` |
| `src/vtic/storage.py` | Implement sort key mapping (severity order, status order, dates, title) |
| `src/vtic/cli/main.py` | Add `--sort` option to `list_tickets` command |
| `tests/test_storage.py` | Add tests: list sorted by severity, status, created_at, title |

### Phase 6: Reindex

| File | Change |
|------|--------|
| `src/vtic/cli/main.py` | Add `reindex` command (rebuilds BM25 index) |
| `tests/test_cli.py` | Add test: reindex command exists and succeeds |

---

## 7. Test Plan

### New Tests Required

```
tests/test_storage.py:
  test_soft_delete_moves_file_to_trash()
  test_soft_delete_creates_trash_directory()
  test_force_delete_permanently_removes()
  test_restore_from_trash()
  test_list_excludes_trash_directory()
  test_find_ticket_excludes_trash_directory()
  test_soft_delete_preserves_file_content()
  test_trash_directory_structure()

tests/test_cli.py:
  test_get_format_json_outputs_valid_json()
  test_get_format_table_outputs_rich_panel()
  test_list_format_json_outputs_array()
  test_search_format_json_outputs_results()
  test_create_with_owner_flag()
  test_create_with_status_flag()
  test_delete_without_force_does_soft_delete()
  test_delete_with_force_does_hard_delete()
  test_delete_confirmation_prompt()
  test_list_sort_by_severity()
  test_list_sort_by_created_at_desc()
  test_list_sort_by_title()

tests/test_integration.py:
  test_full_lifecycle_with_soft_delete()
  test_json_output_roundtrip()  # create → get --format json → parse → verify
```

### Existing Tests to Update

| Test | Change |
|------|--------|
| `test_delete_removes_file` | Update to use `force=True` after soft delete becomes default |
| `test_delete_not_found_raises` | May need adjustment for soft delete default |
| `test_full_lifecycle` | Update delete invocation to use `--force --yes` |

---

## 8. Acceptance Criteria

The Core Ticket Lifecycle CRUD use case is complete when:

1. **All 99 existing tests still pass** — no regressions
2. **Soft delete works** — `vtic delete --id C1` moves to `.trash/`, file no longer appears in list/search/get
3. **Hard delete works** — `vtic delete --id C1 --force` permanently removes file
4. **JSON output works** — `vtic get C1 --format json` outputs valid JSON to stdout
5. **List JSON works** — `vtic list --format json` outputs JSON array to stdout
6. **Search JSON works** — `vtic search "query" --format json` outputs JSON with results
7. **CLI create has all flags** — `--owner` and `--status` available on create
8. **List sorting works** — `vtic list --sort severity` returns sorted results
9. **Bug fixes applied** — AUTH enum is `"auth"`, pyyaml is in dependencies
10. **Test coverage** — All new features have corresponding tests, total tests ≥ 120

### Verification Commands

```bash
# Run full test suite
python -m pytest tests/ -v

# Manual CLI smoke test
vtic init --dir /tmp/vtic-test
vtic create --repo test/test --title "Test ticket" --severity critical
vtic get C1 --format json
vtic list --format json
vtic search "test" --format json
vtic delete --id C1            # soft delete
vtic list                     # C1 should NOT appear
vtic delete --id C1 --force    # would fail (already trashed) or force-purge trash

# API smoke test
vtic serve --dir /tmp/vtic-test &
curl -X POST http://localhost:8900/tickets -H "Content-Type: application/json" -d '{"title":"API Test","repo":"test/test"}'
curl http://localhost:8900/tickets
curl http://localhost:8900/tickets/C2
curl -X PATCH http://localhost:8900/tickets/C2 -H "Content-Type: application/json" -d '{"status":"fixed"}'
curl -X DELETE http://localhost:8900/tickets/C2
curl http://localhost:8900/health
```

---

## 9. Next Steps for 2am Scaffold Job

The scaffold job should implement in this order:

1. **Fix the 3 bugs** (AUTH enum, search.py truncation, pyyaml dep) — 5 min
2. **Implement soft delete** (storage.py + cli/main.py) — 30 min
3. **Add `--format json` to get/list/search** — 20 min
4. **Add `--owner` and `--status` to create** — 10 min
5. **Add `--sort` to list** — 15 min
6. **Write all new tests** — 30 min
7. **Run full suite, fix any regressions** — 10 min
8. **Commit all changes** — 5 min

**Estimated total: ~2 hours of focused Codex work**

The scaffold job should use `codex --full-auto exec` with specific prompts for each phase, committing after each phase to maintain clean git history.
