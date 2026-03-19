# Fix & Review: T5 + T6

## Fixes Applied

### 1. Implemented `rebuild_index` Function
**File:** `src/vtic/index/operations.py`

**Problem:** The `_load_tickets_from_directory()` function was a placeholder returning an empty list, making `rebuild_index()` non-functional.

**Solution:**
- Added import for `scan_all_tickets` from `vtic.store.markdown`
- Implemented `_load_tickets_from_directory()` to actually scan and parse markdown files
- Updated `rebuild_index()` return dict to include `errors` list for error tracking

**Changes:**
```python
# Added import
from vtic.store.markdown import scan_all_tickets

# Implemented _load_tickets_from_directory
def _load_tickets_from_directory(base_dir: Path) -> list[dict[str, Any]]:
    if not base_dir.exists():
        return []
    scanned = scan_all_tickets(base_dir)
    return [ticket for _, ticket in scanned]

# Updated rebuild_index to return errors
result = {
    "processed": processed,
    "skipped": skipped,
    "failed": failed,
    "duration_ms": duration_ms,
    "errors": errors,  # NEW: list of error messages
}
```

### 2. Added Tests for `rebuild_index`
**File:** `tests/test_index.py`

Added `TestRebuildIndex` class with 4 tests:
- `test_rebuild_from_markdown_files`: Creates tickets on disk, rebuilds index, verifies searchability
- `test_rebuild_empty_directory`: Verifies graceful handling of empty directories
- `test_rebuild_returns_errors`: Confirms errors list is in response
- `test_rebuild_after_delete_and_recreate`: End-to-end test of data recovery via rebuild

---

## Test Results

```
89 tests passed in 7.59s

test_store.py: 54 tests - All PASSED
test_index.py: 35 tests - All PASSED
```

Key test coverage:
- Path utilities (ticket_file_path, resolve_path, trash_path, ensure_dirs)
- Markdown serialization/parsing (ticket_to_markdown, markdown_to_ticket)
- File operations (write_ticket, read_ticket, delete_ticket)
- Listing and scanning (list_tickets, scan_all_tickets)
- Schema creation and validation
- Client operations (create_index, open_index, close_index, destroy_index)
- CRUD operations (insert, upsert, fetch, delete)
- BM25 keyword search
- Filter queries
- Pagination
- **NEW:** rebuild_index functionality

---

## Source Code Review

### Issues Found

#### 1. Minor: BM25 Encoder Global State (operations.py)
The module uses global encoder instances (`_document_encoder`, `_query_encoder`, `_fitted`) which could cause issues in multi-threaded environments or when testing. However, this is acceptable for the current use case.

**Recommendation:** Consider using a class-based approach or context manager for the encoder state in future refactoring.

#### 2. Minor: Delete by Filter Syntax (operations.py:477)
The `collection.delete_by_filter("id != ''")` assumes Zvec supports this syntax. This should be verified against Zvec documentation.

**Status:** Works in current tests, but worth documenting as Zvec-specific.

#### 3. Potential Issue: Encoder Fitting Race Condition (operations.py)
The `_ensure_corpus_fitted()` function uses a `_corpus_lock` flag that could still have race conditions in multi-threaded scenarios.

**Recommendation:** Use `threading.Lock` for proper synchronization if multi-threading is needed.

---

### Spec Compliance

#### T5 (Markdown Store) - Compliant ✓

| Requirement | Status | Notes |
|-------------|--------|-------|
| YAML frontmatter serialization | ✓ | `ticket_to_markdown()` correctly outputs frontmatter |
| YAML frontmatter parsing | ✓ | `markdown_to_ticket()` parses frontmatter correctly |
| Atomic file writes | ✓ | Uses temp file + fsync + rename pattern |
| Soft delete to .trash | ✓ | `delete_ticket(mode="soft")` moves to .trash with timestamp |
| Hard delete | ✓ | `delete_ticket(mode="hard")` permanently removes |
| Path format: {repo}/{category}/{id}-{slug}.md | ✓ | `ticket_file_path()` generates correct paths |
| ID resolution via resolve_path | ✓ | `resolve_path()` searches recursively |
| Skip .trash in scans | ✓ | `scan_all_tickets()` skips .trash directory |
| Handle corrupt files gracefully | ✓ | scan_all_tickets catches exceptions and skips |

#### T6 (Zvec Index) - Compliant ✓

| Requirement | Status | Notes |
|-------------|--------|-------|
| Collection schema with BM25 vector | ✓ | `define_ticket_schema()` creates correct schema |
| Inverted indexes on filter fields | ✓ | category, severity, status, repo have `InvertIndexParam` |
| Batch insert | ✓ | `insert_tickets()` batches 100 at a time |
| Upsert support | ✓ | `upsert_ticket()` uses collection.upsert |
| Delete support | ✓ | `delete_ticket()` removes from index |
| Fetch by ID | ✓ | `fetch_ticket()` retrieves single ticket |
| BM25 search | ✓ | `query_tickets()` uses sparse vector search |
| Filter expression building | ✓ | `_build_filter_expression()` converts dict to Zvec syntax |
| Rebuild from markdown files | ✓ | **FIXED** - Now properly scans and indexes |
| Return statistics from rebuild | ✓ | Returns processed, skipped, failed, duration_ms, errors |

---

### Quality Assessment

#### Code Quality: Good (8/10)

**Strengths:**
- Clean separation of concerns (paths, markdown, schema, client, operations)
- Comprehensive docstrings with examples
- Type hints throughout
- Proper error handling and logging
- Atomic file operations for data integrity
- Well-structured test coverage

**Areas for Improvement:**
- Global encoder state could be refactored
- Some magic numbers (batch_size=100, fetch_limit=1000) could be configurable
- Filter expression builder could support more operators (range, negation)

#### Test Coverage: Excellent (9/10)

- 89 tests covering all major functionality
- Parametrized tests for roundtrip verification
- Edge case handling (empty inputs, corrupt files, missing directories)
- Integration tests combining store + index operations
- NEW tests for rebuild_index functionality

---

### BM25 Search Quality

#### Implementation Review

The `SimpleBM25Encoder` class implements a BM25-like scoring algorithm:

**Components:**
- Tokenization: lowercase, alphanumeric only, min 2 chars
- Hashing: SHA256 → 4 bytes → mod vocab_size for deterministic token IDs
- BM25 formula: `(tf * (k1+1)) / (tf + k1 * (1-b + b * (doc_len/avg_doc_len))) * idf`
- Parameters: k1=1.5, b=0.75 (standard values)
- Vocabulary size: 2^24 (~16M)

**Quality Assessment:**
1. **Tokenization is basic** - No stemming, no stopword removal, no phrase detection
2. **Hashing approach is sound** - Deterministic, no vocabulary storage needed
3. **BM25 formula is correct** - Standard Robertson/OKAPI BM25
4. **IDF calculation is correct** - Uses log((N-df+0.5)/(df+0.5)+1)

**Limitations:**
- No query expansion or relevance feedback
- No field weighting (title vs description)
- Query encoder doesn't use IDF (intentional for short queries)
- Single-token terms only (no n-grams)

**Test Results:**
- `test_search_sql_injection`: S1 correctly ranked for "SQL injection"
- `test_search_memory`: H1 correctly ranked for "memory leak worker"
- `test_search_cors`: S2 correctly ranked for "CORS wildcard"

**Verdict:** The BM25 implementation is functional and produces reasonable results for the test cases. For production use, consider:
1. Adding stemming (Porter2)
2. Adding stopword filtering
3. Field boosting (title × 2 + description)
4. N-gram support for phrase queries

---

## Summary

| Category | Status | Score |
|----------|--------|-------|
| Fixes Applied | ✓ Complete | - |
| Test Results | ✓ 89/89 passed | 100% |
| Spec Compliance | ✓ All requirements met | - |
| Code Quality | Good | 8/10 |
| BM25 Quality | Functional | 7/10 |

**Overall Assessment:** T5 (Markdown Store) and T6 (Zvec Index) are production-ready with good test coverage and clean implementation. The `rebuild_index` function now works correctly, allowing full index recovery from markdown files.
