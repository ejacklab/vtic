# Test Review: T5 (Markdown Store) + T6 (Zvec Index)

## Summary
**pass** with minor suggestions

The test suite provides good coverage for both the Markdown Store (T5) and Zvec Index (T6) modules. All 85 tests pass. The tests verify core functionality including atomic writes, roundtrip serialization, soft/hard deletes, BM25 search, filters, and pagination.

---

## Issues Found

### Critical
None

### Warnings

1. **Missing explicit atomic write failure test** (`test_store.py`)
   - The `test_atomic_write_no_partial_files` test verifies no temp files remain after *successful* writes
   - It does NOT simulate an actual write failure (e.g., disk full, permission denied) to verify cleanup on exception
   - The source code (`markdown.py::write_ticket`) has exception handling to clean up temp files, but this path isn't directly tested

2. **BM25 search tests don't verify ranking order** (`test_index.py`)
   - Tests verify that search "returns results" containing expected IDs
   - They don't assert that higher-relevance documents rank above lower-relevance ones
   - Example: `test_search_sql_injection` checks S1 is in results, but doesn't verify it's ranked higher than less-relevant tickets

3. **Missing tests for special characters in titles/slugs** (`test_store.py`)
   - No tests for titles with quotes, brackets, or YAML-special characters
   - The slug in path generation is tested but not edge cases like empty slug or slug exceeding length limits

4. **Duplicate ID handling not tested** (`test_store.py`)
   - The `write_ticket` function can overwrite existing files (used for updates)
   - No test verifies behavior when writing a ticket with same ID but different content

5. **Fix field edge cases incomplete** (`test_store.py`)
   - `test_ticket_with_fix` tests a non-null fix value
   - No test for empty string fix (`""`) vs null fix behavior
   - The markdown output treats empty string as truthy and would show Fix section

### Suggestions

1. **Add test for write failure cleanup simulation**
   ```python
   def test_atomic_write_cleanup_on_failure(self, tmp_path, monkeypatch):
       """Test temp file is cleaned up if write fails mid-operation."""
       ticket_path = tmp_path / "test.md"
       ticket = SAMPLE_TICKETS[0]
       
       # Simulate write failure
       def fail_write(*args, **kwargs):
           raise OSError("Disk full")
       
       monkeypatch.setattr("os.write", fail_write)
       
       with pytest.raises(OSError):
           write_ticket(ticket_path, ticket)
       
       # Verify no temp files left behind
       assert list(tmp_path.glob("*.tmp")) == []
       assert not ticket_path.exists()
   ```

2. **Add ranking verification to BM25 tests**
   ```python
   def test_search_ranking_order(self, collection):
       """Verify BM25 ranks more relevant documents higher."""
       insert_tickets(collection, SAMPLE_TICKETS)
       results = query_tickets(collection, "SQL injection security", limit=5)
       
       # S1 (SQL Injection in title AND description) should rank higher than S2
       s1_idx = next(i for i, r in enumerate(results) if r["id"] == "S1")
       s2_idx = next((i for i, r in enumerate(results) if r["id"] == "S2"), None)
       
       if s2_idx is not None:
           assert s1_idx < s2_idx, "S1 should rank higher than S2"
   ```

3. **Add edge case tests for YAML-special characters**
   - Test ticket with title containing `:`, `#`, `"`, `'` characters
   - Verify roundtrip preserves these correctly

4. **Expand pagination test to verify offset behavior**
   - Current `test_offset_pagination` only checks that pages are different
   - Should verify specific ticket IDs appear at expected offsets

5. **Add test for combined filter + search query**
   - Current filter tests use generic search terms
   - Should test that filters actually restrict results (e.g., search for "api" with repo filter excludes tickets from other repos that also mention "api")

---

## Coverage Analysis

| Module | Public Functions | Tested | Missing |
|--------|-----------------|--------|---------|
| `paths.py` | `ticket_file_path`, `resolve_path`, `trash_path`, `ensure_dirs` | 4/4 | None |
| `markdown.py` | `ticket_to_markdown`, `markdown_to_ticket`, `write_ticket`, `read_ticket`, `delete_ticket`, `list_tickets`, `scan_all_tickets` | 7/7 | None |
| `schema.py` | `define_ticket_schema` | 1/1 | None |
| `client.py` | `create_index`, `open_index`, `close_index`, `get_collection`, `destroy_index` | 5/5 | None |
| `operations.py` | `insert_tickets`, `upsert_ticket`, `delete_ticket`, `fetch_ticket`, `query_tickets`, `rebuild_index`, `_ticket_to_doc`, `_doc_to_ticket` | 7/8 | `rebuild_index` (placeholder implementation) |

**Notes:**
- `rebuild_index` in `operations.py` has a placeholder implementation (`_load_tickets_from_directory` returns empty list) so it's not meaningfully testable
- All other public functions have direct test coverage

---

## BM25 Search Verification

| Query | Expected Result | Test Covers? |
|-------|----------------|--------------|
| "SQL injection" | Returns S1 (SQL Injection in Login) | ✅ `test_search_sql_injection` |
| "memory leak worker" | Returns H1 (Memory Leak in Worker) | ✅ `test_search_memory` |
| "CORS wildcard" | Returns S2 (CORS Wildcard Origin) | ✅ `test_search_cors` |
| "crash" | Returns C1, C2 (crash category) | ✅ Implicitly in various tests |
| "api" | Returns tickets from ejacklab/api repo | ⚠️ Returns results, but repo filter tested separately |
| Empty query "" | Returns empty list | ✅ `test_search_empty_query` |
| Whitespace query "   " | Returns empty list | ✅ `test_search_whitespace_query` |
| Relevance scoring | Results include score field | ✅ `test_search_returns_scores` |
| Ranking order | Higher relevance first | ❌ Not verified |

---

## Detailed Checklist Verification

| # | Check | Status | Notes |
|---|-------|--------|-------|
| 1 | Store coverage - all public functions | ✅ PASS | All 4 paths + 7 markdown functions tested |
| 2 | Atomic writes - no partial files | ⚠️ PARTIAL | Tests success case; failure cleanup assumed by code inspection |
| 3 | Roundtrip preserves ALL fields | ✅ PASS | `test_roundtrip_preserves_all_fields` tests all SAMPLE_TICKETS |
| 4 | Soft/hard delete both tested | ✅ PASS | `test_soft_delete_moves_to_trash`, `test_hard_delete_removes_file` |
| 5 | List/scan filters work | ✅ PASS | Repo, category, combined filters tested; empty results handled |
| 6 | Path generation format | ✅ PASS | `{repo}/{category}/{id}-{slug}.md` verified in `test_basic_path_generation` |
| 7 | Zvec schema - scalar fields + BM25 | ✅ PASS | `test_schema_creation` checks all fields |
| 8 | BM25 search - actual keyword matching | ✅ PASS | Specific keyword queries tested (SQL, memory, CORS) |
| 9 | Filters (category, severity, repo, combined) | ✅ PASS | All filter types tested in `TestFilterQueries` |
| 10 | Pagination offset/limit | ⚠️ PARTIAL | Offset tested but not with predictable ordering |
| 11 | Delete from index - query after delete | ✅ PASS | `test_query_after_delete` verifies S1 not returned after deletion |
| 12 | Edge cases - empty strings, None, special chars | ⚠️ PARTIAL | None values tested; empty strings and special chars not fully covered |
| 13 | Cleanup - temp files/indexes | ✅ PASS | pytest tmp_path fixture handles cleanup; `test_atomic_write_no_partial_files` verifies no temp files |
| 14 | Test isolation | ✅ PASS | Each test uses fresh tmp_path and collection fixtures |

---

## Test Quality Assessment

### Strengths
1. **Comprehensive roundtrip testing** - Parametrized test covers all sample tickets
2. **Good use of pytest fixtures** - Clean setup/teardown with tmp_path and collection fixtures
3. **Integration test coverage** - `TestIntegration` verifies full CRUD workflow
4. **Error cases covered** - Invalid frontmatter, missing files, invalid delete modes all tested
5. **Unicode support verified** - `test_roundtrip_with_unicode` tests non-ASCII characters
6. **Trash directory exclusion** - `test_scan_skips_trash_directory` verifies .trash is ignored

### Areas for Improvement
1. **Missing negative test for atomic write failure** - Only success path tested
2. **No ranking verification** - BM25 tests check inclusion but not relevance ordering
3. **Missing edge case tests** - Special YAML characters, empty strings, very long titles
4. **No concurrent access tests** - Atomic writes imply thread-safety but not tested
5. **Date field verification** - Roundtrip tests compare string dates, not datetime objects

---

## Conclusion

The test suite is **production-ready** with good coverage of core functionality. The warnings identified are minor and don't block deployment, but addressing them would improve confidence in edge case handling. The most important gap is the lack of explicit atomic write failure testing, though the source code does implement proper exception handling.

**Recommendation:** Address warnings 1-3 before declaring the module fully robust, but the current test suite is sufficient for initial release.
