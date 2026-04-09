# vtic OpenAPI Specification Review

**Reviewed:** 2026-03-17  
**File:** `/home/smoke01/.openclaw/workspace-dave/research-ejack-yao/openapi.yaml`  
**OpenAPI Version:** 3.1.1

---

## Executive Summary

| Category | Rating |
|----------|--------|
| **Overall** | ⚠️ **NEEDS FIXES** |
| Spec Compliance | 🔴 Critical issues |
| Completeness | 🟢 Excellent |
| Data Models | 🟡 Good with gaps |
| Error Handling | 🟢 Well-designed |
| Search Design | 🟢 Excellent |
| Filter Design | 🟢 Well-designed |
| Pagination | 🟢 Consistent |
| Naming Conventions | 🟢 Good |

### The Good
- Comprehensive endpoint coverage for a ticket CRUD + search system
- Well-designed hybrid search with BM25 + semantic capabilities
- Consistent pagination pattern across list endpoints
- Clean error envelope format with machine-readable codes
- Thoughtful filter design for ticket attributes
- Good use of examples throughout

### The Bad
- **CRITICAL:** References a non-existent `stage1-foundation.yaml` file with 15+ `$ref` pointers
- Missing `required` arrays on several schema objects
- Inconsistent use of `oneOf` vs `type: [string, 'null']`
- Schema version mismatch (`$schema` points to 3.1.0 but `openapi` is 3.1.1)

### The Ugly
- The spec is **broken** as-is — it cannot be validated or used for code generation due to missing referenced file
- Several schemas defined locally that are also referenced from the missing file (duplication/confusion)

---

## Detailed Findings

### 1. Spec Compliance

#### 🔴 Critical Issues

**1.1 Missing Referenced File (Lines 98-99, 155, 205, 276, 298, 340, 366, 478, 530, etc.)**

The spec contains **15+ references** to `stage1-foundation.yaml` which does not exist:

```yaml
$ref: stage1-foundation.yaml#/components/schemas/DoctorResult
$ref: stage1-foundation.yaml#/components/schemas/HealthResponse
$ref: stage1-foundation.yaml#/components/parameters/explainParam
$ref: stage1-foundation.yaml#/components/schemas/SearchQuery
$ref: stage1-foundation.yaml#/components/schemas/SearchResult
$ref: stage1-foundation.yaml#/components/schemas/ErrorResponse
$ref: stage1-foundation.yaml#/components/schemas/ReindexResult
$ref: stage1-foundation.yaml#/components/schemas/StatsResponse
$ref: stage1-foundation.yaml#/components/schemas/Severity
$ref: stage1-foundation.yaml#/components/schemas/Status
$ref: stage1-foundation.yaml#/components/schemas/Category
```

**Impact:** Spec cannot be validated, used for code generation, or rendered in Swagger UI.

**Fix:** Either:
1. Provide the missing `stage1-foundation.yaml` file, OR
2. Inline all referenced schemas/parameters into the main spec

---

**1.2 Schema Version Mismatch (Lines 6-7)**

```yaml
$schema: https://spec.openapis.org/oas/3.1.0  # Points to 3.1.0
openapi: 3.1.1                                  # Declares 3.1.1
```

While not strictly invalid (3.1.1 is a patch of 3.1.0), this is inconsistent and may confuse some validators.

**Fix:** Update to:
```yaml
$schema: https://spec.openapis.org/oas/3.1/3.1.1
```
Or simply use 3.1.0 for both if the patch version changes aren't relevant.

---

**1.3 Invalid Schema Keywords (Line 729)**

```yaml
type:
- string
- 'null'
```

In OpenAPI 3.1 (which uses JSON Schema 2020-12), this is valid. However, some older validators may not accept it. The alternative is using `oneOf`:

```yaml
oneOf:
- type: string
- type: 'null'
```

**Verdict:** Valid per spec, but note tooling compatibility.

---

**1.4 Missing `required` Arrays**

Several schemas have optional fields that should likely be required in context:

- `TicketResponse.data` - marked required ✓
- `TicketListResponse.data` and `meta` - marked required ✓
- `SearchResult.query`, `hits`, `total` - marked required ✓
- `StatsResponse` - missing `required` array entirely (lines 799-856)

```yaml
StatsResponse:
  type: object
  description: Ticket statistics
  required:  # MISSING - should be:
  - totals
  - by_status
  - by_severity
  - by_category
  properties:
    ...
```

**Fix:** Add `required` arrays to all schemas where appropriate.

---

### 2. Completeness

#### ✅ Excellent Coverage

The spec covers all essential endpoints for a ticket CRUD + search system:

| Endpoint Type | Status | Notes |
|--------------|--------|-------|
| Create ticket | ✅ | POST /tickets |
| Read ticket | ✅ | GET /tickets/{id} |
| Update ticket | ✅ | PATCH /tickets/{id} |
| Delete ticket | ✅ | DELETE /tickets/{id} |
| List tickets | ✅ | GET /tickets (with filters, pagination) |
| Search | ✅ | POST /search (hybrid BM25 + semantic) |
| Bulk create | ✅ | POST /tickets/bulk |
| Bulk update | ✅ | PATCH /tickets/bulk |
| Bulk delete | ✅ | DELETE /tickets/bulk |
| Health | ✅ | GET /health |
| Stats | ✅ | GET /stats |
| Import | ✅ | POST /import |
| Export | ✅ | GET /export |
| Reindex | ✅ | POST /reindex |
| Doctor | ✅ | GET /doctor |
| Validate | ✅ | GET /validate |
| Config | ✅ | GET/PATCH /config |
| Trash operations | ✅ | GET /trash, DELETE /trash/clean, POST /trash/{id}/restore |
| Autocomplete | ✅ | GET /search/suggest |
| OpenAPI spec | ✅ | GET /openapi.json |
| Webhooks | ✅ | ticket.created, ticket.updated, ticket.deleted |

**Gaps to consider:**

1. **Batch read** - No endpoint to fetch multiple tickets by ID in one request
   - **Recommendation:** Add `POST /tickets/batch` with `{ "ids": ["C1", "C2", "C3"] }`

2. **Comments/activity log** - No support for ticket comments or history
   - **Recommendation:** Consider for future version if needed

3. **Attachments** - No file attachment support
   - **Recommendation:** Consider for future version if needed

4. **Search highlight configuration** - No way to control highlight fragment size
   - **Recommendation:** Add `highlight_size` parameter to SearchQuery

---

### 3. Data Models

#### ✅ Well-Designed, Pydantic-Compatible

The schema designs are generally well-suited for Pydantic models:

```yaml
Ticket:
  type: object
  required:
  - id
  - title
  - description
  - repo
  - category
  - severity
  - status
  - created
  - updated
  properties:
    id:
      type: string
      pattern: ^[CFGHST]\d+$
    # ...
```

#### 🟡 Issues to Address

**3.1 Inconsistent Nullable Representation**

Mix of approaches:

```yaml
# Approach 1: type array (used in most places)
assignee:
  type:
  - string
  - 'null'

# Approach 2: oneOf (used in TicketUpdate)
severity:
  oneOf:
  - $ref: '#/components/schemas/Severity'
  - type: 'null'
```

**Recommendation:** Pick one style and use consistently. For OpenAPI 3.1, the type array is cleaner:
```yaml
severity:
  anyOf:
  - $ref: '#/components/schemas/Severity'
  - type: 'null'
```

---

**3.2 Pattern Constraints Good, But Missing Some**

Good patterns:
```yaml
id:
  pattern: ^[CFGHST]\d+$          # Ticket ID format
slug:
  pattern: ^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$  # URL-safe slug
repo:
  pattern: ^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$  # owner/repo format
```

Missing patterns:
```yaml
# No constraint on assignee format
assignee:
  type:
  - string
  - 'null'
  description: Assigned team member username
  # Should have: pattern: ^[a-zA-Z0-9_-]{1,39}$ or similar
```

---

**3.3 Tag Constraints Well-Defined**

```yaml
tags:
  type: array
  items:
    type: string
    maxLength: 50
  maxItems: 20
```

Good! Proper constraints on tag count and length.

---

### 4. Error Handling

#### ✅ Excellent Design

The `ErrorResponse` schema is well-designed:

```yaml
ErrorResponse:
  type: object
  required:
  - error
  properties:
    error:
      type: object
      required:
      - code
      - message
      properties:
        code:
          type: string
          description: Machine-readable error code (e.g., VALIDATION_ERROR, NOT_FOUND)
        message:
          type: string
          description: Human-readable error description
        details:
          type: array
          items:
            type: object
            properties:
              field:
                type: string
              message:
                type: string
              value:
                type:
                - string
                - 'null'
        docs:
          type:
          - string
          - 'null'
          description: Link to error documentation
```

**Strengths:**
- Machine-readable `code` for programmatic handling
- Human-readable `message`
- Structured `details` array for field-level validation errors
- Optional `docs` link for help
- Consistent envelope structure

**HTTP Status Codes Used Correctly:**
- `200` - Success
- `201` - Created
- `204` - No content (webhook ack)
- `400` - Bad request / validation error
- `404` - Not found
- `409` - Conflict / duplicate / invalid transition
- `413` - Payload too large
- `500` - Internal server error
- `503` - Service unavailable (no embedding provider)

---

### 5. Search Design

#### ✅ Excellent Hybrid Search Support

The search endpoint is well-designed for hybrid BM25 + semantic search:

```yaml
/search:
  post:
    summary: Hybrid search for tickets
    operationId: searchTickets
    requestBody:
      content:
        application/json:
          schema:
            $ref: stage1-foundation.yaml#/components/schemas/SearchQuery
```

**SearchQuery features (defined locally):**
```yaml
SearchQuery:
  type: object
  required:
  - query
  properties:
    query:
      type: string
      minLength: 1
      maxLength: 500
    semantic:
      type: boolean
      default: false
      description: Enable semantic (vector) search in addition to BM25
    filters:
      $ref: '#/components/schemas/FilterSet'
    limit:
      type: integer
      minimum: 1
      maximum: 100
      default: 20
    offset:
      type: integer
      minimum: 0
      default: 0
    sort:
      type: string
      default: -score
      pattern: ^-?[a-zA-Z_]+$
```

**SearchHit response:**
```yaml
SearchHit:
  properties:
    ticket_id:
      type: string
    score:
      type: number
      format: double
    source:
      type: string
      enum:
      - bm25
      - semantic
      - hybrid
    bm25_score:      # Only in explain mode
      type:
      - number
      - 'null'
    semantic_score:  # Only in explain mode
      type:
      - number
      - 'null'
    highlight:
      type:
      - string
      - 'null'
```

**Strengths:**
- Explicit `semantic` flag to opt-in to hybrid search
- `source` field shows which search method produced ranking
- `explain` parameter for debugging scores
- Proper score fusion metadata in response
- 503 response when semantic requested but no provider configured

**Minor gap:** No `min_score` threshold to filter low-relevance results.
```yaml
# Recommended addition:
min_score:
  type: number
  minimum: 0
  maximum: 1
  description: Minimum relevance score threshold
```

---

### 6. Filter Design

#### ✅ Comprehensive Filter Support

The `FilterSet` schema covers all ticket attributes:

```yaml
FilterSet:
  properties:
    severity:
      type:
      - array
      - 'null'
      items:
        $ref: '#/components/schemas/Severity'
    status:
      type:
      - array
      - 'null'
      items:
        $ref: '#/components/schemas/Status'
    repo:
      type:
      - array
      - 'null'
      items:
        type: string
      description: 'Filter by repo. Supports globs: "ejacklab/*"'
    category:
      type:
      - array
      - 'null'
      items:
        $ref: '#/components/schemas/Category'
    assignee:
      type:
      - string
      - 'null'
    tags:
      type:
      - array
      - 'null'
      description: Filter by tags (ticket must have ALL specified tags)
    created_after:
      type:
      - string
      - 'null'
      format: date-time
    created_before:
      type:
      - string
      - 'null'
      format: date-time
    updated_after:
      type:
      - string
      - 'null'
      format: date-time
```

**Strengths:**
- Multi-value filters with arrays (OR logic within same field)
- Glob patterns for repo filtering (`ejacklab/*`)
- Date range filters for created/updated
- Tag intersection (AND logic)
- Consistent pattern with list endpoint query params

**Filter consistency:** ✅ Same filters available on:
- GET /tickets (query params)
- POST /search (request body filters)
- GET /export (query params)
- Bulk operations (request body filters)

---

### 7. Pagination

#### ✅ Consistent Pattern

Pagination is consistent across all list endpoints:

**Query parameters:**
```yaml
limitParam:
  name: limit
  in: query
  schema:
    type: integer
    minimum: 1
    maximum: 100
    default: 20

offsetParam:
  name: offset
  in: query
  schema:
    type: integer
    minimum: 0
    default: 0
```

**Response meta:**
```yaml
meta:
  type: object
  required:
  - total
  - limit
  - offset
  - has_more
  properties:
    total:
      type: integer
    limit:
      type: integer
    offset:
      type: integer
    has_more:
      type: boolean
```

**Endpoints using this pattern:**
- GET /tickets
- POST /search
- GET /trash
- GET /search/suggest (uses limit only, no offset needed)

**Good:** `has_more` boolean is more efficient than computing `total > offset + limit`.

---

### 8. Naming Conventions

#### ✅ RESTful and Consistent

**URL naming:** ✅ Kebab-case for paths, snake_case for query params
```
/tickets
/tickets/{ticket_id}
/search/suggest
/trash/{ticket_id}/restore
```

**JSON properties:** ✅ snake_case consistently
```json
{
  "ticket_id": "C1",
  "created_at": "...",
  "updated_at": "...",
  "has_more": true,
  "bm25_score": 0.85
}
```

**Operation IDs:** ✅ camelCase
```yaml
operationId: getTicket
operationId: createTicket
operationId: searchTickets
operationId: bulkCreateTickets
```

**Schema names:** ✅ PascalCase
```yaml
Ticket
TicketCreate
TicketUpdate
SearchQuery
FilterSet
ErrorResponse
```

**Enum values:** ✅ snake_case
```yaml
enum: [open, in_progress, blocked, fixed, wont_fix, closed]
enum: [critical, high, medium, low, info]
```

---

### 9. Specific Issues

| Line(s) | Issue | Severity | Fix |
|---------|-------|----------|-----|
| 98-99 | `$ref` to non-existent `stage1-foundation.yaml` | 🔴 Critical | Provide file or inline schemas |
| 6-7 | `$schema` version mismatch | 🟡 Minor | Update to 3.1.1 or align both to 3.1.0 |
| 206 | `SearchQuery` referenced from missing file but also defined locally | 🟡 Confusion | Remove duplicate, keep one definition |
| 340 | `ErrorResponse` same issue | 🟡 Confusion | Consolidate definitions |
| 276 | `SearchResult` same issue | 🟡 Confusion | Consolidate definitions |
| 530 | `ReindexResult` same issue | 🟡 Confusion | Consolidate definitions |
| 478 | `StatsResponse` same issue | 🟡 Confusion | Consolidate definitions |
| 799-856 | `StatsResponse` missing `required` array | 🟡 Minor | Add required fields |
| 215 | `explainParam` referenced from missing file | 🔴 Critical | Inline or provide file |
| 517 | `WebhookPayload.previous` type is `object` without schema | 🟡 Minor | Define PreviousState schema |
| 965 | `repoFilter` parameter missing `description` | 🟡 Minor | Add description |

---

### 10. Webhooks Section

#### ✅ Well-Structured

```yaml
webhooks:
  ticket.created:
    post:
      operationId: webhookTicketCreated
      requestBody:
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/WebhookPayload'
```

**WebhookPayload includes:**
- `event` type enum (created, updated, deleted)
- `ticket` full object
- `previous` state for updates
- `timestamp`
- `signature` for HMAC verification

**Good:** Security via HMAC-SHA256 signature.

---

## Recommended Fixes

### Priority 1 (Blocking)

1. **Provide `stage1-foundation.yaml`** OR inline all referenced schemas:
   - `Severity`, `Status`, `Category` enums
   - `SearchQuery`, `SearchResult`, `SearchHit`
   - `ErrorResponse`, `HealthResponse`, `ReindexResult`, `StatsResponse`, `DoctorResult`
   - `explainParam` parameter

### Priority 2 (Important)

2. **Remove schema duplication** - Several schemas are defined both locally and referenced from the missing file. Choose one approach.

3. **Add missing `required` arrays** to:
   - `StatsResponse`
   - `DoctorResult.checks` items (partially done)

4. **Standardize nullable handling** - Use `type: [string, 'null']` consistently

### Priority 3 (Nice to Have)

5. **Add batch read endpoint**:
   ```yaml
   /tickets/batch:
     post:
       summary: Fetch multiple tickets by ID
       requestBody:
         content:
           application/json:
             schema:
               type: object
               required: [ids]
               properties:
                 ids:
                   type: array
                   items:
                     type: string
                     pattern: ^[CFGHST]\d+$
                   maxItems: 100
   ```

6. **Add `min_score` to SearchQuery** for relevance thresholding

7. **Add `request_id` to all responses** for tracing

8. **Add descriptions to all parameters** (some are missing)

---

## Final Verdict

# ⚠️ **NEEDS FIXES**

The vtic OpenAPI spec is **well-designed** with excellent coverage, thoughtful search/filter design, and consistent patterns. However, it has a **critical blocker**:

> **The spec references a non-existent `stage1-foundation.yaml` file with 15+ `$ref` pointers, making it unusable for validation, code generation, or documentation rendering.**

### What's Ready
- Overall structure and patterns
- Error handling design
- Search and filter design
- Pagination approach
- Naming conventions

### What Needs Work
- **CRITICAL:** Provide missing `stage1-foundation.yaml` or inline all schemas
- Remove duplicate schema definitions
- Add missing `required` arrays
- Minor consistency fixes

### Timeline Estimate
- **To make usable:** 2-4 hours (inline schemas or provide missing file)
- **To production-ready:** 4-8 hours (add batch endpoint, polish, validate)

---

*Review complete. The spec shows good API design sense but needs the missing reference file resolved before it can be used.*
