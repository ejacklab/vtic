# vtic Final Audit - Reconciliation Check

**Date:** 2026-03-18  
**Auditor:** Subagent (final-audit-3)  
**Files Audited:**
- openapi.yaml
- DATA_FLOWS_OPERATIONS.md
- DATA_FLOWS_DETAILED.md
- data-models-stage1-enums.md
- data-models-stage2-ticket.md
- data-models-stage3-search.md
- data-models-stage6-errors-map.md

---

## Audit Results

| Check | Expected | Found | Status |
|-------|----------|-------|--------|
| 1. No `created_at`, `updated_at`, `SearchRequest`, `topk`, `match_type`, `server.port`, `tickets.dir` | None used as active field names | Only appear in "Key Changes" documentation (stage3-search) and mapping tables (stage6-errors-map) documenting old→new transitions. Not used actively. | **PASS** |
| 2. Category values | crash, hotfix, feature, security, general | crash, hotfix, feature, security, general across all docs | **PASS** |
| 3. Severity includes `info` | info in severity enum | critical, high, medium, low, info in openapi.yaml, stage1-enums, DATA_FLOWS examples | **PASS** |
| 4. ID pattern | `^[CFGHST]\d+$` | `^[CFGHST]\d+$` in openapi.yaml, stage1-enums, stage2-ticket, DATA_FLOWS_DETAILED.md | **PASS** |
| 5. Error codes match OpenAPI (6 codes) | VALIDATION_ERROR, NOT_FOUND, CONFLICT, PAYLOAD_TOO_LARGE, INTERNAL_ERROR, SERVICE_UNAVAILABLE | DATA_FLOWS_OPERATIONS.md shows HTTP 502 for "Embedding provider error" but OpenAPI uses 503 with SERVICE_UNAVAILABLE. DATA_FLOWS_DETAILED.md correctly uses 6 codes. | **FAIL** |
| 6. Field names match Pydantic models | Consistent field names in walkthroughs | title, description, repo, category, severity, status, assignee, fix, tags, references, created, updated consistent across all flows | **PASS** |
| 7. Search flow uses SearchQuery, limit, offset, source, hits | SearchQuery model with limit, offset; SearchHit with source; SearchResult with hits | SearchQuery (limit=20, offset=0), SearchHit.source (bm25/semantic/hybrid), SearchResult.hits array - all correct | **PASS** |
| 8. Module names match module map | api/routes/system.py, api/routes/search.py, api/routes/tickets.py | DATA_FLOWS_DETAILED.md incorrectly references `routes/health.py` and `routes/config.py` instead of `api/routes/system.py` | **FAIL** |
| 9. Config uses api.port, storage.dir, port 8080 | api.port, storage.dir, default port 8080 | api.port, storage.dir in openapi.yaml ConfigResponse; port 8080 default in all docs | **PASS** |
| 10. End-to-end field consistency | Field names consistent through create→search→update→delete | id, title, description, repo, category, severity, status, assignee, fix, tags, references, created, updated consistent throughout | **PASS** |

---

## Issues Found

### Issue 1: HTTP 502 vs 503 for Embedding Provider Error (Check 5)

**Location:** `DATA_FLOWS_OPERATIONS.md`, POST /search flow diagram

**Problem:**
```mermaid
E502["HTTP 502<br/>{error: 'Embedding provider error'}"]
```

**Expected (per OpenAPI):**
- HTTP Status: 503
- Error Code: SERVICE_UNAVAILABLE
- Example from openapi.yaml:
```json
{
  "error": {
    "code": "SERVICE_UNAVAILABLE",
    "message": "Semantic search requested but no embedding provider is configured"
  }
}
```

**Fix Required:** Change `E502` to `E503` and update error message to match OpenAPI spec.

---

### Issue 2: Incorrect Module Paths (Check 8)

**Location:** `DATA_FLOWS_DETAILED.md`, sections 3.1 and 3.2

**Problem:**
- Section 3.1 (Health Check): References `routes/health.py`
- Section 3.2 (Configuration): References `routes/config.py`

**Expected (per stage6-errors-map module structure):**
```
api/routes/
├── tickets.py   # CRUD endpoints
├── search.py    # search endpoint
└── system.py    # health, stats, reindex, config
```

Health and config endpoints are both in `api/routes/system.py`, not separate files.

**Fix Required:**
- Change `routes/health.py` → `api/routes/system.py`
- Change `routes/config.py` → `api/routes/system.py`

---

## Summary

| Metric | Count |
|--------|-------|
| Total Checks | 10 |
| Passed | 8 |
| Failed | 2 |

**Overall Status: FAIL**

Two issues require fixes before implementation:
1. DATA_FLOWS_OPERATIONS.md: Change HTTP 502 → 503 for embedding provider error
2. DATA_FLOWS_DETAILED.md: Correct module paths from `routes/health.py` and `routes/config.py` to `api/routes/system.py`

---

## Verification Details

### Forbidden Terms Search Results

| Term | Found In | Context | Acceptable? |
|------|----------|---------|-------------|
| `created_at` | stage6-errors-map | Field mapping table documenting old→new | Yes (documentation) |
| `updated_at` | stage6-errors-map | Field mapping table documenting old→new | Yes (documentation) |
| `SearchRequest` | stage3-search | "Key Changes" section listing rename to SearchQuery | Yes (documentation) |
| `topk` | stage3-search, stage6-errors-map | "Key Changes" and mapping table | Yes (documentation) |
| `match_type` | stage3-search, stage6-errors-map | "Key Changes" and mapping table | Yes (documentation) |
| `server.port` | stage6-errors-map | Field mapping table | Yes (documentation) |
| `tickets.dir` | stage6-errors-map | Field mapping table | Yes (documentation) |

All forbidden terms only appear in documentation explaining the migration from old names to new names. They are NOT used as active field names in any model, flow, or API definition.

### Error Code Verification

| Error Code | HTTP Status | In OpenAPI | In DATA_FLOWS_DETAILED | In DATA_FLOWS_OPERATIONS |
|------------|-------------|------------|------------------------|--------------------------|
| VALIDATION_ERROR | 400 | ✓ | ✓ | ✓ (as 400) |
| NOT_FOUND | 404 | ✓ | ✓ | ✓ (as 404) |
| CONFLICT | 409 | ✓ | ✓ | ✓ (as 409) |
| PAYLOAD_TOO_LARGE | 413 | ✓ | ✓ | Not shown |
| INTERNAL_ERROR | 500 | ✓ | ✓ | ✓ (as 500) |
| SERVICE_UNAVAILABLE | 503 | ✓ | ✓ | ✓ (as 503) |
| (extra 502) | 502 | ✗ | ✗ | ✓ (should not exist) |

---

*Audit completed at 2026-03-18*
