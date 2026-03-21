# SESSION_STATE

## Task
- TDD for `shared.prompt_utils` in `/tmp/codex-promptutils`

## Status
- DONE

## Plan
- [x] Inspect target tree and determine minimal layout
- [x] Create `tests/test_prompt_utils.py` first
- [x] Implement `backend/shared/prompt_utils.py`
- [x] Run targeted pytest and confirm all cases pass

## Completed
- Confirmed `/tmp/codex-promptutils` was empty and no existing project config was present.
- Added test coverage for `format_money` and `extract_preferences` before implementation.

## In Progress
- None.

## Decisions Made
- Keep the slice minimal: direct import from `backend.shared.prompt_utils`, relying on the project root on `sys.path`.

## Failed Approaches
- The direct patch tool was blocked by the read-only sandbox; switched to the local patch utility with escalated shell access.

## Blocked
- None.

## Next Steps
- None.

## Verify
- `cd /tmp/codex-promptutils && python3 -m pytest tests/test_prompt_utils.py`
