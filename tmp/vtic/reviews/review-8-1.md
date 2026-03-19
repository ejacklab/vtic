# Review: test_enums.py

## Previous Findings Status

| Finding | Fixed? | Evidence |
|---------|--------|----------|
| TERMINAL_STATUSES includes FIXED? | ❌ **NOT FIXED** | Source still has `TERMINAL_STATUSES = {Status.CLOSED, Status.WONT_FIX}` - FIXED missing |
| get_prefix(None) guard added? | ✅ FIXED | Lines 65-66: `if category is None: return "G"` + test at lines 77-78 |
| All enum values tested? | ✅ VERIFIED | 5 Category, 5 Severity, 6 Status, 4 EmbeddingProvider, 2 DeleteMode all tested |
| Status transitions (valid + invalid) tested? | ✅ VERIFIED | 6 test methods covering all statuses with valid + invalid transitions |

## Critical Issue: TERMINAL_STATUSES Inconsistency

The fix review claimed TERMINAL_STATUSES was updated to include FIXED, but the **source code was never updated**:

**Source code (enums.py line 111):**
```python
TERMINAL_STATUSES: Set[Status] = {Status.CLOSED, Status.WONT_FIX}
```

**Spec (data-models-stage1-enums.md):**
> Terminal statuses: closed, wont_fix, fixed

**is_terminal property:**
```python
return self in (Status.FIXED, Status.WONT_FIX, Status.CLOSED)
```

**Current test (line 113):**
```python
assert Status.FIXED not in TERMINAL_STATUSES  # FIXED is not in the constant
```

**The inconsistency:**
- `Status.FIXED.is_terminal` returns `True` ✓
- `Status.FIXED in TERMINAL_STATUSES` returns `False` ✗
- Spec says FIXED should be terminal

**Verdict**: Test correctly documents broken implementation. Source needs fix, not test.

## Coverage Analysis

| Enum/API | Tested | Missing |
|----------|--------|---------|
| Category (5 values) | ✅ All | - |
| Category.get_prefix() | ✅ enum, str, unknown, None | Empty string `""` |
| Severity (5 values) | ✅ All | - |
| Severity.weight | ✅ All weights 0-4 | - |
| Status (6 values) | ✅ All | - |
| Status.is_terminal | ✅ All 6 statuses | - |
| Status.display_name | ✅ All 6 names | - |
| Status.can_transition_to() | ✅ All transitions | - |
| VALID_STATUS_TRANSITIONS | ✅ Contents verified | - |
| TERMINAL_STATUSES | ⚠️ Partial | FIXED missing (source bug) |
| EmbeddingProvider (4 values) | ✅ All | - |
| DeleteMode (2 values) | ✅ All | - |

## Test Quality

**Strengths:**
- Clear, descriptive test names
- Independent tests (no shared mutable state)
- Both positive and negative cases tested
- Good coverage of edge cases (None, unknown strings)
- Transitions tested comprehensively with valid AND invalid cases

**Minor gaps:**
- `Category.get_prefix("")` not tested (returns "G" but unverified)
- No parameterized tests (could reduce repetition in value checks)

## New Issues Found

### Critical

1. **TERMINAL_STATUSES constant inconsistent with spec and is_terminal property**
   - Location: `src/vtic/models/enums.py` line 111
   - Fix: Change to `{Status.CLOSED, Status.WONT_FIX, Status.FIXED}`
   - Test should then be updated to `assert Status.FIXED in TERMINAL_STATUSES`

### Suggestions

1. **Add empty string test for get_prefix**
   ```python
   def test_category_prefix_mapping_empty_string(self):
       assert Category.get_prefix("") == "G"
   ```

## Test Results

```
32 passed in 0.07s ✅
```

All tests pass because the test correctly matches current (buggy) implementation.

## Verdict: WARN

Tests are well-written and comprehensive. However:
- The claimed fix to TERMINAL_STATUSES was never applied to source code
- There's a 3-way inconsistency between spec, `is_terminal` property, and `TERMINAL_STATUSES` constant
- The test correctly documents the broken state

**Action required**: Fix `src/vtic/models/enums.py` line 111:
```python
TERMINAL_STATUSES: Set[Status] = {Status.CLOSED, Status.WONT_FIX, Status.FIXED}
```

Then update test line 113:
```python
assert Status.FIXED in TERMINAL_STATUSES
```
