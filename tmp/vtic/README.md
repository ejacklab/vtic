# vtic

> Lightweight, local-first ticket system with vector search. Built on [Zvec](https://github.com/alibaba/zvec).

**Zero infrastructure.** No database server, no Docker, no cloud service. `pip install vtic` and go.

---

## 🚀 Quick Setup (For Non-Developers)

### Step 1: Install Python

Make sure you have Python 3.10 or newer installed.

```bash
python3 --version
```

If you see `Python 3.10.x` or higher, you're good. If not, install Python from [python.org](https://www.python.org/downloads/).

### Step 2: Install uv (Package Manager)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Step 3: Clone and Install vtic

```bash
# Download the code
git clone https://github.com/661818yijack/vtic.git
cd vtic

# Create virtual environment with Python 3.12
uv venv --python 3.12

# Activate it
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate     # Windows

# Install vtic
uv pip install -e ".[dev]"
```

### Step 4: Test It Works

```bash
vtic --help
```

You should see a list of commands like `init`, `create`, `list`, `search`, etc.

### Step 5: Start Using vtic

```bash
# 1. Create a project folder
mkdir my-tickets
cd my-tickets

# 2. Initialize vtic (creates config file + tickets directory)
vtic init .

# 3. Start the server (MUST run from same directory as vtic.toml)
vtic serve

# 4. In another terminal, go to same folder and create a ticket
cd my-tickets
vtic create --repo "myproject/app" --title "My first ticket"
```

**Important:** Always run `vtic serve` from the same directory where you ran `vtic init`. The `vtic.toml` config file tells vtic where to store tickets.

That's it! You're ready to use vtic.

### Troubleshooting

**If you see `ModuleNotFoundError: No module named 'vtic.index'`:**

This means the package isn't installed correctly. Follow these steps **from the vtic repo root**:

```bash
# 1. Go to vtic repo (where pyproject.toml is)
cd /path/to/vtic   # <-- MUST be in the vtic directory!

# 2. Verify you're in the right place
ls pyproject.toml  # Should show the file

# 3. Recreate venv from scratch
rm -rf .venv
uv venv --python 3.12
source .venv/bin/activate

# 4. Install fresh
uv pip install -e ".[dev]"

# 5. Verify installation
python -c "from vtic.index import client; print('OK')"
python -c "from vtic.ticket import TicketService; print('OK')"
```

If both commands print `OK`, the installation is correct.

**If `vtic serve` fails with TOML errors:**

```bash
# Delete old config and re-init
rm vtic.toml
vtic init .
```

---

## Why vtic?

Traditional ticket systems store issues in databases — great for CRUD, terrible for search. Finding "all auth-related security issues across 5 repos" means reading every ticket, every label, every description.

**vtic** stores tickets as markdown files on disk (durable, git-trackable) and indexes them with Zvec for instant hybrid search:

- **Keyword search** (BM25) — exact matches on ticket IDs, file paths, error codes. Built-in, zero config.
- **Semantic search** (dense embeddings) — find tickets by meaning, not just keywords. Optional, plug in any embedding provider.

No web UI needed. No browser tab open. Just an API and a CLI.

## Features

- 🚀 **Hybrid search** — BM25 + dense vectors in a single query
- 📁 **Markdown files** — tickets live on disk, git-friendly, human-readable
- 🔍 **Semantic queries** — "show me all CORS-related issues" without exact keywords
- 🏷️ **Structured filtering** — filter by repo, severity, status, category, date
- 🔌 **Pluggable embeddings** — bring your own (OpenAI, local model, or skip entirely)
- ⚡ **In-process** — no server to manage, just Python
- 📦 **Multi-repo** — organize tickets across any number of repositories

## Quick Start

### Install

```bash
pip install vtic
```

### Initialize

```bash
# Create a project folder first
mkdir my-vtic-project
cd my-vtic-project

# Initialize vtic in current directory
vtic init .
```

This creates:
- `vtic.toml` — config file (must stay in this folder)
- `tickets/` — where ticket markdown files are stored

**Tip:** Always run `vtic serve` and `vtic create` from the same directory as `vtic.toml`.

### Create a Ticket

```bash
vtic create \
  --repo "ejacklab/open-dsearch" \
  --category "security" \
  --severity "critical" \
  --title "CORS Wildcard in Production" \
  --description "All FastAPI services use allow_origins=['*']..." \
  --file "backend/api-gateway/main.py:27-32" \
  --fix "Use ALLOWED_ORIGINS from env..."
```

### Search

```bash
# Keyword search (BM25, built-in, no config needed)
vtic search "CORS wildcard misconfiguration"

# Filter by fields
vtic search --severity critical --status open

# Semantic search (requires embedding provider)
vtic search "authentication vulnerabilities" --semantic

# Combined: semantic + filters
vtic search "auth issues" --semantic --severity high --repo "ejacklab/*"
```

### List & Filter

```bash
vtic list --repo "ejacklab/open-dsearch"
vtic list --severity critical
vtic list --status open --category security
```

### Update

```bash
vtic update C1 --status fixed
vtic update C1 --severity high --description "Updated after partial fix"
```

### Delete

```bash
vtic delete C1
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
| `POST` | `/search` | Hybrid search |
| `GET` | `/tickets` | List with filters |

### Example

```bash
curl -X POST http://localhost:8900/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "auth security issues",
    "semantic": true,
    "filters": {
      "severity": "critical",
      "status": "open"
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
# C1 - CORS Wildcard in Production

**Severity:** critical
**Status:** open
**Category:** security
**Repo:** ejacklab/open-dsearch
**File:** backend/api-gateway/main.py:27-32
**Created:** 2026-03-16
**Updated:** 2026-03-16

## Description
All FastAPI services use allow_origins=['*'] which enables CSRF attacks.

## Fix
Use ALLOWED_ORIGINS from environment variable:

```python
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
```
```

## Configuration

Create `vtic.toml` in your project root or `~/.config/vtic/config.toml` globally:

```toml
[tickets]
dir = "./tickets"

[search]
# BM25 is always enabled (zero config)
# Dense embeddings are optional
enable_semantic = true
embedding_provider = "openai"  # "openai" | "local" | "custom"
embedding_model = "text-embedding-3-small"
embedding_dimensions = 1536

[api]
host = "127.0.0.1"
port = 8900
```

### Embedding Providers

#### OpenAI (recommended)

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

#### No Embeddings (BM25 only)

Just use `vtic` as-is. Keyword search works out of the box.

---

### Semantic Search (Coming November 2026)

Semantic search is **not implemented yet**. Why?

- BM25 covers 95% of use cases for technical tickets
- Embedding API costs add up at scale
- Waiting for token prices to drop further

**Planned:** November 2026, when embedding costs are projected to be 10x cheaper.

If you need semantic search now, you can implement `search/semantic.py` yourself — the hooks are already in place.

---

## Architecture

```
┌─────────────────────────────────┐
│           vtic API / CLI         │
│   (FastAPI + Typer)             │
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
- **API** hides all implementation details — callers never see Zvec or embeddings

## API Design

When designing or extending the vtic REST API, always refer to the [OpenAPI Specification](https://swagger.io/specification/) first. All endpoints must follow OpenAPI 3.1 conventions.

## Built With

- [Zvec](https://github.com/alibaba/zvec) — In-process vector database by Alibaba (Proxima engine)
- [FastAPI](https://fastapi.tiangolo.com/) — HTTP API server
- [Typer](https://typer.tiangolo.com/) — CLI interface
- [Pydantic](https://docs.pydantic.dev/) — Data validation

## License

[MIT](LICENSE)
