# REVIEW-011-012: GET/DELETE /api/user/tokens Endpoints

**Reviewer:** GLM-5  
**Date:** 2026-03-24  
**Scope:** Token management endpoint spec review

---

## GET /api/user/tokens

### What's Defined ✓
- Authorization header with Firebase ID token
- Response format: `{ tokens: [...] }` array
- Token object includes: `token_id`, `label`, `permissions`, `created_at`, `expires_at`, `is_active`
- Clear purpose: "Lists all tokens for the authenticated user"

### Gaps

| # | Issue | Severity |
|---|-------|----------|
| 1 | **No pagination defined** — Response assumes all tokens fit in one page. For users with many agents/devices, this could return large payloads or hit Firestore limits. | P2 |
| 2 | **No query parameters documented** — Can't filter by `is_active`, agent name, or date range | P2 |
| 3 | **No error responses documented** — What happens with invalid/expired auth token? | P1 |
| 4 | **Missing `last_used_at` field** — Documented in credential storage but not returned in API response | P1 |

---

## DELETE /api/user/tokens/<token_id>

### What's Defined ✓
- Authorization header with Firebase ID token
- Path parameter: `token_id`
- Success response: `{ success: true }`

### Gaps

| # | Issue | Severity |
|---|-------|----------|
| 1 | **Ownership verification not documented** — Spec doesn't state that backend must verify `token_id` belongs to the authenticated user. Without this, user A could revoke user B's token by guessing IDs. | **P0** |
| 2 | **Soft delete not documented in main spec** — Only mentioned in P1 fix notes. Main spec should explicitly state: sets `is_active: false` and `revoked_at: <timestamp>` | **P0** |
| 3 | **No error responses documented** — Missing: 404 (token not found), 403 (token belongs to another user), 409 (already revoked), 401 (invalid auth) | **P0** |
| 4 | **No response body for deleted token info** — Should return which token was revoked (label, token_id) for client confirmation | P2 |
| 5 | **No idempotency guidance** — Should DELETE on already-revoked token return 200 or 409? | P1 |

---

## Summary

| Severity | Count |
|----------|-------|
| **P0** | 3 (all on DELETE) |
| **P1** | 3 |
| **P2** | 3 |

### Critical Path
1. **DELETE must document ownership check** — This is a security hole
2. **DELETE must document soft delete + audit trail** in the main spec, not just fix notes
3. **DELETE must document error responses** — Clients can't handle failures properly

### Notes
- GET endpoint is reasonably complete for MVP scope
- DELETE endpoint has security and observability gaps that must be addressed before shipping
- Both endpoints missing standard error response documentation (400/401/403/404/500)
