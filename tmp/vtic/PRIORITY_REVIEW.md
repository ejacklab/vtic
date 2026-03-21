# vtic — Priority Review Summary

**Reviewed by:** 3 GLM-5 agents  
**Total features reviewed:** ~200  
**Principle:** Default is DOWN. Only Core if removing it breaks the product.

---

## Totals

| Priority | Count | What Ships When |
|----------|-------|-----------------|
| **Core** | 35 | v0.1 — product doesn't exist without these |
| **Must Have** | 79 | Pre-v1.0 — production-ready requires these |
| **Should Have** | 84 | Post-v1.0 — important but not blocking |
| **Good to Have** | 70 | Backlog — polish and nice-to-haves |

---

## v0.1 Scope (35 Core Features)

These are the ONLY features that ship in v0.1:

### Ticket Lifecycle (13 Core)
- CLI ticket creation
- Auto-generated IDs
- Timestamp auto-fill
- Required field validation
- Get by ID
- Field-level updates (CLI)
- Delete ticket (CLI)
- Built-in statuses (open, fixed, wont_fix, etc.)

### Search (6 Core)
- BM25 full-text search
- Equality filters (severity, status, category, repo)
- Sort by field
- Sort by relevance (search score)
- Limit/offset pagination

### Storage (6 Core)
- Hierarchical directory structure
- Human-readable markdown format
- Git compatibility
- Atomic writes
- In-process Zvec index
- Rebuild index from source

### API (4 Core)
- Search endpoint (`POST /search`)
- Health check (`GET /health`)
- JSON responses
- Consistent error envelope

### CLI (4 Core)
- Core commands (init, create, get, update, delete, list, search, serve)
- JSON output format
- Debug mode
- No-color mode

### Configuration (1 Core)
- Sensible defaults (zero-config works)

### Security (1 Core)
- Input validation

**Everything else is Must Have or below.**

---

## Key Downgrades (P0 → Not Core)

| Feature | Old | New | Reason |
|---------|-----|-----|--------|
| API ticket creation | P0 | Must Have | CLI is primary interface |
| Semantic search | P0 | Must Have | BM25 alone is viable |
| Soft delete | P0 | Must Have | Hard delete works |
| All REST CRUD endpoints | P0 | Must Have | API is secondary |
| Incremental indexing | P0 | Must Have | Full rebuild works |
| Embedding on write | P0 | Must Have | BM25 works without embeddings |
| Config files | P0 | Must Have | Defaults work |
| OpenAI provider | P0 | Must Have | BM25-only is valid |
| Local provider | P0 | Must Have | Optional upgrade |
| Pagination metadata | P0 | Must Have | Simple limit/offset sufficient |

---

## Full Review Files

- `/tmp/vtic/review-agent1.md` — Categories 1-5 (Lifecycle, Search, Storage, API, CLI)
- `/tmp/vtic/review-agent2.md` — Categories 6-9 (Config, Embeddings, Multi-Repo, Integration)
- `/tmp/vtic/review-agent3.md` — Categories 10-13 (Performance, Security, Export/Import, DX)
