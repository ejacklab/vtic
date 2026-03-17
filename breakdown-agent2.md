# vtic — 6-Level Feature Breakdown (Search + Storage Core)

**Scope:** 6 Search Capabilities + 6 Storage features = 12 total  
**Purpose:** Implementation-ready specification for coding agents

---

## SEARCH CAPABILITIES (6 Core Features)

---

### L1: Search Capabilities
### L2: BM25 Search
### L3: Full-text Search

**L4: Implementation Unit**
```python
def bm25_search(
    query: str,
    collection: Collection,
    topk: int = 10,
    filters: dict | None = None
) -> list[SearchResult]
```
- Initialize BM25EmbeddingFunction from zvec
- Encode query string to sparse vector
- Build filter expression from filters dict if provided
- Call collection.query() with sparse vector and filter
- Return list of SearchResult with id, score, metadata

**L5: Input/Output Spec**
```
Input:
  query: "CORS wildcard configuration"
  collection: zvec Collection instance
  topk: 10
  filters: {"severity": "critical", "status": "open"}

Output:
  [
    SearchResult(id="C42", score=0.89, metadata={"title": "...", ...}),
    SearchResult(id="C17", score=0.76, metadata={"title": "...", ...}),
    ...
  ]

Error cases:
  - Empty query string → return empty list
  - Collection not initialized → raise CollectionNotInitializedError
  - No matches found → return empty list
```

**L6: Test Cases**
```python
def test_bm25_search_returns_matching_tickets():
    """Basic search returns tickets matching query terms"""
    
def test_bm25_search_with_combined_filters():
    """Search with severity AND status filters works"""
    
def test_bm25_search_no_matches_returns_empty():
    """Query with no matches returns empty list, not error"""
    
def test_bm25_search_empty_query_returns_empty():
    """Empty query string returns empty list gracefully"""
```

---

### L1: Search Capabilities
### L2: Filters & Facets
### L3: Equality Filters

**L4: Implementation Unit**
```python
def build_filter_expression(filters: dict[str, str | list[str]]) -> str:
    """
    Convert filter dict to Zvec filter expression string.
    
    Examples:
      {"severity": "critical"} → "severity == 'critical'"
      {"status": ["open", "in_progress"]} → "status in ['open', 'in_progress']"
      {"severity": "high", "repo": "ejacklab/open-dsearch"} → 
        "severity == 'high' and repo == 'ejacklab/open-dsearch'"
    """

def apply_equality_filters(
    collection: Collection,
    filters: dict[str, str | list[str]],
    limit: int = 100
) -> list[Ticket]
```
- Parse filters dict into filter expression string
- Validate filter keys against allowed fields (severity, status, category, repo)
- Handle single values and lists (IN operator)
- Combine multiple filters with AND logic
- Call collection.query() with filter expression
- Return matching tickets

**L5: Input/Output Spec**
```
Input:
  filters: {
    "severity": "critical",
    "status": ["open", "in_progress"],
    "repo": "ejacklab/open-dsearch"
  }

Output:
  [
    Ticket(id="C1", severity="critical", status="open", ...),
    Ticket(id="C5", severity="critical", status="in_progress", ...),
  ]

Error cases:
  - Invalid filter key → raise InvalidFilterFieldError with allowed fields list
  - Empty filters dict → return all tickets up to limit
```

**L6: Test Cases**
```python
def test_equality_filter_single_value():
    """Filter by single severity value returns matching tickets"""
    
def test_equality_filter_multiple_values():
    """Filter with status in ['open', 'in_progress'] returns both"""
    
def test_equality_filter_combined_filters():
    """Multiple filters combine with AND logic"""
    
def test_equality_filter_invalid_field():
    """Invalid filter field raises helpful error"""
```

---

### L1: Search Capabilities
### L2: Sorting & Pagination
### L3: Sort by Field

**L4: Implementation Unit**
```python
class SortSpec:
    """Specification for sorting results"""
    field: str
    descending: bool
    
    def __init__(self, field: str, descending: bool = False):
        ...

def parse_sort_spec(sort_string: str) -> list[SortSpec]:
    """
    Parse sort string into SortSpec list.
    
    Examples:
      "severity" → [SortSpec("severity", False)]
      "-severity" → [SortSpec("severity", True)]
      "severity,-created" → [SortSpec("severity", False), SortSpec("created", True)]
    """

def sort_tickets_by_field(
    tickets: list[Ticket],
    sort_specs: list[SortSpec]
) -> list[Ticket]
```
- Parse sort string (comma-separated, minus prefix for descending)
- Validate sort fields against ticket schema
- Sort tickets using Python's sorted() with multiple keys
- Handle None values (sort to end)
- Return sorted list

**L5: Input/Output Spec**
```
Input:
  tickets: [Ticket(id="C1", severity="low"), Ticket(id="C2", severity="critical")]
  sort_specs: [SortSpec("severity", True)]  # descending

Output:
  [Ticket(id="C2", severity="critical"), Ticket(id="C1", severity="low")]

Error cases:
  - Invalid sort field → raise InvalidSortFieldError
  - Empty tickets list → return empty list
  - Empty sort_specs → return tickets unchanged
```

**L6: Test Cases**
```python
def test_sort_by_single_field_ascending():
    """Sort by severity ascending orders low→high"""
    
def test_sort_by_single_field_descending():
    """Sort by -severity orders high→low"""
    
def test_sort_by_multiple_fields():
    """Sort by severity, then created date"""
    
def test_sort_handles_none_values():
    """None values sort to end of results"""
    
def test_sort_invalid_field_raises_error():
    """Invalid field name raises clear error"""
```

---

### L1: Search Capabilities
### L2: Sorting & Pagination
### L3: Sort by Relevance (Search Score)

**L4: Implementation Unit**
```python
def sort_by_relevance(
    results: list[SearchResult],
    descending: bool = True
) -> list[SearchResult]:
    """
    Sort search results by relevance score.
    
    Default: descending (highest score first)
    """

def search_with_relevance_sort(
    query: str,
    collection: Collection,
    topk: int = 10,
    filters: dict | None = None
) -> list[SearchResult]
```
- Execute BM25 search
- Results come pre-scored from zvec
- Sort results by score field
- Return sorted results

**L5: Input/Output Spec**
```
Input:
  query: "authentication error"
  collection: zvec Collection with BM25 index

Output (sorted by score descending):
  [
    SearchResult(id="C10", score=0.95, ...),
    SearchResult(id="C3", score=0.82, ...),
    SearchResult(id="C45", score=0.71, ...),
  ]

Note:
  - Relevance sort is DEFAULT when query provided
  - Score is BM25 relevance score (0.0 to 1.0 typically)
```

**L6: Test Cases**
```python
def test_search_results_sorted_by_score_descending():
    """Results are ordered by score highest to lowest"""
    
def test_search_with_no_query_no_relevance_sort():
    """List without query uses field sort, not relevance"""
    
def test_relevance_sort_stable_for_equal_scores():
    """Equal scores maintain consistent order"""
```

---

### L1: Search Capabilities
### L2: Sorting & Pagination
### L3: Limit/Offset Pagination

**L4: Implementation Unit**
```python
@dataclass
class PaginatedResult:
    """Container for paginated results"""
    tickets: list[Ticket]
    total: int
    limit: int
    offset: int
    has_more: bool

def paginate_results(
    tickets: list[Ticket],
    limit: int = 20,
    offset: int = 0
) -> PaginatedResult
```
- Slice tickets list from offset to offset + limit
- Calculate total count before pagination
- Determine has_more flag
- Return PaginatedResult with metadata

**L5: Input/Output Spec**
```
Input:
  tickets: [Ticket(id="C1"), ..., Ticket(id="C100")]  # 100 tickets
  limit: 20
  offset: 40

Output:
  PaginatedResult(
    tickets=[Ticket(id="C41"), ..., Ticket(id="C60")],  # 20 items
    total=100,
    limit=20,
    offset=40,
    has_more=True
  )

Edge cases:
  - offset >= len(tickets) → return empty list, has_more=False
  - limit = 0 → return empty list
  - No limit/offset specified → return all (limit=None or very high)
```

**L6: Test Cases**
```python
def test_pagination_returns_correct_slice():
    """Offset 20, limit 10 returns items 20-29"""
    
def test_pagination_has_more_true_when_more_exist():
    """has_more=True when total > offset + limit"""
    
def test_pagination_has_more_false_at_end():
    """has_more=False when at last page"""
    
def test_pagination_offset_exceeds_total():
    """Offset > total returns empty list gracefully"""
    
def test_pagination_limit_zero():
    """limit=0 returns empty list"""
```

---

### L1: Search Capabilities
### L2: BM25 Search
### L3: Repo Glob Filter

**L4: Implementation Unit**
```python
def parse_repo_glob(repo_pattern: str) -> str:
    """
    Convert repo glob pattern to filter expression.
    
    Examples:
      "ejacklab/open-dsearch" → "repo == 'ejacklab/open-dsearch'"
      "ejacklab/*" → "repo LIKE 'ejacklab/%'"
      "*" → matches all
    """

def filter_by_repo_glob(
    collection: Collection,
    repo_pattern: str
) -> list[Ticket]
```
- Parse glob pattern (* wildcard)
- Convert to LIKE or startswith filter expression
- Execute query with filter
- Return matching tickets

**L5: Input/Output Spec**
```
Input:
  repo_pattern: "ejacklab/*"

Output:
  [
    Ticket(id="C1", repo="ejacklab/open-dsearch", ...),
    Ticket(id="C2", repo="ejacklab/vtic", ...),
    Ticket(id="C3", repo="ejacklab/other-repo", ...),
  ]

Edge cases:
  - "*" → return all repos
  - "ejacklab/open-dsearch" → exact match only
```

**L6: Test Cases**
```python
def test_repo_glob_star_matches_all_in_org():
    """Pattern 'ejacklab/*' matches all ejacklab repos"""
    
def test_repo_exact_match():
    """Exact repo name matches only that repo"""
    
def test_repo_glob_star_matches_all():
    """Pattern '*' matches all repos"""
```

---

## STORAGE (6 Core Features)

---

### L1: Storage
### L2: Markdown Files
### L3: Hierarchical Directory Structure

**L4: Implementation Unit**
```python
class TicketPathResolver:
    """Resolves ticket IDs to file paths and vice versa"""
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
    
    def ticket_to_path(self, ticket_id: str, owner: str, repo: str, category: str) -> Path:
        """
        Convert ticket metadata to file path.
        
        Format: {base_dir}/tickets/{owner}/{repo}/{category}/{ticket_id}.md
        Example: /data/tickets/ejacklab/open-dsearch/crash/C42.md
        """
    
    def path_to_ticket_info(self, path: Path) -> dict:
        """
        Extract ticket metadata from path.
        
        Returns: {"id": "C42", "owner": "ejacklab", "repo": "open-dsearch", "category": "crash"}
        """
    
    def ensure_ticket_dir(self, owner: str, repo: str, category: str) -> Path:
        """Create directory structure if not exists"""
```
- Construct path from components
- Validate path components (no path traversal)
- Create directories as needed
- Parse path back to components

**L5: Input/Output Spec**
```
Input:
  ticket_id: "C42"
  owner: "ejacklab"
  repo: "open-dsearch"
  category: "crash"
  base_dir: Path("/data")

Output:
  Path("/data/tickets/ejacklab/open-dsearch/crash/C42.md")

Error cases:
  - Invalid characters in owner/repo/category → raise InvalidPathComponentError
  - Path traversal attempt → raise SecurityError
```

**L6: Test Cases**
```python
def test_ticket_to_path_correct_format():
    """Ticket ID converts to correct nested path"""
    
def test_path_to_ticket_info_extracts_components():
    """Path parses back to owner/repo/category/id"""
    
def test_ensure_ticket_dir_creates_missing_dirs():
    """Missing directories are created"""
    
def test_rejects_path_traversal():
    """Paths with .. or / in components are rejected"""
```

---

### L1: Storage
### L2: Markdown Files
### L3: Human-Readable Markdown Format

**L4: Implementation Unit**
```python
@dataclass
class Ticket:
    id: str
    title: str
    repo: str
    owner: str
    category: str
    severity: str
    status: str
    description: str
    created: datetime
    updated: datetime
    tags: list[str] = field(default_factory=list)
    fix: str | None = None

def serialize_ticket_to_markdown(ticket: Ticket) -> str:
    """
    Convert Ticket object to markdown string with YAML frontmatter.
    
    Format:
    ---
    id: C42
    title: CORS wildcard allows any origin
    repo: ejacklab/open-dsearch
    owner: ejacklab
    category: security
    severity: critical
    status: open
    created: 2024-01-15T10:30:00Z
    updated: 2024-01-15T10:30:00Z
    tags:
      - cors
      - security
    ---
    
    ## Description
    
    The CORS configuration uses wildcard...
    
    ## Fix
    
    <optional fix content>
    """

def parse_markdown_to_ticket(content: str) -> Ticket:
    """
    Parse markdown file content to Ticket object.
    
    - Extract YAML frontmatter between --- markers
    - Parse description and fix sections
    - Validate required fields
    """
```
- Use PyYAML for frontmatter parsing
- Preserve markdown formatting in description
- Handle optional sections gracefully
- Validate all required fields present

**L5: Input/Output Spec**
```
Input (serialize):
  Ticket(id="C42", title="CORS wildcard", ...)

Output (serialize):
  "---\\nid: C42\\ntitle: CORS wildcard\\n...\\n---\\n\\n## Description\\n..."

Input (parse):
  markdown string with frontmatter

Output (parse):
  Ticket object with all fields populated

Error cases:
  - Missing frontmatter → raise MalformedTicketError
  - Missing required field → raise MissingRequiredFieldError
  - Invalid YAML → raise YAMLParseError with line number
```

**L6: Test Cases**
```python
def test_serialize_ticket_includes_all_fields():
    """Serialized markdown contains all ticket fields"""
    
def test_parse_markdown_extracts_frontmatter():
    """YAML frontmatter parses to dict correctly"""
    
def test_parse_handles_optional_sections():
    """Missing fix/refs sections don't cause errors"""
    
def test_roundtrip_preserves_data():
    """Ticket → markdown → Ticket preserves all data"""
    
def test_missing_required_field_raises_error():
    """Missing id/title/repo raises clear error"""
```

---

### L1: Storage
### L2: Markdown Files
### L3: Git Compatibility

**L4: Implementation Unit**
```python
class GitCompatibleStorage:
    """Ensures all file operations are git-friendly"""
    
    def create_ticket_file(self, path: Path, content: str) -> None:
        """
        Create ticket file with git-friendly settings.
        - UTF-8 encoding
        - LF line endings
        - Trailing newline
        - 0644 permissions
        """
    
    def update_ticket_file(self, path: Path, content: str) -> None:
        """Update file, preserving git-blame friendliness"""
    
    def get_file_diff_info(self, path: Path) -> dict:
        """
        Return git metadata for file if in repo.
        
        Returns: {
            "tracked": bool,
            "modified": bool,
            "last_commit": str | None,
            "last_author": str | None
        }
        """
```
- Use UTF-8 encoding consistently
- Normalize to LF line endings
- Add trailing newline (POSIX standard)
- Avoid binary content in markdown
- Preserve file mode

**L5: Input/Output Spec**
```
Input:
  path: Path("tickets/ejacklab/open-dsearch/crash/C42.md")
  content: "---\\nid: C42\\n..."

Output:
  File written with:
  - UTF-8 encoding
  - LF line endings (even on Windows)
  - Trailing newline
  - Readable by git diff/blame

Verification:
  - git diff shows clean line-by-line changes
  - git blame can attribute lines
```

**L6: Test Cases**
```python
def test_file_uses_utf8_encoding():
    """File is written with UTF-8 encoding"""
    
def test_file_uses_lf_line_endings():
    """Line endings are LF regardless of OS"""
    
def test_file_has_trailing_newline():
    """File ends with newline character"""
    
def test_file_is_git_diff_friendly():
    """git diff shows clean line changes"""
    
def test_unicode_content_preserved():
    """Unicode characters in description preserved correctly"""
```

---

### L1: Storage
### L2: Markdown Files
### L3: Atomic Writes

**L4: Implementation Unit**
```python
class AtomicFileWriter:
    """Write files atomically to prevent corruption"""
    
    def __init__(self, target_path: Path):
        self.target_path = target_path
        self.temp_path = target_path.with_suffix('.tmp')
    
    def write(self, content: str) -> None:
        """
        Write content atomically.
        
        1. Write to temp file in same directory
        2. Sync to disk (fsync)
        3. Atomic rename temp → target
        """
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            # Clean up temp file on error
            self.temp_path.unlink(missing_ok=True)
        return False

def atomic_write(path: Path, content: str) -> None:
    """Convenience function for atomic writes"""
```
- Write to temp file first
- Call fsync to ensure data on disk
- Use atomic rename (os.replace)
- Clean up temp file on failure
- Handle concurrent writes (last write wins)

**L5: Input/Output Spec**
```
Input:
  path: Path("tickets/ejacklab/open-dsearch/crash/C42.md")
  content: "---\\nid: C42\\n..."

Behavior:
  1. Create: tickets/.../C42.md.tmp
  2. Write content to .tmp
  3. fsync .tmp
  4. Rename .tmp → C42.md (atomic)

Error cases:
  - Write fails → .tmp deleted, original file unchanged
  - Disk full → .tmp deleted, original unchanged
  - Crash mid-write → On restart, .tmp file can be cleaned up
```

**L6: Test Cases**
```python
def test_atomic_write_creates_target_file():
    """Successful write creates target file"""
    
def test_atomic_write_no_temp_file_left():
    """Temp file is cleaned up after successful write"""
    
def test_atomic_write_survives_crash_simulation():
    """Simulated crash leaves temp file, original intact"""
    
def test_concurrent_writes_dont_corrupt():
    """Multiple simultaneous writes don't produce mixed content"""
    
def test_partial_write_rollback():
    """Exception during write leaves original file intact"""
```

---

### L1: Storage
### L2: Zvec Index
### L3: In-Process Zvec Index

**L4: Implementation Unit**
```python
from zvec import LocalIndex, Collection
from zvec.embeddings import BM25EmbeddingFunction

class TicketIndex:
    """In-process Zvec index for ticket search"""
    
    def __init__(self, index_dir: Path):
        """
        Initialize or load index from disk.
        
        Index stored at: {index_dir}/.vtic/zvec_index/
        """
        self.index_dir = index_dir / ".vtic"
        self.index = LocalIndex(str(self.index_dir))
        self.collection: Collection | None = None
        self.bm25_ef: BM25EmbeddingFunction | None = None
    
    def initialize(self) -> None:
        """
        Create or load collection with BM25 embedding function.
        
        - Create .vtic directory if needed
        - Initialize LocalIndex
        - Create/get "tickets" collection
        - Set up BM25EmbeddingFunction
        """
    
    def is_initialized(self) -> bool:
        """Check if index is ready for queries"""
    
    def get_collection(self) -> Collection:
        """Get tickets collection, raise if not initialized"""
```
- No separate server process required
- Index runs in same Python process
- Persistent on disk
- Load on demand

**L5: Input/Output Spec**
```
Input:
  index_dir: Path("/data/tickets")

Behavior:
  1. Check if .vtic/zvec_index exists
  2. If exists → load existing index
  3. If not → create new index
  4. Initialize BM25 embedding function
  5. Collection ready for queries

Output:
  TicketIndex instance with:
  - index: LocalIndex (zvec)
  - collection: Collection ("tickets")
  - bm25_ef: BM25EmbeddingFunction

Error cases:
  - Index corrupted → raise IndexCorruptedError (suggest rebuild)
  - Permission denied → raise PermissionError
```

**L6: Test Cases**
```python
def test_index_initializes_in_vtic_dir():
    """Index created in .vtic subdirectory"""
    
def test_index_persists_across_restarts():
    """Index data survives process restart"""
    
def test_index_no_separate_server_needed():
    """All operations work in-process"""
    
def test_index_detects_corruption():
    """Corrupted index raises specific error"""
```

---

### L1: Storage
### L2: Zvec Index
### L3: Rebuild Index from Source

**L4: Implementation Unit**
```python
class IndexRebuilder:
    """Rebuild Zvec index from markdown source files"""
    
    def __init__(self, index: TicketIndex, path_resolver: TicketPathResolver):
        self.index = index
        self.path_resolver = path_resolver
    
    def rebuild(self, progress_callback: Callable[[int, int], None] | None = None) -> int:
        """
        Rebuild entire index from source markdown files.
        
        Steps:
        1. Clear existing collection
        2. Scan all .md files in tickets directory
        3. Parse each ticket
        4. Add to collection with BM25 embedding
        5. Persist index
        
        Args:
            progress_callback: Optional callback(current, total)
        
        Returns:
            Number of tickets indexed
        """
    
    def rebuild_incremental(self, changed_files: list[Path]) -> int:
        """
        Rebuild only specified files (for incremental updates).
        
        Not Core but useful foundation.
        """
```
- Full scan of tickets directory
- Parse each markdown file
- Clear existing index
- Re-add all tickets with embeddings
- Report progress for large datasets

**L5: Input/Output Spec**
```
Input:
  index: TicketIndex instance
  tickets_dir: Path("/data/tickets")

Behavior:
  1. Delete existing collection data
  2. Find all *.md files under tickets/
  3. For each file:
     - Parse markdown to Ticket
     - Generate BM25 embedding
     - Add to collection
  4. Persist index to disk
  5. Return count of indexed tickets

Output:
  42  # Number of tickets indexed

Progress callback example:
  progress_callback(10, 42)  # Processing 10th of 42 files

Error cases:
  - Malformed ticket file → skip with warning, continue
  - No tickets found → return 0, index still valid
  - Disk full during rebuild → raise error, old index may be corrupted
```

**L6: Test Cases**
```python
def test_rebuild_clears_existing_index():
    """Rebuild starts fresh, old data removed"""
    
def test_rebuild_indexes_all_tickets():
    """All .md files in tickets dir are indexed"""
    
def test_rebuild_skips_malformed_files():
    """Malformed files are skipped with warning, not fatal"""
    
def test_rebuild_progress_callback():
    """Progress callback receives current/total counts"""
    
def test_rebuild_empty_dir_returns_zero():
    """Empty tickets directory results in empty index"""
    
def test_rebuild_makes_searchable():
    """After rebuild, search finds expected tickets"""
```

---

## Summary

| Category | L2 Sub-category | L3 Feature | L4 Key Function/Class |
|----------|-----------------|------------|----------------------|
| Search | BM25 Search | Full-text Search | `bm25_search()` |
| Search | Filters & Facets | Equality Filters | `build_filter_expression()`, `apply_equality_filters()` |
| Search | Sorting & Pagination | Sort by Field | `sort_tickets_by_field()`, `SortSpec` |
| Search | Sorting & Pagination | Sort by Relevance | `sort_by_relevance()`, `search_with_relevance_sort()` |
| Search | Sorting & Pagination | Limit/Offset Pagination | `paginate_results()`, `PaginatedResult` |
| Search | BM25 Search | Repo Glob Filter | `parse_repo_glob()`, `filter_by_repo_glob()` |
| Storage | Markdown Files | Hierarchical Directory Structure | `TicketPathResolver` |
| Storage | Markdown Files | Human-Readable Markdown Format | `serialize_ticket_to_markdown()`, `parse_markdown_to_ticket()` |
| Storage | Markdown Files | Git Compatibility | `GitCompatibleStorage` |
| Storage | Markdown Files | Atomic Writes | `AtomicFileWriter`, `atomic_write()` |
| Storage | Zvec Index | In-Process Zvec Index | `TicketIndex` |
| Storage | Zvec Index | Rebuild Index from Source | `IndexRebuilder.rebuild()` |

---

**Total: 12 features × 6 levels = Complete implementation specification**
