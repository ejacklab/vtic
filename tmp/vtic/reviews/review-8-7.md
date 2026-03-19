# Review: test_index.py

## Previous Findings Status

| Finding | Fixed? | Evidence |
|---------|--------|----------|
| `rebuild_index` placeholder implementation | ✅ YES | `operations.py:429-482` - Now uses `scan_all_tickets()` from markdown store, properly clears index with `delete_by_filter()`, batches inserts, returns `errors` list |
| BM25 ranking order not verified | ❌ NO | Tests still use `assert "S1" in ids` pattern (inclusion check) rather than `assert results[0]["id"] == "S1"` (ranking check) |

---

## New Issues

### Critical

None

### Warnings

#### 1. BM25 Ranking Not Verified (Still Open)
**File:** `test_index.py` lines 254-277

Tests verify that search results **contain** expected tickets, but do not verify that more relevant documents rank higher. This was flagged in the previous review and remains unaddressed.

**Example:**
```python
def test_search_sql_injection(self, collection):
    results = query_tickets(collection, "SQL injection", limit=10)
    assert len(results) > 0
    ids = [r["id"] for r in results]
    assert "S1" in ids  # ❌ Only checks inclusion, not ranking
```

**Should be:**
```python
def test_search_sql_injection_ranking(self, collection):
    results = query_tickets(collection, "SQL injection", limit=10)
    # S1 has "SQL Injection" in title AND "SQL injection" in description
    # Should rank higher than any other ticket
    assert results[0]["id"] == "S1", f"Expected S1 first, got {results[0]['id']}"
```

#### 2. Tags Filter Not Implemented
**Files:** `operations.py:193-226`, spec `data-models-stage3-search.md`

The spec defines `FilterSet.tags: Optional[list[str]]` but `_build_filter_expression()` only handles:
- `severity`, `status`, `category`, `repo` (multi-value)
- `assignee` (single-value)

**Missing:** Tags filter support. The schema stores tags as comma-separated string, which would require `LIKE` or string matching, not currently supported.

**Impact:** Tests don't cover tags filtering because it's not implemented. Spec compliance gap.

#### 3. Filter Expression Syntax Not Verified Against Zvec API
**File:** `operations.py:193-226`

The filter builder uses:
- Single `=` for equality: `field = 'value'`
- `IN (v1, v2)` for membership

These syntax assumptions should be verified against actual Zvec documentation. Tests pass, but only because Zvec accepts them, not because the test suite verifies correct syntax.

### Suggestions

#### 1. Add Score Threshold Verification
Tests verify scores exist (`assert "score" in r`), but don't verify:
- Score range (should be 0.0-1.0 per spec, but raw BM25 scores can be higher)
- Score ordering (results should be sorted descending by score)

```python
def test_search_scores_sorted_descending(self, collection):
    results = query_tickets(collection, "security", limit=10)
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True), "Results should be sorted by score descending"
```

#### 2. Verify Pagination Correctness More Thoroughly
Current `test_offset_pagination` only verifies pages don't overlap. Should verify:
- Total count behavior
- Consistent ordering between paginated requests

#### 3. Test Delete by Filter in rebuild_index
The `rebuild_index` function uses `collection.delete_by_filter("id != ''")` but this is not directly tested. Add a test that verifies the index is cleared before rebuild:

```python
def test_rebuild_clears_existing_data(self, temp_dir):
    # Insert directly, then rebuild with different data
    # Verify old data is gone
```

---

## Coverage Analysis

| Function | Tested | Edge Cases Missing |
|----------|--------|-------------------|
| `define_ticket_schema` | ✅ | None |
| `create_index` | ✅ | None |
| `open_index` | ✅ | None |
| `close_index` | ✅ | None |
| `get_collection` | ✅ | None |
| `destroy_index` | ✅ | None |
| `insert_tickets` | ✅ | Large batch (>100) not tested |
| `upsert_ticket` | ✅ | None |
| `delete_ticket` | ✅ | None |
| `fetch_ticket` | ✅ | None |
| `query_tickets` | ✅ | Ranking order, score bounds |
| `rebuild_index` | ✅ | Clear existing data verification |
| `_build_filter_expression` | ⚠️ | Tags not tested (not implemented) |
| `SimpleBM25Encoder` | ⚠️ | Encoding quality only tested via search |

---

## BM25 Search Quality

| Query | Expected | Test Verifies Ranking? |
|-------|----------|----------------------|
| "SQL injection" | S1 should be top result | ❌ Only checks S1 is **in** results |
| "memory leak worker" | H1 should be top result | ❌ Only checks H1 is **in** results |
| "CORS wildcard" | S2 should be top result | ❌ Only checks S2 is **in** results |
| "crash" | C1, C2 should rank high | ❌ No test for this query |
| Empty query "" | Empty results | ✅ Correct |
| Whitespace "   " | Empty results | ✅ Correct |
| Limit enforcement | <= N results | ✅ Correct |
| Score presence | All results have score | ✅ Correct |

**Assessment:** Tests verify **recall** (correct results are found) but not **precision ordering** (correct ranking).

---

## Zvec API Correctness

| Operation | Test Coverage | Notes |
|-----------|---------------|-------|
| `zvec.create_and_open(path, schema)` | ✅ `test_create_index` | Correct usage |
| `zvec.open(path)` | ✅ `test_open_index` | Correct usage |
| `collection.insert(docs)` | ✅ `test_insert_tickets_batch` | Batch insert works |
| `collection.upsert(doc)` | ✅ `test_upsert_ticket_*` | Single upsert works |
| `collection.delete(id)` | ✅ `test_delete_ticket_*` | Single delete works |
| `collection.delete_by_filter(expr)` | ⚠️ Indirect via rebuild | Used in rebuild_index, not directly tested |
| `collection.fetch(id)` | ✅ `test_fetch_ticket_*` | Returns dict keyed by ID |
| `collection.query(vectors, topk, filter, output_fields)` | ✅ Search tests | BM25 sparse vector search works |

**Filter Syntax:**
```python
# Single equality
"field = 'value'"

# Membership
"field IN ('v1', 'v2')"

# Combined
"field1 = 'v1' AND field2 IN ('v2', 'v3')"
```

This syntax is assumed to match Zvec API. Tests pass, confirming it works.

---

## Schema Fields vs Spec

| Spec Field | Schema Field | Status |
|------------|--------------|--------|
| id | id (STRING) | ✅ |
| title | title (STRING) | ✅ |
| description | description (STRING) | ✅ |
| repo | repo (STRING, indexed) | ✅ |
| category | category (STRING, indexed) | ✅ |
| severity | severity (STRING, indexed) | ✅ |
| status | status (STRING, indexed) | ✅ |
| assignee | assignee (STRING, nullable) | ✅ |
| tags | tags (STRING, comma-joined) | ✅ |
| references | references (STRING, comma-joined) | ✅ |
| created | created (STRING) | ✅ |
| updated | updated (STRING) | ✅ |
| BM25 sparse vector | bm25_sparse (SPARSE_VECTOR_FP32) | ✅ |

**Spec Compliance:** Schema matches Stage 1 & 3 data models. All required fields present.

---

## Test Results

```
36 tests passed in 8.88s

TestSchema: 2 tests
TestClient: 8 tests
TestInsertOperations: 5 tests
TestDeleteOperations: 2 tests
TestBM25Search: 7 tests
TestFilterQueries: 5 tests
TestQueryAfterDelete: 1 test
TestPagination: 1 test
TestRebuildIndex: 4 tests
```

---

## Verdict: **WARN**

### Summary
- **Tests Pass:** ✅ 36/36
- **Previous Findings:** 1/2 addressed (rebuild_index ✅, ranking order ❌)
- **Spec Compliance:** Partial (tags filter not implemented)
- **Code Quality:** Good, well-structured tests

### Blockers for PASS
1. **BM25 ranking verification still missing** - Previous review flagged this, still not addressed
2. **Tags filter not implemented** - Spec defines it, code doesn't support it

### Recommendations
1. Add explicit ranking tests that assert `results[0]["id"] == expected_top_result`
2. Either implement tags filtering or document it as not supported
3. Add score ordering verification test
4. Consider testing `delete_by_filter` directly (not just via rebuild)

### What's Working Well
- rebuild_index now properly implemented with full test coverage
- Delete from index verified via `test_query_after_delete`
- Pagination offset works (though ordering could be more robust)
- Filter expressions work for implemented fields
- Schema matches spec exactly
- All Zvec API calls use correct syntax
