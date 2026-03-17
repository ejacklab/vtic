# vtic — Build Plan

**Focus:** Ship a working, maintainable, fast ticket system. Nothing more.

---

## Phase 1: Core (T1–T4)

> The thing works end-to-end. CLI + BM25 search. No API, no embeddings, no extras.

### T1 — Scaffolding
- [ ] `pyproject.toml` (zvec, typer, pydantic)
- [ ] Package structure `src/vtic/`
- [ ] `.gitignore`, example `vtic.toml`
- [ ] `pip install -e .` works

### T2 — Markdown Store
- [ ] Ticket → markdown file write (4-level path)
- [ ] Markdown file → ticket read (frontmatter + body)
- [ ] Update, delete, list, rebuild from disk
- [ ] Tests

### T3 — Zvec Index
- [ ] Schema + BM25 sparse vector + inverted indexes
- [ ] Insert, upsert, update, delete, fetch
- [ ] Rebuild from markdown files
- [ ] Tests

### T4 — CLI + BM25 Search
- [ ] `vtic init`, `vtic create`, `vtic get`, `vtic update`, `vtic delete`, `vtic list`
- [ ] `vtic search <query>` — BM25 keyword search
- [ ] Filter flags: `--severity`, `--status`, `--repo`, `--category`
- [ ] `--json` output flag
- [ ] Tests

**Checkpoint:** MVP works. Can create tickets, search them, manage lifecycle.

---

## Phase 2: API (T5–T6)

> HTTP API so any agent/tool/curl can use it.

### T5 — FastAPI Server
- [ ] `POST /tickets`, `GET /tickets/:id`, `PATCH /tickets/:id`, `DELETE /tickets/:id`
- [ ] `GET /tickets` with query params
- [ ] Input validation, error responses
- [ ] Tests

### T6 — Search API
- [ ] `POST /search` — `{ query, filters, topk }`
- [ ] `GET /health` — index stats
- [ ] Tests

**Checkpoint:** API works. Agents can integrate.

---

## Phase 3: Semantic Search (T7–T8)

> Optional upgrade. Pluggable embedding providers.

### T7 — Embedding Abstraction
- [ ] `EmbeddingProvider` interface
- [ ] OpenAI provider
- [ ] Local provider (sentence-transformers)
- [ ] Auto-detect from config, skip if not configured
- [ ] Tests

### T8 — Hybrid Search
- [ ] Dense vector insert alongside BM25
- [ ] `WeightedReRanker` for BM25 + dense
- [ ] `--semantic` flag on CLI, `semantic: true` on API
- [ ] Tests

**Checkpoint:** Full hybrid search works. Zero-config BM25 + optional semantic.

---

## Phase 4: Ship (T9–T10)

> Tests, CI, publish.

### T9 — Tests & CI
- [ ] Unit tests (store, index, search)
- [ ] Integration tests (CLI, API)
- [ ] GitHub Actions (lint, test, Python 3.10–3.12)
- [ ] Coverage report

### T10 — Publish
- [ ] Build wheels
- [ ] Test `pip install vtic` from wheel
- [ ] Publish to PyPI

---

## Priorities

```
T1 → T2 → T3 → T4 → T5 → T6 → T9 → T10 → T7 → T8
         │              │              │
         └──────────────┘──────────────┘
          MVP: works     Ship: tested   Semantic: optional
```

**MVP = T1–T4.** Everything else follows.

---

## What We're NOT Building (Yet)

- ❌ Web UI
- ❌ RAG / auto-suggestions
- ❌ Email-to-ticket
- ❌ Plugin system
- ❌ Webhooks
- ❌ Status workflows
- ❌ Ticket linking
- ❌ Export/import
- ❌ Rate limiting / auth

These are all valid features. They're not v0.1.
