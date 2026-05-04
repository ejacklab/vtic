# Diary

## 2026-04-29 — VTIC Phase 2 due_date

**Goal:** Add optional ticket due dates across VTIC models, storage, CLI, API, migration tooling, and tests.
**Outcome:** DONE

### What happened
Implemented `due_date` on ticket create/update/response flows, frontmatter serialization/parsing, due range filters, CLI/API query support, and `due_date` sorting. Added the migration script from the Phase 2 plan and covered model, storage, CLI, and API behavior with tests.

### Decisions
- Applied the corrected `due_before` expectation: C2 due on 2026-06-15 is excluded by `due_before=2026-06-01`.
- Left pre-existing untracked `tickets/` content untouched.

### Dead ends
- none

### State at session end
Verified with `python -m pytest tests/ -v 2>&1 | tail -40` -> `200 passed in 1.44s`.

## 2026-03-14 — self-harness bootstrap

**Goal:** Give cclow a lightweight operating harness inside this workspace.
**Outcome:** DONE

### What happened
Created local workflow rules, lightweight skill docs, task state scaffolding, and AGENTS hooks so future non-trivial work follows a plan/review/retro loop.

### Decisions
- Default to `scrum-master-lite` rather than heavy ceremony.
- Keep the self-harness workspace-local and adapted to OpenClaw instead of copying the portable pack verbatim.

### Dead ends
- Initially optimized the portable release artifact instead of adopting the harness for myself.

### State at session end
Local harness files exist under `skills/`, `rules/workflow/`, `plans/`, and `state.md`. Next step is to consistently use them during real tasks.
## 2026-03-20

- Completed a small TDD slice for `shared.prompt_utils` in `/tmp/codex-promptutils`.
- Wrote `tests/test_prompt_utils.py` first, then implemented `backend/shared/prompt_utils.py`.
- Verified with `cd /tmp/codex-promptutils && python3 -m pytest tests/test_prompt_utils.py` because `pytest` was not on PATH.

## 2026-03-22

- Fixed MoneyFlow agent auth blockers in `/tmp/lovemonself`.
- Patched `backend/shared/agent_tokens.py` so token creation uses a Firestore transaction that removes the plaintext `token` field before commit and returns only the in-memory plaintext once.
- Patched `backend/shared/auth.py` so `verify_agent_token()` accepts `required_permission`, captures client IP, and `require_permission()` routes agent permission checks through the shared verifier.
- Updated `backend/api-gateway/routes/analytics.py` to require explicit read permissions instead of Firebase-only auth.
- Added targeted tests in `backend/api-gateway/tests/test_auth.py` and `backend/shared/test_agent_tokens.py`.
- Verified with `pytest /tmp/lovemonself/backend/api-gateway/tests/test_auth.py /tmp/lovemonself/backend/shared/test_agent_tokens.py` → `25 passed`.
- Follow-up noted: `datetime.utcnow()` in `agent_tokens.py` emits a deprecation warning and should be moved to timezone-aware UTC values.

## 2026-03-23 (afternoon)

### Security Review + Deployment Fixes
- Completed security review of MoneyFlow API key auth (S6/S7/S8)
- Committed fixes: `1a55f4c` — S6/S7/S8 security patches
- Gemini CLI deployment found Cloud Run gaps:
  - Missing `email-validator` in requirements.txt (EmailStr needs it)
  - Missing `field_validator` import in routes/agent_tokens.py
  - Missing env vars in service.yaml: FIREBASE_PROJECT_ID, TOKEN_HASH_SECRET, ALLOWED_ORIGINS
- Committed deploy fixes: `560ea9c`
- TOKEN_HASH_SECRET must be set via `gcloud run services update` — not in service.yaml (secrets management)
- `datetime.utcnow()` in agent_tokens.py has deprecation warning → should use timezone-aware UTC (follow-up)

## 2026-03-23 (evening)

### MoneyFlow API Deployment + Token Generator
- API gateway deployed successfully (was crashing — FIREBASE_PROJECT_ID env var was missing)
- All 4 critical bug fixes in agent_tokens.py: TypeError on generate_token(), disabled user bypass, TOCTOU race, datetime.utcnow() deprecation
- Unified TOKEN_HASH_SECRET format with vti-ap01- prefix (same as API tokens)
- Token format: vti-ap01-<18 hex chars> (72 bits entropy)
- Created scripts/create_finan_token.py to create agent tokens
- API gateway live at: https://api-gateway-197629616256.asia-southeast1.run.app
- service.yaml now has FIREBASE_PROJECT_ID and TOKEN_HASH_SECRET as placeholders (to be injected via gcloud run services update)
- KEY LESSON: gcloud beta run services logs read — not gcloud run logs read
- KEY LESSON: @db.transactional is the decorator, not transaction=True parameter

## 2026-03-24

### mfl CLI — Device Code Flow
- Built full `mfl` CLI tool: connect, status, tokens, revoke
- SPEC written + reviewed by 3 agents (Kimi + GLM-5 + MiniMax), 11 review files committed
- Key design: device_code (UUID) for API, user_code (6-digit) for human entry
- Token stored after /complete, returned lazily on first /poll

### mfl Backend — Connect Endpoints
- GLM-5 built 6 endpoints in MoneyFlow backend (connect flow + token management)
- Kimi review found 3 issues: /poll rate limit missing, tokens returning revoked, token=None on first poll
- All 3 fixed and committed

### Lessons Learned
1. **Subagents can't spawn subagents** — cascading work must be sequential, not nested
2. **Firebase ID tokens from /complete** — store the Google ID token, return it in /poll (don't generate on-demand)
3. **slow_down needs in-memory tracking** — poll count per device_code in dict
4. **Token revocation = soft delete** — is_active:false filter keeps revoked tokens out of GET /user/tokens
5. **Concise reviews work better** — 400-500 word limit kept Kimi's output tight and actionable
6. **Working files → workspace, not /tmp/** — /tmp/ wiped on restart; always use /home/smoke01/.openclaw/workspace-cclow/tmp/

### What's Next
- API Keys page needs full build in ejai-landing-page
- mfl backend needs deploy + e2e test: mfl connect finan
