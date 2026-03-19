# Review: test_search_models.py

## Test Results
- **Tests Run:** 58
- **Passed:** 58
- **Failed:** 0
- **Duration:** 0.07s

## Previous Findings Status

| Finding | Fixed? | Evidence |
|---------|--------|----------|
| Missing test for SearchHit score > 1.0 | ❌ No | `test_score_range_0_to_1` (lines 304-314) tests valid: 0.0, 0.5, 1.0 and invalid: -0.1. Does NOT test 1.1 (above upper bound). |
| FilterSet.is_empty() missing updated_before check | ❌ No | Source code (search.py lines 159-170) still missing `self.updated_before is None` in `is_empty()` check. Test doesn't verify this edge case. |

## New Issues

### Critical

1. **SuggestResult model deviates from spec**
   - **Test implementation**: `query: str`, `suggestions: list[str]`
   - **Spec (data-models-stage3-search.md)**: `suggestion: str`, `ticket_count: int`
   - The spec defines individual suggestions with counts: `[{"suggestion": "CORS wildcard issue", "ticket_count": 3}]`
   - Test model uses: `{"query": "cor", "suggestions": ["CORS wildcard issue", ...]}`
   - **Impact**: API contract mismatch - backend and frontend will disagree on response format
   - **Location**: test_search_models.py lines 490-515, search.py lines 517-540

### Warnings

1. **SearchQuery min_score upper bound not tested**
   - `test_min_score_range_0_to_1` tests valid: 0.0, 0.5, 1.0 and invalid: -0.1
   - Does NOT test that 1.1 is rejected
   - Same issue as SearchHit score upper bound
   - **Location**: test_search_models.py lines 115-126

2. **FilterSet.is_empty() source bug - no test coverage**
   - Source code missing `self.updated_before is None` in the `is_empty()` check
   - If only `updated_before` filter is set, `is_empty()` incorrectly returns `True`
   - Test `test_empty_filters` only tests completely empty FilterSet
   - Should add test: `FilterSet(updated_before=datetime(...)).is_empty()` returns `False`
   - **Location**: search.py lines 159-170

3. **FilterSet.to_zvec_filter() incomplete test coverage**
   - Tests cover: empty, severity, status, repo, tags, combined
   - **Missing tests for**:
     - `assignee` filter formatting
     - `category` filter formatting
     - `created_after`/`created_before` date formatting
     - `updated_after`/`updated_before` date formatting
   - Tests verify string containment (`"severity:critical" in expr`) but not exact format
   - **Location**: test_search_models.py lines 265-304

4. **SearchMeta.latency_ms type mismatch with spec (noted previously)**
   - Implementation: `Optional[float]`
   - Spec: `latency_ms: type: integer`
   - Already noted in review-fix-2.md but not fixed
   - **Location**: search.py line 393

### Suggestions

1. **Add explicit upper bound tests for score fields**
   ```python
   def test_score_above_1_rejected(self):
       """Score above 1.0 should be rejected."""
       with pytest.raises(ValidationError):
           SearchHit(ticket_id="C1", score=1.1, source="bm25")
   
   def test_min_score_above_1_rejected(self):
       """min_score above 1.0 should be rejected."""
       with pytest.raises(ValidationError):
           SearchQuery(query="test", min_score=1.1)
   ```

2. **Add test for is_empty() with individual filters**
   - Test each filter type individually to ensure `is_empty()` works correctly
   - Particularly important for `updated_before` which is missing from source

3. **Add test for to_zvec_filter() exact format**
   - Verify the AND/OR combination logic is correct
   - Verify date ISO format in filter strings

4. **Add tests for SearchMeta field validation**
   - Test that `total` must be >= 0
   - Test that `limit` must be >= 1
   - Test that `offset` must be >= 0

## Coverage Analysis

| Model | Fields/Methods | Tested | Missing |
|-------|----------------|--------|---------|
| **SearchQuery** | query, semantic, filters, limit, offset, sort, min_score, get_sort_field(), is_descending(), is_semantic_enabled() | All fields tested, all methods tested | min_score upper bound |
| **FilterSet** | severity, status, category, repo, tags, assignee, created_after, created_before, updated_after, updated_before, is_empty(), to_zvec_filter() | severity, status, repo, tags, assignee, created_*, is_empty() (partial), to_zvec_filter() (partial) | category in to_zvec_filter(), updated_* in to_zvec_filter(), is_empty() with updated_before |
| **SearchHit** | ticket_id, score, source, bm25_score, semantic_score, highlight, is_hybrid_match(), is_high_confidence() | All fields tested, all methods tested | score upper bound (1.1) |
| **SearchMeta** | total, limit, offset, has_more, bm25_weight, semantic_weight, latency_ms, semantic_used, request_id | All fields tested | Field constraint validation (ge=0 for total, ge=1 for limit) |
| **SearchResult** | query, hits, total, meta, has_results(), get_hybrid_matches(), get_high_confidence_results() | All fields tested, all methods tested | None |
| **SuggestResult** | query, suggestions | Both fields tested | **SPEC MISMATCH**: should be `suggestion` + `ticket_count` |

## Spec Compliance Issues

| Field | OpenAPI Spec | Implementation | Test Coverage | Issue |
|-------|--------------|----------------|---------------|-------|
| SearchHit.score | minimum: 0, maximum: 1 (implied) | ge=0.0, le=1.0 | Lower bound tested | Upper bound NOT tested |
| SearchQuery.min_score | min: 0, max: 1 | ge=0.0, le=1.0 | Lower bound tested | Upper bound NOT tested |
| SearchMeta.latency_ms | type: integer | float | Uses float in test | Type mismatch |
| FilterSet.is_empty() | Should check all fields | Missing updated_before | Not tested | Bug in source |
| SuggestResult | `{suggestion, ticket_count}` | `{query, suggestions[]}` | Tests current model | **Major spec deviation** |

## Verdict: **WARN**

### Summary
- All 58 tests pass
- Good test organization and coverage for happy paths
- **Critical issue**: SuggestResult model does not match spec at all (different structure)
- **Source bugs**: FilterSet.is_empty() missing updated_before check
- **Test gaps**: No upper bound tests for score/min_score fields
- **Incomplete coverage**: FilterSet.to_zvec_filter() missing several filter types

### Recommendations
1. **Fix SuggestResult** to match spec (suggestion + ticket_count) or update spec
2. **Fix FilterSet.is_empty()** to include updated_before check
3. **Add upper bound tests** for SearchHit.score and SearchQuery.min_score
4. **Add to_zvec_filter() tests** for category, assignee, and date filters
5. **Align SearchMeta.latency_ms** to int per spec
