# VTIC Phase 2 Due Date Session State

## Task
- Add due_date support across VTIC models, storage, CLI, API, migration, and tests.

## Status
- DONE

## Plan
- [x] Step 1: Update `src/vtic/models.py`
- [x] Step 2: Update `src/vtic/storage.py`
- [x] Step 3: Update `src/vtic/cli/main.py`
- [x] Step 4: Update `src/vtic/api.py`
- [x] Step 5: Add `scripts/migrate_add_due_date.py`
- [x] Step 6: Add/adjust tests
- [x] Step 7: Run `python -m pytest tests/ -v 2>&1 | tail -40`

## Completed
- Read workspace identity, user context, long-term memory, workflow rules, and the full Phase 2 plan.
- Removed stale `BOOTSTRAP.md` per workspace startup instruction.
- Added `due_date` support across models, storage, CLI, API, and tests.
- Added `scripts/migrate_add_due_date.py`.
- Verified with `python -m pytest tests/ -v 2>&1 | tail -40` -> `200 passed in 1.44s`.

## In Progress
- none

## Decisions Made
- Leave pre-existing untracked `tickets/` content untouched.
- Apply the requested corrected due_before assertion: `["C1"]`.

## Failed Approaches
- none

## Blocked
- none

## Next Steps
- none

## Verify
- `cd /home/smoke01/.hermes/profiles/apex/workspace/vtic && python -m pytest tests/ -v 2>&1 | tail -40` -> passed
