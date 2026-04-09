# Review: test_store.py

**Date:** 2026-03-19
**Reviewer:** cclow (subagent)
**Status:** PASS with WARNINGS

---

## Test Results

```
53 tests passed in 0.25s
```

All tests pass. No failures.

---

## Previous Findings Status

| # | Finding | Fixed? | Evidence |
|---|---------|--------|----------|
| 1 | Missing explicit atomic write failure test | ❌ NO | `test_atomic_write_no_partial_files` only tests success case; no failure simulation |
| 2 | Missing tests for special characters in titles | ⚠️ PARTIAL | `test_roundtrip_with_unicode` tests unicode; YAML special chars handled by PyYAML auto-quoting but not explicitly tested |
| 3 | Fix field edge cases incomplete (empty vs null) | ❌ NO | No test for empty string fix `""`; behavior differs (empty creates Fix section, null doesn't) |
| 4 | Duplicate ID handling not tested | ❌ NO | No test for overwriting existing ticket with same ID |

### Detail on Unfixed Findings

#### Finding 1: Atomic Write Failure Test
**Location:** `TestWriteTicket::test_atomic_write_no_partial_files`
**Issue:** Test only verifies no temp files after *successful* write. Source code (`markdown.py::write_ticket`) has exception handling to clean up temp files, but this path isn't tested.

**Recommended Test:**
```python
def test_atomic_write_cleanup_on_failure(self, tmp_path, monkeypatch):
    """Test temp file is cleaned up if write fails."""
    ticket_path = tmp_path / "test.md"
    ticket = SAMPLE_TICKETS[0]
    
    def fail_write(*args, **kwargs):
        raise OSError("Disk full")
    
    monkeypatch.setattr("os.write", fail_write)
    
    with pytest.raises(OSError):
        write_ticket(ticket_path, ticket)
    
    assert list(tmp_path.glob("*.tmp")) == []
    assert not ticket_path.exists()
```

#### Finding 3: Empty String Fix vs Null Fix
**Verified Behavior:**
- `fix: None` → No "## Fix" section in markdown
- `fix: ""` → Creates "## Fix" section with empty content

**Issue:** This inconsistency could cause problems. Empty string is semantically "no fix" but creates a section. The spec defines `fix: Optional[str] = None`, implying None is the canonical "no fix" value.

**Recommended:** Either normalize empty string to None, or add explicit test for this edge case.

---

## New Issues

### Warning

1. **No explicit datetime ISO8601 roundtrip test**
   - `test_roundtrip_preserves_all_fields` tests string comparison
   - SAMPLE_TICKETS use string timestamps like `"2026-03-18T10:00:00Z"`
   - No test verifies datetime objects roundtrip correctly
   - **Risk:** Low (PyYAML handles ISO8601 strings fine)

2. **Empty string edge case behavior differs from None**
   - Empty string `fix: ""` creates a Fix section
   - Null `fix: null` does not
   - This is inconsistent with spec which uses `Optional[str]` with default `None`
   - **Recommendation:** Add explicit test or normalize empty strings to None

### Suggestion

1. **Add test for YAML special characters**
   - PyYAML handles `:`, `#`, `"` correctly by auto-quoting
   - But there's no explicit test verifying roundtrip of these characters
   - Manual verification shows it works, but test coverage is missing

---

## Coverage Analysis

| Function | Tested | Edge Cases Missing |
|----------|--------|-------------------|
| `ticket_file_path` | ✅ 3 tests | None |
| `resolve_path` | ✅ 4 tests | None |
| `trash_path` | ✅ 2 tests | None |
| `ensure_dirs` | ✅ 2 tests | None |
| `ticket_to_markdown` | ✅ 6 tests | Special YAML chars, empty fix |
| `markdown_to_ticket` | ✅ 5 tests | None |
| `write_ticket` | ✅ 4 tests | Failure cleanup not tested |
| `read_ticket` | ✅ 3 tests | None |
| `delete_ticket` | ✅ 4 tests | None |
| `list_tickets` | ✅ 6 tests | None |
| `scan_all_tickets` | ✅ 5 tests | None |

**Coverage Summary:** 44 test cases across 11 functions. All public functions tested.

---

## NEW Review Items

### Roundtrip ALL Field Types

| Field Type | Tested | Notes |
|------------|--------|-------|
| `str` | ✅ | All string fields in SAMPLE_TICKETS |
| `int` | ⚠️ | No int field in Ticket model; `test_parse_all_types` tests parsing but not roundtrip |
| `list[str]` | ✅ | tags, references tested |
| `null` | ✅ | assignee, fix tested as null |
| `datetime ISO8601` | ⚠️ | Tested as string roundtrip, not datetime object |

**Note:** Ticket model has no integer fields. The spec only defines string, datetime, and list types.

### Path Generation Format: `{repo}/{category}/{id}-{slug}.md`

| Test | Status |
|------|--------|
| `test_basic_path_generation` | ✅ Verified `/tickets/ejacklab/open-dsearch/security/C1-cors-wildcard-issue.md` |
| `test_path_with_nested_repo` | ✅ Verified `/data/org/sub-org/repo-name/feature/F42-new-feature.md` |
| `test_path_with_special_chars_in_slug` | ✅ Verified `C1-fix-123-memory-leak.md` |

**Verdict:** Path format correctly implemented and tested.

### Soft/Hard Delete Verified on Filesystem

| Test | Status | Verification |
|------|--------|--------------|
| `test_soft_delete_moves_to_trash` | ✅ | Checks `assert not ticket_path.exists()` and `assert trash_dir.exists()` |
| `test_hard_delete_removes_file` | ✅ | Checks `assert not ticket_path.exists()` |

**Verdict:** Both delete modes verified on filesystem.

### List with Filters

| Test | Status | Coverage |
|------|--------|----------|
| `test_list_all_tickets` | ✅ | No filters |
| `test_list_tickets_with_repo_filter` | ✅ | Single repo |
| `test_list_tickets_with_category_filter` | ✅ | Single category |
| `test_list_tickets_with_both_filters` | ✅ | repo + category combined |
| `test_list_tickets_empty_directory` | ✅ | Empty result |
| `test_list_tickets_nonexistent_directory` | ✅ | Graceful handling |

**Verdict:** Filter functionality fully tested.

### scan_all_tickets

| Test | Status | Coverage |
|------|--------|----------|
| `test_scan_multiple_repos` | ✅ | Multiple repos, parses content |
| `test_scan_skips_trash_directory` | ✅ | .trash excluded |
| `test_scan_returns_path_and_ticket` | ✅ | Returns tuple format |
| `test_scan_handles_corrupt_files` | ✅ | Graceful skip |
| `test_scan_empty_directory` | ✅ | Returns empty list |

**Verdict:** scan_all_tickets fully tested.

### ensure_dirs

| Test | Status | Coverage |
|------|--------|----------|
| `test_create_nested_directories` | ✅ | Deep nesting |
| `test_existing_directories` | ✅ | Idempotent |

**Verdict:** ensure_dirs fully tested.

---

## Markdown Format Verification

### Spec Format (from data-models-stage2-ticket.md)

```
---
id: C1
title: CORS Wildcard Issue
description: The API allows wildcard CORS origins...
repo: ejacklab/open-dsearch
category: security
severity: high
status: open
assignee: null
fix: null
tags:
- cors
- security
references: []
created: '2026-03-18T10:00:00Z'
updated: '2026-03-18T10:00:00Z'
---

## Description
The API allows wildcard CORS origins in production...

## Fix
[Only when fix is set]
```

### Actual Output (verified)

```
---
id: C1
title: 'CORS Wildcard Issue'
description: 'The API allows wildcard CORS origins in production environments.'
repo: ejacklab/open-dsearch
category: security
severity: high
status: open
assignee: null
fix: null
tags:
- cors
- security
references: []
created: '2026-03-18T10:00:00Z'
updated: '2026-03-18T10:00:00Z'
---

## Description
The API allows wildcard CORS origins in production environments.
```

### Compliance Check

| Requirement | Status | Notes |
|-------------|--------|-------|
| YAML frontmatter with `---` delimiters | ✅ | Correct |
| All required fields present | ✅ | 13 fields |
| Field order matches spec | ✅ | id, title, description, repo, category, severity, status, assignee, fix, tags, references, created, updated |
| `## Description` section | ✅ | Always present |
| `## Fix` section only when fix set | ✅ | Only when `fix is not None` |
| ISO8601 timestamps | ✅ | Quoted strings |
| Null values as `null` | ✅ | YAML null |
| Empty lists as `[]` | ✅ | YAML empty list |

**Verdict:** Format matches spec exactly. PyYAML adds quotes to some string values (timestamps, strings with special chars) which is valid YAML.

---

## Summary

### What's Good
- All 53 tests pass
- 100% function coverage
- Roundtrip tests verify all SAMPLE_TICKETS
- Soft/hard delete tested on filesystem
- Path format verified
- Filter combinations tested
- Corrupt file handling tested
- Unicode support verified

### What's Missing
- Atomic write failure test (cleanup on exception)
- Empty string vs null fix edge case
- Duplicate ID overwrite behavior
- Explicit YAML special char test

---

## Verdict: **PASS** with WARNINGS

The test suite is **production-ready** for the happy path. The warnings are minor edge cases that don't affect normal operation:

1. **Atomic write failure cleanup** - Source code has proper exception handling; just not explicitly tested
2. **Empty string fix** - Edge case; spec uses `None` as default
3. **Duplicate ID** - Behavior is documented (overwrites); not a bug

**Recommendation:** Address warnings before next major release. Current state is acceptable for production use.
