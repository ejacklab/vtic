# Diary

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
