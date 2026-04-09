# Autonomous Ticket Work Plan

## Goal
Work through MoneyFlow (lovemonself) tickets while Ejack sleeps.

## Ticket Queue (Priority Order)

1. **S15-create-shared-prompt-utils** (code_quality) — 1-2h
   - Extract duplicated prompt logic from services to `backend/shared/prompt_utils.py`
   - Add tests
   - Refactor services to import from shared

2. **S15-add-contracts-tests** (testing) — 1-2h
   - Add tests for `backend/shared/contracts/` (4 source files, zero tests)

3. **S13-add-ai-retry-error-handling** (performance) — 2-3h
   - Create `backend/shared/retry.py` with exponential backoff
   - Update orchestrators to use retry logic
   - Add overall timeout to `asyncio.gather()`

4. **S7-add-python-tests-critical-paths** (testing) — 3-4h
   - Tests for auth, transactions, models
   - Blocked by S1 ✅, S4 ✅

5. **S8-add-github-actions-ci-pipeline** (testing) — 1-2h
   - Create `.github/workflows/ci.yml`
   - Blocked by S7

6. **S9-add-agent-auth-rate-limiting** (architecture) — 2-3h
   - Agent API key auth
   - Rate limiting with slowapi
   - Blocked by S1 ✅, S2 ✅

7. **S10-build-summary-budget-api** (architecture) — 3-4h
   - GET /api/summary, GET /api/budget/status, POST /api/budget/set, GET /api/alerts
   - Blocked by S3 ✅, S9

8. **S11-build-transaction-trends-export-api** (architecture) — 3-4h
   - GET /api/transactions, GET /api/trends, GET /api/transactions/export
   - Blocked by S3 ✅, S9, S10

9. **S14-add-caching-frontend-polish** (performance) — 2-3h
   - Preferences caching with 60s TTL
   - Blocked by S3 ✅, S10

## Workflow Per Ticket

1. Read ticket at `/home/smoke01/.openclaw/workspace-cclow/tmp/vtic/tickets/yi1jack0/lovemonself/{category}/{ticket}.md`
2. Read relevant source files in `/tmp/lovemonself/`
3. Implement the fix
4. Run validation (tests if applicable, import checks)
5. Commit with descriptive message
6. Push to `yi1jack0/lovemonself`
7. Update ticket status to "done"
8. Update `memory/2026-03-21.md` with work done
9. Send progress update to Discord

## Completed This Session

- ✅ S1 - Auth consolidation (commit `3181391`)
- ✅ S2 - CORS (already fixed)
- ✅ S3 - Frontend routing (N/A - frontend removed)
- ✅ S4 - Input validation (commit `a0eb5b4`)
