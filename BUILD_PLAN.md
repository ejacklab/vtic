# vtic — Build Plan & Tickets

**Project:** https://github.com/661818yijack/vtic  
**Created:** 2026-03-17  
**Status:** Planning → Building

---

## Phase 1: Foundation

### T1 — Project scaffolding
- [ ] Create `pyproject.toml` with dependencies (zvec, fastapi, typer, pydantic)
- [ ] Create package structure (`src/vtic/`)
- [ ] Add `.gitignore`, `vtic.toml` example config
- [ ] Verify `pip install -e .` works

### T2 — Markdown ticket store
- [ ] Implement `TicketStore` class — CRUD for markdown files
- [ ] 4-level path: `tickets/{owner}/{repo}/{category}/{id}.md`
- [ ] Frontmatter parsing/writing (severity, status, category, repo, file, dates)
- [ ] Generate ticket content from structured data
- [ ] Parse ticket content back to structured data
- [ ] Rebuild index from markdown files (scan disk)

### T3 — Zvec index
- [ ] Implement `TicketIndex` class — wraps Zvec
- [ ] Schema: scalar fields (repo, severity, status, category, file, title, created_at) + BM25 sparse vector
- [ ] `create_and_open` on init, `open` on subsequent runs
- [ ] Inverted indexes on severity, status, repo, category
- [ ] Insert, upsert, update, delete, fetch, delete_by_filter
- [ ] `optimize()` after bulk inserts

---

## Phase 2: Search

### T4 — BM25 search (keyword, zero config)
- [ ] `BM25EmbeddingFunction` integration for query encoding
- [ ] Sparse vector insert on ticket create/update
- [ ] Keyword search via `collection.query()` with sparse vector
- [ ] Combined filter + keyword search (e.g. `severity = "critical" AND bm25 match`)

### T5 — Semantic search (dense embeddings, optional)
- [ ] Abstract `EmbeddingProvider` interface
- [ ] OpenAI provider (`text-embedding-3-small`, 1536 dim)
- [ ] Local provider (`sentence-transformers`, `all-MiniLM-L6-v2`, 384 dim)
- [ ] Config-driven: auto-detect provider from `vtic.toml`
- [ ] Skip entirely if no provider configured
- [ ] Dense vector insert on ticket create/update (if provider exists)

### T6 — Hybrid search
- [ ] Combine BM25 + dense vectors in single query
- [ ] `WeightedReRanker` with configurable weights
- [ ] Unified `POST /search` endpoint and `vtic search` CLI
- [ ] Filter syntax: `severity = "critical" AND status = "open"`

---

## Phase 3: CLI

### T7 — CLI core commands
- [ ] `vtic init <dir>` — create storage + index
- [ ] `vtic create --repo --category --severity --title --description --file --fix` — create ticket
- [ ] `vtic get <id>` — show ticket details
- [ ] `vtic update <id> --status --severity --description` — update fields
- [ ] `vtic delete <id>` — remove ticket (file + index)
- [ ] `vtic list [--repo] [--severity] [--status] [--category]` — filter & list

### T8 — CLI search
- [ ] `vtic search <query>` — BM25 keyword search
- [ ] `vtic search <query> --semantic` — enable dense vector search
- [ ] `vtic search <query> --severity X --status Y` — combined filters
- [ ] Pretty-print results (table or JSON with `--json` flag)

---

## Phase 4: API Server

### T9 — FastAPI server
- [ ] `vtic serve --host --port`
- [ ] `POST /tickets` — create
- [ ] `GET /tickets/:id` — read
- [ ] `PATCH /tickets/:id` — update
- [ ] `DELETE /tickets/:id` — delete
- [ ] `GET /tickets?repo=X&severity=Y&status=Z` — list with query params

### T10 — Search API
- [ ] `POST /search` — `{ query, semantic?, filters, topk }`
- [ ] `GET /search?q=X&severity=Y` — simple search via query params
- [ ] Unified response: `{ results: [{ id, score, title, severity, status, ... }] }`
- [ ] Input validation with Pydantic models

### T11 — Health & stats
- [ ] `GET /health` — index status, ticket count, uptime
- [ ] `GET /stats` — tickets by severity, by status, by repo

---

## Phase 5: Polish

### T12 — Tests
- [ ] Unit tests for TicketStore (CRUD, parsing, path generation)
- [ ] Unit tests for TicketIndex (insert, query, update, delete, rebuild)
- [ ] Integration tests for API (all endpoints)
- [ ] Integration tests for CLI (all commands)
- [ ] Test coverage report

### T13 — CI/CD
- [ ] GitHub Actions workflow (lint, test, build)
- [ ] Test matrix: Python 3.10, 3.11, 3.12

### T14 — Documentation
- [ ] API reference (OpenAPI auto-generated from FastAPI)
- [ ] Configuration guide
- [ ] Embedding provider setup guide
- [ ] Contributing guide

### T15 — Publish
- [ ] Build wheels (`build` package)
- [ ] Test `pip install vtic` from local wheel
- [ ] Publish to PyPI (when ready)

---

## Priority Order

```
T1 → T2 → T3 → T4 → T7 → T9 → T10 → T12 → T13 → T14 → T15
                 ↓         ↓
                 T5 → T6 → T8 → T11
```

**MVP (minimum viable product):** T1 → T2 → T3 → T4 → T7 — CLI with BM25 keyword search, no embeddings, no API.

**Full release:** All tickets complete.

---

## Notes

- Zvec requires Linux x86_64/ARM64 or macOS ARM64 (no Windows native)
- BM25 works out of the box — no API keys, no config, no external deps
- Dense embeddings are purely optional
- Markdown files are the source of truth, Zvec is the search index
- Rebuilding index from disk is always possible (defensive design)
