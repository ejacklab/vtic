# vtic Implementation Plan: Core Ticket Lifecycle CRUD (v0.1 MVP)

> Generated: 2026-04-09
> Branch: feat/ticket-lifecycle-core
> Scope: CLI-based ticket CRUD with markdown file storage and BM25 search.

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
│       ├── models.py
│       ├── config.py
│       ├── errors.py
│       ├── constants.py
│       ├── utils.py
│       ├── id_gen.py
│       ├── store.py
│       ├── ticket.py
│       ├── search.py
│       └── cli/
│           ├── __init__.py
│           └── main.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_models.py
    ├── test_config.py
    ├── test_errors.py
    ├── test_id_gen.py
    ├── test_store.py
    ├── test_ticket.py
    ├── test_search.py
    └── test_cli.py
```

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "vtic"
version = "0.1.0"
description = "Lightweight, local-first ticket system with markdown-backed storage"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.0",
    "typer>=0.12",
    "rich>=13.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=5.0",
]

[project.scripts]
vtic = "vtic.cli.main:app"

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = [
    "integration: marks tests as integration tests (deselect with '-m \"not integration\"')",
]

[tool.hatch.build.targets.wheel]
packages = ["src/vtic"]
```

---

## 2. File List

| File | Description |
|------|-------------|
| `src/vtic/__init__.py` | Package exports: `__version__`, key classes |
| `src/vtic/models.py` | All Pydantic models: enums (`Severity`, `Status`, `Category`), `Ticket`, `TicketCreate`, `TicketUpdate`, `TicketResponse`, `SearchFilters`, `SearchResult`, `SearchResponse` |
| `src/vtic/config.py` | `VticConfig`, `TicketsConfig`, `ServerConfig`, `SearchConfig`. TOML loading with `tomllib`. Env var overrides (`VTIC_TICKETS_DIR`, etc.). `load_config()`, `get_config()` singleton. |
| `src/vtic/errors.py` | `VticError` base + all subclasses: `TicketNotFoundError`, `TicketAlreadyExistsError`, `ValidationError`, `ConfigError`, `TicketWriteError`, `TicketReadError` |
| `src/vtic/constants.py` | `CATEGORY_PREFIXES` dict, `VALID_STATUSES` list, `TERMINAL_STATUSES` list, `STATUS_METADATA` dict |
| `src/vtic/utils.py` | `slugify(text: str) -> str`, `utcnow() -> datetime`, `iso_format(dt: datetime) -> str` |
| `src/vtic/id_gen.py` | `generate_ticket_id(category: Category, existing_ids: set[str]) -> str` |
| `src/vtic/store.py` | `TicketStore` class — markdown file CRUD: `get()`, `save()`, `delete()`, `move_to_trash()`, `list()`, `exists()`, `list_ids()`. YAML frontmatter parse/write. Atomic file writes. |
| `src/vtic/ticket.py` | `TicketService` class — orchestration: `create()`, `get()`, `update()`, `delete()`, `list()`. Coordinates ID generation, timestamps, store persistence, and index updates. |
| `src/vtic/search.py` | `BM25Search` class — pure-Python BM25 implementation: `index_ticket()`, `remove_ticket()`, `search()`, `rebuild()`. Tokenizer, scoring, result ranking. |
| `src/vtic/cli/__init__.py` | CLI package init |
| `src/vtic/cli/main.py` | Typer app with commands: `init`, `create`, `get`, `list`, `update`, `delete`, `search`. Rich-formatted output. |
| `tests/conftest.py` | Shared fixtures: `tmp_ticket_dir` (ticket store on tmp_path), `sample_ticket`, `store` (populated TicketStore), `cli_runner` (Typer CliRunner) |
| `tests/test_models.py` | Enum values, Ticket validation (ID format, repo format, tags, timestamps), TicketCreate defaults, TicketUpdate partial fields |
| `tests/test_config.py` | TOML loading, env var overrides, defaults, invalid config |
| `tests/test_errors.py` | Error construction, error_code/message/status_code, `to_response()` method |
| `tests/test_id_gen.py` | Sequential IDs, gap filling, unknown categories, empty set, concurrent safety |
| `tests/test_store.py` | File roundtrip (write → read), atomic writes, frontmatter parsing, directory structure, trash operations, list filtering, exists check |
| `tests/test_ticket.py` | `TicketService.create()` (auto ID, timestamps, validation), `get()`, `update()` (partial, timestamp refresh, immutable fields), `delete()` (soft/hard) |
| `tests/test_search.py` | BM25 scoring (exact match > partial), filtering, empty results, special characters, reindex |
| `tests/test_cli.py` | All commands via `CliRunner`: init, create, get, list, update, delete, search. Exit codes, output formats |

---

## 3. Implementation Order (Dependency Graph)

```
Phase 1: Foundation (no dependencies)
  ├── constants.py     # Pure data, no deps
  ├── errors.py        # Only depends on models (for ErrorDetail) — but define ErrorDetail inline
  ├── utils.py         # Pure functions, no deps
  └── models.py        # Depends on: nothing external (pydantic only)

Phase 2: Core Services (depends on Phase 1)
  ├── id_gen.py        # Depends on: constants.py (CATEGORY_PREFIXES)
  ├── config.py        # Depends on: models.py (for config model types)
  └── store.py         # Depends on: models.py, errors.py, utils.py, config.py

Phase 3: Orchestration (depends on Phase 2)
  ├── ticket.py        # Depends on: store.py, id_gen.py, models.py, errors.py, utils.py
  └── search.py        # Depends on: models.py, store.py (for ticket text)

Phase 4: CLI (depends on Phase 3)
  └── cli/main.py      # Depends on: ticket.py, search.py, config.py, models.py, errors.py

Phase 5: Tests (parallel with development, final pass)
  └── tests/*.py       # Test each module in Phase order
```

### Implementation Sequence (Single Dev)

1. `pyproject.toml` — project metadata, dependencies
2. `src/vtic/__init__.py` — version string
3. `src/vtic/constants.py` — prefixes, statuses, metadata
4. `src/vtic/utils.py` — slugify, utcnow
5. `src/vtic/errors.py` — error hierarchy
6. `src/vtic/models.py` — all Pydantic models (largest file)
7. `src/vtic/config.py` — TOML + env loading
8. `src/vtic/id_gen.py` — ID generation
9. `src/vtic/store.py` — markdown file I/O
10. `src/vtic/ticket.py` — CRUD orchestration
11. `src/vtic/search.py` — BM25 search
12. `src/vtic/cli/__init__.py` + `src/vtic/cli/main.py` — CLI
13. `tests/conftest.py` — shared fixtures
14. `tests/test_*.py` — all test files
15. Verify: `python -m pytest tests/ -v`

---

## 4. Data Models (`src/vtic/models.py`)

### Enums

```python
from enum import StrEnum

class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    FIXED = "fixed"
    WONT_FIX = "wont_fix"
    CLOSED = "closed"

class Category(StrEnum):
    SECURITY = "security"
    AUTH = "auth"
    CODE_QUALITY = "code_quality"
    PERFORMANCE = "performance"
    FRONTEND = "frontend"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    CONFIGURATION = "configuration"
    API = "api"
    DATA = "data"
    UI = "ui"
    DEPENDENCIES = "dependencies"
    BUILD = "build"
    OTHER = "other"
```

### VticBaseModel

```python
from pydantic import BaseModel, ConfigDict

class VticBaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="ignore",
    )
```

### Ticket

```python
class Ticket(VticBaseModel):
    # Identity
    id: str = Field(..., min_length=1, max_length=20, pattern=r"^[A-Z]\d+$")
    
    # Content
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    
    # Metadata
    repo: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    
    # References
    file: Optional[str] = Field(default=None, max_length=500, pattern=r"^[^:]+(:\d+(-\d+)?)?$")
    tags: list[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(...)
    updated_at: datetime = Field(...)
    
    # Derived
    slug: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    
    # Validators (from DATA_MODELS.md):
    # - validate_id_format: regex match, .upper()
    # - validate_title_not_empty: strip check
    # - validate_repo_format: owner/repo check, .lower()
    # - normalize_tags: lowercase, strip, dedup, max 50
    # - validate_timestamps: updated_at >= created_at
    
    @property
    def is_terminal(self) -> bool: ...
    @property
    def filename(self) -> str: ...  # "{id}-{slug}.md"
    @property
    def filepath(self) -> str: ...  # "{repo}/{category}/{filename}"
    @property
    def search_text(self) -> str: ...  # "title description fix tags..."
```

### TicketCreate

```python
class TicketCreate(VticBaseModel):
    """Request body for creating a ticket. Required: title, repo."""
    title: str = Field(..., min_length=1, max_length=200)
    repo: str = Field(..., min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$")
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Category = Field(default=Category.CODE_QUALITY)
    severity: Severity = Field(default=Severity.MEDIUM)
    status: Status = Field(default=Status.OPEN)
    file: Optional[str] = Field(default=None, max_length=500)
    tags: list[str] = Field(default_factory=list)
```

### TicketUpdate

```python
class TicketUpdate(VticBaseModel):
    """Partial update. All fields optional. extra='forbid'."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=50000)
    fix: Optional[str] = Field(default=None, max_length=20000)
    owner: Optional[str] = Field(default=None, max_length=100)
    category: Optional[Category] = Field(default=None)
    severity: Optional[Severity] = Field(default=None)
    status: Optional[Status] = Field(default=None)
    file: Optional[str] = Field(default=None, max_length=500)
    tags: Optional[list[str]] = Field(default=None)
    # NOTE: id, created_at, repo are IMMUTABLE — not included here
```

### TicketResponse (CLI/API serialization)

```python
class TicketResponse(VticBaseModel):
    """Serializable ticket for CLI/API output. All enum values as strings."""
    id: str
    title: str
    description: Optional[str] = None
    fix: Optional[str] = None
    repo: str
    owner: Optional[str] = None
    category: str  # Category.value
    severity: str  # Severity.value
    status: str    # Status.value
    file: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: str  # ISO 8601
    updated_at: str  # ISO 8601
    slug: str
    is_terminal: bool
    filename: str
    filepath: str

    @classmethod
    def from_ticket(cls, ticket: Ticket) -> "TicketResponse": ...
```

### Search Models (minimal for v0.1)

```python
class SearchFilters(VticBaseModel):
    severity: Optional[list[Severity]] = None
    status: Optional[list[Status]] = None
    repo: Optional[list[str]] = None  # supports glob patterns
    category: Optional[list[Category]] = None
    tags: Optional[list[str]] = None  # AND matching

class SearchResult(VticBaseModel):
    id: str
    title: str
    repo: str
    category: str
    severity: str
    status: str
    score: float = Field(ge=0.0)
    highlights: list[str] = Field(default_factory=list)

class SearchResponse(VticBaseModel):
    results: list[SearchResult] = Field(default_factory=list)
    total: int = Field(ge=0)
    query: str
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
```

---

## 5. Markdown File Format (`src/vtic/store.py`)

### Ticket File Format

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

### Directory Structure

```
tickets/
├── {owner}/                    # e.g., "ejacklab"
│   └── {repo}/                 # e.g., "open-dsearch"
│       └── {category}/         # e.g., "security"
│           └── {id}-{slug}.md  # e.g., "S1-cors-wildcard.md"
└── .trash/                     # soft-deleted tickets
    └── {id}-{slug}.md
```

### TicketStore Class

```python
class TicketStore:
    """Markdown file-based ticket storage."""
    
    def __init__(self, base_dir: Path):
        """Initialize store with base directory path.
        Creates base_dir/.trash/ if not exists."""
        self.base_dir = base_dir
        self.trash_dir = base_dir / ".trash"
    
    def save(self, ticket: Ticket) -> None:
        """Write ticket as markdown file. Atomic: write to temp, then rename.
        Raises TicketAlreadyExistsError if file exists.
        Raises TicketWriteError on IO failure.
        Creates parent directories as needed."""
        ...
    
    def get(self, ticket_id: str) -> Ticket:
        """Read ticket by ID. Case-insensitive lookup.
        Scans directory tree to find file matching ID prefix.
        Raises TicketNotFoundError if not found.
        Raises TicketReadError on parse/IO failure."""
        ...
    
    def update(self, ticket: Ticket) -> None:
        """Overwrite existing ticket file. Atomic write.
        Raises TicketNotFoundError if original file missing.
        Raises TicketWriteError on IO failure."""
        ...
    
    def delete(self, ticket_id: str) -> None:
        """Permanently delete ticket file and parent dirs if empty.
        Raises TicketNotFoundError if not found."""
        ...
    
    def move_to_trash(self, ticket_id: str) -> None:
        """Move ticket to .trash/ directory.
        Raises TicketNotFoundError if not found."""
        ...
    
    def exists(self, ticket_id: str) -> bool:
        """Check if ticket exists. Case-insensitive."""
        ...
    
    def list(self, filters: Optional[SearchFilters] = None) -> list[Ticket]:
        """List all tickets, optionally filtered. Walk directory tree."""
        ...
    
    def list_ids(self) -> set[str]:
        """Return all ticket IDs. Used by ID generator."""
        ...
    
    # --- Internal ---
    
    def _ticket_path(self, ticket: Ticket) -> Path:
        """Build full path: base_dir/repo/category/id-slug.md"""
        ...
    
    def _find_ticket_file(self, ticket_id: str) -> Path:
        """Walk directory tree to find file matching ticket_id.
        Returns Path or raises TicketNotFoundError."""
        ...
    
    def _write_markdown(self, path: Path, ticket: Ticket) -> None:
        """Serialize ticket to markdown with YAML frontmatter.
        Write to temp file in same directory, then os.rename()."""
        ...
    
    def _parse_markdown(self, path: Path) -> Ticket:
        """Parse markdown file into Ticket model.
        Split on '---' delimiters, parse YAML frontmatter,
        extract <!-- DESCRIPTION --> and <!-- FIX --> sections."""
        ...
```

### YAML Frontmatter Parsing

Use `pyyaml` directly (avoid `python-frontmatter` dependency):

```python
import yaml

def _parse_markdown(path: Path) -> Ticket:
    content = path.read_text(encoding="utf-8")
    
    # Split frontmatter
    if not content.startswith("---\n"):
        raise TicketReadError(path.name, "Missing YAML frontmatter")
    
    parts = content.split("---\n", 2)
    if len(parts) < 3:
        raise TicketReadError(path.name, "Invalid frontmatter format")
    
    frontmatter = yaml.safe_load(parts[1])
    body = parts[2].strip()
    
    # Extract sections from body
    description = _extract_section(body, "DESCRIPTION")
    fix = _extract_section(body, "FIX")
    
    # Merge sections into frontmatter
    if description:
        frontmatter["description"] = description
    if fix:
        frontmatter["fix"] = fix
    
    return Ticket(**frontmatter)

def _extract_section(body: str, section_name: str) -> Optional[str]:
    """Extract content between <!-- SECTION --> markers."""
    pattern = rf"<!--\s*{section_name}\s*-->\s*\n(.*?)(?=\n<!--|$)"
    match = re.search(pattern, body, re.DOTALL)
    return match.group(1).strip() if match else None

def _write_markdown(path: Path, ticket: Ticket) -> None:
    """Build markdown string and write atomically."""
    # Build frontmatter dict (exclude description/fix)
    fm = ticket.model_dump(exclude={"description", "fix"}, mode="json")
    
    # Convert enums to values
    for key in ("category", "severity", "status"):
        if key in fm and hasattr(fm[key], "value"):
            fm[key] = fm[key].value
    # Convert datetime to ISO string
    for key in ("created_at", "updated_at"):
        if key in fm:
            fm[key] = fm[key].isoformat() if isinstance(fm[key], datetime) else str(fm[key])
    
    lines = ["---", yaml.dump(fm, default_flow_style=False, allow_unicode=True).rstrip(), "---", ""]
    
    if ticket.description:
        lines.extend(["<!-- DESCRIPTION -->", ticket.description, ""])
    if ticket.fix:
        lines.extend(["<!-- FIX -->", ticket.fix, ""])
    
    content = "\n".join(lines) + "\n"
    
    # Atomic write: temp file + rename
    tmp_path = path.with_suffix(".tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.rename(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise
```

---

## 6. CLI Commands (`src/vtic/cli/main.py`)

### App Setup

```python
import typer
from rich.console import Console

app = typer.Typer(
    name="vtic",
    help="Lightweight, local-first ticket system",
    no_args_is_help=True,
)
console = Console()
```

### `vtic init`

```python
@app.command()
def init(
    dir: Path = typer.Argument(..., help="Ticket storage directory"),
) -> None:
    """Initialize ticket storage directory."""
    # 1. Create dir if not exists
    # 2. Create dir/.trash/ 
    # 3. Create vtic.toml in CWD (or dir?) with default config
    # 4. Print success message with path
    # Exit: 0
```

### `vtic create`

```python
@app.command()
def create(
    title: str = typer.Option(..., "--title", "-t", help="Ticket title"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repository (owner/repo)"),
    category: Category = typer.Option(Category.CODE_QUALITY, "--category", "-c"),
    severity: Severity = typer.Option(Severity.MEDIUM, "--severity", "-s"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="File reference (path:line)"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
) -> None:
    """Create a new ticket."""
    # 1. Parse tags string → list[str]
    # 2. Build TicketCreate
    # 3. Call TicketService.create()
    # 4. Print created ticket summary (table format)
    # Exit: 0 success, 2 validation error
```

### `vtic get`

```python
@app.command()
def get(
    ticket_id: str = typer.Argument(..., help="Ticket ID (e.g., C1)"),
    format: str = typer.Option("table", "--format", "-F", help="Output format"),
    raw: bool = typer.Option(False, "--raw", help="Output raw markdown"),
) -> None:
    """Get a ticket by ID."""
    # 1. Call TicketService.get(ticket_id)
    # 2. If raw: print raw markdown file
    # 3. If format=="json": print TicketResponse.model_dump_json()
    # 4. If format=="table": print Rich table
    # 5. If format=="markdown": print formatted markdown
    # Exit: 0 success, 1 not found, 2 invalid format
```

### `vtic list`

```python
@app.command()
def list_tickets(
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    severity: Optional[Severity] = typer.Option(None, "--severity", "-s"),
    status: Optional[Status] = typer.Option(None, "--status"),
    category: Optional[Category] = typer.Option(None, "--category", "-c"),
    limit: int = typer.Option(50, "--limit", "-n"),
    offset: int = typer.Option(0, "--offset"),
    format: str = typer.Option("table", "--format", "-F"),
) -> None:
    """List tickets with optional filters."""
    # 1. Build SearchFilters from args
    # 2. Call TicketService.list(filters, limit, offset)
    # 3. Output as table/json
    # Exit: 0
```

### `vtic update`

```python
@app.command()
def update(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    status: Optional[Status] = typer.Option(None, "--status"),
    severity: Optional[Severity] = typer.Option(None, "--severity", "-s"),
    category: Optional[Category] = typer.Option(None, "--category", "-c"),
    description: Optional[str] = typer.Option(None, "--description", "-d"),
    fix: Optional[str] = typer.Option(None, "--fix"),
    tags: Optional[str] = typer.Option(None, "--tags"),
) -> None:
    """Update ticket fields."""
    # 1. Build TicketUpdate from non-None args
    # 2. If no fields provided, print "No changes specified" and exit 2
    # 3. Call TicketService.update(ticket_id, update)
    # 4. Print updated ticket summary
    # Exit: 0 success, 1 not found, 2 validation error
```

### `vtic delete`

```python
@app.command()
def delete(
    ticket_id: str = typer.Argument(..., help="Ticket ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    force: bool = typer.Option(False, "--force", help="Permanent delete (no trash)"),
) -> None:
    """Delete a ticket."""
    # 1. If not --yes: prompt "Delete ticket {id}? [y/N]"
    # 2. If cancelled: print "Cancelled" and exit 2
    # 3. Call TicketService.delete(ticket_id, force=force)
    # 4. Print "Deleted {id} (moved to trash)" or "Permanently deleted {id}"
    # Exit: 0 success, 1 not found, 2 cancelled
```

### `vtic search`

```python
@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    repo: Optional[str] = typer.Option(None, "--repo", "-r"),
    severity: Optional[Severity] = typer.Option(None, "--severity", "-s"),
    status: Optional[Status] = typer.Option(None, "--status"),
    category: Optional[Category] = typer.Option(None, "--category", "-c"),
    limit: int = typer.Option(10, "--limit", "-n"),
    offset: int = typer.Option(0, "--offset"),
) -> None:
    """Search tickets by keyword (BM25)."""
    # 1. Build SearchFilters from args
    # 2. Call SearchEngine.search(query, filters, limit, offset)
    # 3. Print results as Rich table with score column
    # 4. Print "Found N results" summary
    # Exit: 0
```

### Output Formatting (Rich)

```python
def format_ticket_table(ticket: Ticket) -> Table:
    """Format ticket as Rich table for terminal display."""
    table = Table(title=f"Ticket {ticket.id}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")
    table.add_row("ID", ticket.id)
    table.add_row("Title", ticket.title)
    table.add_row("Repo", ticket.repo)
    table.add_row("Category", ticket.category.value)
    table.add_row("Severity", severity_colored(ticket.severity))
    table.add_row("Status", status_colored(ticket.status))
    table.add_row("Owner", ticket.owner or "-")
    table.add_row("File", ticket.file or "-")
    table.add_row("Tags", ", ".join(ticket.tags) or "-")
    table.add_row("Created", ticket.created_at.isoformat())
    table.add_row("Updated", ticket.updated_at.isoformat())
    if ticket.description:
        table.add_row("Description", ticket.description[:200] + "..." if len(ticket.description) > 200 else ticket.description)
    return table

def format_list_table(tickets: list[Ticket]) -> Table:
    """Format ticket list as compact table."""
    table = Table()
    table.add_column("ID", style="bold")
    table.add_column("Title")
    table.add_column("Repo")
    table.add_column("Severity")
    table.add_column("Status")
    table.add_column("Category")
    for t in tickets:
        table.add_row(t.id, t.title, t.repo, t.severity.value, t.status.value, t.category.value)
    return table
```

---

## 7. BM25 Search (`src/vtic/search.py`)

### Pure-Python BM25 Implementation

```python
import math
import re
from collections import Counter
from dataclasses import dataclass, field

@dataclass
class BM25Search:
    """In-process BM25 keyword search. No external dependencies."""
    
    k1: float = 1.5      # Term frequency saturation
    b: float = 0.75       # Length normalization
    _documents: dict[str, "IndexedDoc"] = field(default_factory=dict)
    _avg_dl: float = 0.0
    _N: int = 0
    _df: Counter = field(default_factory=Counter)  # document frequency per term
    
    @dataclass
    class IndexedDoc:
        ticket_id: str
        tokens: list[str]
        raw_text: str
        ticket: Ticket  # reference for filtering
    
    def _tokenize(self, text: str) -> list[str]:
        """Lowercase, split on non-alphanumeric, filter empty."""
        return [t for t in re.split(r'[^a-z0-9]+', text.lower()) if t]
    
    def index_ticket(self, ticket: Ticket) -> None:
        """Add/update ticket in search index."""
        text = ticket.search_text
        tokens = self._tokenize(text)
        doc = self.IndexedDoc(ticket_id=ticket.id, tokens=tokens, raw_text=text, ticket=ticket)
        
        # Remove old if re-indexing
        if ticket.id in self._documents:
            self._remove_from_stats(ticket.id)
        
        self._documents[ticket.id] = doc
        self._update_stats()
    
    def remove_ticket(self, ticket_id: str) -> None:
        """Remove ticket from index."""
        if ticket_id in self._documents:
            self._remove_from_stats(ticket_id)
            del self._documents[ticket_id]
            self._update_stats()
    
    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResponse:
        """Search tickets using BM25 scoring."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return SearchResponse(results=[], total=0, query=query, limit=limit, offset=offset, has_more=False)
        
        scores: list[tuple[str, float]] = []
        
        for doc_id, doc in self._documents.items():
            # Apply filters first
            if filters and not self._matches_filters(doc.ticket, filters):
                continue
            
            score = self._bm25_score(query_tokens, doc)
            if score > 0:
                scores.append((doc_id, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Paginate
        total = len(scores)
        page = scores[offset:offset + limit]
        
        results = []
        for doc_id, score in page:
            doc = self._documents[doc_id]
            highlights = self._highlight(query_tokens, doc.raw_text)
            results.append(SearchResult(
                id=doc.ticket.id,
                title=doc.ticket.title,
                repo=doc.ticket.repo,
                category=doc.ticket.category.value,
                severity=doc.ticket.severity.value,
                status=doc.ticket.status.value,
                score=round(score, 4),
                highlights=highlights,
            ))
        
        return SearchResponse(
            results=results,
            total=total,
            query=query,
            limit=limit,
            offset=offset,
            has_more=(offset + len(results)) < total,
        )
    
    def _bm25_score(self, query_tokens: list[str], doc: "IndexedDoc") -> float:
        """Calculate BM25 score for a document."""
        score = 0.0
        tf = Counter(doc.tokens)
        dl = len(doc.tokens)
        
        for token in query_tokens:
            if token not in tf:
                continue
            
            freq = tf[token]
            n = self._N or 1
            df = self._df.get(token, 0)
            idf = math.log((n - df + 0.5) / (df + 0.5) + 1.0)
            tf_norm = (freq * (self.k1 + 1)) / (freq + self.k1 * (1 - self.b + self.b * dl / (self._avg_dl or 1)))
            score += idf * tf_norm
        
        return score
    
    def _matches_filters(self, ticket: Ticket, filters: SearchFilters) -> bool:
        """Check if ticket matches all filter criteria."""
        if filters.severity and ticket.severity not in filters.severity:
            return False
        if filters.status and ticket.status not in filters.status:
            return False
        if filters.category and ticket.category not in filters.category:
            return False
        if filters.repo:
            if not any(self._glob_match(ticket.repo, pattern) for pattern in filters.repo):
                return False
        if filters.tags:
            if not all(t in ticket.tags for t in filters.tags):
                return False
        return True
    
    def _glob_match(self, value: str, pattern: str) -> bool:
        """Simple glob: '*' matches any characters within a segment."""
        # Convert glob to regex: e.g., "ejacklab/*" → "^ejacklab/.*$"
        regex = "^" + re.escape(pattern).replace(r"\*", ".*") + "$"
        return bool(re.match(regex, value, re.IGNORECASE))
    
    def _highlight(self, query_tokens: list[str], text: str, context: int = 40) -> list[str]:
        """Extract text snippets around matching terms."""
        # Find first occurrence of any query token in original text
        lower = text.lower()
        for token in query_tokens:
            idx = lower.find(token)
            if idx >= 0:
                start = max(0, idx - context)
                end = min(len(text), idx + len(token) + context)
                snippet = text[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(text):
                    snippet = snippet + "..."
                return [snippet]
        return []
    
    def rebuild(self, tickets: list[Ticket]) -> None:
        """Rebuild index from list of tickets."""
        self._documents.clear()
        self._df.clear()
        self._N = 0
        self._avg_dl = 0.0
        for ticket in tickets:
            self.index_ticket(ticket)
```

---

## 8. ID Generation (`src/vtic/id_gen.py`)

```python
from vtic.constants import CATEGORY_PREFIXES, Category
from vtic.errors import ValidationError

def generate_ticket_id(category: Category, existing_ids: set[str]) -> str:
    """
    Generate unique ticket ID based on category prefix.
    
    Algorithm:
    1. Get prefix from CATEGORY_PREFIXES for category (default "O" for unknown)
    2. Find all existing IDs with this prefix
    3. Extract numbers from those IDs
    4. Find the lowest gap (starting from 1)
    5. Return "{PREFIX}{NUMBER}"
    
    Examples:
        category=Category.SECURITY, existing_ids={"S1", "S2"} → "S3"
        category=Category.SECURITY, existing_ids={"S1", "S3"} → "S2" (gap fill)
        category=Category.OTHER, existing_ids=set() → "O1"
    """
    prefix = CATEGORY_PREFIXES.get(category, "O")
    
    # Find existing numbers for this prefix
    existing_numbers = set()
    for eid in existing_ids:
        if eid.upper().startswith(prefix):
            num_str = eid.upper()[len(prefix):]
            if num_str.isdigit():
                existing_numbers.add(int(num_str))
    
    # Find lowest available number
    n = 1
    while n in existing_numbers:
        n += 1
    
    return f"{prefix}{n}"
```

---

## 9. Error Handling (`src/vtic/errors.py`)

```python
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    code: str

class VticError(Exception):
    """Base exception for all vtic errors."""
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 500,
        details: list[ErrorDetail] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)

class TicketNotFoundError(VticError):
    def __init__(self, ticket_id: str):
        super().__init__(
            error_code="TICKET_NOT_FOUND",
            message=f"Ticket {ticket_id} not found",
            status_code=404,
        )

class TicketAlreadyExistsError(VticError):
    def __init__(self, ticket_id: str):
        super().__init__(
            error_code="TICKET_ALREADY_EXISTS",
            message=f"Ticket {ticket_id} already exists",
            status_code=409,
        )

class TicketWriteError(VticError):
    def __init__(self, ticket_id: str, details: str):
        super().__init__(
            error_code="TICKET_WRITE_ERROR",
            message=f"Failed to write ticket {ticket_id}: {details}",
            status_code=500,
        )

class TicketReadError(VticError):
    def __init__(self, ticket_id: str, details: str):
        super().__init__(
            error_code="TICKET_READ_ERROR",
            message=f"Failed to read ticket {ticket_id}: {details}",
            status_code=500,
        )

class ValidationError(VticError):
    def __init__(self, message: str, details: list[ErrorDetail] | None = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )

class ConfigError(VticError):
    def __init__(self, message: str):
        super().__init__(
            error_code="CONFIG_ERROR",
            message=message,
            status_code=500,
        )
```

### CLI Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Not found (ticket, config) |
| 2 | Validation error / user cancelled |
| 3 | Config error / not initialized |
| 130 | Ctrl+C (SIGINT) — let Typer handle |

---

## 10. Ticket Service (`src/vtic/ticket.py`)

```python
class TicketService:
    """High-level ticket CRUD orchestration."""
    
    def __init__(self, store: TicketStore, search: BM25Search):
        self.store = store
        self.search = search
    
    def create(self, data: TicketCreate) -> Ticket:
        """Create a new ticket.
        1. Validate required fields (Pydantic handles this)
        2. Generate ID: generate_ticket_id(data.category, store.list_ids())
        3. Generate slug: slugify(data.title)
        4. Set timestamps: now = utcnow()
        5. Build Ticket model
        6. store.save(ticket) — atomic write
        7. search.index_ticket(ticket)
        8. Return ticket
        Raises: TicketAlreadyExistsError (shouldn't happen with auto-ID), ValidationError
        """
        ...
    
    def get(self, ticket_id: str) -> Ticket:
        """Get ticket by ID. Case-insensitive.
        Delegates to store.get().
        Raises: TicketNotFoundError"""
        ...
    
    def update(self, ticket_id: str, update: TicketUpdate) -> Ticket:
        """Update ticket fields.
        1. Fetch existing: store.get(ticket_id)
        2. Merge update fields (only non-None)
        3. Refresh updated_at = utcnow()
        4. Recalculate slug if title changed
        5. store.update(ticket)
        6. search.index_ticket(ticket) — re-index
        7. Return updated ticket
        Raises: TicketNotFoundError, ValidationError"""
        ...
    
    def delete(self, ticket_id: str, force: bool = False) -> None:
        """Delete ticket.
        1. Verify exists: store.exists(ticket_id)
        2. If force: store.delete(ticket_id)
        3. Else: store.move_to_trash(ticket_id)
        4. search.remove_ticket(ticket_id)
        Raises: TicketNotFoundError"""
        ...
    
    def list(
        self,
        filters: SearchFilters | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Ticket]:
        """List tickets with filters.
        Delegates to store.list(filters), then paginate."""
        ...
    
    def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> SearchResponse:
        """Search tickets using BM25.
        Delegates to search.search()."""
        ...
```

---

## 11. Config (`src/vtic/config.py`)

```python
from pathlib import Path
import tomllib

class TicketsConfig(BaseModel):
    dir: Path = Field(default=Path("./tickets"))
    
    @field_validator("dir")
    @classmethod
    def validate_dir(cls, v: Path) -> Path:
        return v.expanduser().resolve()

class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8900, ge=1, le=65535)

class SearchConfig(BaseModel):
    bm25_enabled: bool = True

class VticConfig(BaseModel):
    tickets: TicketsConfig = Field(default_factory=TicketsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    
    @classmethod
    def from_toml(cls, path: Path) -> "VticConfig": ...
    
    @classmethod
    def from_env(cls) -> "VticConfig": ...
    
    @classmethod
    def load(cls) -> "VticConfig":
        """Load config: check CWD vtic.toml → ~/.config/vtic/config.toml → defaults.
        Override with VTIC_* env vars."""
        ...

_config: VticConfig | None = None

def get_config() -> VticConfig:
    """Singleton config access."""
    global _config
    if _config is None:
        _config = VticConfig.load()
    return _config

def init_config(tickets_dir: Path) -> None:
    """Write default vtic.toml to current directory."""
    config = VticConfig(tickets=TicketsConfig(dir=tickets_dir))
    # Write TOML
    ...
```

---

## 12. Test Plan

### conftest.py Fixtures

```python
import pytest
from pathlib import Path
from typer.testing import CliRunner

@pytest.fixture
def tmp_store(tmp_path):
    """TicketStore pointing to a temp directory."""
    from vtic.store import TicketStore
    store = TicketStore(tmp_path / "tickets")
    store.base_dir.mkdir(parents=True, exist_ok=True)
    store.trash_dir.mkdir(exist_ok=True)
    return store

@pytest.fixture
def sample_ticket():
    """A valid Ticket instance for testing."""
    from vtic.models import Ticket
    from datetime import datetime, timezone
    return Ticket(
        id="S1",
        title="CORS Wildcard in Production",
        repo="ejacklab/open-dsearch",
        category=Category.SECURITY,
        severity=Severity.CRITICAL,
        status=Status.OPEN,
        created_at=datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 3, 16, 10, 0, 0, tzinfo=timezone.utc),
        slug="cors-wildcard-in-production",
        description="All FastAPI services use allow_origins=['*']",
        tags=["cors", "security"],
    )

@pytest.fixture
def populated_store(tmp_store, sample_ticket):
    """Store with one ticket pre-saved."""
    tmp_store.save(sample_ticket)
    return tmp_store

@pytest.fixture
def cli_runner():
    """Typer CLI test runner."""
    return CliRunner()
```

### test_models.py (25 tests)

| Test | What it verifies |
|------|-----------------|
| `test_severity_values` | All 4 severity values exist |
| `test_status_values` | All 6 status values exist |
| `test_category_values` | All 15 category values exist |
| `test_ticket_valid_minimal` | Ticket with only required fields |
| `test_ticket_valid_all_fields` | Ticket with all fields populated |
| `test_ticket_id_format_valid` | Accepts "C1", "S99" |
| `test_ticket_id_format_invalid` | Rejects "1", "abc", "C", "c1" |
| `test_ticket_id_uppercased` | "c1" → "C1" |
| `test_ticket_repo_format_valid` | Accepts "owner/repo" |
| `test_ticket_repo_format_invalid` | Rejects "repo", "a/b/c" |
| `test_ticket_repo_lowercased` | "Owner/Repo" → "owner/repo" |
| `test_ticket_title_empty_rejected` | Empty/whitespace title raises |
| `test_ticket_tags_normalized` | Lowercase, dedup, max 50 |
| `test_ticket_tags_too_many` | 51 tags raises |
| `test_ticket_timestamps_valid` | updated_at >= created_at |
| `test_ticket_timestamps_invalid` | updated_at < created_at raises |
| `test_ticket_filename` | "C1" + "bug" → "C1-bug.md" |
| `test_ticket_filepath` | "{repo}/{category}/{filename}" |
| `test_ticket_is_terminal` | fixed/wont_fix/closed = True |
| `test_ticket_create_defaults` | category=code_quality, severity=medium, status=open |
| `test_ticket_update_all_optional` | All fields Optional |
| `test_ticket_update_extra_forbidden` | extra="forbid" rejects unknown fields |
| `test_ticket_response_from_ticket` | Conversion preserves all fields |
| `test_ticket_search_text` | Combines title+description+fix+tags |

### test_id_gen.py (8 tests)

| Test | What it verifies |
|------|-----------------|
| `test_first_id_in_category` | Empty set → prefix + "1" |
| `test_sequential_ids` | S1,S2 → S3 |
| `test_gap_filling` | S1,S3 → S2 |
| `test_unknown_category` | No prefix → "O1" |
| `test_mixed_categories` | S1,C1,C2 → C3 |
| `test_empty_existing_ids` | Any category → X1 |
| `test_large_gap` | S1,S100 → S2 |
| `test_all_prefixes` | Each category gets correct prefix |

### test_store.py (18 tests)

| Test | What it verifies |
|------|-----------------|
| `test_save_and_get_roundtrip` | Write ticket → read back → fields match |
| `test_save_creates_directories` | Missing dirs are created |
| `test_save_atomic_write` | No partial files on crash (check no .tmp after save) |
| `test_save_duplicate_raises` | Save same ID twice → TicketAlreadyExistsError |
| `test_get_not_found` | Non-existent ID → TicketNotFoundError |
| `test_get_case_insensitive` | "s1" finds "S1" |
| `test_update_overwrites` | Save → update → get returns new values |
| `test_delete_removes_file` | File gone after delete |
| `test_delete_not_found` | Non-existent ID → TicketNotFoundError |
| `test_move_to_trash` | File in .trash/ after soft delete |
| `test_move_to_trash_creates_trash_dir` | .trash/ auto-created |
| `test_exists_true` | Returns True for existing ticket |
| `test_exists_false` | Returns False for missing ticket |
| `test_list_returns_all` | Multiple tickets all listed |
| `test_list_with_filters` | Only matching tickets returned |
| `test_list_ids` | Returns set of ID strings |
| `test_parse_frontmatter` | YAML frontmatter correctly parsed |
| `test_parse_description_section` | <!-- DESCRIPTION --> content extracted |

### test_search.py (12 tests)

| Test | What it verifies |
|------|-----------------|
| `test_exact_match_highest_score` | Exact term scores higher than partial |
| `test_no_results_empty_query` | Empty string returns empty |
| `test_filter_by_severity` | Only matching severity in results |
| `test_filter_by_status` | Only matching status in results |
| `test_filter_by_repo_glob` | "ejacklab/*" matches repos |
| `test_pagination_limit_offset` | Correct page of results |
| `test_highlight_snippet` | Query term appears in highlight |
| `test_reindex_rebuilds` | Clear + rebuild produces same results |
| `test_remove_ticket_excluded` | Deleted ticket not in results |
| `test_special_characters_ignored` | Query with symbols still works |
| `test_multiple_terms_better_than_single` | "CORS wildcard" scores higher than "CORS" alone |
| `test_score_ordering` | Results sorted by score descending |

### test_cli.py (20 tests)

| Test | What it verifies |
|------|-----------------|
| `test_init_creates_directory` | `vtic init ./tmp` creates dir |
| `test_init_creates_trash` | .trash/ subdirectory created |
| `test_init_creates_config` | vtic.toml written |
| `test_create_minimal` | `vtic create -t "Bug" -r "owner/repo"` succeeds |
| `test_create_with_all_options` | All flags accepted |
| `test_create_invalid_repo` | Bad repo format → exit code 2 |
| `test_get_existing` | Shows ticket in table format |
| `test_get_json_format` | Valid JSON output with --format json |
| `test_get_not_found` | Exit code 1 |
| `test_get_raw` | --raw outputs markdown |
| `test_list_empty` | No tickets → "No tickets found" |
| `test_list_with_filter` | --severity critical filters correctly |
| `test_update_status` | --status fixed updates ticket |
| `test_update_multiple_fields` | Combined flags work |
| `test_update_not_found` | Exit code 1 |
| `test_delete_with_yes` | --yes skips prompt, exit 0 |
| `test_delete_force` | --force permanent delete |
| `test_delete_not_found` | Exit code 1 |
| `test_search_query` | Returns matching tickets |
| `test_search_with_filter` | Combined query + filter |

### test_config.py (6 tests)

| Test | What it verifies |
|------|-----------------|
| `test_default_config` | No file → defaults |
| `test_load_toml` | Parse valid vtic.toml |
| `test_env_override` | VTIC_TICKETS_DIR overrides |
| `test_config_cwd_precedence` | CWD config > global config |
| `test_invalid_toml` | Bad TOML → ConfigError |
| `test_init_config_writes_file` | init_config creates vtic.toml |

### test_errors.py (5 tests)

| Test | What it verifies |
|------|-----------------|
| `test_error_base_properties` | error_code, message, status_code |
| `test_ticket_not_found_404` | Correct attributes |
| `test_validation_error_400` | Correct attributes + details |
| `test_error_inheritance` | All errors are VticError |
| `test_error_str` | str(error) == message |

**Total: ~94 tests**

---

## 13. Constants (`src/vtic/constants.py`)

```python
from vtic.models import Category

CATEGORY_PREFIXES: dict[Category, str] = {
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

TERMINAL_STATUSES: set[str] = {"fixed", "wont_fix", "closed"}

STATUS_METADATA: dict[str, dict] = {
    "open": {"display_name": "Open", "color": "blue"},
    "in_progress": {"display_name": "In Progress", "color": "yellow"},
    "blocked": {"display_name": "Blocked", "color": "red"},
    "fixed": {"display_name": "Fixed", "color": "green"},
    "wont_fix": {"display_name": "Won't Fix", "color": "dim"},
    "closed": {"display_name": "Closed", "color": "cyan"},
}
```

---

## 14. Next Steps for 2am Scaffold Job

The scaffold job should:

1. **Create all files** listed in Section 2 following the exact signatures in Sections 4-12
2. **Copy model code** from DATA_MODELS.md almost verbatim — the spec is the contract
3. **Implement store.py first** — it's the critical path; everything else depends on file I/O
4. **Wire up CLI last** — after all services work in isolation
5. **Run tests incrementally** — don't wait until all files exist:
   - After Phase 1: `pytest tests/test_models.py tests/test_constants.py tests/test_errors.py`
   - After Phase 2: `pytest tests/test_id_gen.py tests/test_store.py tests/test_config.py`
   - After Phase 3: `pytest tests/test_ticket.py tests/test_search.py`
   - After Phase 4: `pytest tests/test_cli.py`
   - Full: `pytest tests/ -v --cov=vtic`
6. **Target: green test suite** — all ~94 tests passing before commit
7. **Commit message**: `feat: scaffold core ticket lifecycle CRUD (v0.1 MVP)`

### Estimated File Sizes

| File | Lines (est.) |
|------|-------------|
| models.py | ~300 |
| config.py | ~120 |
| errors.py | ~80 |
| constants.py | ~40 |
| utils.py | ~30 |
| id_gen.py | ~30 |
| store.py | ~250 |
| ticket.py | ~120 |
| search.py | ~200 |
| cli/main.py | ~350 |
| **Source total** | **~1520** |
| tests/*.py | ~1200 |
| **Grand total** | **~2720** |
