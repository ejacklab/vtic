# vtic Final Audit - OpenAPI vs Data Models

**Audit Date:** 2026-03-18
**Auditor:** Subagent (final-audit-1)
**Scope:** Stages 1-3 data models against OpenAPI 3.1.1 specification

---

## Summary

| Category | Count |
|----------|-------|
| ✅ PASS | 15 schemas |
| ❌ FAIL (Extra field in model) | 1 |
| ❌ FAIL (Missing from models) | 10 |
| ⚠️ Stage file discrepancy | 1 |

**Overall Status: FAIL — 11 issues found**

---

## Detailed Results

### Stage 1: Enums

| Check | OpenAPI | Data Model | Status |
|-------|---------|------------|--------|
| Category values | crash, hotfix, feature, security, general | CRASH, HOTFIX, FEATURE, SECURITY, GENERAL | ✅ PASS |
| Severity values | critical, high, medium, low, info | CRITICAL, HIGH, MEDIUM, LOW, INFO | ✅ PASS |
| Status values | open, in_progress, blocked, fixed, wont_fix, closed | OPEN, IN_PROGRESS, BLOCKED, FIXED, WONT_FIX, CLOSED | ✅ PASS |
| EmbeddingProvider values | local, openai, custom, none | LOCAL, OPENAI, CUSTOM, NONE | ✅ PASS |

---

### Stage 2: Ticket Models

| Check | OpenAPI | Data Model | Status |
|-------|---------|------------|--------|
| Ticket fields | id, slug, title, description, repo, category, severity, status, assignee, fix, tags, references, created, updated | Same | ✅ PASS |
| Ticket.required | [id, title, description, repo, category, severity, status, created, updated] | Same | ✅ PASS |
| Ticket.id pattern | `^[CFGHST]\d+$` | `r"^[CFGHST]\d+$"` | ✅ PASS |
| Ticket.slug pattern | `^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$` | Same | ✅ PASS |
| Ticket.title | string, min 1, max 200 | str, min_length=1, max_length=200 | ✅ PASS |
| Ticket.description | string, min 1 | str, min_length=1 | ✅ PASS |
| Ticket.repo pattern | `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` | Same | ✅ PASS |
| Ticket.tags | array, maxItems:20, item maxLength:50 | List[str], max_length=20, validator checks 50 | ✅ PASS |
| Ticket.references | array, item pattern `^[CFGHST]\d+$` | List[str], validator checks pattern | ✅ PASS |
| **TicketCreate.fix** | **NOT IN SPEC** | **Optional[str] = Field(default=None)** | ❌ **EXTRA FIELD** |
| TicketCreate required | [title, description, repo] | Same | ✅ PASS |
| TicketUpdate fields | title, description, description_append, category, severity, status, assignee, fix, tags, references | Same (all Optional) | ✅ PASS |
| TicketSummary fields | id, title, severity, status, repo, category, assignee, created, updated | Same | ✅ PASS |
| TicketSummary.required | [id, title, severity, status, repo, category, created] | Same | ✅ PASS |
| TicketResponse fields | data (Ticket), meta (object) | Same | ✅ PASS |
| TicketListResponse fields | data (array), meta (object with total, limit, offset, has_more) | Same | ✅ PASS |
| ErrorResponse structure | error.code, error.message, error.details[], error.docs | Same | ✅ PASS |

---

### Stage 2: Missing Models

| Check | OpenAPI Location | Data Model | Status |
|-------|------------------|------------|--------|
| BatchGetRequest | stage2-crud.yaml, /tickets/batch | NOT IN data-models-stage2-ticket.md | ❌ MISSING |
| BatchGetResponse | stage2-crud.yaml, /tickets/batch | NOT IN data-models-stage2-ticket.md | ❌ MISSING |

---

### Stage 3: Search Models

| Check | OpenAPI | Data Model | Status |
|-------|---------|------------|--------|
| SearchQuery.query | string, min 1, max 500 | str, min_length=1, max_length=500 | ✅ PASS |
| SearchQuery.semantic | boolean, default false | bool, default=False | ✅ PASS |
| SearchQuery.filters | FilterSet (optional) | Optional[FilterSet] | ✅ PASS |
| SearchQuery.limit | integer, min 1, max 100, default 20 | int, ge=1, le=100, default=20 | ✅ PASS |
| SearchQuery.offset | integer, min 0, default 0 | int, ge=0, default=0 | ✅ PASS |
| SearchQuery.sort | string, default -score, pattern `^-?[a-zA-Z_]+$` | str, default="-score", pattern | ✅ PASS |
| SearchQuery.min_score | number | null, min 0, max 1, default 0.0 | Optional[float], ge=0.0, le=1.0, default=0.0 | ✅ PASS |
| FilterSet fields | severity[], status[], repo[], category[], tags[], assignee, created_after, created_before, updated_after | Same | ✅ PASS |
| FilterSet array types | All nullable arrays with correct item types | Same | ✅ PASS |
| SearchHit.required | [ticket_id, score, source] | Same | ✅ PASS |
| SearchHit.source | enum [bm25, semantic, hybrid] | Literal["bm25", "semantic", "hybrid"] | ✅ PASS |
| SearchHit optional fields | bm25_score, semantic_score, highlight | Same (all Optional) | ✅ PASS |
| SearchResult.required | [query, hits, total] | Same | ✅ PASS |
| SearchResult.meta | SearchMeta (bm25_weight, semantic_weight, latency_ms, semantic_used, request_id) | Same | ✅ PASS |
| SuggestResult/SuggestionItem | suggestion (string), ticket_count (integer) | Same | ✅ PASS |

---

### Stage 1 & Additional: Missing Models

| Check | OpenAPI Location | Data Model | Status |
|-------|------------------|------------|--------|
| HealthResponse | openapi.yaml, stage1-foundation.yaml | NOT IN any data model doc | ❌ MISSING |
| ConfigResponse | openapi.yaml, stage1-foundation.yaml | NOT IN any data model doc | ❌ MISSING |
| ConfigUpdate | stage1-foundation.yaml | NOT IN any data model doc | ❌ MISSING |
| DoctorResult | openapi.yaml, stage1-foundation.yaml | NOT IN any data model doc | ❌ MISSING |
| ReindexResult | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| StatsResponse | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| BulkCreateRequest | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| BulkUpdateRequest | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| BulkDeleteRequest | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| BulkOperationResult | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| ImportRequest | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| ImportResult | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| ExportOptions | openapi.yaml | NOT IN any data model doc | ❌ MISSING |
| WebhookPayload | openapi.yaml | NOT IN any data model doc | ❌ MISSING |

---

## Issues Found

### 1. ❌ TicketCreate.fix — Extra Field in Model

**File:** data-models-stage2-ticket.md
**Location:** `TicketCreate` class, line ~195

**OpenAPI Spec:**
```yaml
TicketCreate:
  required: [title, description, repo]
  properties:
    title, description, repo, category, severity, status, assignee, tags, references
    # NO 'fix' field
```

**Data Model:**
```python
class TicketCreate(BaseModel):
    ...
    fix: Optional[str] = Field(
        default=None,
        description="Resolution details (usually set later)",
    )
```

**Issue:** The `fix` field exists in the Pydantic model but is NOT in the OpenAPI `TicketCreate` schema. The `fix` field only appears in the full `Ticket` and `TicketUpdate` schemas.

**Recommendation:** Remove `fix` from `TicketCreate` model, or add it to OpenAPI spec if it should be allowed at creation time.

---

### 2. ❌ Missing Models from Data Model Docs

The following schemas are defined in the OpenAPI specification but are NOT documented in any of the data model markdown files:

| Missing Model | Documented In | Should Be In |
|---------------|---------------|--------------|
| BatchGetRequest | stage2-crud.yaml | data-models-stage2-ticket.md |
| BatchGetResponse | stage2-crud.yaml | data-models-stage2-ticket.md |
| HealthResponse | openapi.yaml, stage1-foundation.yaml | data-models-stage1-enums.md (or new doc) |
| ConfigResponse | openapi.yaml, stage1-foundation.yaml | data-models-stage1-enums.md (or new doc) |
| ConfigUpdate | stage1-foundation.yaml | data-models-stage1-enums.md (or new doc) |
| DoctorResult | openapi.yaml, stage1-foundation.yaml | data-models-stage1-enums.md (or new doc) |
| ReindexResult | openapi.yaml | data-models-stage1-enums.md (or new doc) |
| StatsResponse | openapi.yaml | data-models-stage2-ticket.md (or new doc) |
| BulkCreateRequest | openapi.yaml | New doc needed |
| BulkUpdateRequest | openapi.yaml | New doc needed |
| BulkDeleteRequest | openapi.yaml | New doc needed |
| BulkOperationResult | openapi.yaml | New doc needed |
| ImportRequest | openapi.yaml | New doc needed |
| ImportResult | openapi.yaml | New doc needed |
| ExportOptions | openapi.yaml | New doc needed |
| WebhookPayload | openapi.yaml | New doc needed |

---

## Stage File Discrepancy (Not a Data Model Issue)

### ⚠️ SearchQuery.sort Constraint Mismatch

**Files:** 
- openapi.yaml: Uses `pattern: ^-?[a-zA-Z_]+$`
- stage2-search.yaml: Uses `enum: [score, -score, created, -created, updated, -updated, severity, -severity]`

**Data Model:** Uses pattern (matches main openapi.yaml)

**Impact:** The data model is consistent with the main openapi.yaml. This is a discrepancy between stage2-search.yaml and the main spec, not a data model issue. The stage file should be updated to match.

---

## Recommendations

1. **Remove `fix` from TicketCreate** — The field should not be settable at creation time per the OpenAPI spec.

2. **Add missing Stage 2 models:**
   - `BatchGetRequest`
   - `BatchGetResponse`
   
3. **Create Stage 1 response/config models:**
   - `HealthResponse`
   - `ConfigResponse`
   - `ConfigUpdate`
   - `DoctorResult`
   - `ReindexResult`
   - `StatsResponse`

4. **Create Stage 4 or supplementary docs for:**
   - Bulk operations (`BulkCreateRequest`, `BulkUpdateRequest`, `BulkDeleteRequest`, `BulkOperationResult`)
   - Import/Export (`ImportRequest`, `ImportResult`, `ExportOptions`)
   - Webhooks (`WebhookPayload`)

5. **Fix stage2-search.yaml** — Update `sort` field to use pattern instead of enum to match main openapi.yaml.

---

## Conclusion

**FAIL — 11 issues found**

The core ticket and search models (Stages 1-3) are well-aligned with the OpenAPI specification for the fields that are documented. However:

1. One extra field (`fix` in `TicketCreate`) contradicts the spec
2. Multiple schemas are missing from the data model documentation entirely

The enum definitions are perfectly aligned. The SearchQuery, FilterSet, SearchHit, and SearchResult models are correctly implemented.
