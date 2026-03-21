# vtic — Core Features Breakdown (API + CLI)

**Scope:** 4 Core API features + 4 Core CLI features  
**Purpose:** Implementation-ready specification for coding agent

---

## API FEATURES (4 Core)

---

### Feature 1: Search Endpoint

#### L1: API

#### L2: Endpoints

#### L3: Search endpoint

#### L4: Implementation Unit

```rust
async fn handle_search(
    State(index): State<Arc<TicketIndex>>,
    Json(req): Json<SearchRequest>
) -> Result<Json<SearchResponse>, ApiError>
```

Responsibilities:
- Validate `SearchRequest`: ensure `query` is non-empty string, `filters` keys are valid field names, `topk` is 1-1000
- Call `index.search(query, filters, topk)` to get ranked results
- Construct `SearchResponse` with results array, total count, and echo query
- Return HTTP 200 with JSON body
- Return HTTP 400 if validation fails

#### L5: Input/Output Spec

**Input:**
```http
POST /search
Content-Type: application/json

{
  "query": "CORS wildcard configuration",
  "filters": {
    "severity": "critical",
    "status": "open"
  },
  "topk": 10
}
```

**Output (Success):**
```json
{
  "results": [
    {
      "id": "C1",
      "title": "CORS wildcard allows any origin",
      "severity": "critical",
      "status": "open",
      "score": 0.95
    },
    {
      "id": "C2",
      "title": "CORS headers not configured",
      "severity": "critical",
      "status": "in_progress",
      "score": 0.87
    }
  ],
  "total": 2,
  "query": "CORS wildcard configuration"
}
```

**Status:** 200 OK

**Output (Error - Empty Query):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Query cannot be empty",
    "details": {"field": "query"}
  }
}
```

**Status:** 400 Bad Request

#### L6: Test Cases

```rust
#[test]
fn test_search_endpoint_returns_results_with_filters() {
    // Setup: Create 3 tickets, 2 with severity=critical, 1 with severity=low
    // Request: POST /search with query="CORS", filters={"severity": "critical"}
    // Assert: Response has 2 results, all with severity=critical
    // Assert: Status is 200
}

#[test]
fn test_search_endpoint_empty_query_returns_400() {
    // Request: POST /search with query=""
    // Assert: Response has error.code == "VALIDATION_ERROR"
    // Assert: Status is 400
}

#[test]
fn test_search_endpoint_invalid_filter_field_returns_400() {
    // Request: POST /search with filters={"invalid_field": "value"}
    // Assert: Response error mentions "invalid filter field"
    // Assert: Status is 400
}

#[test]
fn test_search_endpoint_respects_topk() {
    // Setup: Create 10 tickets matching query
    // Request: POST /search with topk=3
    // Assert: Response has exactly 3 results
    // Assert: total field shows 10
}
```

---

### Feature 2: Health Check Endpoint

#### L1: API

#### L2: Monitoring

#### L3: Health check endpoint

#### L4: Implementation Unit

```rust
async fn handle_health_check(
    State(store): State<Arc<TicketStore>>,
    State(index): State<Arc<TicketIndex>>
) -> Result<Json<HealthResponse>, ApiError>
```

Responsibilities:
- Check `store.health()` returns Ok (tickets directory exists and is readable)
- Check `index.health()` returns Ok (index file exists and is not corrupted)
- Return 200 with `{"status": "ok", ...}` if both checks pass
- Return 503 with `{"status": "unhealthy", ...}` if any check fails
- Include individual component status in response

#### L5: Input/Output Spec

**Input:**
```http
GET /health
```

**Output (Healthy):**
```json
{
  "status": "ok",
  "components": {
    "storage": "healthy",
    "index": "healthy"
  },
  "version": "0.1.0"
}
```

**Status:** 200 OK

**Output (Unhealthy - Index Missing):**
```json
{
  "status": "unhealthy",
  "components": {
    "storage": "healthy",
    "index": "missing"
  },
  "version": "0.1.0"
}
```

**Status:** 503 Service Unavailable

#### L6: Test Cases

```rust
#[test]
fn test_health_check_returns_200_when_all_healthy() {
    // Setup: Initialize store and index in temp directory
    // Request: GET /health
    // Assert: Response status == "ok"
    // Assert: components.storage == "healthy"
    // Assert: components.index == "healthy"
    // Assert: Status is 200
}

#[test]
fn test_health_check_returns_503_when_index_missing() {
    // Setup: Initialize store but delete index file
    // Request: GET /health
    // Assert: Response status == "unhealthy"
    // Assert: components.index == "missing"
    // Assert: Status is 503
}

#[test]
fn test_health_check_returns_503_when_storage_unreadable() {
    // Setup: Create store, then make tickets directory unreadable (chmod 000)
    // Request: GET /health
    // Assert: Response status == "unhealthy"
    // Assert: components.storage == "unhealthy"
    // Assert: Status is 503
}
```

---

### Feature 3: JSON Responses

#### L1: API

#### L2: Response Format

#### L3: JSON response serialization

#### L4: Implementation Unit

```rust
fn json_response<T: Serialize>(data: T, status: StatusCode) -> Response<Body>
```

Responsibilities:
- Serialize `data` to JSON using `serde_json::to_string`
- Set `Content-Type: application/json; charset=utf-8` header
- Set `X-Content-Type-Options: nosniff` security header
- Construct Response with status code and JSON body
- Handle serialization errors by returning 500 Internal Server Error

#### L5: Input/Output Spec

**Input:**
```rust
let data = Ticket {
    id: "C1".to_string(),
    title: "Fix CORS issue".to_string(),
    severity: "critical".to_string(),
};
let response = json_response(data, StatusCode::OK);
```

**Output:**
```http
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
X-Content-Type-Options: nosniff

{"id":"C1","title":"Fix CORS issue","severity":"critical"}
```

**Status:** 200 OK (or as specified)

#### L6: Test Cases

```rust
#[test]
fn test_json_response_sets_correct_content_type() {
    // Input: Any serializable struct
    // Execute: json_response(data, 200)
    // Assert: Response header "Content-Type" == "application/json; charset=utf-8"
}

#[test]
fn test_json_response_includes_nosniff_header() {
    // Input: Any serializable struct
    // Execute: json_response(data, 200)
    // Assert: Response header "X-Content-Type-Options" == "nosniff"
}

#[test]
fn test_json_response_serializes_struct_to_valid_json() {
    // Input: Ticket struct with known values
    // Execute: json_response(ticket, 200)
    // Assert: Response body parses as valid JSON
    // Assert: Parsed JSON matches input struct
}

#[test]
fn test_json_response_uses_provided_status_code() {
    // Input: Any data, StatusCode::CREATED (201)
    // Execute: json_response(data, 201)
    // Assert: Response status code is 201
}
```

---

### Feature 4: Consistent Error Envelope

#### L1: API

#### L2: Error Handling

#### L3: Error envelope format

#### L4: Implementation Unit

```rust
#[derive(Serialize)]
struct ApiError {
    error: ErrorBody,
}

#[derive(Serialize)]
struct ErrorBody {
    code: String,        // Machine-readable code: "NOT_FOUND", "VALIDATION_ERROR", etc.
    message: String,     // Human-readable message
    details: Value,      // Optional additional context (null or object)
}

impl ApiError {
    fn not_found(resource: &str, id: &str) -> Self { ... }
    fn validation_error(field: &str, reason: &str) -> Self { ... }
    fn internal_error(context: &str) -> Self { ... }
    fn to_response(&self, status: StatusCode) -> Response<Body> { ... }
}
```

Responsibilities:
- Define standard error structure with `code`, `message`, `details` fields
- Map domain errors to appropriate HTTP status codes (404, 400, 500, etc.)
- Serialize error to JSON using `json_response` helper
- Include actionable context in `message` field

#### L5: Input/Output Spec

**Input (NotFound):**
```rust
let error = ApiError::not_found("Ticket", "C999");
let response = error.to_response(StatusCode::NOT_FOUND);
```

**Output:**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": {
    "code": "NOT_FOUND",
    "message": "Ticket with id 'C999' not found",
    "details": null
  }
}
```

**Status:** 404 Not Found

**Input (ValidationError):**
```rust
let error = ApiError::validation_error("title", "Title is required and cannot be empty");
let response = error.to_response(StatusCode::BAD_REQUEST);
```

**Output:**
```http
HTTP/1.1 400 Bad Request
Content-Type: application/json

{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid value for field 'title': Title is required and cannot be empty",
    "details": {
      "field": "title",
      "constraint": "required"
    }
  }
}
```

**Status:** 400 Bad Request

#### L6: Test Cases

```rust
#[test]
fn test_error_envelope_not_found_format() {
    // Create: ApiError::not_found("Ticket", "C1")
    // Execute: error.to_response(404)
    // Assert: JSON body has "error" object
    // Assert: error.code == "NOT_FOUND"
    // Assert: error.message contains "C1"
    // Assert: Status is 404
}

#[test]
fn test_error_envelope_validation_error_format() {
    // Create: ApiError::validation_error("severity", "must be one of: low, medium, high, critical")
    // Execute: error.to_response(400)
    // Assert: error.code == "VALIDATION_ERROR"
    // Assert: error.details.field == "severity"
    // Assert: Status is 400
}

#[test]
fn test_error_envelope_internal_error_sanitizes_details() {
    // Create: ApiError::internal_error("Database connection failed")
    // Execute: error.to_response(500)
    // Assert: error.code == "INTERNAL_ERROR"
    // Assert: error.message does NOT contain stack traces or file paths
    // Assert: Status is 500
}

#[test]
fn test_all_errors_have_json_content_type() {
    // Create: Any ApiError variant
    // Execute: error.to_response(status)
    // Assert: Content-Type is application/json
}
```

---

## CLI FEATURES (4 Core)

---

### Feature 5: Core Commands

#### L1: CLI

#### L2: Commands

#### L3: Core command system

#### L4: Implementation Unit

```rust
#[derive(Parser)]
#[command(name = "vtic", version = "0.1.0")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
    
    #[arg(long, global = true)]
    format: Option<OutputFormat>,
    
    #[arg(long, global = true)]
    debug: bool,
    
    #[arg(long, global = true)]
    no_color: bool,
}

#[derive(Subcommand)]
enum Commands {
    Init { dir: Option<PathBuf> },
    Create {
        #[arg(long)]
        title: String,
        #[arg(long)]
        repo: String,
        #[arg(long)]
        description: Option<String>,
        #[arg(long)]
        severity: Option<String>,
        #[arg(long)]
        category: Option<String>,
    },
    Get { id: String },
    Update {
        id: String,
        #[arg(long)]
        status: Option<String>,
        #[arg(long)]
        severity: Option<String>,
        #[arg(long)]
        description: Option<String>,
    },
    Delete {
        id: String,
        #[arg(long)]
        force: bool,
    },
    List {
        #[arg(long)]
        status: Option<String>,
        #[arg(long)]
        severity: Option<String>,
        #[arg(long)]
        repo: Option<String>,
    },
    Search {
        query: String,
        #[arg(long)]
        topk: Option<usize>,
    },
    Serve {
        #[arg(long, default_value = "3000")]
        port: u16,
    },
}

async fn run_command(cmd: Commands, config: Config) -> Result<ExitCode, CliError> { ... }
```

Responsibilities:
- Parse command-line arguments using clap
- Load configuration from `vtic.toml` and environment variables
- Dispatch to appropriate command handler based on subcommand
- Handle errors with user-friendly messages
- Return exit code (0 for success, 1 for errors, 2 for usage errors)

#### L5: Input/Output Spec

**Input (Create):**
```bash
vtic create --title "Fix CORS wildcard" --repo "ejacklab/open-dsearch" --severity critical
```

**Output:**
```
Created ticket C1: "Fix CORS wildcard"
  repo: ejacklab/open-dsearch
  severity: critical
  status: open
```

**Exit Code:** 0

**Input (Get):**
```bash
vtic get C1
```

**Output:**
```markdown
# C1: Fix CORS wildcard

- **Status:** open
- **Severity:** critical
- **Repo:** ejacklab/open-dsearch
- **Created:** 2024-01-15T10:30:00Z

## Description
[No description]
```

**Exit Code:** 0

**Input (Search):**
```bash
vtic search "CORS" --topk 5
```

**Output:**
```
Found 3 tickets for query "CORS":

  C1  [critical] Fix CORS wildcard (score: 0.95)
  C2  [high]      CORS headers not set (score: 0.82)
  C5  [medium]    Document CORS config (score: 0.71)
```

**Exit Code:** 0

**Input (Error - Ticket Not Found):**
```bash
vtic get C999
```

**Output:**
```
Error: Ticket 'C999' not found
Run 'vtic list' to see available tickets
```

**Exit Code:** 1

#### L6: Test Cases

```rust
#[test]
fn test_cli_create_command_creates_ticket() {
    // Setup: Initialize temp vtic directory
    // Execute: run_command(Commands::Create { title: "Test", repo: "test/repo", ... })
    // Assert: Ticket file exists at tickets/test/repo/bug/C1.md
    // Assert: Ticket has correct title and repo
    // Assert: Exit code is 0
}

#[test]
fn test_cli_get_command_returns_ticket() {
    // Setup: Create ticket C1 with known content
    // Execute: run_command(Commands::Get { id: "C1" })
    // Assert: Output contains ticket title
    // Assert: Exit code is 0
}

#[test]
fn test_cli_update_command_modifies_fields() {
    // Setup: Create ticket C1 with status=open
    // Execute: run_command(Commands::Update { id: "C1", status: Some("fixed"), ... })
    // Assert: Ticket file now has status=fixed
    // Assert: updated timestamp changed
    // Assert: Exit code is 0
}

#[test]
fn test_cli_delete_command_removes_ticket() {
    // Setup: Create ticket C1
    // Execute: run_command(Commands::Delete { id: "C1", force: true })
    // Assert: Ticket file no longer exists
    // Assert: Index no longer contains C1
    // Assert: Exit code is 0
}

#[test]
fn test_cli_list_command_filters_by_status() {
    // Setup: Create 3 tickets: 2 with status=open, 1 with status=fixed
    // Execute: run_command(Commands::List { status: Some("open"), ... })
    // Assert: Output shows exactly 2 tickets
    // Assert: Both have status=open
}

#[test]
fn test_cli_search_command_returns_ranked_results() {
    // Setup: Create 5 tickets, 3 mentioning "CORS"
    // Execute: run_command(Commands::Search { query: "CORS".to_string(), topk: Some(2) })
    // Assert: Output shows exactly 2 tickets
    // Assert: Results are sorted by score (highest first)
}

#[test]
fn test_cli_get_nonexistent_ticket_returns_error() {
    // Setup: Initialize empty vtic directory
    // Execute: run_command(Commands::Get { id: "C999" })
    // Assert: Error message mentions "not found"
    // Assert: Exit code is 1
}

#[test]
fn test_cli_create_missing_required_field_returns_error() {
    // Execute: run_command(Commands::Create { title: "".to_string(), repo: "test/repo", ... })
    // Assert: Error message mentions "title is required"
    // Assert: Exit code is 1
}
```

---

### Feature 6: JSON Output Format

#### L1: CLI

#### L2: Output

#### L3: JSON output format

#### L4: Implementation Unit

```rust
#[derive(Clone, Copy, ValueEnum)]
enum OutputFormat {
    Table,
    Json,
}

fn format_output<T: Serialize>(
    data: &T,
    format: OutputFormat,
    pretty: bool
) -> Result<String, FormatError> { ... }

fn print_output<T: Serialize>(
    data: &T,
    format: OutputFormat,
    pretty: bool,
    no_color: bool
) -> Result<(), IoError> { ... }
```

Responsibilities:
- Accept `--format json` or `--format table` flag (default: table)
- Serialize output data to JSON using serde_json
- Support `--pretty` flag for human-readable JSON with indentation
- Write to stdout; errors to stderr
- When JSON format is selected, suppress progress messages and spinners

#### L5: Input/Output Spec

**Input (Compact JSON):**
```bash
vtic get C1 --format json
```

**Output:**
```json
{"id":"C1","title":"Fix CORS wildcard","severity":"critical","status":"open","repo":"ejacklab/open-dsearch","created":"2024-01-15T10:30:00Z","updated":"2024-01-15T10:30:00Z"}
```

**Input (Pretty JSON):**
```bash
vtic get C1 --format json --pretty
```

**Output:**
```json
{
  "id": "C1",
  "title": "Fix CORS wildcard",
  "severity": "critical",
  "status": "open",
  "repo": "ejacklab/open-dsearch",
  "created": "2024-01-15T10:30:00Z",
  "updated": "2024-01-15T10:30:00Z"
}
```

**Input (List JSON):**
```bash
vtic list --status open --format json
```

**Output:**
```json
[
  {"id":"C1","title":"Fix CORS wildcard","severity":"critical","status":"open"},
  {"id":"C2","title":"Auth bypass","severity":"high","status":"open"}
]
```

**Input (Error in JSON):**
```bash
vtic get C999 --format json
```

**Output (to stdout):**
```json
{"error":{"code":"NOT_FOUND","message":"Ticket 'C999' not found"}}
```

**Exit Code:** 1

#### L6: Test Cases

```rust
#[test]
fn test_json_output_format_serializes_single_ticket() {
    // Setup: Create ticket C1
    // Execute: CLI with get C1 --format json
    // Assert: Output is valid JSON
    // Assert: JSON has id="C1"
    // Assert: No ANSI color codes in output
}

#[test]
fn test_json_output_format_serializes_list() {
    // Setup: Create 3 tickets
    // Execute: CLI with list --format json
    // Assert: Output is valid JSON array
    // Assert: Array has 3 elements
}

#[test]
fn test_json_output_pretty_flag_adds_indentation() {
    // Setup: Create ticket C1
    // Execute: CLI with get C1 --format json --pretty
    // Assert: Output contains newlines and indentation
    // Assert: Output is still valid JSON
}

#[test]
fn test_json_output_suppresses_progress_messages() {
    // Setup: Many tickets for a slow operation
    // Execute: CLI with search "query" --format json
    // Assert: No "Searching..." messages in stdout
    // Assert: Only pure JSON output
}

#[test]
fn test_json_output_for_errors() {
    // Setup: No tickets
    // Execute: CLI with get C999 --format json
    // Assert: Output is valid JSON with "error" key
    // Assert: error.code exists
    // Assert: Exit code is 1
}

#[test]
fn test_json_output_to_stdout_errors_to_stderr() {
    // Setup: Create ticket
    // Execute: CLI with get C1 --format json, capture stdout and stderr separately
    // Assert: stdout contains only JSON
    // Assert: stderr is empty (no warnings mixed in)
}
```

---

### Feature 7: Debug Mode

#### L1: CLI

#### L2: Logging

#### L3: Debug mode

#### L4: Implementation Unit

```rust
fn setup_logging(debug: bool, no_color: bool) -> Result<(), LogError> {
    let level = if debug { LevelFilter::Debug } else { LevelFilter::Warn };
    
    let formatter = FormatterBuilder::new()
        .with_target(true)
        .with_thread_ids(debug)
        .with_line_number(debug)
        .with_file(debug)
        .build();
    
    // Log to stderr only, never stdout (to keep stdout clean for piping)
    tracing_subscriber::fmt()
        .with_max_level(level)
        .with_writer(stderr)
        .event_format(formatter)
        .init();
    
    Ok(())
}

// Usage in command handlers:
#[instrument(skip(store))]
async fn handle_create(cmd: CreateCommand, store: &TicketStore) -> Result<Ticket, CliError> {
    debug!("Creating ticket with title: {}", cmd.title);
    debug!("Resolved repo path: {:?}", store.repo_path(&cmd.repo));
    // ... implementation
    debug!("Ticket created successfully: id={}", ticket.id);
    Ok(ticket)
}
```

Responsibilities:
- Accept `--debug` or `-d` flag globally
- When enabled, set log level to DEBUG
- Log to stderr only (never stdout)
- Include timestamp, source file, line number, and module path in debug logs
- Include operation context (ticket IDs, file paths, config values)
- When disabled, only show WARN and ERROR level logs

#### L5: Input/Output Spec

**Input (Normal Mode):**
```bash
vtic create --title "Test" --repo "test/repo"
```

**Stderr Output:**
```
(empty)
```

**Input (Debug Mode):**
```bash
vtic create --title "Test" --repo "test/repo" --debug
```

**Stderr Output:**
```
2024-01-15T10:30:00.123Z DEBUG vtic::commands::create: Creating ticket with title: Test
    at src/commands/create.rs:45 on main
2024-01-15T10:30:00.125Z DEBUG vtic::storage::store: Resolved repo path: "tickets/test/repo"
    at src/storage/store.rs:112 on main
2024-01-15T10:30:00.130Z DEBUG vtic::storage::store: Writing ticket file: tickets/test/repo/bug/C1.md
    at src/storage/store.rs:78 on main
2024-01-15T10:30:00.135Z DEBUG vtic::index::zvec: Adding ticket to index: C1
    at src/index/zvec.rs:203 on main
2024-01-15T10:30:00.140Z DEBUG vtic::commands::create: Ticket created successfully: id=C1
    at src/commands/create.rs:67 on main
```

**Stdout Output (Same in Both Modes):**
```
Created ticket C1: "Test"
```

#### L6: Test Cases

```rust
#[test]
fn test_debug_mode_enables_debug_level_logs() {
    // Setup: Capture stderr
    // Execute: CLI with --debug flag on any command
    // Assert: Stderr contains "DEBUG" level messages
}

#[test]
fn test_debug_mode_disabled_hides_debug_logs() {
    // Setup: Capture stderr
    // Execute: CLI without --debug flag
    // Assert: Stderr does not contain "DEBUG" messages
    // Assert: Stderr is empty or only has WARN/ERROR
}

#[test]
fn test_debug_mode_logs_to_stderr_not_stdout() {
    // Setup: Capture stdout and stderr separately
    // Execute: CLI with --debug
    // Assert: Stdout does NOT contain debug messages
    // Assert: Stderr DOES contain debug messages
}

#[test]
fn test_debug_mode_includes_source_location() {
    // Setup: Capture stderr
    // Execute: CLI with --debug
    // Assert: Log lines contain file paths (e.g., "at src/commands/...")
    // Assert: Log lines contain line numbers
}

#[test]
fn test_debug_mode_shows_operation_context() {
    // Setup: Capture stderr
    // Execute: vtic create --title "Test" --repo "test/repo" --debug
    // Assert: Debug output contains ticket title "Test"
    // Assert: Debug output contains repo path
}

#[test]
fn test_debug_mode_works_with_all_commands() {
    // Execute: vtic init --debug
    // Execute: vtic create ... --debug
    // Execute: vtic get C1 --debug
    // Execute: vtic search "test" --debug
    // Assert: All commands produce debug output to stderr
}
```

---

### Feature 8: No-Color Mode

#### L1: CLI

#### L2: Output

#### L3: No-color mode

#### L4: Implementation Unit

```rust
#[derive(Clone, Copy, ValueEnum)]
enum ColorChoice {
    Auto,    // Detect TTY: color if stdout is terminal
    Always,  // Force color even when piped
    Never,   // Disable all color codes
}

fn configure_color_output(choice: ColorChoice) -> Result<(), ConfigError> {
    let should_color = match choice {
        ColorChoice::Auto => stdout().is_terminal(),
        ColorChoice::Always => true,
        ColorChoice::Never => false,
    };
    
    // Set global color flag for all formatters
    COLOR_ENABLED.store(should_color, Ordering::Relaxed);
    
    // Configure colored crate
    colored::control::set_override(should_color);
    
    Ok(())
}

fn format_status(status: &str) -> String {
    if COLOR_ENABLED.load(Ordering::Relaxed) {
        match status {
            "open" => status.red().to_string(),
            "in_progress" => status.yellow().to_string(),
            "fixed" => status.green().to_string(),
            "wont_fix" => status.dimmed().to_string(),
            _ => status.to_string(),
        }
    } else {
        status.to_string()
    }
}

fn format_severity(severity: &str) -> String {
    if COLOR_ENABLED.load(Ordering::Relaxed) {
        match severity {
            "critical" => severity.red().bold().to_string(),
            "high" => severity.red().to_string(),
            "medium" => severity.yellow().to_string(),
            "low" => severity.blue().to_string(),
            _ => severity.to_string(),
        }
    } else {
        severity.to_string()
    }
}
```

Responsibilities:
- Accept `--no-color` flag OR `--color never|always|auto` (default: auto)
- When disabled, strip all ANSI color codes from output
- When auto, detect if stdout is a TTY; disable color if piped
- Apply to ALL output: tables, lists, errors, help text
- Ensure JSON output never has color codes regardless of setting

#### L5: Input/Output Spec

**Input (Color Enabled - TTY):**
```bash
vtic list
# (running in terminal with color support)
```

**Output (with ANSI codes):**
```
  C1  \u001b[31;1mcritical\u001b[0m  \u001b[31mopen\u001b[0m     Fix CORS wildcard
  C2  \u001b[33mhigh\u001b[0m       \u001b[33min_progress\u001b[0m  Auth token leak
  C3  \u001b[34mlow\u001b[0m        \u001b[32mfixed\u001b[0m      Update README
```

**Input (No-Color Mode):**
```bash
vtic list --no-color
```

**Output (plain text, no ANSI):**
```
  C1  critical  open         Fix CORS wildcard
  C2  high      in_progress  Auth token leak
  C3  low       fixed        Update README
```

**Input (Auto Mode, Piped):**
```bash
vtic list | cat
# (auto detects pipe, disables color)
```

**Output (plain text, no ANSI):**
```
  C1  critical  open         Fix CORS wildcard
  C2  high      in_progress  Auth token leak
  C3  low       fixed        Update README
```

**Input (Color Never in Error Messages):**
```bash
vtic get C999 --no-color
```

**Output (no ANSI in error):**
```
Error: Ticket 'C999' not found
Run 'vtic list' to see available tickets
```

#### L6: Test Cases

```rust
#[test]
fn test_no_color_flag_disables_all_ansi_codes() {
    // Setup: Create multiple tickets
    // Execute: CLI with --no-color, capture output
    // Assert: Output contains no ANSI escape sequences (no \u001b[)
}

#[test]
fn test_color_auto_disables_when_piped() {
    // Setup: Create tickets
    // Execute: CLI with --color auto, pipe to cat, capture output
    // Assert: Output contains no ANSI escape sequences
}

#[test]
fn test_color_auto_enables_in_terminal() {
    // Setup: Mock TTY environment (stdout is terminal)
    // Execute: CLI with --color auto
    // Assert: Output contains ANSI escape sequences
}

#[test]
fn test_color_always_forces_color_when_piped() {
    // Setup: Create tickets
    // Execute: CLI with --color always, pipe to cat, capture output
    // Assert: Output DOES contain ANSI escape sequences
}

#[test]
fn test_no_color_applies_to_error_messages() {
    // Execute: CLI with --no-color and invalid command (should error)
    // Capture: Stderr
    // Assert: Error message has no ANSI codes
}

#[test]
fn test_no_color_applies_to_help_text() {
    // Execute: CLI with --no-color --help
    // Assert: Help output has no ANSI codes
}

#[test]
fn test_json_output_never_has_color_regardless_of_flag() {
    // Execute: vtic list --format json --color always
    // Assert: JSON output has no ANSI codes
    // (JSON should always be plain, color flag is for table output)
}

#[test]
fn test_no_color_global_flag_affects_all_commands() {
    // Execute: vtic --no-color list
    // Execute: vtic --no-color search "test"
    // Execute: vtic --no-color get C1
    // Assert: All outputs have no ANSI codes
}
```

---

## Summary

| Feature | Category | Sub-Category | Implementation Complexity |
|---------|----------|--------------|---------------------------|
| Search endpoint | API | Endpoints | Medium (validation + index integration) |
| Health check | API | Monitoring | Low (simple checks) |
| JSON responses | API | Response Format | Low (wrapper function) |
| Error envelope | API | Error Handling | Medium (error types + mapping) |
| Core commands | CLI | Commands | High (8 commands + dispatcher) |
| JSON output | CLI | Output | Low (serializer + flag) |
| Debug mode | CLI | Logging | Medium (logger setup + instrumentation) |
| No-color mode | CLI | Output | Low (flag + conditional formatting) |

**Implementation Order (Recommended):**

1. **API Foundation:** JSON responses → Error envelope → Health check → Search endpoint
2. **CLI Foundation:** No-color mode → Debug mode → JSON output → Core commands

**Dependencies:**
- Search endpoint requires: TicketIndex with search capability
- Core commands require: TicketStore (storage layer), TicketIndex (search)
- All API features require: JSON response helper
- All CLI features require: Configuration loading

**Testing Priority:**
1. Error envelope (used everywhere)
2. JSON responses (used everywhere)
3. Core commands (main user interface)
4. Search endpoint (core value proposition)
5. Health check, JSON output, Debug mode, No-color (supporting features)
