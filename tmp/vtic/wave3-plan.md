# Wave 3 Implementation Plan

> **Phase: Implementation Plan Only** — File ownership, task breakdown, test plan. No implementation code.

---

## 1. Task Breakdown

### Task A: Search Engine + BM25 Integration (Agent A)
**Estimated Time: 15-20 min**

#### Files to Create/Modify
1. **`src/vtic/search/__init__.py`** (create/modify)
   - Export `SearchEngine` class
2. **`src/vtic/search/engine.py`** (implement)
   - `SearchEngine.__init__(collection)` — Initialize with Zvec collection
   - `SearchEngine.search(query, request_id)` → `SearchResult` — Main search
   - `SearchEngine.suggest(partial, limit)` → `list[SuggestResult]` — Autocomplete
   - `_build_filter_dict(filters)` — Convert FilterSet → zvec filter dict
   - `_normalize_score(raw_score)` — Normalize BM25 to 0.0-1.0 range
   - `_generate_highlight(ticket_id, query, content)` — Extract matching snippet
   - `_apply_min_score(hits, min_score)` — Filter low scores
   - `_apply_sort(hits, sort)` — Sort by field with `-` prefix support

#### Key Implementation Details
- **Sync methods** (SearchEngine is pure CPU/index, no I/O)
- Uses `operations.query_tickets()` internally
- Min-max scaling for score normalization: `(score - min) / (max - min)`
- Highlight: Find query term in description, extract surrounding context
- Sort support: `score`, `created`, `updated`, `severity` with `-` prefix for desc

#### Dependencies
```python
from typing import Optional
from zvec import Collection
from vtic.models.search import SearchQuery, SearchResult, SearchHit, SearchMeta, FilterSet, SuggestResult
from vtic.index.operations import query_tickets
import time
```

---

### Task B: Search Routes (Agent B)
**Estimated Time: 15-20 min**

#### Files to Create/Modify
1. **`src/vtic/api/routes/search.py`** (implement)
   - `POST /search` → `search_tickets()` — Hybrid BM25 search
   - `GET /search/suggest` → `suggest_search()` — Autocomplete suggestions

#### Endpoint Definitions

**`POST /search`**
```python
@router.post(
    "",
    response_model=SearchResult,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Semantic search unavailable"},
    },
    summary="Hybrid search for tickets",
)
async def search_tickets(
    request: Request,
    query: SearchQuery,
    explain: bool = Query(default=False, description="Show scoring breakdown"),
    engine: SearchEngine = Depends(get_search_engine),
) -> SearchResult:
```

**`GET /search/suggest`**
```python
@router.get(
    "/suggest",
    response_model=list[SuggestResult],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid query parameter"},
    },
    summary="Get autocomplete suggestions",
)
async def suggest_search(
    q: str = Query(..., min_length=2, max_length=100, description="Partial query"),
    limit: int = Query(default=5, ge=1, le=20, description="Max suggestions"),
    engine: SearchEngine = Depends(get_search_engine),
) -> list[SuggestResult]:
```

#### How it Connects to SearchEngine
- Uses `get_search_engine()` dependency from `deps.py` (Task C creates this)
- Calls `engine.search(query, request_id)` where `request_id` comes from `request.state.request_id`
- Calls `engine.suggest(q, limit)` for suggestions
- Wraps sync SearchEngine calls (FastAPI handles this fine)

#### Dependencies
```python
from fastapi import APIRouter, Depends, Query, Request
from vtic.models.search import SearchQuery, SearchResult, SuggestResult
from vtic.models.api import ErrorResponse
from vtic.search.engine import SearchEngine
from ..deps import get_search_engine
```

---

### Task C: System Routes + SystemService + Dependencies (Agent C)
**Estimated Time: 15-20 min**

#### Files to Create/Modify

**1. `src/vtic/services/__init__.py` (create)**
   - Export `SystemService`

**2. `src/vtic/services/system.py` (create)**
   - `SystemService.__init__(config, ticket_service)` — Initialize with deps
   - `SystemService.health(version, uptime_seconds)` → `HealthResponse` — Health check
   - `SystemService.stats(by_repo)` → `StatsResponse` — Ticket statistics
   - `SystemService.reindex()` → `ReindexResult` — Rebuild search index
   - `SystemService.doctor()` → `DoctorResult` — Diagnostic checks
   - Private helpers: `_check_zvec_index()`, `_check_config_file()`, `_check_embedding_provider()`, `_check_file_permissions()`, `_check_ticket_files()`

**3. `src/vtic/api/routes/system.py` (implement)**
   - `GET /health` → `get_health()` — Health check endpoint
   - `GET /stats` → `get_stats()` — Ticket statistics
   - `POST /reindex` → `reindex()` — Rebuild search index
   - `GET /doctor` → `run_doctor()` — Diagnostic checks

**4. `src/vtic/api/deps.py` (modify)** — ADD new dependencies:
   - `get_search_engine(config)` → `SearchEngine`
   - `get_system_service(config, ticket_service)` → `SystemService`

**5. `src/vtic/api/app.py` (modify)** — REGISTER new routers:
   - Add `search.router` with prefix `/search`
   - Add `system.router` (no prefix, tags=["System", "Management"])

#### Endpoint Definitions

**`GET /health`**
```python
@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "System unhealthy"}},
    summary="Health check endpoint",
)
async def get_health(
    request: Request,
    service: SystemService = Depends(get_system_service),
) -> HealthResponse | JSONResponse:
```

**`GET /stats`**
```python
@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get ticket statistics",
)
async def get_stats(
    by_repo: bool = Query(default=False, description="Include repo breakdown"),
    service: SystemService = Depends(get_system_service),
) -> StatsResponse:
```

**`POST /reindex`**
```python
@router.post(
    "/reindex",
    response_model=ReindexResult,
    responses={500: {"model": ErrorResponse, "description": "Reindex failed"}},
    summary="Rebuild search index",
)
async def reindex(
    service: SystemService = Depends(get_system_service),
) -> ReindexResult:
```

**`GET /doctor`**
```python
@router.get(
    "/doctor",
    response_model=DoctorResult,
    summary="Run diagnostic checks",
)
async def run_doctor(
    service: SystemService = Depends(get_system_service),
) -> DoctorResult:
```

#### How SystemService Connects
- `health()` — Checks `collection` status, calls `ticket_service.count_tickets()`, reads `config.embeddings`
- `stats()` — Calls `ticket_service.list_tickets()` with high limit, aggregates counts
- `reindex()` — Delegates to `ticket_service.reindex_all()`
- `doctor()` — Runs checks on collection, config, filesystem

---

## 2. File Ownership Table

| Task | Agent | Owns Files (WRITE ONLY THESE) | Reads |
|------|-------|------------------------------|-------|
| **A** | Agent A | `src/vtic/search/__init__.py`<br>`src/vtic/search/engine.py` | `src/vtic/index/operations.py`<br>`src/vtic/models/search.py` |
| **B** | Agent B | `src/vtic/api/routes/search.py` | `src/vtic/search/engine.py`<br>`src/vtic/models/search.py`<br>`src/vtic/models/api.py`<br>`src/vtic/api/deps.py` (to understand interface) |
| **C** | Agent C | `src/vtic/services/__init__.py`<br>`src/vtic/services/system.py`<br>`src/vtic/api/routes/system.py`<br>`src/vtic/api/deps.py`<br>`src/vtic/api/app.py` | `src/vtic/ticket.py` (TicketService)<br>`src/vtic/models/config.py`<br>`src/vtic/models/api.py`<br>`src/vtic/index/client.py` (get_collection) |

**IMPORTANT**: Only Agent C modifies `app.py` and `deps.py`. The dependencies added in `deps.py` are used by Agent B's routes.

---

## 3. Test Plan

### Task A: Search Engine Tests
**Test File: `tests/test_search_engine.py`**

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_search_basic` | query="database", limit=10 | Returns SearchResult with hits, total >= 0, meta.latency_ms > 0 |
| `test_search_with_filters` | query="error", filters={severity: ["critical"]} | Only critical severity tickets in results |
| `test_search_min_score` | query="xyz", min_score=0.5 | Hits all have score >= 0.5 |
| `test_search_sort_created` | query="test", sort="-created" | Hits sorted by created desc |
| `test_search_sort_score` | query="test", sort="-score" | Hits sorted by score desc |
| `test_search_empty_query` | query="" | Returns empty hits, total=0 |
| `test_search_no_results` | query="nonexistentxyz123" | Returns empty hits, total=0 |
| `test_normalize_score` | raw_scores [0, 5, 10] | normalized [0.0, 0.5, 1.0] |
| `test_suggest_basic` | partial="cor", limit=5 | Returns list of SuggestResult, each has suggestion and ticket_count |
| `test_suggest_min_length` | partial="c" | Returns empty list or raises validation error |
| `test_highlight_generation` | query="database", content="..." | Returns snippet containing "database" |

**Integration Test Updates**: Update `tests/test_integration.py`:
- Add `test_search_endpoint` — POST /search returns SearchResult
- Add `test_suggest_endpoint` — GET /search/suggest returns suggestions

---

### Task B: Search Routes Tests
**Test File: `tests/test_routes_search.py`**

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_post_search_success` | {"query": "test", "limit": 10} | 200 OK, SearchResult schema |
| `test_post_search_validation_error` | {"query": ""} | 400 BAD REQUEST, ErrorResponse schema |
| `test_post_search_explain_mode` | {"query": "test"}, explain=true | Hits contain bm25_score field |
| `test_post_search_semantic_unavailable` | {"query": "test", "semantic": true} when no provider | 503 SERVICE UNAVAILABLE |
| `test_get_suggest_success` | ?q=test&limit=5 | 200 OK, list[SuggestResult] |
| `test_get_suggest_min_length` | ?q=x | 400 BAD REQUEST |
| `test_get_suggest_max_limit` | ?q=test&limit=50 | 400 BAD REQUEST (max 20) |
| `test_search_request_id_propagation` | Any valid query | Response meta contains request_id matching request |

**Integration Test Updates**: Update `tests/test_integration.py`:
- Add `test_search_api_integration` — Full flow: create ticket → search → verify found

---

### Task C: System Routes + Service Tests
**Test Files: `tests/test_system_service.py`, `tests/test_routes_system.py`**

**SystemService Tests (`test_system_service.py`):**

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_health_healthy` | version="0.1.0", uptime=3600 | status="healthy", index_status.zvec="available" |
| `test_health_degraded` | index unavailable | status="degraded" or "unhealthy" |
| `test_stats_basic` | by_repo=false | StatsResponse with totals, by_status, by_severity, by_category, by_repo=None |
| `test_stats_with_repo` | by_repo=true | StatsResponse with by_repo populated |
| `test_stats_empty_index` | no tickets | totals.all=0, all breakdowns empty |
| `test_reindex_success` | existing tickets | ReindexResult with processed > 0, failed=0 |
| `test_doctor_all_ok` | healthy system | overall="ok", all checks status="ok" |
| `test_doctor_with_warnings` | missing embedding provider | overall="warnings", embedding_provider check has warning |

**System Routes Tests (`test_routes_system.py`):**

| Test Case | Input | Expected Output |
|-----------|-------|-----------------|
| `test_get_health_success` | GET /health | 200 OK, HealthResponse schema |
| `test_get_health_unhealthy_status` | When index corrupted | 503 SERVICE UNAVAILABLE |
| `test_get_stats_success` | GET /stats | 200 OK, StatsResponse schema |
| `test_get_stats_by_repo` | GET /stats?by_repo=true | by_repo field populated |
| `test_post_reindex_success` | POST /reindex | 200 OK, ReindexResult schema |
| `test_post_reindex_auth` | POST /reindex (if auth added later) | 401/403 if unauthenticated |
| `test_get_doctor_success` | GET /doctor | 200 OK, DoctorResult schema |
| `test_get_doctor_shows_errors` | When index corrupted | overall="errors", error checks present |

**Integration Test Updates**: Update `tests/test_integration.py`:
- Add `test_health_endpoint` — GET /health returns valid response
- Add `test_stats_endpoint` — GET /stats returns aggregated counts
- Add `test_reindex_endpoint` — POST /reindex rebuilds index
- Add `test_doctor_endpoint` — GET /doctor runs diagnostics

---

## 4. Router Registration Plan

### Changes to `src/vtic/api/app.py` (OWNED BY AGENT C)

```python
# Add imports at top
from .routes import tickets, search, system

# In create_app() function, after existing router:
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(system.router, tags=["System", "Management"])
```

### Dependencies to Add in `src/vtic/api/deps.py` (OWNED BY AGENT C)

```python
# Add at top
from vtic.search.engine import SearchEngine
from vtic.services.system import SystemService
from vtic.index.client import get_collection

# Add new dependency functions

def get_search_engine(
    config: Config = Depends(get_config),
) -> SearchEngine:
    """Get SearchEngine instance."""
    collection = get_collection(config.storage.dir)
    return SearchEngine(collection)


def get_system_service(
    config: Config = Depends(get_config),
    ticket_service: TicketService = Depends(get_ticket_service),
) -> SystemService:
    """Get SystemService instance."""
    return SystemService(config, ticket_service)
```

---

## 5. Acceptance Criteria

### POST /search
| Criteria | Required |
|----------|----------|
| Request format matches `SearchQuery` schema | ✅ Must validate with Pydantic |
| Response format matches `SearchResult` schema | ✅ Must include query, hits[], total, meta |
| Status 200 on success | ✅ |
| Status 400 on validation error (empty query, invalid sort) | ✅ ErrorResponse with code="VALIDATION_ERROR" |
| Status 503 when semantic=True but no provider | ✅ ErrorResponse with code="SERVICE_UNAVAILABLE" |
| hits[].score is 0.0-1.0 | ✅ Normalized BM25 scores |
| meta.latency_ms is present and > 0 | ✅ Timing in milliseconds |
| explain=true adds bm25_score to hits | ✅ Optional field |
| request_id propagated from request.state | ✅ meta.request_id matches |

### GET /search/suggest
| Criteria | Required |
|----------|----------|
| Query param `q` required, min_length=2 | ✅ 400 if < 2 chars |
| Query param `limit` default=5, max=20 | ✅ Clamp to valid range |
| Response is `list[SuggestResult]` | ✅ Each has suggestion, ticket_count |
| Status 200 on success | ✅ |
| Status 400 on invalid params | ✅ ErrorResponse |

### GET /health
| Criteria | Required |
|----------|----------|
| Response matches `HealthResponse` schema | ✅ status, version, uptime_seconds, index_status, embedding_provider |
| Status 200 when healthy or degraded | ✅ |
| Status 503 when unhealthy | ✅ When index_status.zvec="corrupted" |
| index_status.zvec is "available"|"unavailable"|"corrupted" | ✅ |
| embedding_provider null when not configured | ✅ |

### GET /stats
| Criteria | Required |
|----------|----------|
| Response matches `StatsResponse` schema | ✅ totals, by_status, by_severity, by_category, by_repo?, date_range? |
| Query param `by_repo` default=false | ✅ |
| by_repo=null when by_repo=false | ✅ |
| by_repo populated when by_repo=true | ✅ Dict[str, int] |
| Status 200 on success | ✅ |

### POST /reindex
| Criteria | Required |
|----------|----------|
| Response matches `ReindexResult` schema | ✅ processed, skipped, failed, duration_ms, errors |
| Calls TicketService.reindex_all() | ✅ Delegates properly |
| Status 200 on success | ✅ |
| Status 500 on failure | ✅ If reindex raises exception |

### GET /doctor
| Criteria | Required |
|----------|----------|
| Response matches `DoctorResult` schema | ✅ overall, checks[] |
| overall is "ok"|"warnings"|"errors" | ✅ Aggregated from checks |
| Checks include: zvec_index, config_file, embedding_provider, file_permissions, ticket_files | ✅ All 5 checks |
| Each check has name, status, message, fix | ✅ DoctorCheck schema |
| Status 200 always (even with errors) | ✅ Errors shown in body, not HTTP status |

---

## 6. Implementation Order

**Parallel Execution:**
1. **Agent A** starts: Implements SearchEngine (no dependencies on other agents)
2. **Agent C** starts: Implements SystemService, deps, app.py changes
3. **Agent B** waits for Agent A + C completion signal, then implements Search Routes

**Alternative (if strict parallelism needed):**
- Agent A and Agent C can work in parallel
- Agent B needs SearchEngine from A and get_search_engine from C
- Have Agent C create stub `get_search_engine()` that raises NotImplementedError
- Agent B implements routes assuming dependencies exist
- Final integration test validates everything works

---

## 7. Notes for Implementers

### Score Normalization
```python
def _normalize_score(self, raw_score: float, all_scores: list[float]) -> float:
    """Min-max normalize to 0.0-1.0 range."""
    if not all_scores or max(all_scores) == min(all_scores):
        return 1.0 if raw_score > 0 else 0.0
    return (raw_score - min(all_scores)) / (max(all_scores) - min(all_scores))
```

### Highlight Generation
- Find query terms in description
- Extract ~100 chars around the match
- Add ellipsis if truncated
- Handle multiple matches (pick best score)

### Suggest Implementation
- Query index with partial + "*" wildcard
- Group results by title prefix
- Count occurrences per group
- Return top N by count

### Health Status Logic
```python
if index_status.zvec == "corrupted":
    overall = "unhealthy"
elif index_status.zvec == "unavailable" or embedding_provider is None:
    overall = "degraded"
else:
    overall = "healthy"
```

### Doctor Checks
1. **zvec_index**: Try collection.fetch("C1") or collection.count()
2. **config_file**: Validate Config loads without errors
3. **embedding_provider**: Check config.embeddings.provider != "none"
4. **file_permissions**: os.access(base_dir, os.W_OK)
5. **ticket_files**: Scan for markdown files with invalid frontmatter

---

*End of Wave 3 Plan*
