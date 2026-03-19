# Wave 3 Design: Search Engine + Routes

> **Phase: Design Only** — Interfaces, contracts, method signatures. No implementation.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API Layer                                      │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────┐  │
│  │ routes/search.py    │  │ routes/system.py    │  │ routes/tickets  │  │
│  │ POST /search        │  │ GET  /health        │  │ (exists)        │  │
│  │ GET  /search/suggest│  │ GET  /stats         │  │                 │  │
│  └─────────┬───────────┘  │ POST /reindex       │  └─────────────────┘  │
│            │              │ GET  /doctor        │                        │
│            │              └─────────┬───────────┘                        │
└────────────┼────────────────────────┼────────────────────────────────────┘
             │                        │
┌────────────┼────────────────────────┼────────────────────────────────────┐
│            ▼            Service Layer                                    │
│  ┌─────────────────┐   ┌─────────────────┐                              │
│  │ SearchEngine    │   │ SystemService   │                              │
│  │ (new)           │   │ (new)           │                              │
│  └────────┬────────┘   └────────┬────────┘                              │
│           │                     │                                        │
└───────────┼─────────────────────┼────────────────────────────────────────┘
            │                     │
┌───────────┼─────────────────────┼────────────────────────────────────────┐
│           ▼           Index Layer                                        │
│  ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────────┐    │
│  │ operations.py   │   │ client.py       │   │ SimpleBM25Encoder   │    │
│  │ query_tickets() │   │ get_collection()│   │ (in operations.py)  │    │
│  │ (exists)        │   │ (exists)        │   │ (exists)            │    │
│  └─────────────────┘   └─────────────────┘   └─────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **SearchEngine** wraps `operations.query_tickets()` with model-aware interface
2. **SystemService** aggregates health/stats/doctor logic (no new index layer code)
3. **Routes** are thin — they call services, handle errors, return responses
4. **Models** already exist in `models/search.py` and `models/api.py`

---

## 2. Sync vs Async Decisions

| Component | Mode | Rationale |
|-----------|------|-----------|
| `SearchEngine.search()` | **SYNC** | Wraps sync `operations.query_tickets()`. No I/O benefit to async. FastAPI routes can `await` sync functions via `run_in_executor` if needed, but overhead is negligible for search latency. |
| `SearchEngine.suggest()` | **SYNC** | Simple index scan, no external API calls. |
| `SystemService.health()` | **ASYNC** | FastAPI route pattern, may check external services in future. |
| `SystemService.stats()` | **ASYNC** | Calls `TicketService.count_tickets()` which is async. |
| `SystemService.reindex()` | **ASYNC** | Calls `TicketService.reindex_all()` which is async. |
| `SystemService.doctor()` | **ASYNC** | May involve file I/O checks, follows route pattern. |

**Decision**: SearchEngine is sync (pure CPU + index). SystemService is async (matches routes + existing TicketService).

---

## 3. Method Signatures

### 3.1 SearchEngine (`src/vtic/search/engine.py`)

```python
from __future__ import annotations

from typing import Optional
from zvec import Collection

from vtic.models.search import (
    SearchQuery,
    SearchResult,
    SearchHit,
    SearchMeta,
    FilterSet,
    SuggestResult,
)


class SearchEngine:
    """
    Higher-level search interface wrapping index operations.
    
    Responsibilities:
    - Convert SearchQuery model → zvec query parameters
    - Build filter expressions from FilterSet
    - Format results into SearchHit + SearchMeta
    - Track latency_ms timing
    - Handle highlight generation
    
    Thread-safe: Each instance holds no mutable state beyond the Collection reference.
    """
    
    def __init__(self, collection: Collection) -> None:
        """
        Initialize search engine with a Zvec collection.
        
        Args:
            collection: Zvec collection for ticket search.
        """
        ...
    
    def search(
        self,
        query: SearchQuery,
        request_id: Optional[str] = None,
    ) -> SearchResult:
        """
        Execute a search query.
        
        Args:
            query: SearchQuery model with all parameters.
            request_id: Optional request ID for tracing.
            
        Returns:
            SearchResult with hits, total, and metadata.
            
        Raises:
            ServiceUnavailableError: If semantic=True but no embedding provider configured.
            
        Notes:
            - Calls operations.query_tickets() internally
            - Applies min_score filtering post-search
            - Handles sort field normalization
            - Calculates latency_ms in metadata
        """
        ...
    
    def suggest(
        self,
        partial: str,
        limit: int = 5,
    ) -> list[SuggestResult]:
        """
        Get autocomplete suggestions for partial query.
        
        Args:
            partial: Partial query string (min 2 chars).
            limit: Maximum suggestions to return (1-20, default 5).
            
        Returns:
            List of SuggestResult with matching ticket titles/phrases.
            
        Notes:
            - Uses BM25 prefix matching on ticket titles
            - Groups by title, counts occurrences
        """
        ...
    
    # --- Private helpers ---
    
    def _build_filter_dict(self, filters: Optional[FilterSet]) -> Optional[dict]:
        """Convert FilterSet to dict for operations.query_tickets()."""
        ...
    
    def _normalize_score(self, raw_score: float) -> float:
        """Normalize BM25 score to 0.0-1.0 range."""
        ...
    
    def _generate_highlight(
        self,
        ticket_id: str,
        query: str,
        content: str,
    ) -> Optional[str]:
        """Extract best matching snippet for highlight."""
        ...
    
    def _apply_min_score(
        self,
        hits: list[SearchHit],
        min_score: float,
    ) -> list[SearchHit]:
        """Filter hits below min_score threshold."""
        ...
    
    def _apply_sort(
        self,
        hits: list[SearchHit],
        sort: str,
    ) -> list[SearchHit]:
        """Sort hits by field (with - prefix for descending)."""
        ...
```

### 3.2 SystemService (`src/vtic/services/system.py`)

```python
from __future__ import annotations

from datetime import datetime
from typing import Optional

from vtic.models.api import (
    HealthResponse,
    StatsResponse,
    ReindexResult,
    DoctorResult,
    DoctorCheck,
)
from vtic.models.config import Config


class SystemService:
    """
    System-level operations: health, stats, reindex, diagnostics.
    
    Aggregates data from:
    - TicketService (for counts and reindex)
    - Zvec collection (for index status)
    - Config (for embedding provider info)
    - File system (for doctor checks)
    """
    
    def __init__(
        self,
        config: Config,
        ticket_service: "TicketService",  # forward reference
    ) -> None:
        """
        Initialize system service.
        
        Args:
            config: Application configuration.
            ticket_service: TicketService instance for counts/reindex.
        """
        ...
    
    async def health(
        self,
        version: str,
        uptime_seconds: Optional[int],
    ) -> HealthResponse:
        """
        Get system health status.
        
        Checks:
        - Zvec index availability
        - Ticket count in index
        - Last reindex timestamp
        - Embedding provider status
        
        Args:
            version: API version string.
            uptime_seconds: Server uptime in seconds.
            
        Returns:
            HealthResponse with nested index_status and embedding_provider.
        """
        ...
    
    async def stats(
        self,
        by_repo: bool = False,
    ) -> StatsResponse:
        """
        Get ticket statistics.
        
        Aggregates:
        - Total counts (all, open, closed)
        - By status, severity, category
        - Optionally by repo
        - Date range (earliest/latest created)
        
        Args:
            by_repo: Include by_repo breakdown (default False).
            
        Returns:
            StatsResponse with nested totals and breakdowns.
        """
        ...
    
    async def reindex(self) -> ReindexResult:
        """
        Rebuild the search index from markdown files.
        
        Delegates to TicketService.reindex_all().
        
        Returns:
            ReindexResult with processed/skipped/failed counts.
        """
        ...
    
    async def doctor(self) -> DoctorResult:
        """
        Run diagnostic checks.
        
        Checks:
        - zvec_index: Index health and accessibility
        - config_file: Configuration validity
        - embedding_provider: Provider configuration status
        - file_permissions: Write permissions on tickets directory
        - ticket_files: Scan for malformed markdown files
        
        Returns:
            DoctorResult with overall status and individual checks.
        """
        ...
    
    # --- Private helpers ---
    
    async def _check_zvec_index(self) -> DoctorCheck:
        """Check Zvec index health."""
        ...
    
    async def _check_config_file(self) -> DoctorCheck:
        """Check configuration validity."""
        ...
    
    async def _check_embedding_provider(self) -> DoctorCheck:
        """Check embedding provider configuration."""
        ...
    
    async def _check_file_permissions(self) -> DoctorCheck:
        """Check file system permissions."""
        ...
    
    async def _check_ticket_files(self) -> DoctorCheck:
        """Scan for malformed ticket files."""
        ...
```

---

## 4. File Ownership Table

| Agent/Phase | Owns Files | May Read | Notes |
|-------------|------------|----------|-------|
| **Wave 3 (This Phase)** | `src/vtic/search/engine.py` (new) | `index/operations.py`, `models/search.py`, `models/api.py` | SearchEngine implementation |
| | `src/vtic/search/__init__.py` (new) | — | Exports SearchEngine |
| | `src/vtic/services/system.py` (new) | `ticket.py`, `models/config.py`, `store/` | SystemService implementation |
| | `src/vtic/api/routes/search.py` (new) | `search/engine.py`, `models/search.py`, `deps.py` | Search routes |
| | `src/vtic/api/routes/system.py` (new) | `services/system.py`, `models/api.py`, `deps.py` | System routes |
| **Existing (Read-Only)** | `index/operations.py` | — | query_tickets(), SimpleBM25Encoder |
| | `models/search.py` | — | SearchQuery, SearchResult, etc. |
| | `models/api.py` | — | HealthResponse, StatsResponse, etc. |
| | `ticket.py` | — | TicketService |
| | `api/app.py` | — | FastAPI app (may need router registration) |
| **BM25** | No new file | — | Logic stays in operations.py |

### BM25 File Decision

**No separate `bm25.py` needed.**

Reasoning:
- `SimpleBM25Encoder` is already in `operations.py` and works correctly
- It's an internal implementation detail of `query_tickets()`
- No external API exposure required
- Moving it would add complexity without benefit
- If semantic search is added later, embedding logic would be separate, not BM25

---

## 5. Data Flow Per Endpoint

### 5.1 POST /search

```
Request (SearchQuery JSON)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/search.py:search_tickets()                               │
│   - Parse SearchQuery from body                                 │
│   - Get SearchEngine from deps                                  │
│   - Call engine.search(query, request_id)                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SearchEngine.search()                                           │
│   1. Start timer                                                │
│   2. Build filter dict from FilterSet                           │
│   3. Call operations.query_tickets(                             │
│        collection, query.query, filters, limit, offset)         │
│   4. Convert results to SearchHit list                          │
│   5. Normalize scores to 0.0-1.0                                │
│   6. Generate highlights                                        │
│   7. Apply min_score filter                                     │
│   8. Apply sort (if not -score)                                 │
│   9. Build SearchMeta with latency_ms                           │
│  10. Return SearchResult                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (SearchResult JSON)
    - query: str
    - hits: list[SearchHit]
    - total: int
    - meta: SearchMeta
```

**Error Cases:**
- `400 VALIDATION_ERROR`: Empty/missing query
- `503 SERVICE_UNAVAILABLE`: semantic=True but no embedding provider

### 5.2 GET /search/suggest

```
Request (?q=partial&limit=5)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/search.py:suggest_search()                               │
│   - Validate q param (min 2 chars)                              │
│   - Call engine.suggest(q, limit)                               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SearchEngine.suggest()                                          │
│   1. Query tickets with partial as prefix                       │
│   2. Group by title                                             │
│   3. Count occurrences                                          │
│   4. Return list[SuggestResult]                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (list[SuggestResult] JSON)
    - [{suggestion: str, ticket_count: int}, ...]
```

### 5.3 GET /health

```
Request (no body)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/system.py:get_health()                                   │
│   - Get SystemService from deps                                 │
│   - Get version from app.state                                  │
│   - Calculate uptime from app start time                        │
│   - Call service.health(version, uptime)                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SystemService.health()                                          │
│   1. Check Zvec collection status                               │
│   2. Get ticket count                                           │
│   3. Get last reindex timestamp                                 │
│   4. Check embedding provider config                            │
│   5. Build HealthResponse                                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (HealthResponse JSON)
    - status: "healthy" | "degraded" | "unhealthy"
    - version: str
    - uptime_seconds: int | null
    - index_status: {zvec, ticket_count, last_reindex}
    - embedding_provider: {name, model, dimension} | null
```

**HTTP Status Mapping:**
- `200 OK`: status is "healthy" or "degraded"
- `503 Service Unavailable`: status is "unhealthy"

### 5.4 GET /stats

```
Request (?by_repo=false)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/system.py:get_stats()                                    │
│   - Get SystemService from deps                                 │
│   - Call service.stats(by_repo)                                 │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SystemService.stats()                                           │
│   1. Get all tickets from TicketService                         │
│   2. Count by status, severity, category                        │
│   3. Optionally count by repo                                   │
│   4. Find date range (earliest/latest)                          │
│   5. Build StatsResponse                                        │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (StatsResponse JSON)
    - totals: {all, open, closed}
    - by_status: dict[str, int]
    - by_severity: dict[str, int]
    - by_category: dict[str, int]
    - by_repo: dict[str, int] | null
    - date_range: {earliest, latest} | null
```

### 5.5 POST /reindex

```
Request (no body)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/system.py:reindex()                                      │
│   - Get SystemService from deps                                 │
│   - Call service.reindex()                                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SystemService.reindex()                                         │
│   1. Delegate to TicketService.reindex_all()                    │
│   2. Convert result to ReindexResult model                      │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (ReindexResult JSON)
    - processed: int
    - skipped: int
    - failed: int
    - duration_ms: int
    - errors: list[{ticket_id, message}]
```

### 5.6 GET /doctor

```
Request (no body)
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ routes/system.py:run_doctor()                                   │
│   - Get SystemService from deps                                 │
│   - Call service.doctor()                                       │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│ SystemService.doctor()                                          │
│   1. Run checks in order:                                       │
│      - _check_zvec_index()                                      │
│      - _check_config_file()                                     │
│      - _check_embedding_provider()                              │
│      - _check_file_permissions()                                │
│      - _check_ticket_files()                                    │
│   2. Aggregate results                                          │
│   3. Determine overall status                                   │
│   4. Build DoctorResult                                         │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
Response (DoctorResult JSON)
    - overall: "ok" | "warnings" | "errors"
    - checks: list[{name, status, message, fix}]
```

---

## 6. Route Definitions

### 6.1 Search Routes (`src/vtic/api/routes/search.py`)

```python
from fastapi import APIRouter, Depends, Query, Request

from vtic.models.search import SearchQuery, SearchResult, SuggestResult
from vtic.models.api import ErrorResponse
from vtic.search.engine import SearchEngine
from ..deps import get_search_engine

router = APIRouter()


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
    """Execute hybrid BM25 + semantic search."""
    ...


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
    """Get typeahead suggestions based on partial query."""
    ...
```

### 6.2 System Routes (`src/vtic/api/routes/system.py`)

```python
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from vtic.models.api import (
    HealthResponse,
    StatsResponse,
    ReindexResult,
    DoctorResult,
    ErrorResponse,
)
from vtic.services.system import SystemService
from ..deps import get_system_service, get_config

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={
        503: {"model": HealthResponse, "description": "System unhealthy"},
    },
    summary="Health check endpoint",
)
async def get_health(
    request: Request,
    service: SystemService = Depends(get_system_service),
) -> HealthResponse | JSONResponse:
    """Get system health status."""
    ...


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Get ticket statistics",
)
async def get_stats(
    by_repo: bool = Query(default=False, description="Include repo breakdown"),
    service: SystemService = Depends(get_system_service),
) -> StatsResponse:
    """Get aggregated ticket statistics."""
    ...


@router.post(
    "/reindex",
    response_model=ReindexResult,
    responses={
        500: {"model": ErrorResponse, "description": "Reindex failed"},
    },
    summary="Rebuild search index",
)
async def reindex(
    service: SystemService = Depends(get_system_service),
) -> ReindexResult:
    """Rebuild the search index from markdown files."""
    ...


@router.get(
    "/doctor",
    response_model=DoctorResult,
    summary="Run diagnostic checks",
)
async def run_doctor(
    service: SystemService = Depends(get_system_service),
) -> DoctorResult:
    """Run system diagnostic checks."""
    ...
```

---

## 7. Dependency Injection Updates (`src/vtic/api/deps.py`)

Add new dependencies:

```python
from vtic.search.engine import SearchEngine
from vtic.services.system import SystemService
from vtic.index.client import get_collection


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

## 8. App Router Registration (`src/vtic/api/app.py`)

Add new routers:

```python
from .routes import tickets, search, system

# In create_app():
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(search.router, prefix="/search", tags=["Search"])
app.include_router(system.router, tags=["System", "Management"])
```

---

## 9. OpenAPI Compliance Notes

### Stage 2: Search Operations

| Endpoint | Spec | Implementation Notes |
|----------|------|---------------------|
| `POST /search` | ✓ | Exact match to `SearchQuery` / `SearchResult` schemas |
| `POST /search?explain=true` | ✓ | Returns `bm25_score`, `semantic_score` in hits |
| `GET /search/suggest` | ✓ | Returns `list[SuggestResult]` |

### Stage 1: Foundation

| Endpoint | Spec | Implementation Notes |
|----------|------|---------------------|
| `GET /health` | ✓ | Returns `HealthResponse` with nested objects |
| `GET /stats` | ✓ | Returns `StatsResponse` with `by_repo` optional |
| `POST /reindex` | ✓ | Returns `ReindexResult` |
| `GET /doctor` | ✓ | Returns `DoctorResult` |

### Error Response Format

All errors follow the `ErrorResponse` schema:

```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Semantic search requested but no embedding provider configured",
    "details": [
      {
        "field": "semantic",
        "message": "Set 'semantic: false' or configure an embedding provider",
        "value": true
      }
    ],
    "docs": "https://vtic.ejai.ai/docs/semantic-search"
  }
}
```

---

## 10. Implementation Checklist

### Wave 3 Phase 2 (Implementation Agent)

- [ ] Create `src/vtic/search/__init__.py`
- [ ] Implement `src/vtic/search/engine.py` (SearchEngine class)
- [ ] Create `src/vtic/services/__init__.py`
- [ ] Implement `src/vtic/services/system.py` (SystemService class)
- [ ] Implement `src/vtic/api/routes/search.py`
- [ ] Implement `src/vtic/api/routes/system.py`
- [ ] Update `src/vtic/api/deps.py` with new dependencies
- [ ] Update `src/vtic/api/app.py` with router registration
- [ ] Add request_id middleware for tracing
- [ ] Write unit tests for SearchEngine
- [ ] Write unit tests for SystemService
- [ ] Write integration tests for routes

---

## 11. Open Questions / Decisions Needed

1. **Score Normalization**: How to normalize BM25 scores to 0.0-1.0?
   - Option A: Min-max scaling across results
   - Option B: Sigmoid function
   - **Recommendation**: Min-max scaling (simpler, predictable)

2. **Highlight Generation**: Where to get content for highlights?
   - Option A: Store full description in index (current)
   - Option B: Fetch from disk after search
   - **Recommendation**: Option A (index has `description` field)

3. **Suggest Implementation**: How to do prefix matching?
   - Option A: Query index with `partial*` pattern
   - Option B: Scan ticket titles in memory
   - **Recommendation**: Option A (leverages existing index)

4. **Embedding Provider Check**: How to detect if semantic is available?
   - Check `config.embeddings.provider != "none"`
   - **Confirmed**: Use config value

---

## 12. Summary

This design defines a clean separation between:

1. **SearchEngine** (sync, pure search logic)
2. **SystemService** (async, orchestration + diagnostics)
3. **Routes** (thin HTTP layer)

All models already exist in `models/search.py` and `models/api.py`. No new models needed.

The only new code is:
- `search/engine.py` — SearchEngine class
- `services/system.py` — SystemService class
- `routes/search.py` — Search endpoints
- `routes/system.py` — System endpoints
- Dependency updates in `deps.py`
- Router registration in `app.py`

**No BM25 file needed** — logic stays in `operations.py`.
