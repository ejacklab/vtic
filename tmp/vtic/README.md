# vtic

> Lightweight, local-first ticket system with vector search. Built on [Zvec](https://github.com/alibaba/zvec).

**Zero infrastructure.** No database server, no Docker, no cloud service. `pip install vtic` and go.

---

## Quick Start

### Install & Setup

```bash
git clone https://github.com/ejacklab/vtic.git
cd vtic

# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install
pip install -e ".[dev]"
```

### Initialize & Run

```bash
# Initialize vtic (creates vtic.toml + tickets/ directory)
vtic init .

# Start the server
vtic serve
```

### CLI Usage

```bash
# Create a ticket
vtic create --repo "myproject/app" --title "My first ticket"

# Search tickets (BM25 keyword search, zero config)
vtic search "CORS wildcard misconfiguration"

# Filter by fields
vtic search --severity critical --status open

# List & manage
vtic list --repo "ejacklab/open-dsearch"
vtic update C1 --status fixed
vtic delete C1
```

### API Endpoints

Run `vtic serve` then:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check & uptime |
| `GET` | `/dashboard` | Web dashboard UI |
| `GET` | `/dashboard/tickets` | List all tickets (from disk) |
| `GET` | `/dashboard/stats` | Ticket statistics |
| `POST` | `/tickets` | Create a ticket |
| `GET` | `/tickets` | List tickets (from index) |
| `GET` | `/tickets/{id}` | Get a ticket by ID |
| `PATCH` | `/tickets/{id}` | Update a ticket |
| `DELETE` | `/tickets/{id}` | Delete a ticket |
| `POST` | `/search` | Hybrid search |
| `POST` | `/api/priority/calculate` | Calculate priority score |

Interactive docs available at `/docs` (Swagger) and `/redoc`.

---

## Dashboard

The web dashboard is built into vtic. Start the server and open:

```
http://localhost:8080/dashboard
```

### Features

- **Auto-connects** when served from `vtic serve` — no configuration needed
- **Dark theme** with sidebar navigation (Overview, Repos, Statuses)
- **Stats grid**: total, open, in progress, blocked, resolved, critical
- **View switching**: All / Stories / Tasks
- **Filtering**: status, severity, category, repo, search, sort
- **Detail panel**: full ticket info with markdown rendering, tags, references, sub-task tree, priority breakdown
- **Pagination**: 25 per page with navigation
- **Keyboard shortcuts**: `/` to search, `Esc` to close modals
- **Offline mode**: load tickets from a directory via file picker (works without API)

### Dashboard API

The dashboard uses dedicated endpoints that scan markdown files directly from disk:

- `GET /dashboard` — serves the HTML UI
- `GET /dashboard/tickets?repo=&status=&severity=&search=&limit=&offset=` — list with filters
- `GET /dashboard/stats` — computed stats by status, severity, category, repo, tag

These endpoints handle both YAML frontmatter and inline `**Key:** Value` header formats, so they work with all ticket file formats.

---

## Configuration

Create `vtic.toml` in your project root:

```toml
[storage]
dir = "./tickets"

[server]
host = "127.0.0.1"
port = 8080
```

### Embedding Providers (Optional)

Dense semantic search is optional. BM25 keyword search works out of the box.

```toml
[search]
enable_semantic = true
embedding_provider = "openai"
embedding_model = "text-embedding-3-small"
embedding_dimensions = 1536
```

---

## Ticket File Structure

Tickets are markdown files organized by repo:

```
tickets/
└── {owner}/                    # 1
    └── {repo}/                 # 2
        └── {category}/         # 3
            └── {ticket_id}.md  # 4
```

### YAML Frontmatter Format

```markdown
---
id: C1
title: CORS Wildcard in Production
severity: critical
status: open
category: security
repo: ejacklab/open-dsearch
tags: [security, cors, frontend]
created: 2026-03-16
---

## Description
All FastAPI services use `allow_origins=['*']` which enables CSRF attacks.

## Fix
Use `ALLOWED_ORIGINS` from environment variable.
```

### Inline Header Format (also supported)

```markdown
# [Task] T1: Add Urgency Enum

**Status:** open
**Severity:** high
**Repo:** ejacklab/vtic

## Details
Add `Urgency` enum to `src/vtic/models/enums.py`.
```

---

## Architecture

```
┌─────────────────────────────────┐
│         vtic API / CLI          │
│    (FastAPI + Typer)            │
├─────────────┬───────────────────┤
│  Ticket      │   Search          │
│  Service     │   Service         │
│  (CRUD)      │   (hybrid)        │
├─────────────┼───────────────────┤
│  Markdown    │   Zvec Index      │
│  Files       │   (BM25 + dense)  │
│  (on disk)   │   (on disk)       │
└─────────────┴───────────────────┘
```

- **Markdown files** are the source of truth — durable, git-trackable, human-readable
- **Zvec index** is the search layer — rebuilt from markdown files if corrupted
- **Dashboard** is a static HTML file served directly by the API

## Project Structure

```
vtic/
├── src/vtic/                  # Source code
│   ├── api/                   # FastAPI application & routes
│   │   └── routes/            # ticket, search, system, priority, dashboard
│   ├── cli/                   # Typer CLI
│   ├── embeddings/            # Embedding providers (OpenAI, local)
│   ├── index/                 # Zvec vector index layer
│   ├── models/                # Pydantic models (ticket, config, enums, search)
│   ├── priority/              # Priority scoring engine
│   ├── search/                # BM25 + semantic search
│   ├── services/              # Business logic services
│   ├── store/                 # Markdown file I/O
│   ├── errors.py              # Error types
│   └── ticket.py              # TicketService (main entry point)
├── dashboard/
│   └── index.html             # Web dashboard (vanilla HTML/CSS/JS)
├── tests/                     # Test suite
├── docs/
│   ├── architecture/          # Design docs (data flows, models, features)
│   └── api/                   # OpenAPI specs
├── pyproject.toml
├── vtic.toml
├── CLAUDE.md                  # AI coding guide
└── README.md
```

## Built With

- [Zvec](https://github.com/alibaba/zvec) — In-process vector database (Alibaba Proxima engine)
- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API server
- [Typer](https://typer.tiangolo.com/) — CLI interface
- [Pydantic](https://docs.pydantic.dev/) — Data validation

## License

[MIT](LICENSE)
