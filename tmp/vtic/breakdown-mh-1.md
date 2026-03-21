# Must Have Features - 6-Level Breakdown

24 Must Have features broken down to implementation-ready specifications.

---

## Feature 1: POST /tickets

### L1: API
### L2: REST Endpoints
### L3: POST /tickets
### L4: `handle_post_tickets(request: Request, store: TicketStore) -> Response`
  - Parse JSON body from request
  - Validate required fields (title, repo)
  - Generate unique ticket ID via ID generator
  - Generate slug from title
  - Auto-fill timestamps (created, updated)
  - Set default values for optional fields
  - Persist ticket to storage layer
  - Trigger embedding generation (async)
  - Return 201 Created with ticket data in envelope

### L5: Spec
```python
def handle_post_tickets(request: Request, store: TicketStore) -> Response:
    """
    Input: POST /tickets
           Body: {"title": "CORS Bug", "repo": "ejacklab/open-dsearch", "severity": "critical"}
    Output: 201 Created
            {"data": {"id": "C1", "title": "CORS Bug", "repo": "ejacklab/open-dsearch",
                      "severity": "critical", "status": "open", "category": "code",
                      "slug": "cors-bug", "created": "2026-03-17T10:00:00Z",
                      "updated": "2026-03-17T10:00:00Z"}, "meta": {}}
    
    Input: POST /tickets
           Body: {"title": "", "repo": "owner/repo"}
    Output: 400 Bad Request
            {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed",
                       "details": [{"field": "title", "message": "Title is required"}]}}
    
    Input: POST /tickets
           Body: {"title": "Bug"}  # missing repo
    Output: 400 Bad Request
            {"error": {"code": "VALIDATION_ERROR", "message": "Validation failed",
                       "details": [{"field": "repo", "message": "Repo is required"}]}}
    """
```

### L6: Test
```python
test_post_tickets_creates_ticket()
test_post_tickets_returns_201()
test_post_tickets_validates_required_fields()
test_post_tickets_generates_id()
test_post_tickets_generates_slug()
test_post_tickets_sets_timestamps()
test_post_tickets_applies_defaults()
test_post_tickets_triggers_embedding()
test_post_tickets_returns_envelope()
test_post_tickets_missing_body_returns_400()
test_post_tickets_invalid_json_returns_400()
```

---

## Feature 2: GET /tickets/:id

### L1: API
### L2: REST Endpoints
### L3: GET /tickets/:id
### L4: `handle_get_ticket(ticket_id: str, store: TicketStore) -> Response`
  - Extract ticket_id from path parameter
  - Normalize ID (case-insensitive lookup)
  - Fetch ticket from storage
  - Return 404 if not found
  - Return 200 with ticket data in envelope

### L5: Spec
```python
def handle_get_ticket(ticket_id: str, store: TicketStore) -> Response:
    """
    Input: GET /tickets/C1
    Output: 200 OK
            {"data": {"id": "C1", "title": "CORS Bug", ...}, "meta": {}}
    
    Input: GET /tickets/c1  # lowercase
    Output: 200 OK  # case-insensitive match
            {"data": {"id": "C1", ...}, "meta": {}}
    
    Input: GET /tickets/NONEXISTENT
    Output: 404 Not Found
            {"error": {"code": "NOT_FOUND", "message": "Ticket NONEXISTENT not found"}}
    """
```

### L6: Test
```python
test_get_ticket_returns_ticket()
test_get_ticket_returns_200()
test_get_ticket_case_insensitive()
test_get_ticket_not_found_returns_404()
test_get_ticket_returns_envelope()
test_get_ticket_empty_id_returns_404()
```

---

## Feature 3: PATCH /tickets/:id

### L1: API
### L2: REST Endpoints
### L3: PATCH /tickets/:id
### L4: `handle_patch_ticket(ticket_id: str, request: Request, store: TicketStore) -> Response`
  - Parse JSON body for partial updates
  - Fetch existing ticket
  - Return 404 if not found
  - Validate update fields
  - Apply only specified field updates
  - Auto-update `updated` timestamp
  - Persist changes
  - Trigger re-embedding if content changed
  - Return 200 with updated ticket

### L5: Spec
```python
def handle_patch_ticket(ticket_id: str, request: Request, store: TicketStore) -> Response:
    """
    Input: PATCH /tickets/C1
           Body: {"status": "fixed", "severity": "critical"}
    Output: 200 OK
            {"data": {"id": "C1", "status": "fixed", "severity": "critical",
                      "updated": "2026-03-17T11:30:00Z", ...}, "meta": {}}
    
    Input: PATCH /tickets/C1
           Body: {}  # empty update
    Output: 200 OK  # only timestamp updated
            {"data": {"id": "C1", "updated": "2026-03-17T11:30:00Z", ...}, "meta": {}}
    
    Input: PATCH /tickets/NONEXISTENT
           Body: {"status": "fixed"}
    Output: 404 Not Found
            {"error": {"code": "NOT_FOUND", "message": "Ticket NONEXISTENT not found"}}
    
    Input: PATCH /tickets/C1
           Body: {"status": "invalid_status"}
    Output: 400 Bad Request
            {"error": {"code": "VALIDATION_ERROR",
                       "message": "Invalid status: invalid_status"}}
    
    Immutable fields (id, created, repo) ignored or rejected
    """
```

### L6: Test
```python
test_patch_ticket_updates_fields()
test_patch_ticket_returns_200()
test_patch_ticket_not_found_returns_404()
test_patch_ticket_updates_timestamp()
test_patch_ticket_validates_fields()
test_patch_ticket_ignores_immutable_fields()
test_patch_ticket_triggers_reembedding()
test_patch_ticket_empty_body_succeeds()
test_patch_ticket_returns_envelope()
```

---

## Feature 4: DELETE /tickets/:id

### L1: API
### L2: REST Endpoints
### L3: DELETE /tickets/:id
### L4: `handle_delete_ticket(ticket_id: str, request: Request, store: TicketStore) -> Response`
  - Extract ticket_id from path
  - Check for soft/hard delete preference (default: soft)
  - Return 404 if not found
  - Soft delete: move to .trash/, mark status as deleted
  - Hard delete (force=true): permanently remove
  - Remove from Zvec index
  - Return 204 No Content or 200 with confirmation

### L5: Spec
```python
def handle_delete_ticket(ticket_id: str, request: Request, store: TicketStore) -> Response:
    """
    Input: DELETE /tickets/C1
    Output: 200 OK (soft delete)
            {"data": {"id": "C1", "deleted": true, "method": "soft"}, "meta": {}}
    
    Input: DELETE /tickets/C1?force=true
    Output: 200 OK (hard delete)
            {"data": {"id": "C1", "deleted": true, "method": "hard"}, "meta": {}}
    
    Input: DELETE /tickets/NONEXISTENT
    Output: 404 Not Found
            {"error": {"code": "NOT_FOUND", "message": "Ticket NONEXISTENT not found"}}
    """
```

### L6: Test
```python
test_delete_ticket_soft_delete_succeeds()
test_delete_ticket_returns_200()
test_delete_ticket_not_found_returns_404()
test_delete_ticket_force_permanently_removes()
test_delete_ticket_removes_from_index()
test_delete_ticket_moves_to_trash()
test_delete_ticket_returns_envelope()
```

---

## Feature 5: GET /tickets

### L1: API
### L2: REST Endpoints
### L3: GET /tickets
### L4: `handle_list_tickets(request: Request, store: TicketStore, index: ZvecIndex) -> Response`
  - Parse query parameters for filters
  - Support filters: repo, status, severity, category
  - Support repo glob patterns (e.g., "ejacklab/*")
  - Support pagination: limit, offset
  - Support sorting: sort, order
  - Query Zvec index for matching tickets
  - Return paginated list in envelope with meta

### L5: Spec
```python
def handle_list_tickets(request: Request, store: TicketStore, index: ZvecIndex) -> Response:
    """
    Input: GET /tickets
    Output: 200 OK
            {"data": [{"id": "C1", ...}, {"id": "C2", ...}],
             "meta": {"total": 2, "limit": 20, "offset": 0, "has_more": false}}
    
    Input: GET /tickets?status=open&severity=critical
    Output: 200 OK
            {"data": [...], "meta": {"total": 5, ...}}
    
    Input: GET /tickets?repo=ejacklab/*&limit=10&offset=0
    Output: 200 OK
            {"data": [...], "meta": {"total": 45, "limit": 10, "offset": 0, "has_more": true}}
    
    Input: GET /tickets?sort=-created
    Output: 200 OK (sorted by created descending)
    
    Input: GET /tickets (empty database)
    Output: 200 OK
            {"data": [], "meta": {"total": 0, "limit": 20, "offset": 0, "has_more": false}}
    """
```

### L6: Test
```python
test_list_tickets_returns_list()
test_list_tickets_returns_200()
test_list_tickets_filters_by_status()
test_list_tickets_filters_by_severity()
test_list_tickets_filters_by_category()
test_list_tickets_filters_by_repo()
test_list_tickets_supports_repo_glob()
test_list_tickets_paginates_results()
test_list_tickets_sorts_by_field()
test_list_tickets_empty_returns_empty_list()
test_list_tickets_returns_envelope()
test_list_tickets_meta_includes_total()
```

---

## Feature 6: POST /search

### L1: API
### L2: REST Endpoints
### L3: POST /search
### L4: `handle_search_tickets(request: Request, index: ZvecIndex) -> Response`
  - Parse JSON body with query and options
  - Support query types: keyword (BM25), semantic, hybrid
  - Apply filters from request body
  - Combine BM25 and semantic results for hybrid
  - Sort by relevance by default, or specified field
  - Support pagination
  - Return scored results in envelope

### L5: Spec
```python
@dataclass
class SearchRequest:
    query: str
    mode: str = "hybrid"  # "keyword", "semantic", "hybrid"
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20
    offset: int = 0
    sort: Optional[str] = None  # "-relevance" (default), "created", "-severity"

def handle_search_tickets(request: Request, index: ZvecIndex) -> Response:
    """
    Input: POST /search
           Body: {"query": "CORS error", "mode": "hybrid", "limit": 10}
    Output: 200 OK
            {"data": [{"id": "C1", "title": "...", "score": 0.95},
                      {"id": "S2", "title": "...", "score": 0.82}],
             "meta": {"total": 15, "mode": "hybrid", "limit": 10, "offset": 0}}
    
    Input: POST /search
           Body: {"query": "authentication", "mode": "semantic"}
    Output: 200 OK (semantic search results)
    
    Input: POST /search
           Body: {"query": "CORS", "mode": "keyword"}
    Output: 200 OK (BM25 search results)
    
    Input: POST /search
           Body: {"query": "", "mode": "hybrid"}
    Output: 400 Bad Request
            {"error": {"code": "VALIDATION_ERROR", "message": "Query cannot be empty"}}
    """
```

### L6: Test
```python
test_search_returns_results()
test_search_returns_200()
test_search_hybrid_mode()
test_search_keyword_mode()
test_search_semantic_mode()
test_search_applies_filters()
test_search_paginates_results()
test_search_sorts_by_relevance()
test_search_empty_query_returns_400()
test_search_no_results_returns_empty()
test_search_returns_envelope()
test_search_includes_scores()
```

---

## Feature 7: GET /health

### L1: API
### L2: REST Endpoints
### L3: GET /health
### L4: `handle_health_check(store: TicketStore, index: ZvecIndex) -> Response`
  - Check storage availability
  - Check Zvec index status
  - Check embedding provider status (if configured)
  - Return healthy/unhealthy status
  - Include version and uptime info
  - Return 200 for healthy, 503 for unhealthy

### L5: Spec
```python
def handle_health_check(store: TicketStore, index: ZvecIndex) -> Response:
    """
    Input: GET /health
    Output: 200 OK (all systems healthy)
            {"data": {"status": "healthy",
                      "checks": {"storage": "ok", "index": "ok", "embedding": "ok"},
                      "version": "0.1.0", "uptime_seconds": 3600},
             "meta": {}}
    
    Input: GET /health (index corrupted)
    Output: 503 Service Unavailable
            {"data": {"status": "unhealthy",
                      "checks": {"storage": "ok", "index": "error: corrupted",
                                 "embedding": "ok"},
                      "version": "0.1.0"},
             "meta": {}}
    
    Input: GET /health?detailed=true
    Output: 200 OK (with additional details)
            {"data": {"status": "healthy", "checks": {...},
                      "details": {"ticket_count": 150, "index_size_mb": 2.5}},
             "meta": {}}
    """
```

### L6: Test
```python
test_health_returns_200_when_healthy()
test_health_returns_503_when_unhealthy()
test_health_checks_storage()
test_health_checks_index()
test_health_checks_embedding_provider()
test_health_includes_version()
test_health_includes_uptime()
test_health_detailed_includes_counts()
test_health_returns_envelope()
```

---

## Feature 8: Consistent Envelope

### L1: API
### L2: Response Formats
### L3: Consistent envelope
### L4: `wrap_response(data: Any, meta: Optional[Dict] = None) -> Dict`
  - Wrap all successful responses in `{data: ..., meta: ...}`
  - Wrap all error responses in `{error: {code, message, details}}`
  - Include request_id in meta for tracing
  - Include timestamp in meta
  - Support both single object and list data

### L5: Spec
```python
def wrap_response(data: Any, meta: Optional[Dict] = None, request_id: str = None) -> Dict:
    """
    Input: data = {"id": "C1", "title": "Bug"}
    Output: {"data": {"id": "C1", "title": "Bug"},
             "meta": {"request_id": "req-123", "timestamp": "2026-03-17T10:00:00Z"}}
    
    Input: data = [{"id": "C1"}, {"id": "C2"}], meta = {"total": 2}
    Output: {"data": [{"id": "C1"}, {"id": "C2"}],
             "meta": {"total": 2, "request_id": "req-123", "timestamp": "..."}}
    
    Input: error = ValidationError("Title required")
    Output: {"error": {"code": "VALIDATION_ERROR", "message": "Title required",
                       "details": [{"field": "title", "message": "Title required"}]}}
    
    Input: error = NotFoundError("Ticket C99 not found")
    Output: {"error": {"code": "NOT_FOUND", "message": "Ticket C99 not found"}}
    """

def wrap_error(code: str, message: str, details: Optional[List] = None) -> Dict:
    """
    Create standardized error envelope.
    """
```

### L6: Test
```python
test_wrap_response_single_object()
test_wrap_response_list()
test_wrap_response_includes_meta()
test_wrap_response_includes_request_id()
test_wrap_response_includes_timestamp()
test_wrap_error_creates_error_envelope()
test_wrap_error_includes_code()
test_wrap_error_includes_message()
test_wrap_error_includes_details()
test_all_api_endpoints_use_envelope()
```

---

## Feature 9: API Ticket Creation

### L1: Ticket Lifecycle
### L2: Create
### L3: API ticket creation
### L4: `create_ticket_from_api(payload: Dict[str, Any], store: TicketStore) -> Ticket`
  - Parse JSON payload into ticket data
  - Validate required fields (title, repo)
  - Generate ID, slug, timestamps
  - Set defaults for missing optional fields
  - Persist to storage
  - Queue embedding generation
  - Return created ticket

### L5: Spec
```python
def create_ticket_from_api(payload: Dict[str, Any], store: TicketStore) -> Ticket:
    """
    Input: {"title": "CORS Bug", "repo": "ejacklab/open-dsearch", "severity": "critical"}
    Output: Ticket(id="C1", title="CORS Bug", repo="ejacklab/open-dsearch",
                   severity="critical", status="open", category="code",
                   slug="cors-bug", created="2026-03-17T10:00:00Z",
                   updated="2026-03-17T10:00:00Z")
    
    Input: {"title": "", "repo": "owner/repo"}
    Error: ValidationError("Title is required")
    
    Input: {"title": "Bug"}  # missing repo
    Error: ValidationError("Repo is required")
    
    Input: {"title": "Bug", "repo": "invalid-format"}
    Error: ValidationError("Repo must be in format 'owner/repo'")
    
    Default values:
    - status: "open"
    - category: "code"
    - severity: "medium"
    - tags: []
    - file_refs: []
    """
```

### L6: Test
```python
test_create_ticket_from_api_valid()
test_create_ticket_from_api_generates_id()
test_create_ticket_from_api_generates_slug()
test_create_ticket_from_api_sets_timestamps()
test_create_ticket_from_api_applies_defaults()
test_create_ticket_from_api_validates_required_fields()
test_create_ticket_from_api_validates_repo_format()
test_create_ticket_from_api_queues_embedding()
test_create_ticket_from_api_persists_to_storage()
```

---

## Feature 10: ID Slug from Title

### L1: Ticket Lifecycle
### L2: Create
### L3: ID slug from title
### L4: `generate_slug_from_title(title: str, max_length: int = 50) -> str`
  - Convert title to lowercase
  - Replace spaces with hyphens
  - Remove non-alphanumeric characters (except hyphens)
  - Collapse consecutive hyphens
  - Strip leading/trailing hyphens
  - Truncate to max_length
  - Handle empty/whitespace-only titles

### L5: Spec
```python
def generate_slug_from_title(title: str, max_length: int = 50) -> str:
    """
    Input: "CORS Wildcard Bug"
    Output: "cors-wildcard-bug"
    
    Input: "Fix: API Rate Limiting!!!"
    Output: "fix-api-rate-limiting"
    
    Input: "  Multiple   Spaces  "
    Output: "multiple-spaces"
    
    Input: "Test @#$% Special!!! Characters"
    Output: "test-special-characters"
    
    Input: "A" * 100  # very long title
    Output: "aaa..." (truncated to 50 chars)
    
    Input: ""
    Output: "untitled"
    
    Input: "   "  # whitespace only
    Output: "untitled"
    
    Input: "@#$%!"  # no alphanumeric chars
    Output: "untitled"
    """
```

### L6: Test
```python
test_generate_slug_lowercase()
test_generate_slug_spaces_to_hyphens()
test_generate_slug_removes_special_chars()
test_generate_slug_collapses_hyphens()
test_generate_slug_strips_hyphens()
test_generate_slug_truncates_long_titles()
test_generate_slug_empty_returns_untitled()
test_generate_slug_whitespace_only_returns_untitled()
test_generate_slug_no_alphanumeric_returns_untitled()
test_generate_slug_preserves_numbers()
test_generate_slug_handles_unicode()
```

---

## Feature 11: Output Formats CLI

### L1: CLI
### L2: Output Formats
### L3: Output formats CLI
### L4: `format_ticket_output(ticket: Ticket, format: str) -> str`
### L4: `format_tickets_list(tickets: List[Ticket], format: str) -> str`
  - Support formats: table, json, markdown, yaml
  - Table: human-readable with columns and borders
  - JSON: compact single-line or pretty with --pretty
  - Markdown: formatted for documentation
  - YAML: config-friendly format
  - Output to stdout
  - Validate format string, error on invalid

### L5: Spec
```python
def format_ticket_output(ticket: Ticket, format: str, pretty: bool = False) -> str:
    """
    Input: ticket, format="table"
    Output: 
    +------+------------+----------+--------+
    | ID   | Title      | Status   | Repo   |
    +------+------------+----------+--------+
    | C1   | CORS Bug   | open     | o-d    |
    +------+------------+----------+--------+
    
    Input: ticket, format="json"
    Output: {"id":"C1","title":"CORS Bug","status":"open","repo":"o-d"}
    
    Input: ticket, format="json", pretty=True
    Output:
    {
      "id": "C1",
      "title": "CORS Bug",
      "status": "open",
      "repo": "o-d"
    }
    
    Input: ticket, format="markdown"
    Output:
    ## C1: CORS Bug
    - **Status:** open
    - **Repo:** o-d
    
    Input: ticket, format="yaml"
    Output:
    id: C1
    title: CORS Bug
    status: open
    repo: o-d
    
    Input: ticket, format="invalid"
    Error: ValueError("Unknown format: invalid. Use: table, json, markdown, yaml")
    """

def format_tickets_list(tickets: List[Ticket], format: str) -> str:
    """
    Format multiple tickets for list output.
    
    Input: [ticket1, ticket2], format="table"
    Output: Table with multiple rows
    
    Input: [ticket1, ticket2], format="json"
    Output: [{"id":"C1",...},{"id":"C2",...}]
    """
```

### L6: Test
```python
test_format_ticket_table()
test_format_ticket_json()
test_format_ticket_json_pretty()
test_format_ticket_markdown()
test_format_ticket_yaml()
test_format_ticket_invalid_raises()
test_format_tickets_list_table()
test_format_tickets_list_json()
test_format_tickets_list_empty()
test_format_output_writes_to_stdout()
```

---

## Feature 12: API PATCH Endpoint

### L1: Ticket Lifecycle
### L2: Update
### L3: API PATCH endpoint
### L4: `apply_ticket_patch(ticket_id: str, patch: Dict[str, Any], store: TicketStore) -> Ticket`
  - Fetch existing ticket
  - Raise NotFoundError if not found
  - Validate patch fields against schema
  - Merge patch into existing ticket (partial update)
  - Update `updated` timestamp
  - Persist changes
  - Trigger re-embedding if content fields changed
  - Return updated ticket

### L5: Spec
```python
def apply_ticket_patch(ticket_id: str, patch: Dict[str, Any], store: TicketStore) -> Ticket:
    """
    Input: ticket_id="C1", patch={"status": "fixed", "severity": "critical"}
    Output: Ticket(id="C1", status="fixed", severity="critical",
                   updated="2026-03-17T11:30:00Z", ...other fields preserved)
    
    Input: ticket_id="C1", patch={"tags": ["urgent", "backend"]}
    Output: Ticket(..., tags=["urgent", "backend"], ...)
    
    Input: ticket_id="C1", patch={"description": null}
    Output: Ticket(..., description=None, ...)  # clears field
    
    Input: ticket_id="NONEXISTENT", patch={...}
    Error: NotFoundError("Ticket NONEXISTENT not found")
    
    Input: ticket_id="C1", patch={"status": "invalid"}
    Error: ValidationError("Invalid status: invalid")
    
    Input: ticket_id="C1", patch={"id": "NEW_ID"}
    Output: Ticket(..., id="C1", ...)  # id ignored (immutable)
    
    Input: ticket_id="C1", patch={}
    Output: Ticket(..., updated="2026-03-17T11:30:00Z", ...)  # only timestamp
    """
```

### L6: Test
```python
test_apply_ticket_patch_single_field()
test_apply_ticket_patch_multiple_fields()
test_apply_ticket_patch_preserves_unmodified()
test_apply_ticket_patch_updates_timestamp()
test_apply_ticket_patch_validates_fields()
test_apply_ticket_patch_ticket_not_found_raises()
test_apply_ticket_patch_clears_field_with_null()
test_apply_ticket_patch_ignores_immutable_fields()
test_apply_ticket_patch_empty_only_timestamp()
test_apply_ticket_patch_triggers_reembedding()
```

---

## Feature 13: Soft Delete by Default

### L1: Ticket Lifecycle
### L2: Delete
### L3: Soft delete by default
### L4: `soft_delete_ticket(ticket_id: str, store: TicketStore) -> bool`
  - Move ticket file from tickets/ to .trash/
  - Update ticket status to "deleted"
  - Keep ticket in Zvec index but mark as deleted
  - Preserve all ticket data for recovery
  - Return True if successful, False if not found

### L5: Spec
```python
def soft_delete_ticket(ticket_id: str, store: TicketStore) -> bool:
    """
    Input: ticket_id="C1", store with C1 existing
    Actions:
      - Move tickets/owner/repo/code/C1.md to .trash/owner/repo/code/C1.md
      - Update ticket status to "deleted"
      - Mark as deleted in Zvec index (exclude from search)
    Output: True
    
    Input: ticket_id="C1", store with C1, .trash/ doesn't exist
    Actions:
      - Create .trash/ directory
      - Move ticket to .trash/
    Output: True
    
    Input: ticket_id="NONEXISTENT", store
    Output: False  # no exception
    
    Soft-deleted tickets:
    - Not returned in GET /tickets (filtered out)
    - Not searchable
    - Can be restored via restore command
    - File preserved with original content
    """
```

### L6: Test
```python
test_soft_delete_moves_to_trash()
test_soft_delete_updates_status()
test_soft_delete_removes_from_search()
test_soft_delete_returns_true()
test_soft_delete_not_found_returns_false()
test_soft_delete_creates_trash_dir()
test_soft_delete_preserves_file_content()
test_soft_delete_excludes_from_list()
test_soft_delete_can_be_restored()
test_soft_delete_multiple_tickets()
```

---

## Feature 14: Confirmation Prompt

### L1: Ticket Lifecycle
### L2: Delete
### L3: Confirmation prompt
### L4: `prompt_delete_confirmation(ticket_id: str, force: bool = False) -> bool`
  - Display ticket summary before deletion
  - Prompt user for confirmation
  - Accept y/yes/ENTER as confirmation
  - Accept n/no/q/CTRL+C as cancellation
  - Skip prompt if --yes flag provided
  - Skip prompt if force=True (hard delete still needs confirmation unless --yes)
  - Return True if confirmed, False if cancelled

### L5: Spec
```python
def prompt_delete_confirmation(ticket_id: str, force: bool = False, 
                                skip: bool = False, input_fn=input) -> bool:
    """
    Input: ticket_id="C1", force=False, skip=False
    Output (stdout):
      About to delete ticket C1: "CORS Bug"
      Status: open, Severity: critical
      Move to: .trash/C1.md
      Confirm? [y/N]: 
    Input (user): "y"
    Return: True
    
    Input: ticket_id="C1", force=True, skip=False
    Output (stdout):
      About to PERMANENTLY delete ticket C1: "CORS Bug"
      This cannot be undone!
      Confirm? [y/N]:
    Input (user): "n"
    Return: False
    
    Input: ticket_id="C1", skip=True
    Output: (no prompt)
    Return: True
    
    Input: ticket_id="C1", force=False, skip=False
    Input (user): "" (ENTER)
    Return: True  # default is yes
    
    Input: ticket_id="C1", force=False, skip=False
    Input (user): "q"
    Return: False
    """
```

### L6: Test
```python
test_prompt_delete_confirmation_shows_summary()
test_prompt_delete_confirmation_accepts_y()
test_prompt_delete_confirmation_accepts_yes()
test_prompt_delete_confirmation_accepts_enter()
test_prompt_delete_confirmation_rejects_n()
test_prompt_delete_confirmation_rejects_no()
test_prompt_delete_confirmation_skip_flag_bypasses()
test_prompt_delete_confirmation_force_shows_warning()
test_prompt_delete_confirmation_force_requires_confirmation()
test_prompt_delete_confirmation_ctrl_c_cancels()
```

---

## Feature 15: Semantic Query

### L1: Search
### L2: Semantic Search
### L3: Semantic query
### L4: `execute_semantic_search(query: str, index: ZvecIndex, options: SearchOptions) -> List[SearchResult]`
  - Generate embedding for query text
  - Perform vector similarity search in Zvec
  - Return top-k most similar tickets
  - Apply filters to results
  - Include similarity score (0-1)
  - Support result pagination

### L5: Spec
```python
def execute_semantic_search(query: str, index: ZvecIndex, 
                            options: SearchOptions) -> List[SearchResult]:
    """
    Input: query="authentication fails randomly", options=SearchOptions(limit=10)
    Actions:
      - Generate embedding for query using configured provider
      - Search Zvec index for similar vectors
      - Apply filters (if any)
      - Return top 10 results
    Output: [
      SearchResult(id="C5", ticket=Ticket(...), score=0.92),
      SearchResult(id="S2", ticket=Ticket(...), score=0.87),
      SearchResult(id="C12", ticket=Ticket(...), score=0.81),
      ...
    ]
    
    Input: query="database connection timeout", 
           options=SearchOptions(filters={"severity": "critical"}, limit=5)
    Output: [SearchResult(...), ...]  # only critical tickets
    
    Input: query="", options=...
    Error: ValueError("Query cannot be empty")
    
    Input: query="...", options=SearchOptions(limit=0)
    Error: ValueError("Limit must be positive")
    
    Input: query="...", embedding_provider=None
    Error: EmbeddingNotConfiguredError("Semantic search requires an embedding provider")
    """
```

### L6: Test
```python
test_execute_semantic_search_returns_results()
test_execute_semantic_search_includes_scores()
test_execute_semantic_search_applies_filters()
test_execute_semantic_search_respects_limit()
test_execute_semantic_search_paginates()
test_execute_semantic_search_empty_query_raises()
test_execute_semantic_search_no_provider_raises()
test_execute_semantic_search_no_results_returns_empty()
test_execute_semantic_search_scores_in_range()
test_execute_semantic_search_ranked_by_similarity()
```

---

## Feature 16: Embedding on Write

### L1: Search
### L2: Semantic Search
### L3: Embedding on write
### L4: `embed_ticket_content(ticket: Ticket, provider: EmbeddingProvider) -> EmbeddingResult`
### L4: `queue_embedding_task(ticket_id: str, queue: TaskQueue) -> None`
  - Extract text content from ticket (title + description)
  - Send to embedding provider
  - Store embedding vector in Zvec index
  - Handle embedding failures gracefully
  - Queue async embedding for API writes
  - Sync embedding for CLI writes (with progress)

### L5: Spec
```python
def embed_ticket_content(ticket: Ticket, provider: EmbeddingProvider) -> EmbeddingResult:
    """
    Input: Ticket(id="C1", title="CORS Bug", 
                  description="Wildcard CORS header allows any origin")
    Actions:
      - Combine title + description
      - Call provider.embed(combined_text)
      - Return embedding vector
    Output: EmbeddingResult(vector=[0.1, -0.2, ...], model="text-embedding-3-small")
    
    Input: Ticket(id="C1", title="", description="")
    Actions:
      - Use "untitled" as fallback text
    Output: EmbeddingResult(vector=[...], model="...")
    
    Input: Ticket(...), provider=None
    Error: EmbeddingNotConfiguredError("No embedding provider configured")
    
    Input: Ticket(...), provider with rate limit
    Actions:
      - Retry with exponential backoff
      - Log warning
    Output: EmbeddingResult(...) or raise on max retries
    """

def queue_embedding_task(ticket_id: str, queue: TaskQueue) -> None:
    """
    Queue async embedding generation for ticket.
    Used by API endpoints to avoid blocking.
    
    Input: ticket_id="C1", queue
    Actions:
      - Add task to queue: {"type": "embed", "ticket_id": "C1"}
      - Return immediately
    Output: None
    """
```

### L6: Test
```python
test_embed_ticket_content_generates_vector()
test_embed_ticket_content_combines_title_description()
test_embed_ticket_content_handles_empty_content()
test_embed_ticket_content_stores_in_index()
test_embed_ticket_content_no_provider_raises()
test_embed_ticket_content_handles_provider_error()
test_queue_embedding_task_adds_to_queue()
test_queue_embedding_task_returns_immediately()
test_embedding_on_api_write_queues()
test_embedding_on_cli_write_sync()
```

---

## Feature 17: Re-embed All

### L1: Search
### L2: Semantic Search
### L3: Re-embed all
### L4: `reembed_all_tickets(store: TicketStore, provider: EmbeddingProvider, index: ZvecIndex) -> ReembedStats`
  - Scan all ticket files in storage
  - Extract content from each ticket
  - Generate embeddings in batches
  - Update Zvec index with new embeddings
  - Track progress and statistics
  - Handle failures (skip and log, or abort)
  - Support resumable re-indexing

### L5: Spec
```python
@dataclass
class ReembedStats:
    total: int
    success: int
    failed: int
    skipped: int
    duration_seconds: float

def reembed_all_tickets(store: TicketStore, provider: EmbeddingProvider, 
                        index: ZvecIndex, batch_size: int = 10) -> ReembedStats:
    """
    Input: store with 50 tickets, provider, index
    Actions:
      - List all ticket IDs from store
      - For each ticket:
        - Load ticket content
        - Generate embedding
        - Update Zvec index
      - Track progress
      - Show progress bar (CLI) or log progress (API)
    Output: ReembedStats(total=50, success=48, failed=2, skipped=0, duration=12.5)
    
    Input: store with tickets, provider with rate limit
    Actions:
      - Process in batches of 10
      - Wait between batches if rate limited
    Output: ReembedStats(...)
    
    Input: store, provider=None
    Error: EmbeddingNotConfiguredError("Cannot re-embed without provider")
    
    Input: store with 0 tickets
    Output: ReembedStats(total=0, success=0, failed=0, skipped=0, duration=0)
    """
```

### L6: Test
```python
test_reembed_all_tickets_processes_all()
test_reembed_all_tickets_updates_index()
test_reembed_all_tickets_returns_stats()
test_reembed_all_tickets_handles_failures()
test_reembed_all_tickets_batches_requests()
test_reembed_all_tickets_respects_rate_limits()
test_reembed_all_tickets_no_provider_raises()
test_reembed_all_tickets_empty_store()
test_reembed_all_tickets_progress_reporting()
test_reembed_all_tickets_skips_deleted()
```

---

## Feature 18: Combined Query

### L1: Search
### L2: Hybrid Search
### L3: Combined query
### L4: `execute_hybrid_search(query: str, index: ZvecIndex, options: SearchOptions) -> List[SearchResult]`
  - Execute BM25 search for keyword matches
  - Execute semantic search for vector similarity
  - Combine results using Reciprocal Rank Fusion (RRF)
  - Apply configurable weights (default: 0.5 BM25, 0.5 semantic)
  - Deduplicate results (same ticket from both searches)
  - Sort by combined score
  - Apply filters and pagination

### L5: Spec
```python
def execute_hybrid_search(query: str, index: ZvecIndex, 
                          options: SearchOptions) -> List[SearchResult]:
    """
    Input: query="CORS authentication", options=SearchOptions(limit=10)
    Actions:
      1. Execute BM25 search: [C1(score=0.9), S2(score=0.7), C5(score=0.5)]
      2. Execute semantic search: [C5(score=0.95), C1(score=0.8), C8(score=0.6)]
      3. Apply RRF fusion:
         - C1: BM25 rank 1, semantic rank 2 → RRF score
         - C5: BM25 rank 3, semantic rank 1 → RRF score
         - S2: BM25 rank 2 only → RRF score
         - C8: semantic rank 3 only → RRF score
      4. Sort by combined score
      5. Return top 10
    Output: [
      SearchResult(id="C1", score=0.87, bm25_score=0.9, semantic_score=0.8),
      SearchResult(id="C5", score=0.82, bm25_score=0.5, semantic_score=0.95),
      SearchResult(id="S2", score=0.71, bm25_score=0.7, semantic_score=None),
      ...
    ]
    
    Input: query="exact phrase match", options=SearchOptions(weights={"bm25": 0.8, "semantic": 0.2})
    Actions: Apply 80% weight to BM25, 20% to semantic
    
    Input: query="semantic concept only", options=SearchOptions(weights={"bm25": 0.0, "semantic": 1.0})
    Actions: Only use semantic search
    
    Input: query="", options=...
    Error: ValueError("Query cannot be empty")
    """
```

### L6: Test
```python
test_execute_hybrid_search_returns_results()
test_execute_hybrid_search_combines_bm25_semantic()
test_execute_hybrid_search_applies_weights()
test_execute_hybrid_search_deduplicates()
test_execute_hybrid_search_sorts_by_combined_score()
test_execute_hybrid_search_includes_component_scores()
test_execute_hybrid_search_respects_limit()
test_execute_hybrid_search_applies_filters()
test_execute_hybrid_search_empty_query_raises()
test_execute_hybrid_search_rrf_fusion()
```

---

## Feature 19: Repo Glob Patterns

### L1: Search
### L2: Filters
### L3: Repo glob patterns
### L4: `match_repo_glob(repo: str, pattern: str) -> bool`
### L4: `compile_glob_pattern(pattern: str) -> Pattern`
  - Support * wildcard for matching any characters
  - Support ** for matching across path segments
  - Match against full repo path (owner/repo)
  - Case-insensitive matching
  - Cache compiled patterns for performance

### L5: Spec
```python
def match_repo_glob(repo: str, pattern: str) -> bool:
    """
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/*"
    Output: True
    
    Input: repo="ejacklab/cli-tools", pattern="ejacklab/*"
    Output: True
    
    Input: repo="otherorg/repo", pattern="ejacklab/*"
    Output: False
    
    Input: repo="ejacklab/open-dsearch", pattern="*"
    Output: True  # matches all repos
    
    Input: repo="ejacklab/team/backend/api", pattern="ejacklab/team/**"
    Output: True  # ** matches across segments
    
    Input: repo="ejacklab/open-dsearch", pattern="*dsearch"
    Output: True  # matches suffix
    
    Input: repo="EjackLab/Open-Dsearch", pattern="ejacklab/*"
    Output: True  # case-insensitive
    
    Input: repo="ejacklab/open-dsearch", pattern=""
    Output: False  # empty pattern matches nothing
    """

def compile_glob_pattern(pattern: str) -> Pattern:
    """
    Compile glob pattern to regex for efficient matching.
    
    Input: "ejacklab/*"
    Output: Pattern that matches "ejacklab/<anything>"
    """
```

### L6: Test
```python
test_match_repo_glob_star_wildcard()
test_match_repo_glob_double_star()
test_match_repo_glob_exact_match()
test_match_repo_glob_suffix_match()
test_match_repo_glob_case_insensitive()
test_match_repo_glob_empty_pattern()
test_match_repo_glob_all_repos()
test_compile_glob_pattern_caches()
test_match_repo_glob_multiple_patterns()
test_match_repo_glob_in_list_filter()
```

---

## Feature 20: Sort by Field

### L1: Search
### L2: Sorting
### L3: Sort by field
### L4: `sort_tickets_by_field(tickets: List[Ticket], field: str, order: str = "asc") -> List[Ticket]`
  - Sort tickets by specified field
  - Support ascending (-prefix) and descending (default or +prefix)
  - Handle multiple sort fields (primary, secondary)
  - Support fields: created, updated, severity, status, title, id
  - Handle missing/null values (sort to end)
  - Validate field names

### L5: Spec
```python
def sort_tickets_by_field(tickets: List[Ticket], field: str, 
                          order: str = "asc") -> List[Ticket]:
    """
    Input: [Ticket(severity="low"), Ticket(severity="critical"), Ticket(severity="medium")],
           field="severity", order="desc"
    Output: [Ticket(severity="critical"), Ticket(severity="medium"), Ticket(severity="low")]
    
    Input: [Ticket(created="2026-03-17"), Ticket(created="2026-03-15"), ...],
           field="created", order="asc"
    Output: [Ticket(created="2026-03-15"), Ticket(created="2026-03-17"), ...]
    
    Input: tickets, field="-severity"  # descending via prefix
    Output: Same as order="desc"
    
    Input: tickets, field="+created"  # ascending via prefix
    Output: Same as order="asc"
    
    Input: [Ticket(title=None), Ticket(title="Alpha"), Ticket(title="Beta")],
           field="title"
    Output: [Ticket(title="Alpha"), Ticket(title="Beta"), Ticket(title=None)]
    
    Input: tickets, field="invalid_field"
    Error: ValueError("Unknown sort field: invalid_field")
    
    Severity sort order: critical > high > medium > low
    Status sort order: open > in_progress > blocked > fixed > wont_fix > closed
    """
```

### L6: Test
```python
test_sort_tickets_by_field_asc()
test_sort_tickets_by_field_desc()
test_sort_tickets_by_field_prefix_notation()
test_sort_tickets_by_created()
test_sort_tickets_by_updated()
test_sort_tickets_by_severity()
test_sort_tickets_by_status()
test_sort_tickets_by_title()
test_sort_tickets_handles_nulls()
test_sort_tickets_invalid_field_raises()
test_sort_tickets_severity_order()
test_sort_tickets_status_order()
```

---

## Feature 21: Sort by Relevance

### L1: Search
### L2: Sorting
### L3: Sort by relevance
### L4: `sort_by_relevance(results: List[SearchResult]) -> List[SearchResult]`
  - Default sort for search results
  - Sort by combined score (highest first)
  - Handle ties (secondary sort by created desc)
  - Support relevance score from BM25, semantic, or hybrid
  - Exclude relevance sort when no query (no scores)

### L5: Spec
```python
def sort_by_relevance(results: List[SearchResult]) -> List[SearchResult]:
    """
    Input: [
      SearchResult(id="C1", score=0.75, ticket=Ticket(created="2026-03-15")),
      SearchResult(id="C2", score=0.92, ticket=Ticket(created="2026-03-17")),
      SearchResult(id="C3", score=0.92, ticket=Ticket(created="2026-03-10")),
    ]
    Output: [
      SearchResult(id="C3", score=0.92, ...),  # tie, older first
      SearchResult(id="C2", score=0.92, ...),  # tie, newer
      SearchResult(id="C1", score=0.75, ...),  # lower score
    ]
    
    Input: [], sort_by_relevance
    Output: []  # empty list
    
    Input: [SearchResult(id="C1", score=None), ...]
    Output: [...]  # None scores sorted to end
    
    Default behavior:
    - Search with query → sort by relevance (score desc)
    - List without query → sort by created desc
    - Explicit sort param → use specified sort
    """
```

### L6: Test
```python
test_sort_by_relevance_descending()
test_sort_by_relevance_handles_ties()
test_sort_by_relevance_empty_list()
test_sort_by_relevance_none_scores()
test_sort_by_relevance_secondary_sort()
test_sort_by_relevance_default_for_search()
test_sort_by_relevance_not_default_for_list()
```

---

## Feature 22: Atomic Writes

### L1: Storage
### L2: Markdown Files
### L3: Atomic writes
### L4: `atomic_write_file(path: str, content: str) -> None`
  - Write content to temporary file first
  - Use OS-level atomic rename (rename(2))
  - Ensure no partial/corrupted files
  - Handle concurrent write attempts
  - Clean up temp files on failure
  - Preserve file permissions

### L5: Spec
```python
def atomic_write_file(path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Input: path="tickets/owner/repo/code/C1.md", content="---\nid: C1\n..."
    Actions:
      1. Create temp file: tickets/owner/repo/code/.C1.md.tmp
      2. Write content to temp file
      3. Sync temp file to disk (fsync)
      4. Atomic rename: .C1.md.tmp → C1.md
      5. Clean up temp file on any error
    Output: None
    
    Input: path="tickets/new/...", content="..."  # dir doesn't exist
    Actions:
      - Create parent directories
      - Proceed with atomic write
    Output: None
    
    Input: path="tickets/...", content=""  # empty content
    Actions:
      - Write empty file atomically
    Output: None
    
    Input: concurrent writes to same path
    Actions:
      - Last write wins (atomic rename guarantees consistency)
      - No corruption possible
    
    Input: write fails mid-operation
    Actions:
      - Temp file cleaned up
      - Original file unchanged
    """
```

### L6: Test
```python
test_atomic_write_creates_file()
test_atomic_write_uses_temp_file()
test_atomic_write_renames_atomically()
test_atomic_write_creates_parent_dirs()
test_atomic_write_cleans_up_on_failure()
test_atomic_write_preserves_permissions()
test_atomic_write_concurrent_no_corruption()
test_atomic_write_empty_content()
test_atomic_write_overwrites_existing()
test_atomic_write_handles_unicode()
```

---

## Feature 23: Index Co-location

### L1: Storage
### L2: Zvec Index
### L3: Index co-location
### L4: `get_index_path(tickets_dir: str) -> str`
### L4: `initialize_index_storage(tickets_dir: str) -> ZvecIndex`
  - Store Zvec index in `.vtic/` directory within tickets root
  - Create `.vtic/` if it doesn't exist
  - Store index files: `index.zvec`, `metadata.json`
  - Store config: `config.json`
  - Relative to tickets directory for portability

### L5: Spec
```python
def get_index_path(tickets_dir: str) -> str:
    """
    Input: tickets_dir="/home/user/projects/myapp/tickets"
    Output: "/home/user/projects/myapp/tickets/.vtic"
    
    Input: tickets_dir="./tickets"
    Output: "./tickets/.vtic"
    
    Input: tickets_dir="."
    Output: "./.vtic"
    """

def initialize_index_storage(tickets_dir: str) -> ZvecIndex:
    """
    Initialize or load Zvec index from .vtic/ directory.
    
    Input: tickets_dir="/path/to/tickets", .vtic/ exists
    Actions:
      - Load existing index from .vtic/index.zvec
      - Load metadata from .vtic/metadata.json
    Output: ZvecIndex(loaded=True)
    
    Input: tickets_dir="/path/to/tickets", .vtic/ doesn't exist
    Actions:
      - Create .vtic/ directory
      - Create empty index
      - Write initial metadata
    Output: ZvecIndex(loaded=False)
    
    Index files:
    - .vtic/index.zvec      # Zvec index data
    - .vtic/metadata.json   # Index metadata (version, counts, last_update)
    - .vtic/config.json     # Index configuration (embedding model, etc.)
    - .vtic/lock            # Lock file for concurrent access
    """
```

### L6: Test
```python
test_get_index_path_returns_vtic_dir()
test_get_index_path_relative()
test_get_index_path_absolute()
test_initialize_index_storage_creates_vtic_dir()
test_initialize_index_storage_loads_existing()
test_initialize_index_storage_creates_index_file()
test_initialize_index_storage_creates_metadata()
test_index_path_portable_with_relative_paths()
test_index_files_created_correctly()
test_index_co_location_within_tickets()
```

---

## Feature 24: Incremental Indexing

### L1: Storage
### L2: Zvec Index
### L3: Incremental indexing
### L4: `detect_changed_tickets(store: TicketStore, index: ZvecIndex) -> List[str]`
### L4: `incremental_reindex(ticket_ids: List[str], store: TicketStore, index: ZvecIndex) -> ReindexStats`
  - Compare file modification times with index metadata
  - Detect new tickets (not in index)
  - Detect modified tickets (file newer than index)
  - Detect deleted tickets (in index but no file)
  - Only re-index changed tickets
  - Track index version/timestamp

### L5: Spec
```python
def detect_changed_tickets(store: TicketStore, index: ZvecIndex) -> List[str]:
    """
    Detect which tickets need re-indexing.
    
    Input: store with [C1, C2, C3], index with [C1, C2]
    Actions:
      - C1, C2: Check file mtime vs index mtime
      - C3: Not in index → needs indexing
    Output: ["C3"]  # or ["C1", "C3"] if C1 modified
    
    Input: store with [C1], index with [C1, C2, C3]
    Actions:
      - C2, C3: In index but file missing → mark for removal
    Output: []  # for reindex, or return removed list separately
    
    Input: store empty, index empty
    Output: []
    """

def incremental_reindex(ticket_ids: List[str], store: TicketStore, 
                        index: ZvecIndex, provider: EmbeddingProvider) -> ReindexStats:
    """
    Re-index only specified tickets.
    
    Input: ticket_ids=["C1", "C3"], store, index, provider
    Actions:
      - Load C1, C3 from store
      - Generate embeddings
      - Update Zvec index
      - Update index metadata
    Output: ReindexStats(processed=2, success=2, failed=0)
    
    Input: ticket_ids=[], store, index, provider
    Actions: No-op
    Output: ReindexStats(processed=0, ...)
    
    Input: ticket_ids=["C1"], store, index, provider=None
    Actions: Skip embedding, index text only (BM25)
    Output: ReindexStats(processed=1, embedded=0, ...)
    """
```

### L6: Test
```python
test_detect_changed_tickets_new_ticket()
test_detect_changed_tickets_modified_ticket()
test_detect_changed_tickets_deleted_ticket()
test_detect_changed_tickets_unchanged()
test_detect_changed_tickets_empty()
test_incremental_reindex_processes_new()
test_incremental_reindex_processes_modified()
test_incremental_reindex_removes_deleted()
test_incremental_reindex_updates_metadata()
test_incremental_reindex_empty_list()
test_incremental_reindex_without_provider()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | API | REST Endpoints | POST /tickets | `handle_post_tickets()` |
| 2 | API | REST Endpoints | GET /tickets/:id | `handle_get_ticket()` |
| 3 | API | REST Endpoints | PATCH /tickets/:id | `handle_patch_ticket()` |
| 4 | API | REST Endpoints | DELETE /tickets/:id | `handle_delete_ticket()` |
| 5 | API | REST Endpoints | GET /tickets | `handle_list_tickets()` |
| 6 | API | REST Endpoints | POST /search | `handle_search_tickets()` |
| 7 | API | REST Endpoints | GET /health | `handle_health_check()` |
| 8 | API | Response Formats | Consistent envelope | `wrap_response()`, `wrap_error()` |
| 9 | Ticket Lifecycle | Create | API ticket creation | `create_ticket_from_api()` |
| 10 | Ticket Lifecycle | Create | ID slug from title | `generate_slug_from_title()` |
| 11 | CLI | Output Formats | Output formats CLI | `format_ticket_output()`, `format_tickets_list()` |
| 12 | Ticket Lifecycle | Update | API PATCH endpoint | `apply_ticket_patch()` |
| 13 | Ticket Lifecycle | Delete | Soft delete by default | `soft_delete_ticket()` |
| 14 | Ticket Lifecycle | Delete | Confirmation prompt | `prompt_delete_confirmation()` |
| 15 | Search | Semantic Search | Semantic query | `execute_semantic_search()` |
| 16 | Search | Semantic Search | Embedding on write | `embed_ticket_content()`, `queue_embedding_task()` |
| 17 | Search | Semantic Search | Re-embed all | `reembed_all_tickets()` |
| 18 | Search | Hybrid Search | Combined query | `execute_hybrid_search()` |
| 19 | Search | Filters | Repo glob patterns | `match_repo_glob()`, `compile_glob_pattern()` |
| 20 | Search | Sorting | Sort by field | `sort_tickets_by_field()` |
| 21 | Search | Sorting | Sort by relevance | `sort_by_relevance()` |
| 22 | Storage | Markdown Files | Atomic writes | `atomic_write_file()` |
| 23 | Storage | Zvec Index | Index co-location | `get_index_path()`, `initialize_index_storage()` |
| 24 | Storage | Zvec Index | Incremental indexing | `detect_changed_tickets()`, `incremental_reindex()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Tuple
from datetime import datetime

@dataclass
class Ticket:
    id: str
    title: str
    repo: str
    slug: str = ""
    description: Optional[str] = None
    category: str = "code"
    severity: str = "medium"
    status: str = "open"
    tags: List[str] = field(default_factory=list)
    file_refs: List[str] = field(default_factory=list)
    fix: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None

@dataclass
class SearchResult:
    id: str
    ticket: Ticket
    score: float
    bm25_score: Optional[float] = None
    semantic_score: Optional[float] = None

@dataclass
class SearchOptions:
    query: str
    mode: str = "hybrid"
    filters: Dict[str, Any] = field(default_factory=dict)
    limit: int = 20
    offset: int = 0
    sort: Optional[str] = None
    weights: Dict[str, float] = field(default_factory=lambda: {"bm25": 0.5, "semantic": 0.5})

@dataclass
class ReembedStats:
    total: int
    success: int
    failed: int
    skipped: int
    duration_seconds: float

@dataclass
class ReindexStats:
    processed: int
    success: int
    failed: int
    embedded: int

@dataclass
class Response:
    status_code: int
    body: Dict[str, Any]
    headers: Dict[str, str] = field(default_factory=dict)

class TicketStore(Protocol):
    def get(self, ticket_id: str) -> Optional[Ticket]: ...
    def save(self, ticket: Ticket) -> None: ...
    def delete(self, ticket_id: str) -> bool: ...
    def move_to_trash(self, ticket_id: str) -> bool: ...
    def list_ids(self) -> Set[str]: ...
    def list_all(self) -> List[Ticket]: ...

class ZvecIndex(Protocol):
    def search(self, query: str, limit: int, filters: Dict) -> List[SearchResult]: ...
    def search_vector(self, vector: List[float], limit: int) -> List[SearchResult]: ...
    def add(self, ticket_id: str, text: str, vector: List[float]) -> None: ...
    def remove(self, ticket_id: str) -> bool: ...
    def get_metadata(self) -> Dict[str, Any]: ...

class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
```
