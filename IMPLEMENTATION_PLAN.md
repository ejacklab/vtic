# vtic Implementation Plan: Core Ticket Lifecycle CRUD

> Generated: 2026-04-22 01:00 UTC
> Branch: feat/ticket-lifecycle-core
> Scope: CLI-based ticket CRUD with markdown file storage and BM25 search.
> Status: **IMPLEMENTED** — all modules present, 176 tests passing.

---

## 1. Project Structure

```
vtic/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── vtic/
│       ├── __init__.py
│       ├── models.py          # Pydantic models, enums, validation
│       ├── config.py          # TOML config loading, env overrides
│       ├── errors.py          # Custom exception hierarchy
│       ├── constants.py       # CATEGORY_PREFIXES, VALID_STATUSES, etc.
│       ├── utils.py           # slugify, utc_now, parse_repo, ticket_path
│       ├── storage.py         # TicketStore — markdown CRUD
│       ├── search.py          # BM25 keyword search (built-in)
│       ├── api.py             # FastAPI HTTP endpoints
│       └── cli/
│           ├── __init__.py
│           └── main.py        # Typer CLI commands
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_storage.py
    ├── test_search.py
    ├── test_cli.py
    ├── test_api.py
    └── test_integration.py
```

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "vtic"
version = "0.1.0"
description = "Lightweight, local-first ticket system with vector search."
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.9",
    "rich>=13.0",
    "fastapi>=0.100",
    "uvicorn[standard]>=0.20",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
]

[project.scripts]
vtic = "vtic.cli.main:app"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
addopts = "-ra"
```

---

## 2. File List

| File | Description |
|------|-------------|
| `src/vtic/__init__.py` | Package exports: `__version__`, key models |
| `src/vtic/models.py` | Enums (`Severity`, `Status`, `Category`), `Ticket`, `TicketCreate`, `TicketUpdate`, `TicketResponse`, `SearchFilters`, `SearchRequest`, `SearchResult`, `SearchResponse`, `ErrorDetail`, `ErrorResponse`, `PaginatedResponse`, `HealthResponse` |
| `src/vtic/config.py` | `VticConfig`, `TicketsConfig`, `ServerConfig`, `SearchConfig`, `SharedConfig`. TOML loading via `tomllib`. Env var overrides (`VTIC_TICKETS_DIR`, etc.). Singleton via `load_config()`. |
| `src/vtic/errors.py` | `VticError` base + subclasses: `TicketNotFoundError`, `TicketAlreadyExistsError`, `ValidationError`, `ConfigError`, `TicketWriteError`, `TicketReadError`, `TicketDeleteError`, `ConflictError` |
| `src/vtic/constants.py` | `CATEGORY_PREFIXES` dict, `VALID_STATUSES`, `TERMINAL_STATUSES`, `STATUS_METADATA`, default config paths |
| `src/vtic/utils.py` | `slugify()`, `utc_now()`, `isoformat_z()`, `normalize_tags()`, `parse_repo()`, `ticket_path()` |
| `src/vtic/storage.py` | `TicketStore` class — markdown file CRUD: `create()`, `get()`, `update()`, `delete()`, `restore()`, `list()`, `exists()`. YAML frontmatter parse/write. Atomic file writes (`tempfile` + rename). File locking via `fcntl`. Soft-delete to `.trash/`. |
| `src/vtic/search.py` | `TicketSearch` class with built-in `_BuiltinBM25` (Okapi-style). `index_ticket()`, `remove_ticket()`, `search()`, `rebuild()`. Tokenizer, scoring, result ranking. Caches corpus metadata by mtime. |
| `src/vtic/api.py` | FastAPI app factory `create_app()`. Endpoints: `POST /tickets`, `GET /tickets/{id}`, `PATCH /tickets/{id}`, `DELETE /tickets/{id}`, `GET /tickets`, `POST /search`, `GET /health`. Consistent JSON envelope, validation error handling. |
| `src/vtic/cli/main.py` | Typer app. Commands: `init`, `create`, `get`, `list`, `update`, `delete`, `restore`, `search`, `serve`, `reindex`. Rich table/JSON output. `--format json\|table`. |

---

## 3. Implementation Order

The codebase was built in the following dependency order:

1. **`constants.py`** — static lookup tables, no dependencies.
2. **`errors.py`** — exception hierarchy, no dependencies.
3. **`utils.py`** — helper functions (slugify, time, tags), no dependencies.
4. **`models.py`** — Pydantic models and enums. Depends on `constants.py` and `utils.py`.
5. **`config.py`** — TOML config loader. Depends on `models.py`, `constants.py`, `errors.py`.
6. **`storage.py`** — `TicketStore`. Depends on `models.py`, `errors.py`, `constants.py`, `utils.py`.
7. **`search.py`** — `TicketSearch` with BM25. Depends on `storage.py`, `models.py`, `errors.py`.
8. **`api.py`** — FastAPI app. Depends on `storage.py`, `search.py`, `models.py`, `config.py`, `errors.py`, `utils.py`.
9. **`cli/main.py`** — Typer CLI. Depends on `storage.py`, `search.py`, `models.py`, `config.py`, `errors.py`, `utils.py`.

---

## 4. Data Models

### 4.1 Enums

| Enum | Values |
|------|--------|
| `Severity` | `critical`, `high`, `medium`, `low` |
| `Status` | `open`, `in_progress`, `blocked`, `fixed`, `wont_fix`, `closed` |
| `Category` | `security`, `auth`, `code_quality`, `performance`, `frontend`, `testing`, `documentation`, `infrastructure`, `configuration`, `api`, `data`, `ui`, `dependencies`, `build`, `other` |

### 4.2 Category ID Prefix Mapping

```python
CATEGORY_PREFIXES = {
    Category.CODE_QUALITY: "C",
    Category.SECURITY: "S",
    Category.AUTH: "A",
    Category.INFRASTRUCTURE: "I",
    Category.DOCUMENTATION: "D",
    Category.TESTING: "T",
    Category.PERFORMANCE: "P",
    Category.FRONTEND: "F",
    Category.CONFIGURATION: "N",
    Category.API: "X",
    Category.DATA: "M",
    Category.UI: "U",
    Category.DEPENDENCIES: "Y",
    Category.BUILD: "B",
    Category.OTHER: "O",
}
```

### 4.3 Ticket (Core Model)

```python
class Ticket(VticBaseModel):
    id: str                    # e.g. "C1", "S2" — pattern r"^[A-Z]\d+$"
    title: str                 # 1-200 chars, required
    description: str | None    # up to 50000 chars
    fix: str | None            # up to 20000 chars
    repo: str                  # "owner/repo" format, required
    owner: str | None
    category: Category         # default CODE_QUALITY
    severity: Severity         # default MEDIUM
    status: Status             # default OPEN
    file: str | None           # path:line or path:start-end
    tags: list[str]            # max 50, normalized lowercase
    created_at: datetime
    updated_at: datetime
    slug: str                  # URL-safe, derived from title
```

### 4.4 TicketCreate

Input model for creation. `id`, `slug`, `created_at`, `updated_at` are auto-generated. `title` and `repo` are required.

### 4.5 TicketUpdate

Partial update model. All fields optional. `extra="forbid"` to reject unknown fields. `updated_at` refreshed automatically by storage layer.

### 4.6 TicketResponse

API response wrapper with all fields as plain strings/enums plus computed `is_terminal`, `filename`, `filepath`.

---

## 5. Markdown File Format

Tickets are stored as markdown files with YAML frontmatter:

```markdown
---
id: S1
title: CORS Wildcard in Production
repo: ejacklab/open-dsearch
category: security
severity: critical
status: open
owner: ejacklab
file: backend/api-gateway/main.py:27-32
created_at: 2026-03-16T10:00:00Z
updated_at: 2026-03-16T10:00:00Z
tags:
  - cors
  - security
---

<!-- DESCRIPTION -->
All FastAPI services use allow_origins=['*'] which enables CSRF attacks.

<!-- FIX -->
Use ALLOWED_ORIGINS from environment variable.
```

### File Layout on Disk

```
tickets/
└── {owner}/
    └── {repo}/
        └── {category}/
            └── {ticket_id}-{slug}.md
```

Example: `tickets/ejacklab/open-dsearch/security/S1-cors-wildcard.md`

### Storage Guarantees

- **Atomic writes**: content written to temp file, then `os.replace()` to target.
- **File locking**: advisory `fcntl.LOCK_EX` on `.vtic.lock` during writes.
- **Path traversal prevention**: `ticket_path()` validates no `..` segments.
- **Soft delete**: moves to `.trash/{id}-{slug}.md` by default.
- **Hard delete**: `--force` permanently removes file.

---

## 6. CLI Commands

| Command | Description |
|---------|-------------|
| `vtic init [dir]` | Initialize ticket storage directory |
| `vtic create --repo OWNER/REPO --title "..." [--category X] [--severity Y] [--status Z] [--description "..."] [--fix "..."] [--file PATH] [--tags a,b,c]` | Create a new ticket |
| `vtic get <id> [--format table\|json]` | Display a single ticket |
| `vtic list [--repo GLOB] [--severity S] [--status S] [--category C] [--owner O] [--tags a,b] [--has-fix] [--sort field] [--limit N] [--offset N]` | List tickets with filters |
| `vtic update <id> [--title ...] [--description ...] [--fix ...] [--severity ...] [--status ...] [--category ...] [--owner ...] [--file ...] [--tags ...]` | Update ticket fields |
| `vtic delete <id> [--yes] [--force]` | Soft-delete (or permanent with `--force`) |
| `vtic restore <id>` | Restore a soft-deleted ticket |
| `vtic search "query" [--severity ...] [--status ...] [--repo ...] [--limit N] [--offset N]` | BM25 keyword search with filters |
| `vtic reindex` | Rebuild BM25 index from all markdown files |
| `vtic serve [--host HOST] [--port PORT]` | Start FastAPI HTTP server |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Not found |
| 2 | Validation / cancelled |

---

## 7. BM25 Search

### Architecture

`TicketSearch` maintains an in-process BM25 index over ticket markdown files. It does **not** require an external database.

### Built-in BM25 (`_BuiltinBM25`)

Implements Okapi BM25:
- `k1 = 1.5`
- `b = 0.75`
- IDF: `log((N - df + 0.5) / (df + 0.5) + 1)`
- Score: `idf * (freq * (k1 + 1)) / (freq + k1 * (1 - b + b * |D| / avgdl))`

### Tokenization

- Lowercase
- Split on non-alphanumeric (regex `[a-z0-9]+`)
- Filters out pure numbers for relevance

### Caching

- `TicketSearch` caches `_CorpusCacheEntry` per ticket, keyed by file mtime.
- On `search()`, only changed files are re-parsed and re-tokenized.
- `rebuild()` clears cache and re-indexes everything.

### Search Flow

1. Parse query into tokens.
2. Collect all `.md` files under `base_dir` (excluding `.trash/`).
3. Load/cache each ticket via `TicketStore.get()`.
4. Build BM25 corpus from `ticket.search_text` (title + description + fix + tags).
5. Score documents against query tokens.
6. Apply structured filters (`severity`, `status`, `repo` glob, `category`, `owner`, `tags`, `has_fix`, date ranges).
7. Sort by BM25 score descending (or by field if specified in API).
8. Return paginated `SearchResponse`.

### API Search Endpoint

`POST /search`
```json
{
  "query": "auth security issues",
  "filters": {
    "severity": ["critical"],
    "status": ["open"]
  },
  "topk": 10,
  "offset": 0,
  "semantic": false
}
```

Response:
```json
{
  "results": [...],
  "total": 42,
  "query": "auth security issues",
  "semantic": false,
  "limit": 10,
  "offset": 0,
  "has_more": true,
  "took_ms": 12
}
```

---

## 8. Test Plan

| Test Module | Coverage |
|-------------|----------|
| `test_models.py` | Enum behavior, `Ticket` validation, `TicketCreate`, `TicketUpdate`, `SearchFilters`, `SearchRequest`, tag normalization, slug generation, timestamp validation |
| `test_config.py` | TOML loading, env overrides, defaults, validation errors, singleton behavior |
| `test_storage.py` | `TicketStore.create()`, `get()`, `update()`, `delete()`, `restore()`, `list()`, atomic writes, file locking, soft-delete, path traversal protection, concurrent ID generation, corrupt file handling, sorting, date filters |
| `test_search.py` | BM25 scoring, tokenization, query parsing, filtering integration, empty corpus, cache hits/misses, rebuild |
| `test_cli.py` | CLI command dispatch, argument parsing, output formatting (table/JSON), exit codes, error messages, `init`, `create`, `get`, `list`, `update`, `delete`, `search`, `serve` |
| `test_api.py` | FastAPI endpoints, HTTP status codes, request/response models, validation errors, pagination, search endpoint, health check |
| `test_integration.py` | End-to-end workflows: create → get → update → search → delete, CLI + API parity |

**Current test status**: 176 tests, all passing.

---

## 9. Next Steps for the 2am Scaffold Job

**Pre-flight result**: Core Ticket Lifecycle CRUD is **fully implemented** and tested.

| Check | Status |
|-------|--------|
| Source files present | ✅ All 10 modules in `src/vtic/` |
| pyproject.toml configured | ✅ Dependencies, entry points, pytest config |
| Tests passing | ✅ 176/176 |
| CLI commands working | ✅ `init`, `create`, `get`, `list`, `update`, `delete`, `restore`, `search`, `serve`, `reindex` |
| API endpoints working | ✅ `POST /tickets`, `GET /tickets/{id}`, `PATCH /tickets/{id}`, `DELETE /tickets/{id}`, `GET /tickets`, `POST /search`, `GET /health` |
| BM25 search working | ✅ Built-in implementation, no external deps |
| Markdown format stable | ✅ YAML frontmatter + description/fix sections |

### Recommended 2am Job Actions

1. **Skip scaffolding** — the codebase is already scaffolded and functional.
2. **Run a full test suite** as verification:
   ```bash
   python -m pytest tests/ -v
   ```
3. **If any tests fail**, run the fix workflow (see `REVIEW_ROUND1.md`, `REVIEW_ROUND2.md` for prior patterns).
4. **If all tests pass**, the 2am job should move to the next milestone:
   - **Milestone 2**: Semantic search integration (OpenAI / local embeddings)
   - **Milestone 3**: Webhook subscriptions
   - **Milestone 4**: Multi-repo configuration profiles
   - **Milestone 5**: Export / import (JSON, CSV)

5. **Optional polish** before moving on:
   - Add `__init__.py` to `tests/` (currently missing — harmless but non-standard).
   - Verify `src/vtic.egg-info/` is in `.gitignore` (it's generated by editable installs).
   - Review `REVIEW_ROUND2.md` for any remaining deferred items.

### Git State

- Branch: `feat/ticket-lifecycle-core`
- Latest commit: `413c6d4 merge: ticket-lifecycle-core feature into main`
- Working tree: clean

No scaffold work needed. The 2am job can proceed directly to **feature enhancement** or **merge to main / tag v0.1.0**.
