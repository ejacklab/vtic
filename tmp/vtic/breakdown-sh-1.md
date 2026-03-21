# Should Have Features (P1) - 6-Level Breakdown

35 Should Have features broken down to implementation-ready specifications.

---

## Feature 1: Custom ID Specification

### L1: Ticket Lifecycle
### L2: Create
### L3: Custom ID specification
### L4: `create_ticket_with_custom_id(custom_id: str, args: CreateArgs, store: TicketStore) -> Ticket`
  - Validate custom ID format (alphanumeric with optional hyphens/underscores)
  - Check custom ID doesn't already exist in store
  - Bypass auto-generation when custom ID provided
  - Apply same validation rules as auto-generated IDs
  - Log warning if custom ID doesn't match category prefix convention
  - Persist ticket with custom ID

### L5: Spec
```python
def create_ticket_with_custom_id(custom_id: str, args: CreateArgs, store: TicketStore) -> Ticket:
    """
    Input: custom_id="MIGRATE-001", CreateArgs(title="Legacy Bug", repo="owner/repo")
    Output: Ticket(id="MIGRATE-001", title="Legacy Bug", ...)
    
    Input: custom_id="C1", CreateArgs(...), store with C1 already exists
    Error: DuplicateIDError(f"Ticket ID 'C1' already exists")
    
    Input: custom_id="invalid id!", CreateArgs(...)
    Error: InvalidIDError("ID must be alphanumeric with optional hyphens/underscores")
    
    Input: custom_id="", CreateArgs(...)
    Error: InvalidIDError("Custom ID cannot be empty")
    """
```

### L6: Test
```python
test_create_ticket_with_custom_id_valid()
test_create_ticket_with_custom_id_duplicate_raises()
test_create_ticket_with_custom_id_invalid_format_raises()
test_create_ticket_with_custom_id_empty_raises()
test_create_ticket_with_custom_id_preserves_category_mismatch_warning()
test_create_ticket_with_custom_id_special_chars_allowed()
```

---

## Feature 2: Field Selection

### L1: Ticket Lifecycle
### L2: Read
### L3: Field selection
### L4: `select_ticket_fields(ticket: Ticket, fields: List[str]) -> Dict[str, Any]`
  - Accept list of field names to include in output
  - Support dot notation for nested fields (future-proofing)
  - Return dictionary with only requested fields
  - Ignore invalid field names silently (or warn with --strict)
  - Preserve field order from input list

### L5: Spec
```python
def select_ticket_fields(ticket: Ticket, fields: List[str]) -> Dict[str, Any]:
    """
    Input: Ticket(id="C1", title="Bug", severity="critical", ...), 
           fields=["id", "title", "severity"]
    Output: {"id": "C1", "title": "Bug", "severity": "critical"}
    
    Input: Ticket(...), fields=["id", "nonexistent"]
    Output: {"id": "C1"}  # nonexistent field ignored
    
    Input: Ticket(...), fields=[]
    Output: {}  # empty selection returns empty dict
    """
```

### L6: Test
```python
test_select_ticket_fields_single_field()
test_select_ticket_fields_multiple_fields()
test_select_ticket_fields_preserves_order()
test_select_ticket_fields_invalid_field_ignored()
test_select_ticket_fields_empty_list_returns_empty()
test_select_ticket_fields_all_fields()
```

---

## Feature 3: Raw File Output

### L1: Ticket Lifecycle
### L2: Read
### L3: Raw file output
### L4: `get_ticket_raw_content(ticket_id: str, store: TicketStore) -> Optional[str]`
  - Read raw markdown file content directly from disk
  - Include YAML frontmatter and body unchanged
  - Return None if ticket file doesn't exist
  - Do not parse or modify content

### L5: Spec
```python
def get_ticket_raw_content(ticket_id: str, store: TicketStore) -> Optional[str]:
    """
    Input: ticket_id="C1", store with C1.md containing:
           ---
           id: C1
           title: Bug Report
           ---
           # Description
           Bug details here
    Output: "---\\nid: C1\\ntitle: Bug Report\\n---\\n# Description\\nBug details here"
    
    Input: ticket_id="NONEXISTENT", store
    Output: None
    
    Input: ticket_id="", store
    Output: None
    """
```

### L6: Test
```python
test_get_ticket_raw_content_returns_full_file()
test_get_ticket_raw_content_not_found_returns_none()
test_get_ticket_raw_content_includes_frontmatter()
test_get_ticket_raw_content_includes_body()
test_get_ticket_raw_content_preserves_formatting()
```

---

## Feature 4: Append to Description

### L1: Ticket Lifecycle
### L2: Update
### L3: Append to description
### L4: `append_to_description(ticket_id: str, text: str, store: TicketStore) -> Ticket`
  - Fetch existing ticket
  - Append text to description with newline separator
  - Handle None description (treat as empty string)
  - Update `updated` timestamp
  - Persist and return updated ticket

### L5: Spec
```python
def append_to_description(ticket_id: str, text: str, store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", text="Update: Fixed in PR #42", 
           ticket has description="Original bug report"
    Output: Ticket(description="Original bug report\\n\\nUpdate: Fixed in PR #42", 
                   updated="2026-03-17T12:00:00Z", ...)
    
    Input: ticket_id="C1", text="First update", ticket has description=None
    Output: Ticket(description="First update", ...)
    
    Input: ticket_id="NONEXISTENT", text="..."
    Error: TicketNotFoundError(f"Ticket {ticket_id} not found")
    
    Input: ticket_id="C1", text=""
    Output: Ticket unchanged except updated timestamp
    """
```

### L6: Test
```python
test_append_to_description_adds_text()
test_append_to_description_handles_none_description()
test_append_to_description_empty_text_only_updates_timestamp()
test_append_to_description_ticket_not_found_raises()
test_append_to_description_updates_timestamp()
test_append_to_description_adds_separator()
```

---

## Feature 5: Field Clearing

### L1: Ticket Lifecycle
### L2: Update
### L3: Field clearing
### L4: `clear_ticket_fields(ticket_id: str, fields: List[str], store: TicketStore) -> Ticket`
  - Set specified optional fields to None or empty
  - Validate fields are clearable (not required fields like id, title, repo)
  - Update `updated` timestamp
  - Persist and return updated ticket

### L5: Spec
```python
CLEARABLE_FIELDS = ["description", "tags", "file_refs", "fix", "severity", "category"]

def clear_ticket_fields(ticket_id: str, fields: List[str], store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", fields=["description", "tags"]
    Output: Ticket(description=None, tags=[], ...)
    
    Input: ticket_id="C1", fields=["title"]
    Error: UnclearableFieldError("Cannot clear required field: title")
    
    Input: ticket_id="C1", fields=["nonexistent"]
    Output: Ticket unchanged (invalid field names ignored with warning)
    
    Input: ticket_id="NONEXISTENT", fields=["description"]
    Error: TicketNotFoundError(f"Ticket {ticket_id} not found")
    """
```

### L6: Test
```python
test_clear_ticket_fields_single_field()
test_clear_ticket_fields_multiple_fields()
test_clear_ticket_fields_required_field_raises()
test_clear_ticket_fields_invalid_field_ignored()
test_clear_ticket_fields_updates_timestamp()
test_clear_ticket_fields_ticket_not_found_raises()
```

---

## Feature 6: Bulk Update

### L1: Ticket Lifecycle
### L2: Update
### L3: Bulk update
### L4: `bulk_update_tickets(filter: TicketFilter, updates: Dict[str, Any], store: TicketStore) -> BulkResult`
  - Find all tickets matching filter criteria
  - Apply same updates to all matching tickets
  - Track successes and failures separately
  - Update `updated` timestamp for each modified ticket
  - Return summary with count of updated/failed

### L5: Spec
```python
@dataclass
class TicketFilter:
    status: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    repo: Optional[str] = None

@dataclass
class BulkResult:
    updated: int
    failed: int
    errors: List[Tuple[str, str]]  # (ticket_id, error_message)

def bulk_update_tickets(filter: TicketFilter, updates: Dict[str, Any], store: TicketStore) -> BulkResult:
    """
    Input: filter=TicketFilter(status="open"), updates={"status": "reviewing"}
    Output: BulkResult(updated=5, failed=0, errors=[])
    
    Input: filter=TicketFilter(severity="critical"), updates={"severity": "high"}
    Output: BulkResult(updated=3, failed=1, errors=[("C99", "Ticket locked")])
    
    Input: filter=TicketFilter(repo="nonexistent"), updates={...}
    Output: BulkResult(updated=0, failed=0, errors=[])
    """
```

### L6: Test
```python
test_bulk_update_tickets_by_status()
test_bulk_update_tickets_by_severity()
test_bulk_update_tickets_no_matches()
test_bulk_update_tickets_partial_failure()
test_bulk_update_tickets_updates_timestamps()
test_bulk_update_tickets_validates_updates()
```

---

## Feature 7: Cascade Delete

### L1: Ticket Lifecycle
### L2: Delete
### L3: Cascade delete
### L4: `cascade_delete_tickets(scope: DeleteScope, store: TicketStore, force: bool = False) -> BulkResult`
  - Delete all tickets matching scope (category, repo, or all)
  - Require explicit --all flag for safety
  - Apply soft delete by default, hard delete with --force
  - Return count of deleted tickets
  - Remove from index for each deleted ticket

### L5: Spec
```python
@dataclass
class DeleteScope:
    category: Optional[str] = None
    repo: Optional[str] = None
    all: bool = False

def cascade_delete_tickets(scope: DeleteScope, store: TicketStore, force: bool = False) -> BulkResult:
    """
    Input: scope=DeleteScope(category="maintenance"), force=False
    Action: Soft delete all tickets in maintenance category
    Output: BulkResult(updated=12, failed=0, errors=[])
    
    Input: scope=DeleteScope(repo="owner/old-repo"), force=True
    Action: Hard delete all tickets in owner/old-repo
    Output: BulkResult(updated=8, failed=0, errors=[])
    
    Input: scope=DeleteScope(all=True), force=False
    Error: CascadeDeleteError("Must specify --force with --all")
    
    Input: scope=DeleteScope()  # no criteria
    Error: CascadeDeleteError("Must specify category, repo, or --all")
    """
```

### L6: Test
```python
test_cascade_delete_by_category_soft()
test_cascade_delete_by_repo_hard()
test_cascade_delete_all_requires_force()
test_cascade_delete_no_criteria_raises()
test_cascade_delete_removes_from_index()
test_cascade_delete_empty_category_returns_zero()
```

---

## Feature 8: Restore Deleted

### L1: Ticket Lifecycle
### L2: Delete
### L3: Restore deleted
### L4: `restore_ticket(ticket_id: str, store: TicketStore) -> Ticket`
  - Find ticket in .trash/ directory
  - Move ticket back to original location
  - Re-add to Zvec index
  - Update `updated` timestamp
  - Return restored ticket

### L5: Spec
```python
def restore_ticket(ticket_id: str, store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", store with C1 in .trash/
    Action: Move .trash/C1.md to tickets/owner/repo/code/C1.md
            Re-index C1
    Output: Ticket(id="C1", ...)
    
    Input: ticket_id="C1", store with C1 not in .trash/ (active or nonexistent)
    Error: TicketNotFoundError(f"Ticket {ticket_id} not found in trash")
    
    Input: ticket_id="C1", store with C1 restored but C2 already exists at location
    Error: RestoreConflictError(f"Cannot restore: ticket C2 already exists at that location")
    """
```

### L6: Test
```python
test_restore_ticket_moves_from_trash()
test_restore_ticket_reindexes()
test_restore_ticket_not_in_trash_raises()
test_restore_ticket_updates_timestamp()
test_restore_ticket_conflict_raises()
test_restore_ticket_original_location_restored()
```

---

## Feature 9: Custom Statuses

### L1: Ticket Lifecycle
### L2: Status
### L3: Custom statuses
### L4: `load_custom_statuses(config: Config) -> Dict[str, StatusMetadata]`
  - Read custom status definitions from vtic.toml
  - Merge with built-in statuses (built-ins can be overridden)
  - Validate custom status definitions have required fields
  - Provide defaults for optional metadata fields

### L5: Spec
```python
# vtic.toml example:
# [statuses.reviewing]
# display_name = "Under Review"
# description = "Being reviewed by team"
# color = "blue"

def load_custom_statuses(config: Config) -> Dict[str, StatusMetadata]:
    """
    Input: config with vtic.toml containing custom "reviewing" status
    Output: {
        "open": StatusMetadata(...),
        "in_progress": StatusMetadata(...),
        ...,
        "reviewing": StatusMetadata(name="reviewing", display_name="Under Review", 
                                     description="Being reviewed by team", color="blue")
    }
    
    Input: config with invalid status definition (missing required field)
    Error: ConfigValidationError("Status 'reviewing' missing required field 'display_name'")
    
    Input: config with no custom statuses
    Output: Dict with only built-in statuses
    """
```

### L6: Test
```python
test_load_custom_statuses_adds_new_status()
test_load_custom_statuses_overrides_builtin()
test_load_custom_statuses_missing_required_field_raises()
test_load_custom_statuses_no_custom_returns_builtins()
test_load_custom_statuses_applies_defaults()
test_validate_status_recognizes_custom_status()
```

---

## Feature 10: Ticket References

### L1: Ticket Lifecycle
### L2: Linking
### L3: Ticket references
### L4: `add_ticket_references(ticket_id: str, ref_ids: List[str], store: TicketStore) -> Ticket`
  - Add ticket IDs to `relates_to` field
  - Validate referenced tickets exist (optional, --skip-validation to bypass)
  - Store as list in ticket metadata
  - Support bidirectional linking (both tickets reference each other)

### L5: Spec
```python
def add_ticket_references(ticket_id: str, ref_ids: List[str], store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", ref_ids=["C2", "C3"]
    Output: Ticket(id="C1", relates_to=["C2", "C3"], ...)
    
    Input: ticket_id="C1", ref_ids=["C2"], with bidirectional=True
    Action: Add C2 to C1's relates_to, add C1 to C2's relates_to
    Output: Ticket(id="C1", relates_to=["C2"], ...)
    
    Input: ticket_id="C1", ref_ids=["NONEXISTENT"]
    Error: ReferenceValidationError("Referenced ticket 'NONEXISTENT' not found")
    
    Input: ticket_id="C1", ref_ids=["C1"]
    Error: ReferenceValidationError("Cannot reference self")
    """
```

### L6: Test
```python
test_add_ticket_references_single()
test_add_ticket_references_multiple()
test_add_ticket_references_nonexistent_raises()
test_add_ticket_references_self_reference_raises()
test_add_ticket_references_bidirectional()
test_add_ticket_references_duplicate_ignored()
```

---

## Feature 11: Parent/Child Tickets

### L1: Ticket Lifecycle
### L2: Linking
### L3: Parent/child tickets
### L4: `set_ticket_parent(ticket_id: str, parent_id: str, store: TicketStore) -> Ticket`
  - Set parent ticket ID
  - Validate parent exists
  - Prevent circular relationships (A→B→A)
  - Store parent reference in ticket metadata

### L5: Spec
```python
def set_ticket_parent(ticket_id: str, parent_id: str, store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C2", parent_id="C1"
    Output: Ticket(id="C2", parent="C1", ...)
    
    Input: ticket_id="C1", parent_id="C2", where C2 already has parent C1
    Error: CircularReferenceError("Cannot create circular parent relationship")
    
    Input: ticket_id="C1", parent_id="NONEXISTENT"
    Error: ReferenceValidationError("Parent ticket 'NONEXISTENT' not found")
    
    Input: ticket_id="C1", parent_id=None
    Output: Ticket(id="C1", parent=None, ...)  # clear parent
    """
```

### L6: Test
```python
test_set_ticket_parent_valid()
test_set_ticket_parent_clears_parent()
test_set_ticket_parent_nonexistent_raises()
test_set_ticket_parent_circular_raises()
test_set_ticket_parent_deep_circular_raises()
test_get_ticket_children()
```

---

## Feature 12: Fuzzy Matching

### L1: Search
### L2: BM25
### L3: Fuzzy matching
### L4: `fuzzy_search_tickets(query: str, fuzziness: int, store: TicketStore) -> List[SearchResult]`
  - Apply character-level fuzzy matching for typos
  - Configurable fuzziness level (Levenshtein distance)
  - Boost exact matches over fuzzy matches
  - Return results with match type metadata

### L5: Spec
```python
@dataclass
class SearchResult:
    ticket: Ticket
    score: float
    match_type: str  # "exact", "fuzzy"

def fuzzy_search_tickets(query: str, fuzziness: int, store: TicketStore) -> List[SearchResult]:
    """
    Input: query="CORs", fuzziness=1
    Output: [SearchResult(ticket=C1, score=0.95, match_type="fuzzy"), ...]
            # Matches "CORS" with edit distance 1
    
    Input: query="authentcation", fuzziness=2
    Output: [SearchResult(..., match_type="fuzzy")]  # Matches "authentication"
    
    Input: query="exact match", fuzziness=1
    Output: [SearchResult(..., match_type="exact")]  # Exact match when possible
    
    Input: query="", fuzziness=1
    Output: []  # Empty query returns empty results
    """
```

### L6: Test
```python
test_fuzzy_search_typo_one_char()
test_fuzzy_search_typo_two_chars()
test_fuzzy_search_exact_match_preferred()
test_fuzzy_search_empty_query_returns_empty()
test_fuzzy_search_fuzziness_zero_equals_exact()
test_fuzzy_search_high_fuzziness_returns_more_results()
```

---

## Feature 13: Boost Fields

### L1: Search
### L2: BM25
### L3: Boost fields
### L4: `search_with_field_boost(query: str, boosts: Dict[str, float], store: TicketStore) -> List[SearchResult]`
  - Apply different weights to different fields
  - Default: title=2.0, description=1.0, tags=1.5
  - Allow custom boost configuration
  - Combine with BM25 scoring

### L5: Spec
```python
DEFAULT_FIELD_BOOSTS = {
    "title": 2.0,
    "description": 1.0,
    "tags": 1.5,
    "severity": 1.0,
}

def search_with_field_boost(query: str, boosts: Dict[str, float], store: TicketStore) -> List[SearchResult]:
    """
    Input: query="authentication", boosts={"title": 3.0, "description": 1.0}
    Output: [SearchResult(..., score=2.8), ...]  # Title matches ranked higher
    
    Input: query="bug", boosts=DEFAULT_FIELD_BOOSTS
    Output: Results with default weighting applied
    
    Input: query="", boosts={}
    Output: []  # Empty query returns empty
    """
```

### L6: Test
```python
test_search_with_field_boost_title_weighted_higher()
test_search_with_field_boost_custom_weights()
test_search_with_field_boost_default_weights()
test_search_with_field_boost_empty_query()
test_search_with_field_boost_zero_boost_excludes_field()
```

---

## Feature 14: Phrase Search

### L1: Search
### L2: BM25
### L3: Phrase search
### L4: `search_exact_phrase(phrase: str, store: TicketStore) -> List[SearchResult]`
  - Parse quoted phrases from query
  - Match exact sequence of words in order
  - Higher score for phrase matches vs individual word matches
  - Support mixed phrase and keyword queries

### L5: Spec
```python
def search_exact_phrase(phrase: str, store: TicketStore) -> List[SearchResult]:
    """
    Input: phrase="CORS wildcard origin"
    Output: [SearchResult(ticket=C1, score=0.95)]  # Only tickets with exact phrase
    
    Input: phrase="nonexistent phrase xyz"
    Output: []
    
    Input: phrase=""
    Output: []
    
    Note: Phrase search is case-insensitive by default
    """
```

### L6: Test
```python
test_search_exact_phrase_matches()
test_search_exact_phrase_no_match_returns_empty()
test_search_exact_phrase_case_insensitive()
test_search_exact_phrase_empty_returns_empty()
test_search_exact_phrase_partial_no_match()
test_parse_query_extracts_phrases()
```

---

## Feature 15: Embedding Caching

### L1: Search
### L2: Semantic
### L3: Embedding caching
### L4: `get_or_compute_embedding(ticket_id: str, content: str, cache: EmbeddingCache) -> List[float]`
  - Check cache for existing embedding by content hash
  - Return cached embedding if content unchanged
  - Compute and cache new embedding if cache miss or content changed
  - Store cache with content hash for invalidation

### L5: Spec
```python
@dataclass
class EmbeddingCache:
    cache_dir: str
    max_size_mb: int = 500

def get_or_compute_embedding(ticket_id: str, content: str, cache: EmbeddingCache) -> List[float]:
    """
    Input: ticket_id="C1", content="Bug in CORS", cache with C1 entry
    Output: [0.1, 0.2, ...]  # From cache
    
    Input: ticket_id="C1", content="Updated bug in CORS", cache with old C1 entry
    Action: Compute new embedding, update cache
    Output: [0.15, 0.25, ...]  # New embedding
    
    Input: ticket_id="NEW", content="New ticket", cache empty
    Action: Compute embedding, store in cache
    Output: [0.3, 0.4, ...]
    """
```

### L6: Test
```python
test_get_or_compute_embedding_cache_hit()
test_get_or_compute_embedding_cache_miss()
test_get_or_compute_embedding_content_changed_updates()
test_embedding_cache_content_hash_key()
test_embedding_cache_max_size_eviction()
test_embedding_cache_persists_to_disk()
```

---

## Feature 16: Configurable Weights

### L1: Search
### L2: Hybrid
### L3: Configurable weights
### L4: `hybrid_search_weighted(query: str, weights: HybridWeights, store: TicketStore) -> List[SearchResult]`
  - Accept BM25 and semantic weight configuration
  - Default: BM25=0.7, semantic=0.3
  - Apply weights to normalized scores before fusion
  - Support runtime override via CLI flag

### L5: Spec
```python
@dataclass
class HybridWeights:
    bm25: float = 0.7
    semantic: float = 0.3

def hybrid_search_weighted(query: str, weights: HybridWeights, store: TicketStore) -> List[SearchResult]:
    """
    Input: query="auth bug", weights=HybridWeights(bm25=0.7, semantic=0.3)
    Output: Results with weighted fusion applied
    
    Input: query="auth bug", weights=HybridWeights(bm25=1.0, semantic=0.0)
    Output: Results from BM25 only
    
    Input: query="auth bug", weights=HybridWeights(bm25=0.5, semantic=0.5)
    Output: Results with equal weighting
    
    Error: ValueError if weights don't sum to 1.0
    """
```

### L6: Test
```python
test_hybrid_search_weighted_default_weights()
test_hybrid_search_weighted_bm25_only()
test_hybrid_search_weighted_semantic_only()
test_hybrid_search_weighted_equal_weights()
test_hybrid_search_weighted_invalid_weights_raises()
test_hybrid_search_weighted_cli_override()
```

---

## Feature 17: RRF Fusion

### L1: Search
### L2: Hybrid
### L3: RRF fusion
### L4: `rrf_fuse_results(bm25_results: List[SearchResult], semantic_results: List[SearchResult], k: int = 60) -> List[SearchResult]`
  - Implement Reciprocal Rank Fusion algorithm
  - RRF score = Σ 1/(k + rank) for each result list
  - Combine results from multiple search methods
  - Deduplicate by ticket ID, keeping highest score

### L5: Spec
```python
def rrf_fuse_results(bm25_results: List[SearchResult], semantic_results: List[SearchResult], k: int = 60) -> List[SearchResult]:
    """
    Input: bm25_results=[C1@1, C2@2, C3@3], semantic_results=[C2@1, C1@2, C4@3], k=60
    Output: [C2, C1, C3, C4]  # RRF scores: C2=0.0328, C1=0.0322, C3=0.0164, C4=0.0161
    
    Input: bm25_results=[], semantic_results=[C1@1]
    Output: [C1]  # Single list works
    
    Input: bm25_results=[], semantic_results=[]
    Output: []
    
    Note: k=60 is standard RRF constant (smaller k = more weight to top ranks)
    """
```

### L6: Test
```python
test_rrf_fuse_results_combines_ranks()
test_rrf_fuse_results_deduplicates()
test_rrf_fuse_results_empty_lists()
test_rrf_fuse_results_single_list()
test_rrf_fuse_results_custom_k()
test_rrf_fuse_results_rank_order_matters()
```

---

## Feature 18: Score Normalization

### L1: Search
### L2: Hybrid
### L3: Score normalization
### L4: `normalize_scores(results: List[SearchResult], method: str = "minmax") -> List[SearchResult]`
  - Normalize scores to [0, 1] range
  - Support min-max and z-score normalization
  - Handle single result (score = 1.0)
  - Preserve result order

### L5: Spec
```python
def normalize_scores(results: List[SearchResult], method: str = "minmax") -> List[SearchResult]:
    """
    Input: results=[C1@10, C2@5, C3@1], method="minmax"
    Output: [C1@1.0, C2@0.44, C3@0.0]  # (score - min) / (max - min)
    
    Input: results=[C1@10, C2@5, C3@1], method="zscore"
    Output: Normalized using (score - mean) / std_dev
    
    Input: results=[C1@5], method="minmax"
    Output: [C1@1.0]  # Single result normalized to 1.0
    
    Input: results=[], method="minmax"
    Output: []
    """
```

### L6: Test
```python
test_normalize_scores_minmax()
test_normalize_scores_zscore()
test_normalize_scores_single_result()
test_normalize_scores_empty_list()
test_normalize_scores_preserves_order()
test_normalize_scores_all_same_scores()
```

---

## Feature 19: Date Range Filters

### L1: Search
### L2: Filters
### L3: Date range filters
### L4: `filter_by_date_range(tickets: List[Ticket], field: str, start: Optional[datetime], end: Optional[datetime]) -> List[Ticket]`
  - Filter tickets by created or updated date
  - Support open-ended ranges (start only or end only)
  - Parse ISO 8601 date strings
  - Include tickets exactly on boundary dates

### L5: Spec
```python
def filter_by_date_range(tickets: List[Ticket], field: str, start: Optional[datetime], end: Optional[datetime]) -> List[Ticket]:
    """
    Input: tickets=[C1@2026-03-10, C2@2026-03-15, C3@2026-03-20], 
           field="created", start="2026-03-12", end="2026-03-18"
    Output: [C2]  # Only C2 falls in range
    
    Input: tickets=[...], field="updated", start="2026-03-01", end=None
    Output: Tickets updated on or after March 1
    
    Input: tickets=[...], field="created", start=None, end="2026-03-15"
    Output: Tickets created on or before March 15
    
    Input: tickets=[...], field="created", start="2026-03-20", end="2026-03-10"
    Error: ValueError("Start date must be before end date")
    """
```

### L6: Test
```python
test_filter_by_date_range_both_bounds()
test_filter_by_date_range_start_only()
test_filter_by_date_range_end_only()
test_filter_by_date_range_inclusive_boundaries()
test_filter_by_date_range_invalid_range_raises()
test_filter_by_date_range_empty_tickets()
```

---

## Feature 20: Field Existence

### L1: Search
### L2: Filters
### L3: Field existence
### L4: `filter_by_field_existence(tickets: List[Ticket], field: str, exists: bool = True) -> List[Ticket]`
  - Filter tickets by whether a field has a value
  - Check for None, empty string, empty list
  - Support negation with exists=False

### L5: Spec
```python
def filter_by_field_existence(tickets: List[Ticket], field: str, exists: bool = True) -> List[Ticket]:
    """
    Input: tickets=[C1(fix="..."), C2(fix=None), C3(fix="...")], field="fix", exists=True
    Output: [C1, C3]  # Tickets with fix field populated
    
    Input: tickets=[...], field="fix", exists=False
    Output: [C2]  # Tickets without fix field
    
    Input: tickets=[C1(tags=[]), C2(tags=["bug"])], field="tags", exists=True
    Output: [C2]  # Empty list counts as non-existent
    
    Input: tickets=[...], field="nonexistent_field"
    Output: [] or all tickets depending on exists param
    """
```

### L6: Test
```python
test_filter_by_field_existence_has_field()
test_filter_by_field_existence_missing_field()
test_filter_by_field_existence_empty_list_treated_as_missing()
test_filter_by_field_existence_none_treated_as_missing()
test_filter_by_field_existence_empty_string_treated_as_missing()
test_filter_by_field_existence_invalid_field()
```

---

## Feature 21: Cursor Pagination Search

### L1: Search
### L2: Pagination
### L3: Cursor pagination search
### L4: `search_with_cursor(query: str, cursor: Optional[str], limit: int, store: TicketStore) -> CursorResult`
  - Return stable pagination token for next page
  - Cursor encodes sort position (not just offset)
  - Handle inserts/deletes during pagination gracefully
  - Return has_more flag

### L5: Spec
```python
@dataclass
class CursorResult:
    results: List[Ticket]
    next_cursor: Optional[str]
    has_more: bool

def search_with_cursor(query: str, cursor: Optional[str], limit: int, store: TicketStore) -> CursorResult:
    """
    Input: query="bug", cursor=None, limit=10
    Output: CursorResult(results=[C1..C10], next_cursor="eyJpZCI6IkMxMCJ9", has_more=True)
    
    Input: query="bug", cursor="eyJpZCI6IkMxMCJ9", limit=10
    Output: CursorResult(results=[C11..C20], next_cursor="...", has_more=True)
    
    Input: query="bug", cursor="last_page_token", limit=10
    Output: CursorResult(results=[C41..C45], next_cursor=None, has_more=False)
    
    Input: cursor="invalid_token"
    Error: InvalidCursorError("Invalid cursor token")
    """
```

### L6: Test
```python
test_search_with_cursor_first_page()
test_search_with_cursor_next_page()
test_search_with_cursor_last_page()
test_search_with_cursor_invalid_token()
test_search_with_cursor_stable_with_inserts()
test_search_with_cursor_encodes_sort_position()
```

---

## Feature 22: File Locking

### L1: Storage
### L2: Files
### L3: File locking
### L4: `acquire_ticket_lock(ticket_id: str, timeout_ms: int = 5000) -> LockHandle`
  - Acquire exclusive lock on ticket file before write
  - Use file-system level locking (fcntl or portalocker)
  - Timeout if lock not acquired within timeout_ms
  - Auto-release lock on context exit

### L5: Spec
```python
@dataclass
class LockHandle:
    ticket_id: str
    lock_file: str
    acquired_at: datetime

def acquire_ticket_lock(ticket_id: str, timeout_ms: int = 5000) -> LockHandle:
    """
    Input: ticket_id="C1", timeout_ms=5000
    Output: LockHandle(ticket_id="C1", lock_file=".vtic/locks/C1.lock", ...)
    
    Input: ticket_id="C1" (already locked by another process)
    Error: LockTimeoutError("Could not acquire lock for C1 within 5000ms")
    
    Note: Lock files stored in .vtic/locks/ directory
    Note: Locks are released on process exit or explicit release
    """
```

### L6: Test
```python
test_acquire_ticket_lock_success()
test_acquire_ticket_lock_timeout()
test_acquire_ticket_lock_release()
test_acquire_ticket_lock_context_manager()
test_acquire_ticket_lock_prevents_concurrent_write()
test_acquire_ticket_lock_stale_lock_recovery()
```

---

## Feature 23: Index Health Check

### L1: Storage
### L2: Index
### L3: Index health check
### L4: `check_index_health(store: TicketStore) -> IndexHealthReport`
  - Compare index entries to actual ticket files
  - Detect missing index entries (tickets not indexed)
  - Detect orphan index entries (index points to deleted tickets)
  - Check index file integrity
  - Return actionable health report

### L5: Spec
```python
@dataclass
class IndexHealthReport:
    is_healthy: bool
    total_tickets: int
    indexed_tickets: int
    missing_from_index: List[str]  # Ticket IDs in files but not index
    orphan_index_entries: List[str]  # Index entries with no ticket file
    index_file_valid: bool

def check_index_health(store: TicketStore) -> IndexHealthReport:
    """
    Input: store with 100 tickets, 98 indexed, 2 orphans
    Output: IndexHealthReport(
        is_healthy=False,
        total_tickets=100,
        indexed_tickets=98,
        missing_from_index=["C50", "C51"],
        orphan_index_entries=["DELETED1", "DELETED2"],
        index_file_valid=True
    )
    
    Input: store with corrupted index file
    Output: IndexHealthReport(is_healthy=False, index_file_valid=False, ...)
    """
```

### L6: Test
```python
test_check_index_health_healthy()
test_check_index_health_missing_entries()
test_check_index_health_orphan_entries()
test_check_index_health_corrupted_index()
test_check_index_health_empty_store()
test_cli_index_status_command()
```

---

## Feature 24: Index Corruption Recovery

### L1: Storage
### L2: Index
### L3: Index corruption recovery
### L4: `recover_corrupted_index(store: TicketStore, strategy: str = "rebuild") -> RecoveryResult`
  - Detect corruption on index load
  - Auto-prompt for rebuild or restore from backup
  - Support rebuild from source files
  - Log recovery action

### L5: Spec
```python
@dataclass
class RecoveryResult:
    success: bool
    action_taken: str  # "rebuild", "restore", "none"
    tickets_recovered: int
    errors: List[str]

def recover_corrupted_index(store: TicketStore, strategy: str = "rebuild") -> RecoveryResult:
    """
    Input: store with corrupted index, strategy="rebuild"
    Action: Delete corrupted index, rebuild from all ticket files
    Output: RecoveryResult(success=True, action_taken="rebuild", tickets_recovered=100, errors=[])
    
    Input: store with corrupted index, strategy="restore", backup exists
    Action: Restore index from latest backup
    Output: RecoveryResult(success=True, action_taken="restore", ...)
    
    Input: store with corrupted index, strategy="restore", no backup
    Output: RecoveryResult(success=False, action_taken="none", errors=["No backup found"])
    """
```

### L6: Test
```python
test_recover_corrupted_index_rebuild()
test_recover_corrupted_index_restore()
test_recover_corrupted_index_no_backup()
test_recover_corrupted_index_partial_failure()
test_corruption_detection_on_load()
test_auto_prompt_for_recovery()
```

---

## Feature 25: Export to Archive

### L1: Storage
### L2: Backup
### L3: Export to archive
### L4: `export_to_archive(output_path: str, format: str, store: TicketStore, filters: Optional[TicketFilter] = None) -> ExportResult`
  - Create compressed archive of ticket files and index
  - Support tar.gz and zip formats
  - Include metadata file with export timestamp and stats
  - Optionally filter tickets for partial export

### L5: Spec
```python
@dataclass
class ExportResult:
    output_path: str
    tickets_exported: int
    bytes_written: int
    timestamp: str

def export_to_archive(output_path: str, format: str, store: TicketStore, filters: Optional[TicketFilter] = None) -> ExportResult:
    """
    Input: output_path="backup.tar.gz", format="tar.gz", store with 100 tickets
    Action: Create tar.gz with all tickets, index, and manifest.json
    Output: ExportResult(output_path="backup.tar.gz", tickets_exported=100, bytes_written=1024000, ...)
    
    Input: output_path="backup.zip", format="zip", store with 100 tickets
    Action: Create zip archive
    Output: ExportResult(output_path="backup.zip", ...)
    
    Input: output_path="open-only.tar.gz", format="tar.gz", filters=TicketFilter(status="open")
    Action: Export only tickets with status=open
    Output: ExportResult(tickets_exported=25, ...)
    """
```

### L6: Test
```python
test_export_to_archive_tar_gz()
test_export_to_archive_zip()
test_export_to_archive_with_filters()
test_export_includes_manifest()
test_export_includes_index()
test_export_empty_store()
```

---

## Feature 26: Import from Archive

### L1: Storage
### L2: Backup
### L3: Import from archive
### L4: `import_from_archive(archive_path: str, store: TicketStore, mode: str = "merge") -> ImportResult`
  - Extract and validate archive contents
  - Support merge (keep existing), replace (overwrite), and skip_existing modes
  - Validate ticket format before import
  - Rebuild index after import

### L5: Spec
```python
@dataclass
class ImportResult:
    tickets_imported: int
    tickets_skipped: int
    tickets_replaced: int
    errors: List[str]

def import_from_archive(archive_path: str, store: TicketStore, mode: str = "merge") -> ImportResult:
    """
    Input: archive_path="backup.tar.gz", store, mode="merge"
    Action: Import all tickets, skip if ID already exists
    Output: ImportResult(tickets_imported=80, tickets_skipped=20, tickets_replaced=0, errors=[])
    
    Input: archive_path="backup.tar.gz", store, mode="replace"
    Action: Import all tickets, overwrite if ID exists
    Output: ImportResult(tickets_imported=0, tickets_skipped=0, tickets_replaced=100, errors=[])
    
    Input: archive_path="invalid.tar.gz"
    Error: ArchiveError("Invalid or corrupted archive")
    """
```

### L6: Test
```python
test_import_from_archive_merge_mode()
test_import_from_archive_replace_mode()
test_import_from_archive_skip_existing_mode()
test_import_from_archive_invalid_archive()
test_import_from_archive_validates_tickets()
test_import_rebuilds_index()
```

---

## Feature 27: Point-in-Time Recovery

### L1: Storage
### L2: Backup
### L3: Point-in-time recovery
### L4: `recover_to_point_in_time(target_time: datetime, store: TicketStore, git_repo: Optional[str] = None) -> RecoveryResult`
  - Use git history to restore tickets to specific point
  - Checkout ticket files as they existed at target_time
  - Rebuild index for recovered state
  - Support dry-run mode

### L5: Spec
```python
def recover_to_point_in_time(target_time: datetime, store: TicketStore, git_repo: Optional[str] = None) -> RecoveryResult:
    """
    Input: target_time=datetime(2026, 3, 15, 12, 0), store with git history
    Action: Restore all ticket files to March 15 state, rebuild index
    Output: RecoveryResult(success=True, action_taken="pit_recovery", tickets_recovered=95, ...)
    
    Input: target_time=datetime(2030, 1, 1)  # Future date
    Error: RecoveryError("Target time is in the future")
    
    Input: target_time=datetime(2020, 1, 1)  # Before any commits
    Error: RecoveryError("No commits found before target time")
    
    Input: store without git repository
    Error: RecoveryError("Git repository required for point-in-time recovery")
    """
```

### L6: Test
```python
test_recover_to_point_in_time_valid()
test_recover_to_point_in_time_future_raises()
test_recover_to_point_in_time_no_git_raises()
test_recover_to_point_in_time_no_commits_raises()
test_recover_to_point_in_time_dry_run()
test_recover_rebuilds_index()
```

---

## Feature 28: Bulk Create API

### L1: API
### L2: REST
### L3: Bulk create API
### L4: `POST /tickets/bulk` endpoint
  - Accept array of ticket objects
  - Validate all tickets before creating any
  - Return created tickets with generated IDs
  - Report partial failures with details

### L5: Spec
```python
# Request
POST /tickets/bulk
{
    "tickets": [
        {"title": "Bug 1", "repo": "owner/repo", "severity": "high"},
        {"title": "Bug 2", "repo": "owner/repo", "severity": "medium"},
        {"title": "", "repo": "owner/repo"}  # Invalid
    ]
}

# Response (200 with partial success)
{
    "data": {
        "created": [
            {"id": "C101", "title": "Bug 1", ...},
            {"id": "C102", "title": "Bug 2", ...}
        ],
        "failed": [
            {"index": 2, "error": "Title is required"}
        ]
    },
    "meta": {"created": 2, "failed": 1}
}

# Response (400 if validation fails before creation)
{
    "error": {"code": "VALIDATION_ERROR", "message": "...", "details": [...]}
}
```

### L6: Test
```python
test_bulk_create_all_success()
test_bulk_create_partial_failure()
test_bulk_create_validation_error()
test_bulk_create_empty_array()
test_bulk_create_large_batch()
test_bulk_create_returns_generated_ids()
```

---

## Feature 29: Bulk Update API

### L1: API
### L2: REST
### L3: Bulk update API
### L4: `PATCH /tickets/bulk` endpoint
  - Accept filter criteria and update payload
  - Apply updates to all matching tickets
  - Return summary of updated/failed
  - Support dry-run mode

### L5: Spec
```python
# Request
PATCH /tickets/bulk
{
    "filter": {"status": "open", "severity": "critical"},
    "updates": {"status": "in_progress"}
}

# Response (200)
{
    "data": {
        "updated": 5,
        "failed": 0,
        "ticket_ids": ["C1", "C5", "C10", "C15", "C20"]
    }
}

# Request (dry-run)
PATCH /tickets/bulk?dry_run=true
{
    "filter": {"status": "open"},
    "updates": {"status": "reviewing"}
}

# Response (200)
{
    "data": {
        "would_update": 15,
        "ticket_ids": ["C1", "C2", ...]
    }
}
```

### L6: Test
```python
test_bulk_update_by_filter()
test_bulk_update_no_matches()
test_bulk_update_partial_failure()
test_bulk_update_dry_run()
test_bulk_update_validates_updates()
test_bulk_update_requires_filter()
```

---

## Feature 30: Bulk Delete API

### L1: API
### L2: REST
### L3: Bulk delete API
### L4: `DELETE /tickets/bulk` endpoint
  - Accept filter criteria or list of IDs
  - Soft delete by default, hard with force=true
  - Return summary of deleted/failed
  - Require explicit confirmation header for safety

### L5: Spec
```python
# Request (by filter)
DELETE /tickets/bulk
{
    "filter": {"status": "wont_fix"},
    "force": false
}

# Response (200)
{
    "data": {
        "deleted": 8,
        "failed": 0,
        "ticket_ids": ["C10", "C11", ...]
    }
}

# Request (by IDs)
DELETE /tickets/bulk
{
    "ids": ["C1", "C2", "C3"],
    "force": true
}

# Response (200)
{
    "data": {
        "deleted": 3,
        "failed": 0,
        "ticket_ids": ["C1", "C2", "C3"]
    }
}

# Request (missing confirmation)
DELETE /tickets/bulk
{
    "filter": {"status": "open"}
}
# Response (400)
{
    "error": {"code": "CONFIRMATION_REQUIRED", "message": "Add X-Confirm-Bulk-Delete header"}
}
```

### L6: Test
```python
test_bulk_delete_by_filter()
test_bulk_delete_by_ids()
test_bulk_delete_soft()
test_bulk_delete_hard()
test_bulk_delete_requires_confirmation()
test_bulk_delete_partial_failure()
```

---

## Feature 31: Get Stats

### L1: API
### L2: REST
### L3: Get stats
### L4: `GET /stats` endpoint
  - Return ticket counts by status, severity, category, repo
  - Include total count and recent activity
  - Support grouped breakdowns

### L5: Spec
```python
# Request
GET /stats

# Response (200)
{
    "data": {
        "total": 150,
        "by_status": {
            "open": 45,
            "in_progress": 20,
            "blocked": 5,
            "fixed": 60,
            "wont_fix": 10,
            "closed": 10
        },
        "by_severity": {
            "critical": 10,
            "high": 25,
            "medium": 50,
            "low": 65
        },
        "by_category": {
            "code": 80,
            "security": 20,
            "docs": 30,
            "infra": 20
        },
        "by_repo": {
            "owner/repo1": 100,
            "owner/repo2": 50
        },
        "recent_activity": {
            "created_last_7d": 12,
            "updated_last_7d": 35,
            "closed_last_7d": 8
        }
    }
}
```

### L6: Test
```python
test_get_stats_total_count()
test_get_stats_by_status()
test_get_stats_by_severity()
test_get_stats_by_category()
test_get_stats_by_repo()
test_get_stats_recent_activity()
test_get_stats_empty_store()
```

---

## Feature 32: OpenAPI Spec

### L1: API
### L2: Documentation
### L3: OpenAPI spec
### L4: `GET /openapi.json` endpoint
  - Generate OpenAPI 3.0 specification
  - Include all endpoints, schemas, and examples
  - Document error responses
  - Support YAML format via Accept header

### L5: Spec
```python
# Request
GET /openapi.json

# Response (200)
{
    "openapi": "3.0.0",
    "info": {
        "title": "vtic API",
        "version": "0.1.0",
        "description": "Ticket management API"
    },
    "paths": {
        "/tickets": {
            "get": {...},
            "post": {...}
        },
        "/tickets/{id}": {
            "get": {...},
            "patch": {...},
            "delete": {...}
        },
        "/search": {...},
        "/stats": {...}
    },
    "components": {
        "schemas": {
            "Ticket": {...},
            "Error": {...}
        }
    }
}

# Request (YAML)
GET /openapi.yaml
Accept: application/yaml

# Response (200)
openapi: "3.0.0"
info:
  title: vtic API
  ...
```

### L6: Test
```python
test_get_openapi_json_valid()
test_get_openapi_yaml_valid()
test_openapi_includes_all_endpoints()
test_openapi_includes_ticket_schema()
test_openapi_includes_error_schema()
test_openapi_includes_examples()
```

---

## Feature 33: Markdown Response

### L1: API
### L2: Response
### L3: Markdown response
### L4: `Accept: text/markdown` content negotiation
  - Return raw markdown when Accept header specifies
  - Fall back to JSON if header not present
  - Include frontmatter in markdown output
  - Single ticket or ticket list supported

### L5: Spec
```python
# Request
GET /tickets/C1
Accept: text/markdown

# Response (200)
Content-Type: text/markdown

---
id: C1
title: CORS Bug
status: open
severity: critical
---

# Description

Details about the CORS issue...

# Request (list)
GET /tickets?status=open
Accept: text/markdown

# Response (200)
Content-Type: text/markdown

## C1: CORS Bug (critical)
## C2: Auth Error (high)
...

# Request (JSON fallback)
GET /tickets/C1

# Response (200)
Content-Type: application/json
{"data": {"id": "C1", ...}}
```

### L6: Test
```python
test_markdown_response_single_ticket()
test_markdown_response_ticket_list()
test_markdown_response_includes_frontmatter()
test_json_fallback_without_header()
test_invalid_accept_header_returns_json()
test_markdown_response_format()
```

---

## Feature 34: Request ID

### L1: API
### L2: Observability
### L3: Request ID
### L4: `add_request_id(response: Response) -> Response`
  - Generate unique request ID for each request
  - Include in X-Request-ID response header
  - Include in error responses
  - Use provided X-Request-ID from client if present

### L5: Spec
```python
# Request
GET /tickets/C1

# Response (200)
X-Request-ID: req_abc123def456
Content-Type: application/json
{"data": {...}}

# Request (with client-provided ID)
GET /tickets/C1
X-Request-ID: client-trace-123

# Response (200)
X-Request-ID: client-trace-123  # Echoes client ID
Content-Type: application/json
{"data": {...}}

# Error response
HTTP/1.1 404 Not Found
X-Request-ID: req_xyz789
Content-Type: application/json
{
    "error": {
        "code": "NOT_FOUND",
        "message": "Ticket C999 not found",
        "request_id": "req_xyz789"
    }
}
```

### L6: Test
```python
test_request_id_generated()
test_request_id_in_response_header()
test_request_id_in_error_response()
test_request_id_echoes_client_id()
test_request_id_unique_per_request()
test_request_id_logged()
```

---

## Feature 35: Cursor Pagination API

### L1: API
### L2: Pagination
### L3: Cursor pagination API
### L4: `GET /tickets?cursor=xxx&limit=20` endpoint support
  - Accept cursor parameter for token-based pagination
  - Return next_cursor in response metadata
  - Include has_more flag
  - Support both offset and cursor pagination

### L5: Spec
```python
# Request (first page)
GET /tickets?limit=20

# Response (200)
{
    "data": [...],  # 20 tickets
    "meta": {
        "total": 100,
        "limit": 20,
        "next_cursor": "eyJpZCI6IkMyMCIsInNvcnQiOiJjcmVhdGVkIn0",
        "has_more": true
    }
}

# Request (next page)
GET /tickets?cursor=eyJpZCI6IkMyMCIsInNvcnQiOiJjcmVhdGVkIn0&limit=20

# Response (200)
{
    "data": [...],  # Next 20 tickets
    "meta": {
        "total": 100,
        "limit": 20,
        "next_cursor": "eyJpZCI6IkM0MCIsInNvcnQiOiJjcmVhdGVkIn0",
        "has_more": true
    }
}

# Request (last page)
GET /tickets?cursor=last_page_token&limit=20

# Response (200)
{
    "data": [...],  # Remaining tickets
    "meta": {
        "total": 100,
        "limit": 20,
        "next_cursor": null,
        "has_more": false
    }
}
```

### L6: Test
```python
test_cursor_pagination_first_page()
test_cursor_pagination_next_page()
test_cursor_pagination_last_page()
test_cursor_pagination_invalid_cursor()
test_cursor_pagination_with_filters()
test_cursor_pagination_stability()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | Ticket Lifecycle | Create | Custom ID specification | `create_ticket_with_custom_id()` |
| 2 | Ticket Lifecycle | Read | Field selection | `select_ticket_fields()` |
| 3 | Ticket Lifecycle | Read | Raw file output | `get_ticket_raw_content()` |
| 4 | Ticket Lifecycle | Update | Append to description | `append_to_description()` |
| 5 | Ticket Lifecycle | Update | Field clearing | `clear_ticket_fields()` |
| 6 | Ticket Lifecycle | Update | Bulk update | `bulk_update_tickets()` |
| 7 | Ticket Lifecycle | Delete | Cascade delete | `cascade_delete_tickets()` |
| 8 | Ticket Lifecycle | Delete | Restore deleted | `restore_ticket()` |
| 9 | Ticket Lifecycle | Status | Custom statuses | `load_custom_statuses()` |
| 10 | Ticket Lifecycle | Linking | Ticket references | `add_ticket_references()` |
| 11 | Ticket Lifecycle | Linking | Parent/child tickets | `set_ticket_parent()` |
| 12 | Search | BM25 | Fuzzy matching | `fuzzy_search_tickets()` |
| 13 | Search | BM25 | Boost fields | `search_with_field_boost()` |
| 14 | Search | BM25 | Phrase search | `search_exact_phrase()` |
| 15 | Search | Semantic | Embedding caching | `get_or_compute_embedding()` |
| 16 | Search | Hybrid | Configurable weights | `hybrid_search_weighted()` |
| 17 | Search | Hybrid | RRF fusion | `rrf_fuse_results()` |
| 18 | Search | Hybrid | Score normalization | `normalize_scores()` |
| 19 | Search | Filters | Date range filters | `filter_by_date_range()` |
| 20 | Search | Filters | Field existence | `filter_by_field_existence()` |
| 21 | Search | Pagination | Cursor pagination search | `search_with_cursor()` |
| 22 | Storage | Files | File locking | `acquire_ticket_lock()` |
| 23 | Storage | Index | Index health check | `check_index_health()` |
| 24 | Storage | Index | Index corruption recovery | `recover_corrupted_index()` |
| 25 | Storage | Backup | Export to archive | `export_to_archive()` |
| 26 | Storage | Backup | Import from archive | `import_from_archive()` |
| 27 | Storage | Backup | Point-in-time recovery | `recover_to_point_in_time()` |
| 28 | API | REST | Bulk create API | `POST /tickets/bulk` |
| 29 | API | REST | Bulk update API | `PATCH /tickets/bulk` |
| 30 | API | REST | Bulk delete API | `DELETE /tickets/bulk` |
| 31 | API | REST | Get stats | `GET /stats` |
| 32 | API | Documentation | OpenAPI spec | `GET /openapi.json` |
| 33 | API | Response | Markdown response | `Accept: text/markdown` |
| 34 | API | Observability | Request ID | `add_request_id()` |
| 35 | API | Pagination | Cursor pagination API | `GET /tickets?cursor=xxx` |

---

## Category Distribution

| L1 Category | Count |
|-------------|-------|
| Ticket Lifecycle | 11 |
| Search | 10 |
| Storage | 6 |
| API | 8 |

---

*35 Should Have features fully specified to implementation level*
