# Fix Report: Blocking Issues 1 & 4

**Date:** 2026-03-19
**Status:** ✅ Fixed & Verified

---

## Issue 1: TERMINAL_STATUSES missing FIXED (Critical)

### Problem
3-way inconsistency between spec, implementation, and test:
- Spec: FIXED is terminal
- `Status.FIXED.is_terminal`: returns `True`
- `TERMINAL_STATUSES` set: did NOT include `FIXED`

### Root Cause
The fix review claimed it was fixed, but the source code was never actually changed.

### Fix Applied
1. **`src/vtic/models/enums.py`** (line 112):
   ```python
   # Before
   TERMINAL_STATUSES: Set[Status] = {Status.CLOSED, Status.WONT_FIX}
   
   # After
   TERMINAL_STATUSES: Set[Status] = {Status.FIXED, Status.CLOSED, Status.WONT_FIX}
   ```

2. **`tests/test_enums.py`** (line 113):
   ```python
   # Before (testing the bug!)
   assert Status.FIXED not in TERMINAL_STATUSES  # FIXED is not in the constant
   
   # After (correct assertion)
   assert Status.FIXED in TERMINAL_STATUSES  # FIXED is terminal
   ```

---

## Issue 4: SuggestResult model deviates from spec (High)

### Problem
Implementation had `{query: str, suggestions: list[str]}` but spec defines:
```python
class SuggestResult(BaseModel):
    suggestion: str    # Single suggestion
    ticket_count: int  # Number of matching tickets
```

The `/search/suggest` endpoint returns `list[SuggestResult]`:
```json
[
    {"suggestion": "CORS wildcard issue", "ticket_count": 3},
    {"suggestion": "CORS configuration error", "ticket_count": 2},
    {"suggestion": "CORS preflight timeout", "ticket_count": 1}
]
```

### Fix Applied
1. **`src/vtic/models/search.py`** (SuggestResult class):
   - Changed from `{query, suggestions: list[str]}` to `{suggestion: str, ticket_count: int}`
   - Updated docstring and example JSON to match spec

2. **`tests/test_search_models.py`** (TestSuggestResult class):
   - Replaced all old tests with new tests for the correct model:
     - `test_required_fields`: Tests `suggestion` and `ticket_count`
     - `test_ticket_count_min_zero`: Validates `ticket_count >= 0`
     - `test_serialization`: Verifies JSON output
     - `test_suggest_result_list_example`: Shows proper usage as `list[SuggestResult]`
   - Updated `TestSampleJsonOutputs.test_suggest_result_json` for new model

---

## Test Results

```
============================= test session starts ==============================
collected 91 items

tests/test_enums.py: 33 passed
tests/test_search_models.py: 58 passed

============================== 91 passed in 0.12s ==============================
```

All tests pass with the fixes applied.

---

## Files Changed

| File | Change |
|------|--------|
| `src/vtic/models/enums.py` | Added `Status.FIXED` to `TERMINAL_STATUSES` |
| `src/vtic/models/search.py` | Aligned `SuggestResult` to spec |
| `tests/test_enums.py` | Fixed assertion to expect `FIXED` in `TERMINAL_STATUSES` |
| `tests/test_search_models.py` | Updated `TestSuggestResult` tests for new model |
