# IMPLEMENTATION PLAN: Core Ticket Lifecycle CRUD

## 1. Scope and normalization decisions

This plan implements the v0.1 core described across `README.md`, `FEATURES.md`, `DATA_MODELS.md`, and `breakdown-agent1.md`, with the following normalization choices where the specs differ:

- Storage format uses markdown files with YAML frontmatter because `FEATURES.md` specifies "Markdown with YAML frontmatter for metadata".
- Ticket filenames use `tickets/{owner}/{repo}/{category}/{ticket_id}-{slug}.md` because the user request and `Ticket.filename` in `DATA_MODELS.md` both require `id + slug`.
- v0.1 search is BM25-only using `rank-bm25`; semantic search and Zvec integration stay scaffolded behind future-facing modules.
- CRUD scope covers CLI-first implementation, with API package scaffolded but not required to be feature-complete in the first coding pass.
- Status workflow validation remains permissive in v0.1, matching `breakdown-agent1.md` Features 11-13.

## 2. Project structure

Full proposed layout under `src/vtic/` plus repo-root files needed to ship the package:

```text
.
├── pyproject.toml
├── README.md
├── FEATURES.md
├── DATA_MODELS.md
├── breakdown-agent1.md
├── IMPLEMENTATION_PLAN.md
├── src/
│   └── vtic/
│       ├── __init__.py
│       ├── models.py
│       ├── config.py
│       ├── errors.py
│       ├── store.py
│       ├── index.py
│       ├── search.py
│       ├── ticket.py
│       ├── constants.py
│       ├── utils.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py
│       │   ├── deps.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       ├── tickets.py
│       │       └── search.py
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── formatting.py
│       │   └── main.py
│       └── embeddings/
│           ├── __init__.py
│           ├── base.py
│           ├── openai.py
│           └── local.py
└── tests/
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_store.py
    ├── test_ticket_service.py
    ├── test_cli.py
    └── test_search.py
```

### File responsibilities

| File | Contains |
|---|---|
| `pyproject.toml` | Package metadata, dependencies, CLI entry point, pytest config |
| `src/vtic/__init__.py` | Version constant, top-level exports for `Ticket`, `TicketService`, `VticConfig` |
| `src/vtic/models.py` | All enums, Pydantic v2 models, response/search models from `DATA_MODELS.md` |
| `src/vtic/config.py` | `TicketsConfig`, `ServerConfig`, `SearchConfig`, `VticConfig`, `load_config()` |
| `src/vtic/errors.py` | `VticError` hierarchy and error-to-response helpers |
| `src/vtic/constants.py` | `CATEGORY_PREFIXES`, terminal status sets, status metadata, defaults |
| `src/vtic/utils.py` | Slugify, UTC timestamp helpers, repo parsing, file-safe helpers |
| `src/vtic/store.py` | Markdown/YAML persistence layer for ticket files on disk |
| `src/vtic/ticket.py` | CRUD orchestration, ID generation, field-level updates, delete semantics |
| `src/vtic/search.py` | BM25 indexing/search service for v0.1 |
| `src/vtic/index.py` | Future compatibility façade; in v0.1 wraps BM25/local search backend |
| `src/vtic/cli/main.py` | Typer app and command wiring |
| `src/vtic/cli/formatting.py` | Rich table rendering, JSON/markdown serialization helpers |
| `src/vtic/api/app.py` | FastAPI app factory scaffold |
| `src/vtic/api/deps.py` | DI helpers for config/store/service/search |
| `src/vtic/api/routes/tickets.py` | CRUD API endpoint scaffold |
| `src/vtic/api/routes/search.py` | Search API endpoint scaffold |
| `src/vtic/embeddings/base.py` | Abstract embedding provider interface |
| `src/vtic/embeddings/openai.py` | Placeholder OpenAI provider for post-v0.1 semantic search |
| `src/vtic/embeddings/local.py` | Placeholder local provider for post-v0.1 semantic search |
| `tests/*` | Unit and CLI integration tests grouped by module |

This follows the module map from `DATA_MODELS.md` section 5, with one additive file: `src/vtic/cli/formatting.py`. That file keeps `main.py` small and testable without changing the published command surface.

## 3. File list with descriptions

### `src/vtic/__init__.py`

- Purpose: package entry surface and version export.
- Key contents:
  - `__version__ = "0.1.0"`
  - Re-exports: `Ticket`, `TicketCreate`, `TicketUpdate`, `TicketService`, `VticConfig`
- Specs implemented:
  - Packaging support implied by `README.md` install and `FEATURES.md` CLI/API expectations.

### `src/vtic/constants.py`

- Purpose: central immutable domain constants.
- Key contents:
  - `CATEGORY_PREFIXES`
  - `VALID_STATUSES`
  - `TERMINAL_STATUSES`
  - `STATUS_METADATA`
  - output-format constants
  - default config path names (`vtic.toml`, `.vtic/`)
- Specs implemented:
  - `DATA_MODELS.md` enum/prefix map
  - `breakdown-agent1.md` Features 2, 11, 12, 13

### `src/vtic/models.py`

- Purpose: all Pydantic v2 models and enums in one contract module.
- Key contents:
  - `Severity`, `Status`, `Category`
  - `VticBaseModel`
  - `Ticket`
  - `TicketCreate`
  - `TicketUpdate`
  - `TicketResponse`
  - `SearchFilters`, `SearchRequest`, `SearchResult`, `SearchResponse`
  - `PaginatedResponse[T]`
  - `ErrorDetail`, `ErrorResponse`, `HealthResponse`, `CountByField`, `StatsResponse`
- Specs implemented:
  - `DATA_MODELS.md` sections 1-2, response models, search models
  - `FEATURES.md` output formats, filtering, pagination envelope groundwork

### `src/vtic/errors.py`

- Purpose: strongly typed domain errors for CLI/API/service/storage.
- Key contents:
  - `VticError`
  - `TicketNotFoundError`
  - `ValidationError`
  - `ConfigError`
  - `SearchIndexError`
  - `EmbeddingError`
  - `TicketAlreadyExistsError`
  - `TicketWriteError`
  - `TicketReadError`
  - `TicketDeleteError`
- Specs implemented:
  - `DATA_MODELS.md` error catalog section 4
  - `FEATURES.md` structured CLI/API error handling

### `src/vtic/config.py`

- Purpose: config loading from defaults, TOML, and environment variables.
- Key contents:
  - `TicketsConfig`
  - `ServerConfig`
  - `SearchConfig`
  - `VticConfig`
  - `load_config(explicit_path: Path | None = None) -> VticConfig`
  - `resolve_config_path() -> Path | None`
- Specs implemented:
  - `README.md` configuration section
  - `DATA_MODELS.md` config schema section 3

### `src/vtic/utils.py`

- Purpose: reusable pure helpers.
- Key contents:
  - `slugify(text: str) -> str`
  - `utc_now() -> datetime`
  - `isoformat_z(dt: datetime) -> str`
  - `parse_repo(repo: str) -> tuple[str, str]`
  - `normalize_tags(tags: list[str]) -> list[str]`
  - `coerce_optional_markdown(text: str | None) -> str | None`
  - `ticket_path(root: Path, ticket: Ticket) -> Path`
- Specs implemented:
  - `DATA_MODELS.md` slug/timestamp conventions
  - `breakdown-agent1.md` Features 2-4 helper behavior

### `src/vtic/store.py`

- Purpose: markdown storage backend.
- Key contents:
  - `class TicketStore`
  - `init_storage()`
  - `save(ticket: Ticket) -> Path`
  - `get(ticket_id: str) -> Ticket | None`
  - `get_by_slug(slug: str) -> Ticket | None`
  - `list(...) -> list[Ticket]`
  - `exists(ticket_id: str) -> bool`
  - `delete(ticket_id: str, force: bool = False) -> bool`
  - `move_to_trash(ticket_id: str) -> bool`
  - `iter_tickets() -> Iterator[Ticket]`
  - private markdown helpers: `_serialize_ticket()`, `_parse_ticket_file()`, `_atomic_write()`
- Specs implemented:
  - `FEATURES.md` storage 3.1
  - `README.md` ticket-on-disk layout
  - `breakdown-agent1.md` Features 5, 9

### `src/vtic/ticket.py`

- Purpose: domain service for ticket lifecycle orchestration.
- Key contents:
  - `class TicketService`
  - `create(data: TicketCreate, custom_id: str | None = None) -> Ticket`
  - `get(ticket_id: str) -> Ticket | None`
  - `list(filters..., limit, offset, sort_by, sort_order) -> list[Ticket]`
  - `update(ticket_id: str, updates: TicketUpdate) -> Ticket`
  - `delete(ticket_id: str, force: bool = False) -> bool`
  - `generate_ticket_id(category: Category, existing_ids: set[str]) -> str`
  - `validate_status_transition(current: Status | None, new: Status) -> tuple[bool, str | None]`
  - `get_status_metadata(status: str) -> StatusMetadata | None`
- Specs implemented:
  - `FEATURES.md` section 1 ticket lifecycle
  - `breakdown-agent1.md` Features 1-13

### `src/vtic/search.py`

- Purpose: BM25-only search engine for v0.1.
- Key contents:
  - `class SearchEngine`
  - `build_index(tickets: Iterable[Ticket]) -> None`
  - `index_ticket(ticket: Ticket) -> None`
  - `remove_ticket(ticket_id: str) -> None`
  - `search(request: SearchRequest) -> SearchResponse`
  - `_tokenize(text: str) -> list[str]`
  - `_apply_filters(tickets, filters) -> list[Ticket]`
  - `_rank_bm25(query, tickets) -> list[SearchResult]`
- Specs implemented:
  - `FEATURES.md` sections 2.1, 2.4, 2.5
  - user requirement to avoid Zvec for v0.1

### `src/vtic/index.py`

- Purpose: compatibility wrapper preserving the future module map.
- Key contents:
  - `class ZvecIndex`
  - In v0.1 this delegates to `SearchEngine` and exposes `add`, `remove`, `search_bm25`, `rebuild`
  - semantic methods raise `SearchIndexError` with "not enabled in v0.1"
- Specs implemented:
  - `DATA_MODELS.md` module map section 5
  - future path for `README.md`/`FEATURES.md` Zvec integration

### `src/vtic/cli/__init__.py`

- Purpose: CLI package marker and app export.
- Key contents:
  - `from .main import app`
- Specs implemented:
  - package entry point for `vtic`

### `src/vtic/cli/formatting.py`

- Purpose: output adapters for `table`, `json`, `markdown`.
- Key contents:
  - `render_ticket_table(ticket: Ticket) -> Table`
  - `render_ticket_list_table(tickets: list[Ticket]) -> Table`
  - `render_ticket_markdown(ticket: Ticket) -> str`
  - `render_json(data: BaseModel | list[BaseModel] | dict) -> str`
- Specs implemented:
  - `FEATURES.md` output format support
  - `breakdown-agent1.md` Feature 6

### `src/vtic/cli/main.py`

- Purpose: Typer command definitions and exit-code mapping.
- Key contents:
  - `app = typer.Typer(...)`
  - commands: `init`, `create`, `get`, `list`, `update`, `delete`, `search`
  - `main()` for console script support
- Specs implemented:
  - `FEATURES.md` section 5.1 core commands
  - user-requested CRUD command set

### `src/vtic/api/__init__.py`

- Purpose: API package marker.
- Key contents:
  - app factory export

### `src/vtic/api/app.py`

- Purpose: FastAPI app assembly scaffold.
- Key contents:
  - `create_app(config: VticConfig | None = None) -> FastAPI`
  - registers `/tickets` and `/search` routers
  - health endpoint scaffold
- Specs implemented:
  - `README.md` API server concept
  - `FEATURES.md` API section groundwork

### `src/vtic/api/deps.py`

- Purpose: share config/store/service/search instances.
- Key contents:
  - `get_config()`
  - `get_store()`
  - `get_ticket_service()`
  - `get_search_engine()`
- Specs implemented:
  - `DATA_MODELS.md` module map section 5

### `src/vtic/api/routes/tickets.py`

- Purpose: CRUD endpoint scaffold parallel to CLI service methods.
- Key contents:
  - `POST /tickets`
  - `GET /tickets/{ticket_id}`
  - `PATCH /tickets/{ticket_id}`
  - `DELETE /tickets/{ticket_id}`
  - `GET /tickets`
- Specs implemented:
  - `FEATURES.md` section 4.1

### `src/vtic/api/routes/search.py`

- Purpose: search endpoint scaffold.
- Key contents:
  - `POST /search`
- Specs implemented:
  - `FEATURES.md` section 4.1

### `src/vtic/embeddings/base.py`

- Purpose: future semantic-search abstraction.
- Key contents:
  - `class EmbeddingProvider(ABC)`
  - `embed(text: str) -> list[float]`
  - `embed_batch(texts: list[str]) -> list[list[float]]`
- Specs implemented:
  - `README.md` pluggable embeddings concept
  - `DATA_MODELS.md` module map section 5

### `src/vtic/embeddings/openai.py`

- Purpose: future OpenAI provider placeholder.
- Key contents:
  - `class OpenAIEmbeddingProvider(EmbeddingProvider)`
  - raises `EmbeddingError` if semantic search is disabled or dependency missing
- Specs implemented:
  - `README.md` embedding provider roadmap

### `src/vtic/embeddings/local.py`

- Purpose: future local provider placeholder.
- Key contents:
  - `class LocalEmbeddingProvider(EmbeddingProvider)`
- Specs implemented:
  - `README.md` local embedding roadmap

## 4. Implementation order

Build in dependency order so every later phase consumes stable interfaces instead of rewriting lower layers.

### Phase 1: Foundation

Build first because every other phase depends on validated models, error types, and config.

1. `pyproject.toml`
2. `src/vtic/__init__.py`
3. `src/vtic/constants.py`
4. `src/vtic/models.py`
5. `src/vtic/errors.py`
6. `src/vtic/config.py`
7. `src/vtic/utils.py`
8. `tests/test_models.py`
9. `tests/test_config.py`

Deliverables:

- Enums and Pydantic v2 models exactly matching `DATA_MODELS.md`
- category-prefix map and status metadata
- config resolution from defaults, TOML, env vars
- shared helpers for slugify/path/timestamps

### Phase 2: Storage

Build after Phase 1 because store serialization depends on `Ticket`, config, constants, and error types.

1. `src/vtic/store.py`
2. `tests/test_store.py`

Deliverables:

- initialize ticket root and `.vtic/` metadata directory
- markdown frontmatter serializer/parser
- atomic write via temp file + rename
- case-insensitive lookup by ID by scanning cached index or ticket tree
- soft delete to `.trash/` and hard delete

### Phase 3: Ticket service

Build after storage because service orchestrates create/get/update/delete through `TicketStore`.

1. `src/vtic/ticket.py`
2. `tests/test_ticket_service.py`

Deliverables:

- `TicketService.create/get/list/update/delete`
- category-based ID generation using lowest available gap
- update timestamp refresh
- field immutability rules
- list/filter/sort logic independent of search index

### Phase 4: CLI

Build after service so commands stay thin adapters over domain methods.

1. `src/vtic/cli/__init__.py`
2. `src/vtic/cli/formatting.py`
3. `src/vtic/cli/main.py`
4. `tests/test_cli.py`

Deliverables:

- `vtic init`
- `vtic create`
- `vtic get`
- `vtic list`
- `vtic update`
- `vtic delete`
- output format handling and exit-code mapping

### Phase 5: BM25 search

Build last because search needs stable ticket content and CRUD hooks.

1. `src/vtic/search.py`
2. `src/vtic/index.py`
3. `tests/test_search.py`
4. optional scaffolding:
   - `src/vtic/api/*`
   - `src/vtic/embeddings/*`

Deliverables:

- rank-bm25 indexing across title + description + tags + fix
- rebuild-on-start and incremental update hooks on create/update/delete
- CLI `search` command or service-internal search entry point
- semantic methods explicitly deferred but scaffolded

## 5. Data models

All enum values and model fields should be copied exactly from `DATA_MODELS.md`.

### Enums

#### `Severity`

- `critical`
- `high`
- `medium`
- `low`

#### `Status`

- `open`
- `in_progress`
- `blocked`
- `fixed`
- `wont_fix`
- `closed`

#### `Category`

- `security`
- `auth`
- `code_quality`
- `performance`
- `frontend`
- `testing`
- `documentation`
- `infrastructure`
- `configuration`
- `api`
- `data`
- `ui`
- `dependencies`
- `build`
- `other`

### `CATEGORY_PREFIXES`

Use the exact mapping from `DATA_MODELS.md`:

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

ID generation rules:

- Prefix comes from `CATEGORY_PREFIXES`.
- Sequence uses the lowest positive integer gap for that prefix.
- IDs are uppercase and match `^[A-Z]\d+$`.
- If a future unknown category ever appears outside enum validation, fallback prefix should be `"X"` at the service helper boundary.

### `Ticket`

Required fields:

- `id: str`
- `title: str`
- `repo: str`
- `created_at: datetime`
- `updated_at: datetime`
- `slug: str`

Optional/defaulted fields:

- `description: str | None = None`
- `fix: str | None = None`
- `owner: str | None = None`
- `category: Category = Category.CODE_QUALITY`
- `severity: Severity = Severity.MEDIUM`
- `status: Status = Status.OPEN`
- `file: str | None = None`
- `tags: list[str] = []`

Derived behaviors:

- `is_terminal`
- `filename`
- `filepath`
- `search_text`
- validators for ID, title, repo, tags, timestamps

### `TicketCreate`

Required:

- `title`
- `repo`

Optional:

- `description`
- `fix`
- `owner`
- `category`
- `severity`
- `status`
- `file`
- `tags`

Not accepted from callers in v0.1 create path:

- `slug`
- `created_at`
- `updated_at`

Service-only optional override:

- `custom_id: str | None` for import/migration path, not on normal CLI surface unless intentionally added later.

### `TicketUpdate`

All fields optional:

- `title`
- `description`
- `fix`
- `owner`
- `category`
- `severity`
- `status`
- `file`
- `tags`

Rules:

- `extra="forbid"`
- immutable fields remain outside update model: `id`, `repo`, `created_at`, `slug`
- `updated_at` is service-controlled

### `TicketResponse`

Expose:

- all `Ticket` fields serialized to strings where required
- computed fields: `is_terminal`, `filename`, `filepath`

Used by:

- CLI JSON output
- future API responses

## 6. Markdown file format

Use YAML frontmatter plus markdown body sections.

### On-disk path

```text
tickets/{owner}/{repo}/{category}/{ticket_id}-{slug}.md
```

Example:

```text
tickets/ejacklab/open-dsearch/security/S1-cors-wildcard-in-production.md
```

### Ticket markdown template

```markdown
---
id: S1
title: CORS Wildcard in Production
repo: ejacklab/open-dsearch
owner:
category: security
severity: critical
status: open
file: backend/api-gateway/main.py:27-32
tags:
  - cors
  - security
  - fastapi
created_at: 2026-03-16T10:00:00Z
updated_at: 2026-03-16T10:00:00Z
slug: cors-wildcard-in-production
---

# S1 - CORS Wildcard in Production

## Description

All FastAPI services use `allow_origins=["*"]` which enables cross-origin abuse and weakens CSRF protections in production.

## Fix

Use `ALLOWED_ORIGINS` from environment configuration and restrict allowed origins by deployment environment.
```

### Serialization rules

- Frontmatter is authoritative for metadata.
- Body header is duplicated for human readability, not parsing.
- `Description` and `Fix` sections are always emitted in this order.
- If `description` is empty, emit `## Description` followed by a blank line.
- If `fix` is empty, emit `## Fix` followed by a blank line.
- `tags` is always a YAML list, even when empty.
- timestamps are UTC and serialized as ISO 8601 with `Z`.
- `owner` and `file` serialize as YAML null/empty value if missing.

### Parsing rules

- Parse YAML frontmatter first.
- Parse body by `## Description` and `## Fix` headings.
- If body sections are missing, fall back to frontmatter plus blank strings and optionally raise validation warning later.
- Ignore extra markdown below known sections for v0.1, or append it to `fix` if that keeps round-trip stable.

### Example full ticket file

```markdown
---
id: C2
title: Duplicated auth helpers across services
repo: ejacklab/open-dsearch
owner: smoke01
category: code_quality
severity: high
status: in_progress
file: backend/auth/utils.py:1-120
tags:
  - auth
  - refactor
  - duplication
created_at: 2026-03-17T09:15:00Z
updated_at: 2026-03-18T14:40:00Z
slug: duplicated-auth-helpers-across-services
---

# C2 - Duplicated auth helpers across services

## Description

Multiple services maintain slightly different token parsing and claims validation helpers. This causes drift and inconsistent authorization behavior.

## Fix

Extract a shared auth utility module and update services to import it. Add regression tests around token parsing and role checks.
```

## 7. CLI commands

Use Typer with `Annotated[..., typer.Option(...)]` and Rich for human-readable output.

### Common output rules

- `table` is default for interactive human output.
- `json` returns machine-readable serialized Pydantic models.
- `markdown` returns the exact stored markdown representation for a single ticket.
- exit code `0` = success
- exit code `1` = not found / expected operational miss
- exit code `2` = validation or usage error
- exit code `3` = storage/config/internal failure

### `vtic init`

Typer signature:

```python
@app.command()
def init(
    tickets_dir: Path = typer.Argument(Path("./tickets")),
    config_path: Path | None = typer.Option(None, "--config"),
    force: bool = typer.Option(False, "--force", help="Create directories even if they already exist"),
) -> None:
    ...
```

Behavior:

- creates ticket root
- creates `.vtic/`
- creates `.trash/`
- optionally writes minimal `vtic.toml` if missing

Options:

- `tickets_dir: Path`, default `./tickets`
- `--config: Path | None`, default `None`
- `--force: bool`, default `False`

Exit codes:

- `0` initialized or already initialized
- `2` invalid path/config
- `3` filesystem failure

Output:

- `table`: not needed
- default human output: confirmation line
- `json`: optional future enhancement, not required for v0.1

### `vtic create`

Typer signature:

```python
@app.command()
def create(
    title: str = typer.Option(..., "--title"),
    repo: str = typer.Option(..., "--repo"),
    description: str | None = typer.Option(None, "--description"),
    fix: str | None = typer.Option(None, "--fix"),
    owner: str | None = typer.Option(None, "--owner"),
    category: Category = typer.Option(Category.CODE_QUALITY, "--category"),
    severity: Severity = typer.Option(Severity.MEDIUM, "--severity"),
    status: Status = typer.Option(Status.OPEN, "--status"),
    file: str | None = typer.Option(None, "--file"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    custom_id: str | None = typer.Option(None, "--id", help="Override ID for migration/import"),
    format: str = typer.Option("table", "--format"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Options and defaults:

- `--title str`, required
- `--repo str`, required
- `--description str | None`, default `None`
- `--fix str | None`, default `None`
- `--owner str | None`, default `None`
- `--category Category`, default `code_quality`
- `--severity Severity`, default `medium`
- `--status Status`, default `open`
- `--file str | None`, default `None`
- `--tag list[str]`, repeatable, default `[]`
- `--id str | None`, default `None`
- `--format str`, `table|json|markdown`, default `table`
- `--config Path | None`, default `None`

Exit codes:

- `0` created
- `2` validation failure
- `3` write/config failure

Output:

- `table`: Rich table with full ticket
- `json`: serialized `TicketResponse`
- `markdown`: exact serialized markdown

### `vtic get`

Typer signature:

```python
@app.command()
def get(
    ticket_id: str = typer.Argument(...),
    format: str = typer.Option("table", "--format"),
    raw: bool = typer.Option(False, "--raw"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Options and defaults:

- positional `ticket_id: str`
- `--format str`, `table|json|markdown`, default `table`
- `--raw bool`, default `False`
- `--config Path | None`, default `None`

Exit codes:

- `0` found
- `1` not found
- `2` invalid format / invalid ID
- `3` read/config failure

Output:

- `table`: Rich key-value table
- `json`: `TicketResponse`
- `markdown`: normalized markdown serialization
- `--raw`: raw file bytes decoded as text from disk, ignoring `--format`

### `vtic list`

Typer signature:

```python
@app.command("list")
def list_tickets(
    repo: list[str] | None = typer.Option(None, "--repo"),
    category: list[Category] | None = typer.Option(None, "--category"),
    severity: list[Severity] | None = typer.Option(None, "--severity"),
    status: list[Status] | None = typer.Option(None, "--status"),
    owner: str | None = typer.Option(None, "--owner"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    has_fix: bool | None = typer.Option(None, "--has-fix/--no-has-fix"),
    sort_by: str = typer.Option("updated_at", "--sort-by"),
    sort_order: str = typer.Option("desc", "--sort-order"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    offset: int = typer.Option(0, "--offset", min=0),
    format: str = typer.Option("table", "--format"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Options and defaults:

- `--repo list[str]`, repeatable, default `None`
- `--category list[Category]`, repeatable, default `None`
- `--severity list[Severity]`, repeatable, default `None`
- `--status list[Status]`, repeatable, default `None`
- `--owner str | None`, default `None`
- `--tag list[str]`, repeatable, default `None`
- `--has-fix/--no-has-fix`, tri-state, default `None`
- `--sort-by str`, `created_at|updated_at|severity|status|id`, default `updated_at`
- `--sort-order str`, `asc|desc`, default `desc`
- `--limit int`, default `50`
- `--offset int`, default `0`
- `--format str`, `table|json`, default `table`
- `--config Path | None`, default `None`

Exit codes:

- `0` success, including empty result
- `2` invalid filter/sort
- `3` read/config failure

Output:

- `table`: compact list with columns `id`, `title`, `repo`, `category`, `severity`, `status`, `updated_at`
- `json`: paginated list payload

### `vtic update`

Typer signature:

```python
@app.command()
def update(
    ticket_id: str = typer.Argument(...),
    title: str | None = typer.Option(None, "--title"),
    description: str | None = typer.Option(None, "--description"),
    fix: str | None = typer.Option(None, "--fix"),
    owner: str | None = typer.Option(None, "--owner"),
    category: Category | None = typer.Option(None, "--category"),
    severity: Severity | None = typer.Option(None, "--severity"),
    status: Status | None = typer.Option(None, "--status"),
    file: str | None = typer.Option(None, "--file"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    append_description: str | None = typer.Option(None, "--append-description"),
    format: str = typer.Option("table", "--format"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Options and defaults:

- positional `ticket_id`
- all updateable fields optional
- `--append-description str | None`, default `None`
- `--format str`, `table|json|markdown`, default `table`
- `--config Path | None`, default `None`

Rules:

- if no mutable fields are provided, command still updates nothing and should return current ticket; optionally keep `updated_at` unchanged unless explicit change occurs. This is the better v0.1 behavior even though `breakdown-agent1.md` suggests timestamp-only updates on empty update requests.
- `repo`, `id`, `created_at`, `slug` are immutable

Exit codes:

- `0` updated
- `1` not found
- `2` validation/immutable-field error
- `3` write/config failure

Output:

- `table`: full updated ticket
- `json`: serialized `TicketResponse`
- `markdown`: exact updated markdown

### `vtic delete`

Typer signature:

```python
@app.command()
def delete(
    ticket_id: str = typer.Argument(...),
    force: bool = typer.Option(False, "--force", help="Permanently delete instead of moving to .trash"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation prompt"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Options and defaults:

- positional `ticket_id`
- `--force bool`, default `False`
- `--yes bool`, default `False`
- `--config Path | None`, default `None`

Exit codes:

- `0` deleted
- `1` not found
- `2` cancelled by prompt
- `3` delete/config failure

Output:

- human text only
- optional `json` output not required for v0.1

### `vtic search`

Although not one of the mandatory CRUD commands, it should be planned in v0.1 because the user requested a BM25 phase.

Typer signature:

```python
@app.command()
def search(
    query: str = typer.Argument(""),
    repo: list[str] | None = typer.Option(None, "--repo"),
    category: list[Category] | None = typer.Option(None, "--category"),
    severity: list[Severity] | None = typer.Option(None, "--severity"),
    status: list[Status] | None = typer.Option(None, "--status"),
    tag: list[str] | None = typer.Option(None, "--tag"),
    topk: int = typer.Option(10, "--topk", min=1, max=100),
    offset: int = typer.Option(0, "--offset", min=0),
    sort_by: str = typer.Option("relevance", "--sort-by"),
    sort_order: str = typer.Option("desc", "--sort-order"),
    format: str = typer.Option("table", "--format"),
    config_path: Path | None = typer.Option(None, "--config"),
) -> None:
    ...
```

Output:

- `table`: result rows plus score column
- `json`: `SearchResponse`

## 8. BM25 search plan

v0.1 explicitly avoids Zvec and dense embeddings.

### Backend choice

- Primary option: `rank-bm25`
- Fallback if dependency becomes problematic: simple in-memory TF-IDF scorer implemented locally
- Recommended v0.1 path: use `rank-bm25`

### Indexed text

Index the combined searchable content:

```python
search_text = " ".join([
    ticket.title,
    ticket.description or "",
    ticket.fix or "",
    " ".join(ticket.tags),
])
```

This aligns with `Ticket.search_text` from `DATA_MODELS.md`. The user specifically asked for `title + description + tags`; including `fix` is still useful and already part of the model contract.

### Tokenization

- lowercase
- split on non-word characters
- drop empty tokens
- keep ticket IDs and file path fragments intact where possible
- no stemming in v0.1

### Index lifecycle

- On `SearchEngine` init: load all tickets from `TicketStore.iter_tickets()` and build corpus
- On create: `index_ticket(new_ticket)`
- On update: remove old document, add updated document
- On delete: `remove_ticket(ticket_id)`
- On CLI `search`: if in-memory index is missing or stale, rebuild synchronously

### Filtering

Apply structured filters before or after ranking depending on simplicity:

- simplest v0.1: filter candidate tickets first, then BM25 rank the filtered subset
- supported filters:
  - `repo`
  - `category`
  - `severity`
  - `status`
  - `tags`
  - `owner`
  - `has_fix`

### Result scoring

- Normalize BM25 scores to `0..1` for `SearchResult.score`
- Set `bm25_score` to normalized score
- Set `semantic_score = None`
- `SearchResponse.semantic = False`

### Sort behavior

- If query is non-empty and `sort_by == relevance`, sort by score desc
- If query is empty, treat `search` as filtered list and sort by requested field

### Persistence

- v0.1 does not require a separately persisted BM25 index
- rebuild from markdown source on process start
- optional later optimization: store token cache under `.vtic/bm25.json`

## 9. Test plan

The test plan should directly cover `breakdown-agent1.md` Features 1-13 plus storage and search behavior introduced by the user request.

### `tests/conftest.py`

Fixtures:

- `tmp_tickets_dir`
- `sample_config`
- `ticket_store`
- `ticket_service`
- `sample_ticket`
- `runner` for `typer.testing.CliRunner`
- deterministic `frozen_now`

### `tests/test_models.py`

Key cases:

- enum values exactly match spec
- `CATEGORY_PREFIXES` matches `DATA_MODELS.md`
- `Ticket` accepts valid minimal payload
- invalid ID format rejected
- invalid repo format rejected
- title whitespace rejected
- tags normalize to lowercase, stripped, deduplicated
- tags > 50 rejected
- `updated_at < created_at` rejected
- `slug` must match `^[a-z0-9-]+$`
- `TicketCreate` defaults category/severity/status correctly
- `TicketUpdate` forbids extra fields
- `TicketResponse.from_ticket()` populates computed fields

Coverage mapping:

- `breakdown-agent1.md` Features 2, 3, 4, 11, 12, 13

### `tests/test_config.py`

Key cases:

- default config values load correctly
- TOML file loads into `VticConfig`
- env vars override defaults
- ticket dir expands and resolves
- semantic config invalid when provider=`none` and semantic enabled
- hybrid weights sum validation
- explicit config path wins over default discovery

Coverage mapping:

- `DATA_MODELS.md` config schema section 3

### `tests/test_store.py`

Key cases:

- `init_storage()` creates root, `.vtic/`, `.trash/`
- save writes correct directory hierarchy `owner/repo/category/id-slug.md`
- save writes expected markdown frontmatter template
- get reads saved ticket back losslessly
- case-insensitive ID lookup works
- list returns all tickets
- list can filter by repo/category/status/severity
- delete with `force=False` moves file to `.trash/`
- delete with `force=True` removes file permanently
- delete of missing ticket returns `False`
- atomic write replaces file cleanly
- malformed frontmatter raises `TicketReadError`

Coverage mapping:

- `breakdown-agent1.md` Features 5, 9, 10
- `FEATURES.md` storage 3.1

### `tests/test_ticket_service.py`

Key cases:

- create minimal ticket
- create full ticket with all optional fields
- missing required title/repo rejected
- ID generation first-in-category
- ID generation sequential
- ID generation fills lowest gap
- category prefix mapping for all categories
- create auto-fills slug and timestamps
- get existing ticket
- get non-existent ticket returns `None`
- update single field
- update multiple fields
- update preserves unmodified fields
- update refreshes `updated_at`
- update invalid status rejected
- update immutable fields rejected or ignored consistently
- delete soft delete returns `True`
- delete hard delete returns `True`
- delete missing ticket returns `False`
- terminal status helper works
- status metadata includes colors and display names
- status transition validator accepts all valid v0.1 statuses

Coverage mapping:

- `breakdown-agent1.md` Features 1-13

### `tests/test_cli.py`

Key cases:

- `init` creates storage structure
- `create` minimal success
- `create` full success
- `create` validation failure exits `2`
- `get` table output success
- `get` json output valid JSON
- `get` markdown output matches serialized markdown
- `get` missing ticket exits `1`
- `list` default table output
- `list --format json` returns serialized array/paginated object
- `update --status fixed` success
- `update` multiple flags success
- `update` missing ticket exits `1`
- `update` invalid enum exits `2`
- `delete --yes` soft delete success
- `delete --force --yes` hard delete success
- `delete` prompt cancel exits `2`

Coverage mapping:

- `breakdown-agent1.md` Features 1, 6, 8, 10

### `tests/test_search.py`

Key cases:

- BM25 index builds from ticket corpus
- query matches title terms
- query matches description terms
- query matches tag terms
- exact repo/category/severity/status filters work
- empty query + filters behaves like filtered list
- create updates search index
- update refreshes search index content
- delete removes ticket from search results
- results sorted by normalized score
- `topk` and `offset` pagination work
- `SearchResponse.semantic` is always `False` in v0.1

Coverage mapping:

- `FEATURES.md` sections 2.1, 2.4, 2.5

## 10. Suggested implementation details by phase

### Phase 1 coding notes

- Put enum definitions and all Pydantic models in `models.py` exactly as in spec.
- Keep `constants.py` small; it should reference enums from `models.py`, so import direction matters.
- To avoid circular imports:
  - `models.py` should not import `constants.py`
  - `constants.py` can import `Category`/`Status`
  - `ticket.py` imports both
- Use `datetime.now(timezone.utc)` in helpers.

### Phase 2 coding notes

- Store should derive `owner` and `repo_name` from `ticket.repo`.
- Prefer YAML frontmatter parsing with `yaml.safe_load`.
- Serialize body from ticket data instead of preserving arbitrary formatting.
- Use `NamedTemporaryFile(delete=False, dir=target.parent)` then `Path.replace()`.
- Maintain an internal lightweight cache of `ticket_id -> Path` if scanning becomes repetitive, but do not make caching a prerequisite for correctness.

### Phase 3 coding notes

- `TicketService.create()`:
  - validate `TicketCreate`
  - load existing IDs from store
  - assign `id`
  - assign `slug`
  - set timestamps
  - instantiate `Ticket`
  - persist via store
- `TicketService.update()`:
  - fetch existing ticket
  - merge only provided fields from `TicketUpdate.model_dump(exclude_unset=True, exclude_none=False)`
  - if title changes, recompute slug and move file path accordingly
  - if category changes, regenerate path but keep ID unchanged
  - update timestamp only when at least one field changed
- `TicketService.delete()`:
  - delegate to store
  - notify search engine if attached

### Phase 4 coding notes

- Keep command functions thin; instantiate config/store/service per invocation.
- Use `typer.Exit(code)` after printing formatted output/errors.
- Centralize exception-to-exit-code handling in a helper decorator or local wrapper to avoid repeated try/except blocks.

### Phase 5 coding notes

- `SearchEngine` should depend only on `TicketStore` and `SearchConfig`.
- Keep the engine in-memory and deterministic.
- Do not overbuild a persistent index yet; correctness matters more than speed for v0.1.

## 11. Complete `pyproject.toml`

```toml
[build-system]
requires = ["hatchling>=1.27.0"]
build-backend = "hatchling.build"

[project]
name = "vtic"
version = "0.1.0"
description = "Lightweight, local-first ticket system with markdown storage and BM25 search"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [
  { name = "vtic contributors" }
]
keywords = ["tickets", "cli", "markdown", "bm25", "search"]
classifiers = [
  "Development Status :: 3 - Alpha",
  "Environment :: Console",
  "Intended Audience :: Developers",
  "License :: OSI Approved :: MIT License",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
  "Topic :: Software Development :: Bug Tracking",
]
dependencies = [
  "typer>=0.16.0,<1.0.0",
  "pydantic>=2.11.0,<3.0.0",
  "rich>=14.0.0,<15.0.0",
  "rank-bm25>=0.2.2,<1.0.0",
  "PyYAML>=6.0.2,<7.0.0",
  "fastapi>=0.115.0,<1.0.0",
  "uvicorn>=0.34.0,<1.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3.0,<9.0.0",
  "pytest-cov>=6.0.0,<7.0.0",
  "httpx>=0.28.0,<1.0.0",
  "ruff>=0.11.0,<1.0.0",
]
openai = [
  "openai>=1.75.0,<2.0.0",
]
local-embeddings = [
  "sentence-transformers>=3.4.0,<4.0.0",
]

[project.scripts]
vtic = "vtic.cli.main:main"

[tool.hatch.build.targets.wheel]
packages = ["src/vtic"]

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests"]
addopts = "-ra -q --strict-markers --cov=vtic --cov-report=term-missing"

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.coverage.run]
source = ["vtic"]
branch = true

[tool.coverage.report]
show_missing = true
skip_covered = false
```

## 12. Immediate coding checklist

Use this order when turning the plan into code:

1. Add `pyproject.toml`.
2. Create `src/vtic/` package skeleton and `tests/`.
3. Implement `models.py`, `constants.py`, `errors.py`, `config.py`, `utils.py`.
4. Write and pass `test_models.py` and `test_config.py`.
5. Implement `TicketStore` with YAML frontmatter round-trip.
6. Write and pass `test_store.py`.
7. Implement `TicketService` and ID generation/status helpers.
8. Write and pass `test_ticket_service.py`.
9. Implement CLI formatting and CRUD commands.
10. Write and pass `test_cli.py`.
11. Implement `SearchEngine` with `rank-bm25`.
12. Write and pass `test_search.py`.
13. Add API and embeddings scaffolding so the repo matches the published module map even if semantic search remains deferred.

## 13. Spec traceability summary

| Area | Primary source |
|---|---|
| Package/module layout | `DATA_MODELS.md` section 5 |
| Enums and Pydantic models | `DATA_MODELS.md` sections 1-2 |
| Config schema | `DATA_MODELS.md` section 3, `README.md` configuration |
| Errors | `DATA_MODELS.md` section 4 |
| CRUD commands | `FEATURES.md` sections 1 and 5 |
| Storage backend | `FEATURES.md` section 3, `README.md` ticket layout |
| Core lifecycle test expectations | `breakdown-agent1.md` Features 1-13 |
| BM25 v0.1 simplification | user requirement, aligned with `README.md` BM25 support |

