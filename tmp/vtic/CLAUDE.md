# CLAUDE.md — vtic AI Coding Guide

## Overview

vtic is a Python ticket system with a FastAPI server, CLI (Typer), and web dashboard. Tickets are markdown files on disk, indexed by Zvec for search.

## Development Setup

```bash
cd vtic
source .venv/bin/activate
python -m vtic serve          # Start API on http://127.0.0.1:8080
pytest                        # Run tests
pytest tests/test_api_routes.py -v  # Single file
```

## Architecture

```
src/vtic/
├── api/                  # FastAPI app (app.py) + routes
│   └── routes/           # tickets.py, search.py, system.py, priority.py, dashboard.py
├── cli/                  # Typer CLI (main.py)
├── embeddings/           # OpenAI and local embedding providers
├── index/                # Zvec vector index (client.py, operations.py, schema.py)
├── models/               # Pydantic models (ticket.py, config.py, enums.py, api.py, search.py)
├── priority/             # Priority scoring engine
├── search/               # BM25 + semantic search engine
├── services/             # System service
├── store/                # Markdown file I/O (markdown.py, paths.py)
├── errors.py             # VticError hierarchy
└── ticket.py             # TicketService — main entry point
```

## Key Patterns

### Config
- `vtic.toml` at project root — validated against `models/config.py:Config`
- No `shared` section — it was removed. Only `[storage]` and `[server]`
- Access config via `api/deps.py:get_config()` in route handlers

### Ticket Storage
- Markdown files under `tickets/{owner}/{repo}/...`
- Two formats: YAML frontmatter (preferred) and inline `**Key:** Value` headers
- `store/markdown.py:markdown_to_ticket()` requires frontmatter
- `api/routes/dashboard.py` has a lenient parser that handles both formats

### Ticket Service
- `ticket.py:TicketService` — initialized from Config, loads from storage
- Methods: `create()`, `get()`, `update()`, `delete()`, `list()`, `search()`
- Index operations in `index/operations.py`

### Error Handling
- `errors.py:VticError` base with status, code, message, details, docs
- Subtypes: `ValidationError`, `NotFoundError`, `IndexError_`, `StorageError`
- All errors auto-handled by FastAPI exception handlers in `app.py`

### API Routes
- Routes are in `api/routes/`, registered in `app.py:create_app()`
- Dashboard routes use `api/routes/dashboard.py` — scans disk directly
- Standard ticket routes use `TicketService` (via Zvec index)

## Dashboard

Single-file vanilla HTML/CSS/JS at `dashboard/index.html`. No build step, no dependencies.

- Served at `GET /dashboard`
- Uses `GET /dashboard/tickets` and `GET /dashboard/stats` endpoints
- Auto-connects when served from vtic server (detects `/dashboard` in URL)
- Also works standalone: enter any vtic API URL or load files via directory picker

## Ticket File Naming

```
tickets/{owner}/{repo}/{category}/{id}-{slug}.md    # with frontmatter
tickets/{owner}/{repo}/STORY-{nnn}-{slug}.md        # stories
tickets/{owner}/{repo}/TASKS-{phase}/{TASK-id}.md   # task groups
```

## Testing

- 24 test files covering models, store, index, API routes, CLI, e2e, performance
- `pytest` — all tests run from repo root
- Zvec tests may have cosmetic RocksDB cleanup errors — these are normal

## Conventions

- **Never modify `tickets/` directory** — it's user data, gitignored
- **Dashboard changes** — edit `dashboard/index.html` only
- **New routes** — create file in `api/routes/`, register in `app.py:create_app()`
- **Config changes** — update `models/config.py:Config` first, then `vtic.toml`
- **Error responses** — always use `VticError` subclasses, never raw dicts
- **Python version** — 3.12+
- **Package manager** — uv (lock file: `uv.lock`)
