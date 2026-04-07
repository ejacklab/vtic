# vtic

> Lightweight, local-first ticket system with markdown-backed storage, a CLI, and an HTTP API.

**Zero infrastructure.** No database server, no Docker, no cloud service. `pip install vtic` and go.

## Why vtic?

Traditional ticket systems store issues in databases — great for CRUD, terrible for search. Finding "all auth-related security issues across 5 repos" means reading every ticket, every label, every description.

**vtic** stores tickets as markdown files on disk (durable, git-trackable) and provides in-process keyword search:

- **Keyword search** (BM25-style scoring) — exact and near-exact matches on ticket IDs, file paths, and descriptions.
- **Structured filtering** — filter by repo, severity, status, category, owner, tags, and dates.

No web UI needed. No browser tab open. Just an API and a CLI.

## Features

- 🚀 **Keyword search** — built-in search over ticket content and metadata
- 📁 **Markdown files** — tickets live on disk, git-friendly, human-readable
- 🏷️ **Structured filtering** — filter by repo, severity, status, category, date
- ⚡ **In-process** — no server to manage, just Python
- 📦 **Multi-repo** — organize tickets across any number of repositories

## Quick Start

### Install

```bash
pip install vtic
```

### Initialize

```bash
vtic init --dir ./tickets
```

This creates the ticket storage directory.

### Create a Ticket

```bash
vtic create \
  --repo "ejacklab/open-dsearch" \
  --category "security" \
  --severity "critical" \
  --title "CORS Wildcard in Production" \
  --description "All FastAPI services use allow_origins=['*']..." \
  --file "backend/api-gateway/main.py:27-32" \
  --tags "cors,security,fastapi"
```

### Search

```bash
# Keyword search
vtic search "CORS wildcard misconfiguration"

# Query plus filters
vtic search "auth issues" --severity high --repo "ejacklab/*"
```

### List & Filter

```bash
vtic list --repo "ejacklab/open-dsearch"
vtic list --severity critical
vtic list --status open --category security
```

### Update

```bash
vtic update --id C1 --status fixed
vtic update --id C1 --severity high --description "Updated after partial fix"
```

### Delete

```bash
vtic delete --id C1 --yes
```

## API Server

Run vtic as an HTTP API:

```bash
vtic serve --host 0.0.0.0 --port 8900
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/tickets` | Create a ticket |
| `GET` | `/tickets/:id` | Get a ticket |
| `PATCH` | `/tickets/:id` | Update a ticket |
| `DELETE` | `/tickets/:id` | Delete a ticket |
| `POST` | `/search` | Keyword search with filters and pagination |
| `GET` | `/tickets` | List with filters |

### Example

`/search` currently supports keyword search only. `semantic`, `sort_by`, and `sort_order` are planned but not implemented yet.

```bash
curl -X POST http://localhost:8900/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "auth security issues",
    "filters": {
      "severity": ["critical"],
      "status": ["open"]
    },
    "topk": 10
  }'
```

## Ticket File Structure

Tickets are stored as markdown files organized in 5 levels:

```
tickets/
└── {owner}/                    # 1
    └── {repo}/                 # 2
        └── {category}/         # 3
            └── {ticket_id}.md  # 4
```

Example:

```
tickets/
└── ejacklab/
    └── open-dsearch/
        ├── security/
        │   └── C1-cors-wildcard.md
        ├── auth/
        │   └── H1-duplicated-auth-functions.md
        └── code_quality/
            └── C3-sys-path-hack.md
```

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

## Configuration

Create `vtic.toml` in your project root or `~/.config/vtic/config.toml` globally:

```toml
[tickets]
dir = "./tickets"

[search]
# Search configuration schema used by the implementation
bm25_enabled = true
semantic_enabled = false
embedding_provider = "openai"  # "openai" | "local" | "none"
embedding_model = "text-embedding-3-small"
embedding_dimensions = 1536
hybrid_weights_bm25 = 0.7
hybrid_weights_semantic = 0.3

[server]
host = "127.0.0.1"
port = 8900
```

### Embedding Providers

#### OpenAI

```bash
export OPENAI_API_KEY="sk-..."
```

```toml
[search]
embedding_provider = "openai"
embedding_model = "text-embedding-3-small"
embedding_dimensions = 1536
```

#### Local Model

No API key needed. Uses `sentence-transformers`:

```bash
pip install vtic[local-embeddings]
```

```toml
[search]
embedding_provider = "local"
embedding_model = "all-MiniLM-L6-v2"
embedding_dimensions = 384
```

#### No Embeddings

Just use `vtic` as-is. Keyword search works out of the box.

## Architecture

- **Markdown files** are the source of truth.
- **TicketStore** handles on-disk CRUD.
- **TicketSearch** provides in-process keyword search over stored tickets.
- **API and CLI** expose the same ticket lifecycle operations.

## API Design

When designing or extending the vtic REST API, always refer to the [OpenAPI Specification](https://swagger.io/specification/) first. All endpoints must follow OpenAPI 3.1 conventions.

## Built With

- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API server
- [Typer](https://typer.tiangolo.com/) — CLI interface
- [Pydantic](https://docs.pydantic.dev/) — Data validation

## License

[MIT](LICENSE)
