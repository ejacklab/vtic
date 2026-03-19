# vtic — Execution Plan

**Version:** 1.0  
**Date:** 2026-03-18  
**Scope:** v0.1 — 35 Core features, ~6 days  
**Agents:** 3 Kimi 2.5 (code) + GLM-5 (review) per task wave  

---

## Agent Assignment Strategy

| Role | Model | Task | Why |
|------|-------|------|-----|
| **Coder** | Kimi 2.5 | Implementation | Cost-effective, good Python, needs clear specs |
| **Reviewer** | GLM-5 | Review + fix | Catches gaps, ensures quality |
| **Architect** | GLM-5 | Complex design | Requirements, integration planning |

### Rules
1. Kimi writes the code following exact specs from data model stages
2. GLM-5 reviews and fixes before merge
3. Each task is independent — no task depends on uncommitted work
4. Tasks within a phase can run in parallel
5. All tasks get unit tests

---

## Wave 1: Foundation (Day 1-2)

### T1 — Scaffolding
**Agent:** Kimi 2.5 (single, fast)
**Time:** ~15 min
**Dependencies:** None

Deliverables:
- `pyproject.toml` with all deps (zvec, fastapi, uvicorn, typer, pydantic, orjson, aiofiles, toml)
- Package structure: `src/vtic/` with all modules (empty `__init__.py` files)
- `.gitignore`, `vtic.toml` (default config)
- `pip install -e .` succeeds
- `pytest` runs (empty suite, 0 tests)

Spec reference: `data-models-stage5-config.md` (config schema), `data-models-stage6-errors-map.md` (module map)

Verification:
```bash
cd /tmp/vtic && pip install -e . && pytest && vtic --help
```

---

### T2 — Enums + Errors + Config
**Agent:** Kimi 2.5
**Time:** ~20 min
**Dependencies:** T1

Deliverables:
- `src/vtic/models/enums.py` — Category, Severity, Status, EmbeddingProvider, DeleteMode, SortField, SortOrder
- `src/vtic/errors.py` — VticError, ErrorDetail, ErrorObject, ErrorResponse, error code constants
- `src/vtic/models/config.py` — Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig, load_config()
- `src/vtic/__init__.py` — version, public API exports

Spec reference: `data-models-stage1-enums.md`, `data-models-stage5-config.md`, `data-models-stage6-errors-map.md`

Tests:
- Test all enum values and default
- Test config loading (default, file, env var override)
- Test error response serialization

---

### T3 — Ticket Models
**Agent:** Kimi 2.5
**Time:** ~20 min
**Dependencies:** T2

Deliverables:
- `src/vtic/models/ticket.py` — Ticket, TicketCreate, TicketUpdate, TicketResponse, TicketSummary
- `src/vtic/models/__init__.py` — re-exports

Spec reference: `data-models-stage2-ticket.md`

Tests:
- Test TicketCreate validation (required fields, defaults)
- Test TicketUpdate (at least one field, partial update detection)
- Test ID pattern validation `^[CFGHST]\d+$`
- Test slug generation from title
- Test TicketResponse serialization

---

### T4 — Search + API Response Models
**Agent:** Kimi 2.5
**Time:** ~20 min
**Dependencies:** T2, T3

Deliverables:
- `src/vtic/models/search.py` — SearchQuery, FilterSet, SearchHit, SearchResult, SearchMeta, SuggestResult
- `src/vtic/models/api.py` — PaginatedResponse, PaginationMeta, HealthResponse, IndexStatus, EmbeddingProviderInfo, StatsResponse, StatsTotals, ReindexResult, DoctorResult, DoctorCheck

Spec reference: `data-models-stage3-search.md`, `data-models-stage4-api.md`

Tests:
- Test SearchQuery validation (limit 1-100, sort format)
- Test FilterSet (arrays for multi-select)
- Test ErrorResponse nested structure
- Test all response models serialize to JSON

---

### Wave 1 Review
**Agent:** GLM-5
**Time:** ~15 min
**After:** T2, T3, T4 all complete

Review:
- All Pydantic models match OpenAPI spec exactly
- All enums import from models/enums.py (no duplicates)
- Config loading precedence correct
- No circular imports
- Tests pass

---

## Wave 2: Store + Index (Day 2-3)

### T5 — Markdown Store
**Agent:** Kimi 2.5
**Time:** ~30 min
**Dependencies:** T3

Deliverables:
- `src/vtic/store/paths.py` — ticket_file_path(), resolve_path(), trash_path()
- `src/vtic/store/markdown.py` — ticket_to_markdown(), markdown_to_ticket(), write_ticket(), read_ticket(), delete_ticket(), list_tickets()
- Atomic write (temp file + rename)
- Recursive directory scanning

Spec reference: `data-models-stage2-ticket.md` (Ticket → markdown format), `DATA_FLOWS_OPERATIONS.md` (create/read/update/delete flows)

Tests:
- Test write → read roundtrip
- Test frontmatter parsing
- Test atomic write (no partial files)
- Test list tickets with filtering
- Test delete (soft + hard)
- Test recursive scan

---

### T6 — Zvec Index
**Agent:** Kimi 2.5
**Time:** ~30 min
**Dependencies:** T3, T5

Deliverables:
- `src/vtic/index/schema.py` — Zvec CollectionSchema (scalar fields + BM25 sparse vector)
- `src/vtic/index/client.py` — open_collection(), create_collection(), destroy_collection(), optimize()
- `src/vtic/index/operations.py` — insert_ticket(), upsert_ticket(), update_ticket(), delete_ticket(), fetch_ticket(), query()

Spec reference: `DATA_FLOWS_OPERATIONS.md` (Zvec operations), Zvec API docs, `data-models-stage3-search.md` (query format)

Tests:
- Test schema creation
- Test insert → fetch roundtrip
- Test BM25 search query
- Test filter expressions
- Test delete from index
- Test rebuild from markdown files (reindex)

---

### Wave 2 Review
**Agent:** GLM-5
**Time:** ~15 min
**After:** T5, T6 complete

Review:
- Markdown store matches Ticket model fields exactly
- Zvec schema matches scalar fields from OpenAPI
- BM25 query returns correct format
- Atomic write verified
- Tests pass

---

## Wave 3: Ticket Service + CRUD API (Day 3-4)

### T7 — Ticket Service (Orchestrator)
**Agent:** Kimi 2.5
**Time:** ~25 min
**Dependencies:** T5, T6

Deliverables:
- `src/vtic/ticket.py` — create_ticket(), get_ticket(), update_ticket(), delete_ticket(), list_tickets(), reindex_all()
- Orchestrates markdown store + Zvec index
- ID generation (category prefix + sequence)
- Slug generation from title
- Timestamp auto-fill

Spec reference: `DATA_FLOWS_OPERATIONS.md` (all CRUD flows), `DATA_FLOWS_DETAILED.md` (step-by-step walkthroughs)

Tests:
- Test create → get roundtrip (file + index)
- Test update → verify both file and index updated
- Test delete → verify both removed
- Test reindex from disk
- Test ID sequence incrementing

---

### T8 — Ticket CRUD API Routes
**Agent:** Kimi 2.5
**Time:** ~25 min
**Dependencies:** T4, T7

Deliverables:
- `src/vtic/api/app.py` — FastAPI app, lifespan (init Zvec on startup)
- `src/vtic/api/deps.py` — get_ticket_service(), get_config()
- `src/vtic/api/routes/tickets.py` — POST/GET/PATCH/DELETE /tickets, GET /tickets (list)
- Error handlers (VticError → ErrorResponse)

Spec reference: `openapi-stages/stage2-crud.yaml`, `data-models-stage4-api.md`

Tests:
- Test POST /tickets → 201 with TicketResponse
- Test GET /tickets/:id → 200
- Test PATCH /tickets/:id → 200
- Test DELETE /tickets/:id → 200
- Test GET /tickets with filters
- Test 404 for missing ticket
- Test 400 for invalid input
- Test error response format

---

### Wave 3 Review
**Agent:** GLM-5
**Time:** ~15 min
**After:** T7, T8 complete

Review:
- API responses match OpenAPI schemas exactly
- Error codes correct (VALIDATION_ERROR, NOT_FOUND, etc.)
- File + index stay in sync
- ID generation follows category prefixes
- Integration test: full create → read → update → delete flow

---

## Wave 4: Search + System (Day 4-5)

### T9 — Search Engine
**Agent:** Kimi 2.5
**Time:** ~30 min
**Dependencies:** T6

Deliverables:
- `src/vtic/search/bm25.py` — BM25 search using Zvec's BM25EmbeddingFunction
- `src/vtic/search/engine.py` — search_tickets(), build_filter_expression()
- Filter expression builder (FilterSet → Zvec SQL-like filter)

Spec reference: `data-models-stage3-search.md`, `openapi-stages/stage2-search.yaml`, `DATA_FLOWS_OPERATIONS.md` (search flow)

Tests:
- Test BM25 keyword search
- Test search with filters (severity, status, category, repo)
- Test sort (relevance, -created, severity)
- Test pagination (limit + offset)
- Test empty query rejection

---

### T10 — Search API Route
**Agent:** Kimi 2.5
**Time:** ~15 min
**Dependencies:** T4, T9

Deliverables:
- `src/vtic/api/routes/search.py` — POST /search

Spec reference: `openapi-stages/stage2-search.yaml`

Tests:
- Test POST /search → ranked results
- Test with filters
- Test pagination
- Test SearchMeta in response
- Test 400 for empty query

---

### T11 — System API Routes
**Agent:** Kimi 2.5
**Time:** ~15 min
**Dependencies:** T4, T7

Deliverables:
- `src/vtic/api/routes/system.py` — GET /health, GET /stats, GET /config, POST /reindex, GET /doctor

Spec reference: `openapi-stages/stage1-foundation.yaml`, `openapi-stages/stage3-bulk.yaml`

Tests:
- Test GET /health → HealthResponse
- Test GET /stats → StatsResponse
- Test POST /reindex → ReindexResult
- Test GET /doctor → DoctorResult

---

### Wave 4 Review
**Agent:** GLM-5
**Time:** ~15 min
**After:** T9, T10, T11 complete

Review:
- Search response matches OpenAPI (hits, not results; ticket_id, not ticket object)
- Health/Stats/Reindex responses match schemas
- Filter expressions produce correct Zvec queries
- No leftover old field names

---

## Wave 5: CLI + Integration (Day 5-6)

### T12 — CLI
**Agent:** Kimi 2.5
**Time:** ~20 min
**Dependencies:** T8, T10, T11

Deliverables:
- `src/vtic/cli/main.py` — Typer app
- `vtic init` — create dirs, init Zvec, write default config
- `vtic serve` — start uvicorn
- `vtic create` — create ticket (calls API)
- `vtic get` — get ticket
- `vtic search` — search tickets

Spec reference: `BUILD_PLAN.md` T4

Tests:
- Test `vtic init` creates directory structure
- Test CLI commands parse arguments correctly

---

### T13 — Integration Tests
**Agent:** GLM-5
**Time:** ~20 min
**Dependencies:** All above

Deliverables:
- `tests/test_integration.py` — full API integration tests
- Test the complete lifecycle: init → create → search → update → delete → reindex → health

---

### T14 — Performance Benchmarks
**Agent:** Kimi 2.5
**Time:** ~15 min
**Dependencies:** T8, T10

Deliverables:
- `tests/test_performance.py` — benchmark suite
- Verify: <10ms BM25, <50ms hybrid, <5ms CRUD, <5s reindex for 10K

---

## Wave 5 Review (Final)
**Agent:** GLM-5
**Time:** ~20 min
**After:** T12, T13, T14

Final verification:
- All endpoints match OpenAPI spec
- All models match OpenAPI schemas
- No old field names anywhere in codebase
- Tests pass (unit + integration + performance)
- `pip install -e .` works
- `vtic init && vtic serve` works
- Performance targets met

---

## Summary

| Wave | Tasks | Agents | Time | Days |
|------|-------|--------|------|------|
| 1. Foundation | T1-T4 + Review | 3 Kimi + 1 GLM-5 | ~90 min | 1-2 |
| 2. Store + Index | T5-T6 + Review | 2 Kimi + 1 GLM-5 | ~75 min | 2-3 |
| 3. CRUD API | T7-T8 + Review | 2 Kimi + 1 GLM-5 | ~65 min | 3-4 |
| 4. Search + System | T9-T11 + Review | 3 Kimi + 1 GLM-5 | ~90 min | 4-5 |
| 5. CLI + Integration | T12-T14 + Review | 2 Kimi + 1 GLM-5 | ~55 min | 5-6 |

**Total: 14 tasks, ~6 days of agent time**

---

## Parallelism Map

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

## Notes

- Each Kimi agent gets exact spec file references and test requirements
- GLM-5 reviews after each wave — catches issues early
- T5 and T6 can run in parallel (store and index are independent)
- T9, T10, T11 can overlap (search engine + system routes are independent)
- All code goes to `/tmp/vtic/src/vtic/`
- Design docs are the contract — coding agents MUST follow them
