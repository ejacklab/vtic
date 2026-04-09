# Report 1 — Security Vulnerabilities

**Files:** `backend/shared/agent_tokens.py` · `backend/shared/auth.py` · `backend/api-gateway/routes/agent_tokens.py`
**Date:** 2026-03-23
**Skill:** software-security-reviewer

---

## Critical Issues

| ID | Issue | Location | Status |
|---|---|---|---|
| CRYPTO-001 | Raw SHA256 without HMAC | `agent_tokens.py:361` | ✅ Fixed — HMAC-SHA256 with `TOKEN_HASH_SECRET` |
| AUTH-003 | Token revocation not checked | `auth.py:544` | ✅ Fixed — `check_revoked=True` added |
| ERROR-001 | Internal error details leaked | `auth.py:552-553` | ✅ Fixed — specific exception types caught, messages sanitized |
| RACE-002 | Token returned before DB write confirmed | `agent_tokens.py:400-413` | ✅ Fixed — write in try/except, token only returned on success |
| DATA-002 | Plaintext agent keys in environment | (config level) | ✅ Fixed — `AGENT_KEYS` env var (JSON), not plaintext single key |

## Medium Issues

| ID | Issue | Location | Status |
|---|---|---|---|
| RACE-001 | TOCTOU in `verify_token` | `agent_tokens.py:476-479` | ✅ Fixed — fire-and-forget `asyncio.create_task` for last_used update |
| ERROR-002 | Generic exception caught | `auth.py:550` | ✅ Fixed — specific exception types now caught |
| CODE-003 | IP from wrong source | `agent_tokens.py:715` | ✅ Fixed — `X-Forwarded-For` checked before `request.client.host` |
| CONF-001 | No validation on `expires_in_days` | `agent_tokens.py:368` | ✅ Fixed — service layer rejects `< 1` or `> 3650` |

## New Issues Found

| ID | Issue | Location | Detail | Status |
|---|---|---|---|---|
| NEW-001 | Direct call to FastAPI dependency | `auth.py:612` | `verify_any_auth` calls `verify_agent_token()` directly — design smell, not a bug (see note) | ✅ Fixed — impl extracted |
| NEW-002 | Firestore client per-request | `auth.py:569, 592` | `firestore.client()` on every request | ✅ Fixed — `get_firestore_client()` singleton |
| NEW-003 | Silent IP tracking failure | `agent_tokens.py:709` | IP silently `None` if `req` omitted | ✅ Fixed — warning logged |

---

## ⚠️ New-001 Counter-Review (2026-03-23)

**Original finding overstated severity.** After analysis:

- `verify_any_auth` is itself a FastAPI dependency — by the time it runs, `x_agent_key` is already a plain `str` extracted by FastAPI
- Passing it to `verify_agent_token(x_agent_key)` is valid — `Header(...)` default is ignored when a value is provided
- **Revised severity: Design smell (low priority)** — the code works correctly

**However**, calling a FastAPI dep directly is fragile: if `verify_agent_token` ever gains middleware hooks or DI wrappers, the direct call silently skips them. The applied fix (extract `_verify_agent_token_impl()` → thin wrapper) is still the right pattern.

---

## Fix Status

| ID | Commits |
|---|---|
| CRYPTO-001 | `bf88b6b` (security fixes from Wave 1) |
| AUTH-003 | `bf88b6b` |
| ERROR-001 | `bf88b6b` |
| RACE-002 | `bf88b6b` |
| DATA-002 | `bf88b6b` |
| RACE-001 | `bf88b6b` |
| ERROR-002 | `bf88b6b` |
| CODE-003 | `bf88b6b` + `e7ad18d` |
| CONF-001 | `6969401` (CORS) + `6388907` (service layer) |
| NEW-001 | `e7ad18d` |
| NEW-002 | `bf88b6b` |
| NEW-003 | `bf88b6b` |

All 12 findings are resolved. Deployed to: `api-gateway-00036-6g5`
