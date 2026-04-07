# Implementation Plan: Core Ticket Lifecycle CRUD

## Scope

Implement the P0 Core Ticket Lifecycle for `vtic` with markdown-backed storage and CLI support:

- `init`
- `create`
- `get`
- `list`
- `update`
- `delete`

Include:

- project/package structure
- data models for CRUD
- markdown read/write format
- BM25 keyword search strategy
- implementation order with dependencies
- test plan

Out of scope for this phase:

- semantic search
- advanced status workflow validation
- bulk operations
- HTTP API expansion beyond what CRUD implementation naturally enables
- restore/trash management beyond what delete architecture needs

## Design Principles

- Local-first, zero-infrastructure storage
- Markdown files as source of truth
- Strong validation at model boundaries
- Deterministic file layout and serialization
- Atomic writes to avoid corruption
- Clear separation between CLI, models, storage, and search
- Search index is derived data and rebuildable from markdown files

## Project Structure

### `pyproject.toml`

Use a standard `src/` layout and expose a `vtic` CLI entrypoint.

Required pieces:

- `project.name = "vtic"`
- `requires-python = ">=3.11"`
- dependencies:
  - `pydantic>=2.0`
  - `typer>=0.9`
  - `rich>=13.0`
  - `pyyaml>=6.0`
- optional search dependency:
  - either no extra dependency if using built-in BM25
  - or optional `rank-bm25` / `zvec` if chosen
- dev dependencies:
  - `pytest`
  - `pytest-cov`

CLI entrypoint:

- `vtic = "vtic.cli.main:app"`

### Package Layout

Recommended package structure:

- `src/vtic/__init__.py`
  - version and package metadata
- `src/vtic/constants.py`
  - category prefixes, default paths, frontmatter markers
- `src/vtic/errors.py`
  - domain-specific exceptions
- `src/vtic/utils.py`
  - `slugify`, UTC timestamp helpers, repo parsing, tag normalization
- `src/vtic/models.py`
  - enums and Pydantic models
- `src/vtic/storage.py`
  - markdown file persistence and CRUD
- `src/vtic/search.py`
  - BM25 indexing and querying
- `src/vtic/config.py`
  - load/resolve ticket directory config
- `src/vtic/cli/__init__.py`
- `src/vtic/cli/main.py`
  - Typer app and command handlers

Tests:

- `tests/test_models.py`
- `tests/test_storage.py`
- `tests/test_cli.py`
- `tests/test_search.py`
- `tests/test_integration.py`

## File List With Purpose

### Core application files

- `pyproject.toml`
  - packaging, dependencies, CLI script registration
- `README.md`
  - user-facing behavior reference
- `src/vtic/models.py`
  - canonical shape of ticket data and CRUD payloads
- `src/vtic/constants.py`
  - stable category-to-prefix mapping and markdown section markers
- `src/vtic/errors.py`
  - `TicketNotFoundError`, `TicketWriteError`, `ValidationError`, etc.
- `src/vtic/utils.py`
  - helpers reused by storage, CLI, and search
- `src/vtic/storage.py`
  - create/get/list/update/delete against markdown files
- `src/vtic/search.py`
  - full-text indexing over ticket content and metadata
- `src/vtic/config.py`
  - resolve tickets directory from config/defaults
- `src/vtic/cli/main.py`
  - user command surface

### Test files

- `tests/conftest.py`
  - shared fixtures, temp directories, CLI runner helpers
- `tests/test_models.py`
  - model validation and normalization
- `tests/test_storage.py`
  - markdown serialization, file paths, atomic CRUD behavior
- `tests/test_cli.py`
  - command parsing, output, exit behavior
- `tests/test_search.py`
  - indexing and query ranking
- `tests/test_integration.py`
  - end-to-end lifecycle coverage

## Data Models

## Enums

Implement as `StrEnum` in Python 3.11+.

### `Severity`

Values:

- `critical`
- `high`
- `medium`
- `low`

### `Status`

Values:

- `open`
- `in_progress`
- `blocked`
- `fixed`
- `wont_fix`
- `closed`

### `Category`

Use the taxonomy from `DATA_MODELS.md`:

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

### Category prefix mapping

Use `CATEGORY_PREFIXES` as the source for ID generation:

- `security -> S`
- `auth -> A`
- `code_quality -> C`
- `performance -> P`
- `frontend -> F`
- `testing -> T`
- `documentation -> D`
- `infrastructure -> I`
- `configuration -> N`
- `api -> X`
- `data -> M`
- `ui -> U`
- `dependencies -> Y`
- `build -> B`
- `other -> O`

## `Ticket` dataclass/model

Use a validated Pydantic model for persistence and API/CLI interchange.

Fields:

- `id: str`
- `title: str`
- `description: str | None`
- `fix: str | None`
- `repo: str`
- `owner: str | None`
- `category: Category`
- `severity: Severity`
- `status: Status`
- `file: str | None`
- `tags: list[str]`
- `created_at: datetime`
- `updated_at: datetime`
- `slug: str`

Derived helpers:

- `filename -> "{id}-{slug}.md"`
- `filepath -> "{owner}/{repo_name}/{category}/{id}-{slug}.md"`
- `search_text -> concatenated text for indexing`

Validation rules:

- `id` matches `^[A-Z]\d+$`
- `title` non-empty after stripping
- `repo` matches `owner/repo`
- `tags` normalized to lowercase and deduplicated
- `updated_at >= created_at`
- `slug` is lowercase kebab-case

## `TicketCreate`

Fields:

- required:
  - `title`
  - `repo`
- optional:
  - `description`
  - `fix`
  - `owner`
  - `category` default `code_quality`
  - `severity` default `medium`
  - `status` default `open`
  - `file`
  - `tags`

Behavior:

- no `id`, `slug`, or timestamps accepted from normal CLI create path
- normalize title, repo, owner, tags
- derive owner from `repo` if omitted

## `TicketUpdate`

Partial update model. All fields optional:

- `title`
- `description`
- `fix`
- `owner`
- `category`
- `severity`
- `status`
- `file`
- `tags`

Behavior:

- `exclude_unset=True` for patch semantics
- if `title` changes, regenerate `slug`
- always refresh `updated_at`
- do not allow direct edits to `id`, `repo`, `created_at`, `slug`

## Markdown File Format

## Directory layout

Source of truth is the markdown tree:

```text
tickets/
└── {owner}/
    └── {repo}/
        └── {category}/
            └── {id}-{slug}.md
```

Example:

```text
tickets/
└── ejacklab/
    └── open-dsearch/
        └── security/
            └── S1-cors-wildcard-in-production.md
```

## Frontmatter format

Use YAML frontmatter plus explicit body markers:

```md
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

## Read behavior

Storage parser should:

- require opening and closing frontmatter delimiters
- parse YAML into a dict
- coerce enums and timestamps via `Ticket`
- parse description/fix from markers
- tolerate empty body sections
- derive `slug` from filename, not frontmatter
- reject malformed files with a domain-specific read error

## Write behavior

Serializer should:

- emit stable field order
- always write timestamps in UTC ISO 8601 with `Z`
- always emit `<!-- DESCRIPTION -->`
- emit `<!-- FIX -->` only when fix content exists
- ensure trailing newline
- use atomic write:
  - write temp file in same directory
  - `os.replace` into final path

## CLI Commands

Implement in `src/vtic/cli/main.py` using Typer.

## `vtic init`

Purpose:

- create the tickets base directory
- create search metadata directory if needed later

Behavior:

- `vtic init --dir ./tickets`
- idempotent
- success message on creation/existing directory

## `vtic create`

Arguments/options:

- `--repo`
- `--title`
- `--description`
- `--fix`
- `--owner`
- `--category`
- `--severity`
- `--status`
- `--file`
- `--tags`
- `--dir`

Behavior:

- validate through `TicketCreate`
- derive owner from repo if omitted
- generate next category-prefixed ID
- generate slug from title
- set `created_at` and `updated_at`
- persist markdown file
- return rendered ticket

Dependencies:

- models
- utils
- storage

## `vtic get`

Arguments/options:

- positional `ticket_id`
- `--format table|json|markdown`
- `--dir`

Behavior:

- lookup by case-insensitive ID
- render normalized ticket or raw markdown
- exit non-zero if not found

Dependencies:

- storage

## `vtic list`

Arguments/options:

- `--repo`
- `--owner`
- `--category`
- `--severity`
- `--status`
- `--tags`
- `--created-after`
- `--created-before`
- `--updated-after`
- `--updated-before`
- `--sort`
- `--format`
- `--dir`

Behavior:

- load tickets from markdown files
- apply structured filters
- sort by `severity`, `status`, `created_at`, `updated_at`, or `title`
- default sort by ID

Dependencies:

- models
- storage

## `vtic update`

Arguments/options:

- `--id`
- any mutable field from `TicketUpdate`
- `--dir`

Behavior:

- read existing ticket
- merge patch data
- if title/category changes, move file path accordingly
- update `updated_at`
- rewrite markdown atomically
- return updated ticket

Dependencies:

- models
- storage
- utils

## `vtic delete`

Arguments/options:

- `--id`
- `--yes`
- `--force` if hard delete is supported in this phase
- `--dir`

Core CRUD behavior:

- remove ticket file from source tree
- require confirmation unless `--yes`
- return success/failure status

Recommendation:

- implement hard delete first for strict CRUD scope
- leave soft delete/trash as a follow-up if scope must stay narrow

Dependencies:

- storage

## Storage Layer Responsibilities

Implement `TicketStore` in `src/vtic/storage.py`.

Public methods:

- `create_ticket(...) -> Ticket`
- `get(ticket_id: str) -> Ticket`
- `list(filters: SearchFilters | None = None, sort_by: str | None = None) -> list[Ticket]`
- `update(ticket_id: str, updates: TicketUpdate) -> Ticket`
- `delete(ticket_id: str) -> None`
- `count() -> int`

Private helpers:

- `_next_id(category: Category) -> str`
- `_find_ticket_path(ticket_id: str) -> Path`
- `_read_ticket(path: Path) -> Ticket`
- `_serialize_ticket(ticket: Ticket) -> str`
- `_write_ticket(ticket: Ticket, path: Path) -> None`
- `_split_frontmatter(raw: str) -> tuple[str, str]`
- `_parse_frontmatter(frontmatter: str) -> dict[str, object]`
- `_parse_body(body: str) -> tuple[str | None, str | None]`
- `_sort_tickets(...)`
- `_matches_filters(...)`

Important decisions:

- ID allocation should be serialized with a lock file if concurrent writers are in scope
- file path should be derived from ticket fields, never manually supplied
- update must handle file move when title/category changes
- malformed markdown files should not crash `list`; they should either:
  - be skipped with collected errors, or
  - fail fast in strict mode

## BM25 Search Plan

This CRUD plan should leave search ready, even if search is not the main deliverable.

## Preferred approach

Implement a built-in BM25 scorer first.

Reasons:

- no external service required
- fully aligned with local-first design
- sufficient for P0 keyword search
- simpler test surface than `zvec`

## `zvec` integration option

If `zvec` is required later:

- keep search behind a `TicketSearch` interface
- make the index derived from `ticket.search_text`
- store index metadata under a hidden path inside tickets dir, for example:
  - `.vtic-search-index.json`
  - or `.vtic/` if multiple index artifacts are added later

Recommendation for this phase:

- ship built-in BM25 as default
- optionally add `zvec` behind a feature flag or adapter later
- do not couple CRUD completion to `zvec`

## Index content

Index these fields:

- `id`
- `title`
- `description`
- `fix`
- `file`
- `tags`

Boost strategy:

- title highest
- id and file medium
- description/fix normal
- tags medium

Simple implementation choices:

- tokenize on non-alphanumeric boundaries
- lowercase normalization
- discard empty tokens
- keep index rebuildable from markdown source

## Search lifecycle hooks

- `create`: index new ticket
- `update`: refresh ticket entry
- `delete`: remove ticket entry
- `reindex`: rebuild from all markdown files

For initial phase, rebuilding on demand is acceptable if persistence is not required yet.

## Implementation Order With Dependencies

## Phase 1: Foundation

1. Finalize `pyproject.toml`
2. Finalize package layout under `src/vtic`
3. Add constants and error types
4. Add utility functions

Dependencies:
- none

## Phase 2: Models

1. Implement enums
2. Implement `Ticket`
3. Implement `TicketCreate`
4. Implement `TicketUpdate`
5. Implement filter models used by list/search

Dependencies:
- Phase 1

## Phase 3: Markdown storage

1. Define canonical file path derivation
2. Implement frontmatter/body parser
3. Implement serializer
4. Implement atomic write helper
5. Implement `create_ticket`
6. Implement `get`
7. Implement `list`
8. Implement `update`
9. Implement `delete`

Dependencies:
- Phase 2

## Phase 4: CLI CRUD

1. Implement `init`
2. Implement `create`
3. Implement `get`
4. Implement `list`
5. Implement `update`
6. Implement `delete`
7. Standardize exit codes and error output

Dependencies:
- Phase 3

## Phase 5: BM25 search

1. Implement tokenizer
2. Implement in-memory BM25 scorer
3. Add index build/rebuild flow
4. Add storage-to-search hooks
5. Add `search` command if desired in same milestone

Dependencies:
- Phase 3

## Phase 6: Hardening

1. concurrency lock for ID generation
2. malformed file handling in list/search
3. deterministic sorting
4. CLI JSON output modes
5. reindex command
6. documentation refresh

Dependencies:
- Phases 4 and 5

## Dependency Notes

- CLI cannot be finalized before storage API is stable
- search depends on `Ticket.search_text` and storage iteration
- update depends on path recalculation rules from `Ticket`
- delete can be implemented before search, but search cleanup hooks should follow immediately after

## Test Plan

## Model tests

`tests/test_models.py`

Cover:

- enum values
- repo validation
- title normalization
- tag normalization and deduplication
- timestamp ordering
- `TicketCreate` defaults
- `TicketUpdate` partial semantics
- invalid IDs and slugs

## Storage tests

`tests/test_storage.py`

Cover:

- create minimal ticket
- create full ticket
- generated file path matches expected owner/repo/category/id-slug layout
- generated markdown matches canonical format
- read ticket from markdown
- update title regenerates slug and moves file
- update category moves directory
- update only touches specified fields
- delete removes file
- get missing ticket raises not found
- list returns all tickets
- list filters by repo/category/severity/status/tags/date
- sort behavior
- malformed frontmatter handling
- malformed body marker handling
- atomic write behavior where practical

## CLI tests

`tests/test_cli.py`

Cover:

- `init` creates directory
- `create` with required args
- `create` with all args
- `get` success and not found
- `list` empty and populated output
- `update` changes specific fields
- `delete --yes` removes ticket
- validation failures return non-zero
- JSON output for `get` and `list` if included

## Search tests

`tests/test_search.py`

Cover:

- tokenization
- exact match on title
- search on description
- search on tags/file/id
- result ordering by score
- filters applied after/before scoring as designed
- update refreshes searchable content
- delete removes searchable content
- rebuild from markdown corpus

## Integration tests

`tests/test_integration.py`

End-to-end flow:

1. `init`
2. `create`
3. `get`
4. `list`
5. `update`
6. `search`
7. `delete`
8. verify removed from get/list/search

## Acceptance Criteria

Core Ticket Lifecycle CRUD is complete when:

- tickets are persisted as markdown files in the documented directory layout
- `vtic init/create/get/list/update/delete` work from the CLI
- ticket IDs are auto-generated from category prefixes
- title changes regenerate slugs correctly
- updates are partial and preserve untouched fields
- all writes are atomic
- list filtering works on core metadata
- BM25 keyword search works with markdown as the source of truth
- test suite covers model, storage, CLI, search, and integration layers