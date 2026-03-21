# Architecture Patterns and Decisions

**Project:** vtic — AI-first ticketing system
**Source:** coding-standards.md, EXECUTION_PLAN.md, BUILD_PLAN.md

---

## Core Architecture Principles

### 1. Local-First, Single User

vtic is designed for **single-user, local-first** operation:

- No authentication required
- No rate limiting
- No multi-tenancy
- All data stored locally in markdown files + Zvec index

**Rationale:** AI agents need fast, programmatic access to tickets without auth overhead. Git handles collaboration.

### 2. Dual Storage: Markdown + Vector Index

Every ticket exists in two places:

```
┌─────────────────────────────────────────────────────────┐
│                    CREATE/UPDATE                         │
│                         │                                │
│           ┌─────────────┴─────────────┐                 │
│           ▼                           ▼                 │
│   ┌───────────────┐          ┌───────────────┐          │
│   │  Markdown     │          │  Zvec Index   │          │
│   │  (source of   │◄────────►│  (search)     │          │
│   │   truth)      │  reindex │               │          │
│   └───────────────┘          └───────────────┘          │
│           │                           │                 │
│           ▼                           ▼                 │
│      Git versioning            BM25 + dense             │
│      Human-readable             vectors                 │
└─────────────────────────────────────────────────────────┘
```

**Rules:**
- Markdown is the **source of truth**
- Zvec index can always be rebuilt from markdown (`vtic reindex`)
- Both must be updated atomically on create/update/delete
- Index corruption = rebuild from markdown, not the other way

### 3. In-Process Vector DB (Zvec)

**Decision:** Use [Zvec](https://github.com/alibaba/zvec) for vector storage.

**Why Zvec:**
- In-process (no Docker, no server)
- File-based persistence
- 8500+ QPS for BM25 search
- Alibaba-backed (Proxima engine)
- Python + npm packages

**What NOT to use:**
- ❌ Qdrant — requires server
- ❌ Pinecone — cloud-only
- ❌ Weaviate — heavy setup
- ❌ ChromaDB — lower performance

### 4. Layered Architecture

```
┌─────────────────────────────────────────────┐
│              CLI (Typer)                     │
├─────────────────────────────────────────────┤
│              REST API (FastAPI)              │
├─────────────────────────────────────────────┤
│           Ticket Service (Orchestrator)      │
├──────────────────────┬──────────────────────┤
│    Markdown Store    │      Zvec Index      │
│   (async file I/O)   │   (BM25 + vectors)   │
└──────────────────────┴──────────────────────┘
```

**Rules:**
- CLI and API both use `TicketService` — no direct store/index access
- `TicketService` orchestrates both storage layers atomically
- Store and Index are independent modules that can be tested separately

---

## Design Doc Hierarchy

### The Problem

When multiple agents write design docs independently, contradictions accumulate:

- **58 contradictions** found in vtic Wave 1 across 6+ independently-written docs
- Enums defined differently in OpenAPI vs data models
- Field types mismatched between specs

### The Solution: Canonical Source First

```
Phase 1: Canonical Source (Sequential)
  1. One agent writes OpenAPI spec (or chosen canonical)
  2. One agent reviews it
  3. Commit as canonical

Phase 2: Parallel Generation
  1. Spawn 3-4 agents, each producing one doc:
     - Data models (align to OpenAPI)
     - Data flows (align to OpenAPI + data models)
     - Breakdown (align to all above)
     - Config schema (align to all above)
  2. Each agent READS the canonical before writing

Phase 3: Cross-Review
  1. Spawn 2-3 review agents (GLM-5)
  2. Each reviewer checks one doc against canonical
  3. Output: numbered list of contradictions

Phase 4: Reconcile
  1. Fix all contradictions
  2. Only then start coding
```

### Rules

- **OpenAPI is canonical** — If it exists, all other docs align to its schemas exactly
- **Field names must match** — `ticket_id` in OpenAPI = `ticket_id` in models, not `id`
- **Types must match** — If OpenAPI says `type: [string, null]`, models use `str | None`
- **Enums must match** — Same values, same order, same defaults
- **Cross-reference before coding** — Run GLM-5 reviews to find contradictions

---

## Wave-Based Execution

### Wave Structure

Development is organized into **waves** of related tasks:

| Wave | Tasks | Focus | Time |
|------|-------|-------|------|
| 1 | T1-T4 | Foundation (scaffolding, enums, models) | Day 1-2 |
| 2 | T5-T6 | Store + Index | Day 2-3 |
| 3 | T7-T8 | Ticket Service + CRUD API | Day 3-4 |
| 4 | T9-T11 | Search + System APIs | Day 4-5 |
| 5 | T12-T14 | CLI + Integration Tests | Day 5-6 |

### Parallelism Map

```
Wave 1 (sequential within):
  T1 ──→ T2 ──→ T3 ──→ T4 ──→ [Review]

Wave 2 (parallel):
  T5 (store) ═══╦═══→ [Review]
  T6 (index) ═══╝

Wave 3 (sequential):
  T7 (service) ──→ T8 (routes) ──→ [Review]

Wave 4 (parallel):
  T9 (search engine) ──→ T10 (search route) ──→ [Review]
  T11 (system routes) ═══════════════════════╝

Wave 5 (parallel):
  T12 (CLI) ═══╦═══→ [Final Review]
  T13 (integ) ═╣
  T14 (perf) ══╝
```

---

## Agent Assignment Strategy

| Role | Model | Task | Why |
|------|-------|------|-----|
| **Coder** | Kimi 2.5 | Implementation | Cost-effective, good Python, needs clear specs |
| **Reviewer** | GLM-5 | Review + fix | Catches gaps, ensures quality |
| **Architect** | GLM-5 | Complex design | Requirements, integration planning |

### Rules

1. Kimi writes the code following exact specs from design docs
2. GLM-5 reviews and fixes before merge
3. Each task is independent — no task depends on uncommitted work
4. Tasks within a phase can run in parallel
5. All tasks get unit tests

---

## Embedding Architecture

### Provider Interface

```python
class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        ...
```

### Supported Providers

| Provider | Dimension | Use Case |
|----------|-----------|----------|
| **Local** (sentence-transformers) | 384-768 | Development, no API costs |
| **OpenAI** (text-embedding-3-small) | 1536 | Production, high quality |
| **Custom HTTP** | Configurable | Self-hosted models |

### Auto-Fallback

```
No provider configured → BM25 only, no errors
Provider configured → Hybrid search (BM25 + dense)
```

---

## Search Architecture

### Hybrid Search Pipeline

```
Query
  │
  ├─── BM25 Search (sparse) ────┐
  │                              │
  └─── Semantic Search (dense) ──┼─── WeightedReRanker ──── Ranked Results
                                 │
                            (configurable weights)
```

### Performance Targets

| Operation | Target | Method |
|-----------|--------|--------|
| BM25 search | < 10ms | Zvec sparse index |
| Hybrid search | < 50ms | BM25 + dense + rerank |
| CRUD | < 5ms | Direct file read + index update |
| Batch create (100) | < 500ms | Bulk insert + async I/O |
| Reindex (10K) | < 5s | Full scan + bulk insert |

---

## Key Architecture Decisions

### Decision 1: Markdown as Source of Truth

**Context:** Need human-readable, git-compatible storage.

**Options:**
1. SQLite only — fast but binary, not git-friendly
2. Markdown + SQLite — dual write complexity
3. Markdown + Zvec — human-readable + fast search

**Decision:** Option 3. Markdown is source of truth, Zvec is search index.

**Trade-offs:**
- (+) Git-friendly, human-readable
- (+) Can rebuild index from files
- (-) Dual write required on every operation

### Decision 2: In-Process vs Client-Server Vector DB

**Context:** Need fast vector search without infrastructure overhead.

**Options:**
1. Qdrant (Docker) — full-featured but needs container
2. Pinecone (cloud) — managed but external dependency
3. Zvec (in-process) — lightweight, fast, no server

**Decision:** Option 3. Zvec for local-first deployment.

**Trade-offs:**
- (+) No Docker, no server process
- (+) 8500+ QPS, file-based persistence
- (-) Single-process only (not distributed)

### Decision 3: Async All the Way

**Context:** Need high performance for API endpoints.

**Decision:** Async file I/O (aiofiles) + async FastAPI handlers.

**Trade-offs:**
- (+) Non-blocking I/O, higher throughput
- (+) Consistent with FastAPI patterns
- (-) Slightly more complex code

---

## Anti-Patterns (What NOT to Do)

### ❌ Reinventing the Wheel

Before building any component:
1. Search GitHub for existing solutions
2. Check PyPI for mature packages
3. Evaluate vs custom build

**Example:** Use Zvec instead of building custom vector indexing.

### ❌ Specs in Code Comments

Design decisions belong in:
- Design docs (OpenAPI, data models)
- ADRs (Architecture Decision Records)
- MEMORY.md (lessons learned)

NOT in inline comments that drift from reality.

### ❌ Dual-Source Truth

Never have two sources of truth. If markdown + Zvec disagree:
1. Markdown wins (it's the source of truth)
2. Rebuild Zvec from markdown
3. Investigate how they got out of sync

---

## References

- `EXECUTION_PLAN.md` — Task breakdown and agent assignment
- `BUILD_PLAN.md` — Phase structure and priorities
- `DATA_FLOWS.md` — Data flow diagrams
- `DATA_MODELS.md` — Schema definitions
- `openapi.yaml` — Canonical API specification
