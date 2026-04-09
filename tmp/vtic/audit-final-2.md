# Final Audit Report - VTIC Design Docs (Stages 4-6) vs OpenAPI

**Date:** 2026-03-18  
**Auditor:** cclow (subagent)  
**Files Reviewed:**
- openapi.yaml (canonical spec)
- openapi-stages/stage1-foundation.yaml
- openapi-stages/stage3-bulk.yaml
- data-models-stage4-api.md
- data-models-stage5-config.md
- data-models-stage6-errors-map.md
- DATA_FLOWS.md

---

## Audit Results

| # | Check | OpenAPI Spec | Data Model/Flow | Status |
|---|-------|--------------|-----------------|--------|
| 1 | ErrorResponse structure | `error: {code, message, details[{field,message,value}], docs}` | `ErrorResponse.ErrorObject: {code, message, details[ErrorDetail], docs}` with `ErrorDetail: {field, message, value}` | ✅ PASS |
| 2 | HealthResponse with nested objects | `index_status: {zvec, ticket_count, last_reindex}`, `embedding_provider: {name, model, dimension}` | `IndexStatus: {zvec, ticket_count, last_reindex}`, `EmbeddingProviderInfo: {name, model, dimension}` | ✅ PASS |
| 3 | StatsResponse structure | `totals: {all, open, closed}`, `by_status`, `by_severity`, `by_category`, `by_repo?`, `date_range?` | `StatsResponse: {totals: StatsTotals, by_status, by_severity, by_category, by_repo?, date_range?}` | ✅ PASS |
| 4 | ReindexResult fields | `processed`, `skipped`, `failed`, `duration_ms`, `errors[]` | `ReindexResult: {processed, skipped, failed, duration_ms, errors[]}` | ✅ PASS |
| 5 | PaginationMeta fields | `total`, `limit`, `offset`, `has_more`, `request_id?` | `PaginationMeta: {total, limit, offset, has_more, request_id?}` | ✅ PASS |
| 6 | Config matches ConfigResponse | `storage.dir`, `api.host`, `api.port`, `search.*`, `embeddings.*` | `Config: {storage: StorageConfig, api: ApiConfig, search: SearchConfig, embeddings: EmbeddingsConfig}` with matching field names | ✅ PASS |
| 7 | Error codes (exactly 6 with HTTP status) | VALIDATION_ERROR(400), NOT_FOUND(404), CONFLICT(409), PAYLOAD_TOO_LARGE(413), INTERNAL_ERROR(500), SERVICE_UNAVAILABLE(503) | Stage 6 defines exactly these 6 codes with correct HTTP status mappings | ✅ PASS |
| 8 | Module map function signatures | References `Ticket`, `SearchQuery`, `SearchHit`, `SearchResult`, `FilterSet`, `Config`, `ErrorResponse`, `HealthResponse`, `ReindexResult`, etc. | All function signatures in stage6-errors-map.md reference correct model names from stages 2-5 | ✅ PASS |
| 9 | DATA_FLOWS.md field names | JSON examples should use `id`, `created`, `updated`, `ticket_id`, `processed`, `failed`, `duration_ms` | All JSON examples in DATA_FLOWS.md use correct field names - no `topk`, `match_type`, `created_at`, `updated_at` | ✅ PASS |
| 10 | No forbidden legacy names | Should NOT have: `created_at`, `updated_at`, `SearchRequest`, `topk`, `match_type` | Searched all files - no forbidden names present in active specs/models. (Legacy mapping table in stage6 is documentation only) | ✅ PASS |

---

## Detailed Verification

### Check 1: ErrorResponse Structure

**OpenAPI (openapi.yaml lines ~950-980):**
```yaml
ErrorResponse:
  type: object
  required: [error]
  properties:
    error:
      type: object
      required: [code, message]
      properties:
        code: string
        message: string
        details: array of {field, message, value}
        docs: string | null
```

**Data Model (stage4-api.md):**
```python
class ErrorResponse(BaseModel):
    class ErrorObject(BaseModel):
        code: str
        message: str
        details: Optional[List[ErrorDetail]] = None
        docs: Optional[str] = None
    error: ErrorObject

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str
    value: Optional[Any] = None
```

✅ **PASS** - Nested structure matches exactly.

---

### Check 2: HealthResponse Nested Objects

**OpenAPI:**
- `index_status: {zvec, ticket_count, last_reindex}`
- `embedding_provider: {name, model, dimension}`

**Data Model (stage4-api.md):**
```python
class IndexStatus(BaseModel):
    zvec: Literal["available", "unavailable", "corrupted"]
    ticket_count: int
    last_reindex: Optional[datetime] = None

class EmbeddingProviderInfo(BaseModel):
    name: Literal["local", "openai", "custom", "none"]
    model: Optional[str] = None
    dimension: Optional[int] = None

class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    uptime_seconds: Optional[int] = None
    index_status: IndexStatus
    embedding_provider: Optional[EmbeddingProviderInfo] = None
```

✅ **PASS** - Nested objects match OpenAPI structure.

---

### Check 3: StatsResponse Structure

**OpenAPI:**
```yaml
StatsResponse:
  properties:
    totals: {all, open, closed}
    by_status: object (additionalProperties: integer)
    by_severity: object (additionalProperties: integer)
    by_category: object (additionalProperties: integer)
    by_repo: object | null
    date_range: {earliest, latest} | null
```

**Data Model (stage4-api.md):**
```python
class StatsTotals(BaseModel):
    all: int
    open: int
    closed: int

class StatsResponse(BaseModel):
    totals: StatsTotals
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    by_repo: Optional[Dict[str, int]] = None
    date_range: Optional[DateRange] = None
```

✅ **PASS** - Structure matches with nested StatsTotals.

---

### Check 4: ReindexResult Fields

**OpenAPI:**
- `processed`, `skipped`, `failed`, `duration_ms`, `errors[]`

**Data Model (stage4-api.md):**
```python
class ReindexResult(BaseModel):
    processed: int
    skipped: int = 0
    failed: int
    duration_ms: int
    errors: List[ReindexError] = Field(default_factory=list)
```

✅ **PASS** - Uses `processed` and `duration_ms` (not legacy `indexed` or `took_ms`).

---

### Check 5: PaginationMeta Fields

**OpenAPI (from TicketListResponse meta):**
```yaml
meta:
  required: [total, limit, offset, has_more]
  properties:
    total: integer
    limit: integer
    offset: integer
    has_more: boolean
    request_id: string
```

**Data Model (stage4-api.md):**
```python
class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool
    request_id: Optional[str] = None
```

✅ **PASS** - All fields match.

---

### Check 6: Config Model vs ConfigResponse

**OpenAPI ConfigResponse:**
```yaml
ConfigResponse:
  properties:
    storage: {dir}
    search: {bm25_enabled, semantic_enabled, bm25_weight, semantic_weight}
    embeddings: {provider, model, dimension}
    api: {host, port}
```

**Data Model (stage5-config.md):**
```python
class StorageConfig(BaseModel):
    dir: Path = Field(default=Path("./tickets"))

class ApiConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=8080, ge=1, le=65535)

class SearchConfig(BaseModel):
    bm25_enabled: bool = True
    semantic_enabled: bool = False
    bm25_weight: float = 0.6
    semantic_weight: float = 0.4

class EmbeddingsConfig(BaseModel):
    provider: Literal["local", "openai", "custom", "none"] = "local"
    model: str | None = None
    dimension: int | None = None

class Config(BaseModel):
    storage: StorageConfig
    api: ApiConfig
    search: SearchConfig
    embeddings: EmbeddingsConfig
```

✅ **PASS** - All field names match OpenAPI ConfigResponse.

---

### Check 7: Error Codes (Exactly 6)

**OpenAPI defines these error codes (from examples and stage3-bulk.yaml):**
1. `VALIDATION_ERROR` → 400
2. `NOT_FOUND` → 404
3. `CONFLICT` → 409
4. `PAYLOAD_TOO_LARGE` → 413
5. `INTERNAL_ERROR` → 500
6. `SERVICE_UNAVAILABLE` → 503

**Data Model (stage6-errors-map.md):**
```python
VALIDATION_ERROR = "VALIDATION_ERROR"      # 400
NOT_FOUND = "NOT_FOUND"                    # 404
CONFLICT = "CONFLICT"                      # 409
PAYLOAD_TOO_LARGE = "PAYLOAD_TOO_LARGE"    # 413
INTERNAL_ERROR = "INTERNAL_ERROR"          # 500
SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"  # 503
```

✅ **PASS** - Exactly 6 error codes with correct HTTP status mappings.

---

### Check 8: Module Map Function Signatures

Sample verification from stage6-errors-map.md:

| Function | References | Model Source |
|----------|------------|--------------|
| `ticket_to_markdown(ticket: Ticket)` | Ticket | stage2 (ticket.py) |
| `markdown_to_ticket(content: str) -> Ticket` | Ticket | stage2 |
| `search(request: SearchQuery) -> SearchResult` | SearchQuery, SearchResult | stage3 (search.py) |
| `bm25_search(..., filters: FilterSet) -> list[SearchHit]` | FilterSet, SearchHit | stage3 |
| `health() -> HealthResponse` | HealthResponse | stage4 (api.py) |
| `reindex() -> ReindexResult` | ReindexResult | stage4 |
| `load_config(path: Path) -> Config` | Config | stage5 (config.py) |

✅ **PASS** - All function signatures reference correct model names.

---

### Check 9: DATA_FLOWS.md Field Names

Verified JSON examples in DATA_FLOWS.md use correct field names:

**Ticket JSON (lines ~710-730):**
- `id` ✅ (not `ticket_id` at root)
- `created` ✅ (not `created_at`)
- `updated` ✅ (not `updated_at`)

**Error Response (lines ~760-770):**
- `error.code` ✅
- `error.message` ✅
- `error.details` ✅

**Search Response (lines ~745-760):**
- `data.results[].ticket` ✅
- `data.results[].score` ✅
- `meta.duration_ms` ✅

✅ **PASS** - No legacy field names in active examples.

---

### Check 10: No Forbidden Legacy Names

Searched for these patterns across all files:

| Forbidden Name | Found In | Context |
|----------------|----------|---------|
| `created_at` | stage6-errors-map.md | "Field Mappings" table (documentation only) |
| `updated_at` | stage6-errors-map.md | "Field Mappings" table (documentation only) |
| `SearchRequest` | None | Not found |
| `topk` | None | Not found |
| `match_type` | stage6-errors-map.md | "Field Mappings" table (documentation only) |

The legacy names appear ONLY in the "Field Name Mappings" section of stage6-errors-map.md, which documents old→new mappings for reference. They do NOT appear in:
- OpenAPI schemas
- Data model definitions
- DATA_FLOWS.md examples
- Function signatures

✅ **PASS** - No forbidden legacy names in active specs/models.

---

## Summary

| Category | Count |
|----------|-------|
| Total Checks | 10 |
| Passed | 10 |
| Failed | 0 |

---

## Result

# ✅ PASS

All data models (stages 4-6) and data flows are correctly aligned with the OpenAPI specification. No discrepancies found.

---

*Audit completed: 2026-03-18*
