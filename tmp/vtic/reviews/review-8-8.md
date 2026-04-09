# Review: test_api_routes.py + Cross-check All Reviews

## Part 1: API Routes Review

### Endpoint Compliance

| Endpoint | HTTP Method | OpenAPI Spec | Implementation | Test Verifies | Match? |
|----------|-------------|--------------|----------------|---------------|--------|
| `/tickets` | POST | 201 Created | 201 Created | ✅ test_post_ticket_201 | ✅ Yes |
| `/tickets` | GET | 200 OK | 200 OK | ✅ test_list_tickets_200 | ✅ Yes |
| `/tickets/{ticket_id}` | GET | 200 OK | 200 OK | ✅ test_get_ticket_200 | ✅ Yes |
| `/tickets/{ticket_id}` | PATCH | 200 OK | 200 OK | ✅ test_patch_ticket_200 | ✅ Yes |
| `/tickets/{ticket_id}` | DELETE | 200 OK* | 204 No Content | ✅ test_delete_ticket_204 | ⚠️ Spec mismatch |

**Note on DELETE**: OpenAPI spec (stage2-crud.yaml) defines DELETE as returning `200 OK` with `TicketResponse`. Implementation uses `204 No Content`. Tests verify 204. This is a common REST pattern variation - implementation is valid but differs from spec.

### Response Format Compliance

| Model | OpenAPI Schema | Test Verifies | Match? |
|-------|----------------|---------------|--------|
| **TicketResponse** | `{ data: Ticket, meta?: object }` | ✅ test_post_ticket_201, test_get_ticket_200 | ✅ Yes |
| **TicketListResponse** | `{ data: TicketSummary[], meta: { total, limit, offset, has_more } }` | ✅ test_list_tickets_200 | ✅ Yes |
| **ErrorResponse** | `{ error: { code, message, details?, docs? } }` | ✅ test_error_response_format | ✅ Yes |

### Request Body Validation (TicketCreate)

| Field | OpenAPI Requirement | Test Coverage | Match? |
|-------|---------------------|---------------|--------|
| `title` | Required, minLength: 1, maxLength: 200 | ✅ test_create_ticket_minimal_fields | ✅ Yes |
| `description` | Required, minLength: 1 | ✅ test_create_ticket_minimal_fields | ✅ Yes |
| `repo` | Required, pattern: `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$` | ✅ test_create_ticket_minimal_fields | ✅ Yes |
| `category` | Optional, enum | ✅ test_post_ticket_201 | ✅ Yes |
| `severity` | Optional, enum | ✅ test_post_ticket_201 | ✅ Yes |
| `status` | Optional, enum | ✅ test_post_ticket_201 | ✅ Yes |
| `assignee` | Optional, string|null | ✅ test_post_ticket_201 | ✅ Yes |
| `tags` | Optional, array | ✅ test_post_ticket_201 | ✅ Yes |
| `references` | Optional, array | Not explicitly tested | ⚠️ Missing |

### Query Parameters (List Tickets)

| Param | OpenAPI Spec | Test Coverage | Match? |
|-------|--------------|---------------|--------|
| `repo` | string array | ✅ test_list_tickets_filter_by_repo | ✅ Yes |
| `category` | Category array | ✅ test_list_tickets_filter_by_category | ✅ Yes |
| `severity` | Severity array | ✅ test_list_tickets_filter_by_severity | ✅ Yes |
| `status` | Status array | ✅ test_list_tickets_filter_by_status | ✅ Yes |
| `limit` | int, 1-100, default 20 | ✅ test_list_tickets_pagination_limit_offset | ✅ Yes |
| `offset` | int, >=0, default 0 | ✅ test_list_tickets_pagination_limit_offset | ✅ Yes |
| `assignee` | string | Not tested | ⚠️ Missing |
| `tags` | string array | Not tested | ⚠️ Missing |
| `created_after` | date-time | Not tested | ⚠️ Missing |
| `created_before` | date-time | Not tested | ⚠️ Missing |
| `sort` | enum, default `-created` | Not tested | ⚠️ Missing |
| `format` | enum, default `json` | Not tested | ⚠️ Missing |

### Mock Service Verification

**Approach**: Tests use `AsyncMock` with custom side effects that mimic `TicketService` interface.

| TicketService Method | Mock Signature | Matches Interface? |
|---------------------|----------------|-------------------|
| `create_ticket(data: TicketCreate) -> Ticket` | ✅ Yes | ✅ Yes |
| `get_ticket(ticket_id: str) -> Ticket` | ✅ Yes | ✅ Yes |
| `update_ticket(ticket_id: str, data: TicketUpdate) -> Ticket` | ✅ Yes | ✅ Yes |
| `delete_ticket(ticket_id: str, mode: str) -> None` | ✅ Yes | ✅ Yes |
| `list_tickets(**filters) -> list[TicketSummary]` | ✅ Yes | ✅ Yes |
| `count_tickets(**filters) -> int` | ✅ Yes | ✅ Yes |
| `initialize() -> None` | ✅ Yes | ✅ Yes |
| `close() -> None` | ✅ Yes | ✅ Yes |

### Error Response Verification

| Error Code | HTTP Status | Test Coverage | Match? |
|------------|-------------|---------------|--------|
| `NOT_FOUND` | 404 | ✅ test_get_ticket_404, test_patch_ticket_404, test_delete_ticket_404 | ✅ Yes |
| `VALIDATION_ERROR` | 400 | ✅ test_invalid_input_400 | ✅ Yes |

---

## Part 2: Cross-Review Consistency

| Finding | Review Source | Fix Review | Status | Notes |
|---------|---------------|------------|--------|-------|
| TERMINAL_STATUSES missing FIXED | review-tests-1 (T2) | review-fix-1 (T2) | ✅ FIXED | Added FIXED to constant |
| Category.get_prefix(None) crashes | review-tests-1 (T2) | review-fix-1 (T2) | ✅ FIXED | Added None guard returning "G" |
| duration_ms type mismatch (float vs int) | review-tests-3 (T4) | review-fix-2 (T3+T4) | ✅ FIXED | Changed to int |
| rebuild_index placeholder | review-tests-3 (T5+T6) | review-fix-3 (T5+T6) | ✅ FIXED | Implemented full function |
| SearchMeta.latency_ms float vs int | review-fix-2 (T3+T4) | N/A | ⚠️ UNFIXED | Still uses float, spec says int |
| FilterSet.is_empty() missing updated_before | review-fix-2 (T3+T4) | N/A | ⚠️ UNFIXED | Still missing from check |
| BM25 ranking order not tested | review-tests-3 (T5+T6) | N/A | ⚠️ UNFIXED | Tests don't verify ranking |
| Atomic write failure cleanup not tested | review-tests-3 (T5+T6) | N/A | ⚠️ UNFIXED | Only success path tested |

### Contradictions Found

1. **DELETE Status Code**: 
   - OpenAPI spec (stage2-crud.yaml): Returns `200 OK` with `TicketResponse`
   - Implementation (routes/tickets.py): Returns `204 No Content`
   - Tests: Verify `204 No Content`
   - **Assessment**: Implementation is valid REST but diverges from spec. No review flagged this.

2. **Delete Query Params**:
   - OpenAPI spec: `force` (boolean) and `dry_run` parameters
   - Implementation: `mode` (soft/hard) parameter
   - Tests: Verify `mode` parameter works but not `force` or `dry_run`
   - **Assessment**: Implementation uses different API design than spec. No review flagged this.

---

## Part 3: Full Test Suite

```
============== 19 failed, 423 passed, 6 skipped in 45.50s ==============
```

### Test Summary by File

| Test File | Passed | Failed | Notes |
|-----------|--------|--------|-------|
| test_api_routes.py | 18 | 0 | ✅ All pass |
| test_enums.py | 32 | 0 | ✅ All pass |
| test_config.py | 53 | 0 | ✅ All pass |
| test_errors.py | 38 | 0 | ✅ All pass |
| test_ticket_models.py | 48 | 0 | ✅ All pass |
| test_search_models.py | 49 | 0 | ✅ All pass |
| test_api_models.py | 74 | 0 | ✅ All pass |
| test_store.py | 54 | 0 | ✅ All pass |
| test_index.py | 35 | 0 | ✅ All pass |
| test_ticket_service.py | 22 | 1 | ⚠️ 1 filter test failure |
| test_integration.py | 0 | 18 | ❌ All fail - async/await bug |

### Failure Analysis

**test_integration.py (18 failures)**:
- Root cause: `await service.create_ticket()` receives a `Ticket` object instead of a coroutine
- The `TicketService.create_ticket` method is not properly async in the implementation
- **Impact**: Integration tests are completely broken

**test_ticket_service.py (1 failure)**:
- `test_list_tickets_with_filters`: Filter returns empty list instead of expected 2 crash tickets
- **Impact**: Filter functionality may be broken in TicketService

---

## Consolidated Issues (unfixed across all reviews)

| # | Issue | Severity | Source | Status |
|---|-------|----------|--------|--------|
| 1 | SearchMeta.latency_ms uses float, spec says int | Minor | review-fix-2 | UNFIXED |
| 2 | FilterSet.is_empty() missing updated_before check | Minor | review-fix-2 | UNFIXED |
| 3 | BM25 ranking order not tested | Minor | review-tests-3 | UNFIXED |
| 4 | Atomic write failure cleanup not tested | Minor | review-tests-3 | UNFIXED |
| 5 | DELETE endpoint returns 204 vs spec 200 | Medium | This review | UNFLAGGED |
| 6 | DELETE params: mode vs force/dry_run | Medium | This review | UNFLAGGED |
| 7 | TicketService.create_ticket not async | **Critical** | test_integration | **NEW - BLOCKING** |
| 8 | TicketService list filters broken | High | test_ticket_service | **NEW - BLOCKING** |
| 9 | test_api_routes.py missing references test | Minor | This review | UNFIXED |
| 10 | test_api_routes.py missing additional query params | Minor | This review | UNFIXED |

---

## Verdict: WARN

### Positive Findings
- ✅ **test_api_routes.py**: All 18 tests pass, comprehensive coverage of CRUD operations
- ✅ **Mock design**: Correctly mimics TicketService interface
- ✅ **Response formats**: Match OpenAPI ErrorResponse and TicketResponse schemas
- ✅ **HTTP status codes**: Correct for all endpoints except DELETE (which uses valid alternative)
- ✅ **Pagination**: limit/offset correctly tested
- ✅ **Filters**: repo, category, severity, status all tested

### Blocking Issues
1. **TicketService async bug** (Critical): Integration tests fail because `create_ticket` returns Ticket instead of awaitable
2. **Filter functionality broken** (High): `test_list_tickets_with_filters` fails

### Spec Deviations
1. **DELETE endpoint**: Returns 204 instead of 200 with response body
2. **DELETE parameters**: Uses `mode` (soft/hard) instead of `force` (boolean) and `dry_run`

### Recommendations
1. Fix TicketService async/await issues (blocking integration tests)
2. Fix filter logic in list_tickets (blocking service tests)
3. Decide on DELETE spec: either update OpenAPI spec or fix implementation
4. Add tests for missing query params (assignee, tags, created_*, sort, format)
5. Add test for TicketCreate.references field

---

**Review Date**: 2026-03-19
**Reviewer**: Subagent (review-8-8)
**Files Reviewed**: 
- Test: `tests/test_api_routes.py`
- Source: `src/vtic/api/app.py`, `src/vtic/api/deps.py`, `src/vtic/api/routes/tickets.py`
- Spec: `openapi-stages/stage2-crud.yaml`, `openapi-stages/stage1-foundation.yaml`
- Previous reviews: 6 files (review-tests-{1,2,3}.md, review-fix-{1,2,3}.md)
