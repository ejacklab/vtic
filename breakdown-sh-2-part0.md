# Should Have Features - 6-Level Breakdown

10 P1 (Should Have) features broken down to implementation-ready specifications.

---

## Feature 1: Per-Repo Stats

### L1: Multi-Repo Support
### L2: Statistics
### L3: Per-repo stats
### L4: `get_stats_by_repo(store: TicketStore) -> Dict[str, RepoStats]`
  - Aggregate ticket counts by repository
  - Count tickets by status within each repo
  - Count tickets by severity within each repo
  - Count tickets by category within each repo
  - Return dictionary keyed by repo identifier (owner/repo)

### L5: Spec
```python
@dataclass
class RepoStats:
    repo: str
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]

def get_stats_by_repo(store: TicketStore) -> Dict[str, RepoStats]:
    """
    Input: store with tickets from "owner1/repo1", "owner1/repo2", "owner2/repo3"
    Output: {
        "owner1/repo1": RepoStats(
            repo="owner1/repo1",
            total=15,
            by_status={"open": 5, "fixed": 8, "closed": 2},
            by_severity={"critical": 2, "high": 5, "medium": 8},
            by_category={"code": 10, "security": 3, "docs": 2}
        ),
        "owner1/repo2": RepoStats(...),
        "owner2/repo3": RepoStats(...)
    }
    
    Input: store with no tickets
    Output: {}
    
    Input: store with all tickets from single repo
    Output: {"owner/repo": RepoStats(repo="owner/repo", total=N, ...)}
    """
```

### L6: Test
```python
test_get_stats_by_repo_multiple_repos()
test_get_stats_by_repo_single_repo()
test_get_stats_by_repo_empty_store()
test_get_stats_by_repo_counts_by_status_correctly()
test_get_stats_by_repo_counts_by_severity_correctly()
test_get_stats_by_repo_counts_by_category_correctly()
test_get_stats_by_repo_handles_unknown_status()
```

---

## Feature 2: Repo Isolation

### L1: Multi-Repo Support
### L2: Operations
### L3: Repo isolation
### L4: `filter_tickets_by_repo(tickets: List[Ticket], repo: str, exact: bool = True) -> List[Ticket]`
  - Filter tickets to only those belonging to specified repo
  - Support exact match mode (exact=True) for single repo isolation
  - Support glob pattern match (exact=False) for partial matches
  - Return filtered list preserving order

### L4: `cli_with_repo_isolation(repo: str, operation: Callable, store: TicketStore) -> Any`
  - Execute CLI operation with repo scope isolation
  - Create filtered view of store limited to specified repo
  - Pass isolated store to operation
  - Return operation result

### L5: Spec
```python
def filter_tickets_by_repo(tickets: List[Ticket], repo: str, exact: bool = True) -> List[Ticket]:
    """
    Input: tickets=[Ticket(repo="a/b"), Ticket(repo="a/c"), Ticket(repo="x/y")], repo="a/b", exact=True
    Output: [Ticket(repo="a/b")]
    
    Input: tickets=[Ticket(repo="a/b"), Ticket(repo="a/c"), Ticket(repo="x/y")], repo="a/*", exact=False
    Output: [Ticket(repo="a/b"), Ticket(repo="a/c")]
    
    Input: tickets=[], repo="any/repo"
    Output: []
    
    Input: tickets=[Ticket(repo="a/b")], repo="nonexistent/repo"
    Output: []
    """

@dataclass
class IsolatedStore:
    """Read-only view of TicketStore limited to a specific repo."""
    parent_store: TicketStore
    repo: str
    exact: bool = True
    
    def get(self, ticket_id: str) -> Optional[Ticket]:
        """Get ticket only if it belongs to isolated repo."""
    
    def list(self, filters: Optional[Dict] = None) -> List[Ticket]:
        """List tickets only from isolated repo."""

def cli_with_repo_isolation(repo: str, operation: Callable, store: TicketStore, exact: bool = True) -> Any:
    """
    Input: repo="ejacklab/open-dsearch", operation=list_tickets, store with multiple repos
    Action: Create IsolatedStore limited to "ejacklab/open-dsearch"
            Execute list_tickets(isolated_store)
    Output: List of tickets from ejacklab/open-dsearch only
    
    Input: repo="ejacklab/*", exact=False, operation=list_tickets
    Output: List of tickets from all ejacklab/* repos
    
    Error: ValueError if repo format invalid (not "owner/repo" or valid glob)
    """
```

### L6: Test
```python
test_filter_tickets_by_repo_exact_match()
test_filter_tickets_by_repo_glob_match()
test_filter_tickets_by_repo_empty_list()
test_filter_tickets_by_repo_no_matches()
test_isolated_store_get_from_same_repo()
test_isolated_store_get_from_different_repo_returns_none()
test_isolated_store_list_filters_by_repo()
test_cli_with_repo_isolation_limits_scope()
test_cli_with_repo_isolation_glob_pattern()
```

---

## Feature 3: Repo-Specific Defaults

### L1: Multi-Repo Support
### L2: Configuration
### L3: Repo-specific defaults
### L4: `get_repo_defaults(repo: str, config: VticConfig) -> RepoDefaults`
  - Look up default values for specified repo in configuration
  - Return default category, severity, status for repo
  - Fall back to global defaults if repo-specific not configured
  - Return empty RepoDefaults if no defaults configured

### L4: `apply_repo_defaults(ticket_data: Dict[str, Any], repo: str, config: VticConfig) -> Dict[str, Any]`
  - Get repo-specific defaults from config
  - Apply defaults only to fields that are None or missing
  - Preserve explicitly provided values (never override)
  - Return updated ticket data dict

### L5: Spec
```python
@dataclass
class RepoDefaults:
    category: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    tags: List[str] = field(default_factory=list)

def get_repo_defaults(repo: str, config: VticConfig) -> RepoDefaults:
    """
    Input: repo="ejacklab/open-dsearch", config with:
           [repos."ejacklab/open-dsearch"]
           category = "security"
           severity = "high"
    Output: RepoDefaults(category="security", severity="high", status=None, tags=[])
    
    Input: repo="unknown/repo", config with global defaults:
           [defaults]
           category = "code"
           severity = "medium"
    Output: RepoDefaults(category="code", severity="medium", status=None, tags=[])
    
    Input: repo="any/repo", config with no defaults
    Output: RepoDefaults()  # all None
    """

def apply_repo_defaults(ticket_data: Dict[str, Any], repo: str, config: VticConfig) -> Dict[str, Any]:
    """
    Input: ticket_data={"title": "Bug", "repo": "ejacklab/open-dsearch"},
           config with repo defaults: category="security", severity="high"
    Output: {"title": "Bug", "repo": "ejacklab/open-dsearch", 
             "category": "security", "severity": "high"}
    
    Input: ticket_data={"title": "Bug", "repo": "r", "severity": "critical"},
           config with repo defaults: severity="high"
    Output: {"title": "Bug", "repo": "r", "severity": "critical"}  # explicit value preserved
    
    Input: ticket_data={"title": "Bug", "repo": "r", "category": None},
           config with repo defaults: category="security"
    Output: {"title": "Bug", "repo": "r", "category": "security"}  # None replaced
    """
```

### L6: Test
```python
test_get_repo_defaults_specific_config()
test_get_repo_defaults_fallback_to_global()
test_get_repo_defaults_no_config_returns_empty()
test_apply_repo_defaults_applies_missing_fields()
test_apply_repo_defaults_preserves_explicit_values()
test_apply_repo_defaults_replaces_none_values()
test_apply_repo_defaults_empty_ticket_gets_all_defaults()
test_repo_defaults_config_precedence()
```

---

## Feature 4: On-Create Webhook

### L1: Integration
### L2: Webhooks
### L3: On-create webhook
### L4: `trigger_create_webhook(ticket: Ticket, config: WebhookConfig) -> WebhookResult`
  - Check if create webhook is configured (URL present)
  - Build webhook payload with event type "ticket.created"
  - Include full ticket data in payload
  - POST to configured webhook URL
  - Return result with success status and response details
  - Log webhook attempt and result

### L4: `get_webhook_config_for_event(event: str, config: VticConfig) -> Optional[WebhookEndpoint]`
  - Look up webhook configuration for specific event type
  - Return WebhookEndpoint with URL, headers, timeout settings
  - Return None if webhook not configured for event

### L5: Spec
```python
@dataclass
class WebhookEndpoint:
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 0

@dataclass
class WebhookResult:
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_body: Optional[str] = None
    duration_ms: int = 0

def trigger_create_webhook(ticket: Ticket, config: WebhookConfig) -> WebhookResult:
    """
    Input: ticket=Ticket(id="C1", title="New Bug", repo="owner/repo"),
           config with webhook_url="https://hooks.example.com/vtic"
    Action: POST to https://hooks.example.com/vtic with:
            {
              "event": "ticket.created",
              "timestamp": "2026-03-17T10:00:00Z",
              "data": {"id": "C1", "title": "New Bug", ...}
            }
    Output: WebhookResult(success=True, status_code=200, duration_ms=150)
    
    Input: config with no webhook_url configured
    Output: WebhookResult(success=True)  # no-op, no webhook to call
    
    Input: webhook URL returns 500
    Output: WebhookResult(success=False, status_code=500, error_message="Server error")
    
    Input: webhook URL times out
    Output: WebhookResult(success=False, error_message="Timeout after 30s")
    """

def get_webhook_config_for_event(event: str, config: VticConfig) -> Optional[WebhookEndpoint]:
    """
    Input: event="ticket.created", config with [webhooks.create] url="..."
    Output: WebhookEndpoint(url="...", headers={}, timeout_seconds=30)
    
    Input: event="ticket.created", config with no webhooks section
    Output: None
    """
```

### L6: Test
```python
test_trigger_create_webhook_success()
test_trigger_create_webhook_no_config_returns_success()
test_trigger_create_webhook_server_error()
test_trigger_create_webhook_timeout()
test_trigger_create_webhook_includes_full_ticket()
test_trigger_create_webhook_custom_headers()
test_get_webhook_config_for_event_configured()
test_get_webhook_config_for_event_not_configured()
```

---

## Feature 5: On-Update Webhook

### L1: Integration
### L2: Webhooks
### L3: On-update webhook
### L4: `trigger_update_webhook(ticket: Ticket, changes: Dict[str, Any], config: WebhookConfig) -> WebhookResult`
  - Check if update webhook is configured
  - Build webhook payload with event type "ticket.updated"
  - Include full ticket data AND field-level changes
  - POST to configured webhook URL
  - Return result with success status

### L4: `compute_ticket_changes(before: Ticket, after: Ticket) -> Dict[str, FieldChange]`
  - Compare before and after ticket states
  - Identify which fields changed
  - Record old value, new value for each changed field
  - Skip unchanged fields
  - Return dict of field name -> FieldChange

### L5: Spec
```python
@dataclass
class FieldChange:
    field: str
    old_value: Any
    new_value: Any

def trigger_update_webhook(ticket: Ticket, changes: Dict[str, Any], config: WebhookConfig) -> WebhookResult:
    """
    Input: ticket=Ticket(id="C1", status="fixed", ...),
           changes={"status": {"old": "open", "new": "fixed"}},
           config with webhook_url="https://hooks.example.com/vtic"
    Action: POST with:
            {
              "event": "ticket.updated",
              "timestamp": "2026-03-17T11:00:00Z",
              "data": {"id": "C1", "status": "fixed", ...},
              "changes": {"status": {"old": "open", "new": "fixed"}}
            }
    Output: WebhookResult(success=True, status_code=200)
    
    Input: config with no update webhook
    Output: WebhookResult(success=True)  # no-op
    """

def compute_ticket_changes(before: Ticket, after: Ticket) -> Dict[str, FieldChange]:
    """
    Input: before=Ticket(status="open", severity="medium"),
           after=Ticket(status="fixed", severity="high")
    Output: {
        "status": FieldChange(field="status", old_value="open", new_value="fixed"),
        "severity": FieldChange(field="severity", old_value="medium", new_value="high")
    }
    
    Input: before=Ticket(title="Bug"), after=Ticket(title="Bug")
    Output: {}  # no changes
    
    Input: before=Ticket(tags=["a"]), after=Ticket(tags=["a", "b"])
    Output: {"tags": FieldChange(field="tags", old_value=["a"], new_value=["a", "b"])}
    """
```

### L6: Test
```python
test_trigger_update_webhook_success()
test_trigger_update_webhook_includes_changes()
test_trigger_update_webhook_no_config_noop()
test_compute_ticket_changes_single_field()
test_compute_ticket_changes_multiple_fields()
test_compute_ticket_changes_no_changes()
test_compute_ticket_changes_list_field()
test_compute_ticket_changes_none_to_value()
```

---

## Feature 6: On-Delete Webhook

### L1: Integration
### L2: Webhooks
### L3: On-delete webhook
### L4: `trigger_delete_webhook(ticket_id: str, ticket_snapshot: Optional[Ticket], config: WebhookConfig) -> WebhookResult`
  - Check if delete webhook is configured
  - Build webhook payload with event type "ticket.deleted"
  - Include ticket ID and optionally the full ticket snapshot before deletion
  - Include deletion type (soft delete vs hard delete)
  - POST to configured webhook URL
  - Return result with success status

### L5: Spec
```python
@dataclass
class DeleteEvent:
    ticket_id: str
    deletion_type: str  # "soft" or "hard"
    ticket_snapshot: Optional[Ticket] = None  # ticket data before deletion

def trigger_delete_webhook(ticket_id: str, ticket_snapshot: Optional[Ticket], 
                          deletion_type: str, config: WebhookConfig) -> WebhookResult:
    """
    Input: ticket_id="C1", 
           ticket_snapshot=Ticket(id="C1", title="Old Bug"),
           deletion_type="soft",
           config with webhook_url="https://hooks.example.com/vtic"
    Action: POST with:
            {
              "event": "ticket.deleted",
              "timestamp": "2026-03-17T12:00:00Z",
              "data": {
                "ticket_id": "C1",
                "deletion_type": "soft",
                "ticket": {"id": "C1", "title": "Old Bug", ...}
              }
            }
    Output: WebhookResult(success=True, status_code=200)
    
    Input: deletion_type="hard"
    Action: POST with deletion_type="hard" in payload
    
    Input: config with no delete webhook
    Output: WebhookResult(success=True)  # no-op
    """
```

### L6: Test
```python
test_trigger_delete_webhook_soft_delete()
test_trigger_delete_webhook_hard_delete()
test_trigger_delete_webhook_includes_snapshot()
test_trigger_delete_webhook_no_config_noop()
test_trigger_delete_webhook_server_error()
test_delete_event_payload_structure()
```

---

## Feature 7: Webhook Payload

### L1: Integration
### L2: Webhooks
### L3: Webhook payload
### L4: `build_webhook_payload(event: str, data: Dict[str, Any], config: WebhookConfig) -> WebhookPayload`
  - Construct standardized webhook payload structure
  - Include event type, timestamp, data, and metadata
  - Add configurable webhook secret for HMAC signature
  - Support custom payload templates per webhook endpoint
  - Return serializable WebhookPayload object

### L4: `sign_webhook_payload(payload: WebhookPayload, secret: str) -> str`
  - Generate HMAC-SHA256 signature of payload
  - Use configured webhook secret
  - Return signature in hex format
  - Include signature in X-Vtic-Signature header

### L5: Spec
```python
@dataclass
class WebhookPayload:
    event: str
    timestamp: str  # ISO 8601
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""

def build_webhook_payload(event: str, data: Dict[str, Any], 
                         config: WebhookConfig, 
                         metadata: Optional[Dict] = None) -> WebhookPayload:
    """
    Input: event="ticket.created", 
           data={"id": "C1", "title": "Bug"},
           config with webhook_version="1.0"
    Output: WebhookPayload(
        event="ticket.created",
        timestamp="2026-03-17T10:00:00Z",
        data={"id": "C1", "title": "Bug"},
        metadata={"version": "1.0", "source": "vtic"}
    )
    
    Input: metadata={"custom": "value"}
    Output: WebhookPayload(..., metadata={"version": "1.0", "source": "vtic", "custom": "value"})
    """

def sign_webhook_payload(payload: WebhookPayload, secret: str) -> str:
    """
    Input: payload=WebhookPayload(event="ticket.created", ...),
           secret="webhook-secret-key"
    Output: "sha256=a1b2c3d4..."  # HMAC-SHA256 hex digest
    
    Note: Signature computed over payload.to_json()
    """
```

### L6: Test
```python
test_build_webhook_payload_structure()
test_build_webhook_payload_includes_timestamp()
test_build_webhook_payload_custom_metadata()
test_webhook_payload_to_json_serializable()
test_sign_webhook_payload_generates_hmac()
test_sign_webhook_payload_consistent_for_same_input()
test_sign_webhook_payload_different_for_different_payloads()
test_webhook_payload_event_types()
```

---

## Feature 8: Docker Image

### L1: Integration
### L2: CI/CD
### L3: Docker image
### L4: `Dockerfile` (build configuration)
  - Base image: python:3.11-slim
  - Install vtic package and dependencies
  - Configure entrypoint for CLI usage
  - Expose port 8080 for API server mode
  - Support configuration via environment variables
  - Support volume mounts for tickets directory

### L4: `run_vtic_in_docker(args: List[str], config: DockerRunConfig) -> int`
  - Execute vtic command in Docker container
  - Mount tickets directory from host
  - Pass environment variables for configuration
  - Stream stdout/stderr to host
  - Return exit code from container

### L5: Spec
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install vtic
COPY . .
RUN pip install --no-cache-dir .

# Create tickets directory
RUN mkdir -p /tickets

# Expose API port
EXPOSE 8080

# Default to help
ENTRYPOINT ["vtic"]
CMD ["--help"]
```

```python
@dataclass
class DockerRunConfig:
    image: str = "vtic:latest"
    tickets_dir: str = "./tickets"
    env_vars: Dict[str, str] = field(default_factory=dict)
    port: Optional[int] = None

def run_vtic_in_docker(args: List[str], config: DockerRunConfig) -> int:
    """
    Input: args=["search", "CORS"], 
           config=DockerRunConfig(tickets_dir="/home/user/tickets")
    Action: docker run --rm -v /home/user/tickets:/tickets vtic:latest search CORS
    Output: (stdout from container), return exit code 0
    
    Input: args=["serve"], config=DockerRunConfig(port=8080)
    Action: docker run --rm -p 8080:8080 vtic:latest serve
    Output: (server running), return exit code when container stops
    
    Input: args=["create", "--title", "Bug"], 
           config with env_vars={"VTIC_DEFAULT_REPO": "owner/repo"}
    Action: docker run --rm -e VTIC_DEFAULT_REPO=owner/repo -v ... vtic:latest create --title Bug
    """
```

### L6: Test
```python
test_docker_image_builds_successfully()
test_docker_vtic_init_creates_tickets_dir()
test_docker_vtic_create_writes_to_mounted_volume()
test_docker_vtic_search_reads_from_mounted_volume()
test_docker_vtic_serve_exposes_port()
test_docker_environment_variables_config()
test_docker_cli_exit_codes_propagate()
test_docker_volume_persistence()
```

---

## Feature 9: GitHub Action

### L1: Integration
### L2: CI/CD
### L3: GitHub Action
### L4: `action.yml` (GitHub Action definition)
  - Define action inputs for vtic command and arguments
  - Define action outputs for command result
  - Support ticket creation from GitHub Issues
  - Support search and output to workflow
  - Configure using GitHub secrets for API keys

### L4: `run_vtic_action(inputs: ActionInputs) -> ActionResult`
  - Parse GitHub Action inputs
  - Execute vtic command with inputs
  - Capture output and set action outputs
  - Handle errors and set failed status
  - Return action result

### L5: Spec
```yaml
# action.yml
name: 'vtic'
description: 'Run vtic ticket operations in GitHub Actions'
inputs:
  command:
    description: 'vtic command to run (create, get, update, delete, search, list)'
    required: true
  args:
    description: 'Arguments for the command (JSON string)'
    required: false
    default: '{}'
  tickets-dir:
    description: 'Directory containing tickets'
    required: false
    default: './tickets'
  config:
    description: 'vtic configuration (JSON string)'
    required: false
    default: '{}'

outputs:
  result:
    description: 'Command output (JSON string)'
  exit-code:
    description: 'Exit code from vtic command'

runs:
  using: 'node20'
  main: 'dist/index.js'
```

```python
@dataclass
class ActionInputs:
    command: str
    args: Dict[str, Any]
    tickets_dir: str = "./tickets"
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ActionResult:
    success: bool
    exit_code: int
    output: str
    error: Optional[str] = None
    result_data: Optional[Dict] = None

def run_vtic_action(inputs: ActionInputs) -> ActionResult:
    """
    Input: ActionInputs(command="create", args={"title": "Bug", "repo": "owner/repo"})
    Action: vtic create --title "Bug" --repo "owner/repo"
    Output: ActionResult(success=True, exit_code=0, output="Created C1", 
                         result_data={"id": "C1"})
    
    Input: ActionInputs(command="search", args={"query": "CORS", "format": "json"})
    Action: vtic search CORS --format json
    Output: ActionResult(success=True, exit_code=0, output='[{"id": "C1", ...}]',
                         result_data=[{"id": "C1"}])
    
    Input: ActionInputs(command="invalid")
    Output: ActionResult(success=False, exit_code=1, error="Unknown command: invalid")
    """
```

### L6: Test
```python
test_action_create_ticket()
test_action_search_returns_results()
test_action_get_ticket()
test_action_update_ticket()
test_action_list_tickets()
test_action_invalid_command_fails()
test_action_output_json_parseable()
test_action_exit_code_propagates()
test_action_config_from_inputs()
```

---

## Feature 10: MCP Server

### L1: Integration
### L2: External Tools
### L3: MCP server
### L4: `McpServer` class
  - Implement Model Context Protocol server interface
  - Expose ticket tools: create_ticket, get_ticket, update_ticket, delete_ticket
  - Expose search tools: search_tickets, list_tickets
  - Handle MCP initialization and capability negotiation
  - Support stdio transport for local usage

### L4: `handle_mcp_request(request: McpRequest) -> McpResponse`
  - Parse MCP JSON-RPC request
  - Route to appropriate tool handler
  - Execute tool and format response
  - Handle errors per MCP spec
  - Return MCP-compliant response

### L5: Spec
```python
@dataclass
class McpRequest:
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: Optional[int] = None

@dataclass
class McpResponse:
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

@dataclass
class McpTool:
    name: str
    description: str
    input_schema: Dict[str, Any]  # JSON Schema

class McpServer:
    """
    MCP Server exposing vtic capabilities to AI agents.
    
    Tools exposed:
    - create_ticket: Create a new ticket
    - get_ticket: Get ticket by ID
    - update_ticket: Update ticket fields
    - delete_ticket: Delete a ticket
    - search_tickets: Search tickets with hybrid search
    - list_tickets: List tickets with filters
    - get_stats: Get ticket statistics
    
    Usage: vtic mcp-server
    """
    
    TOOLS = [
        McpTool(
            name="create_ticket",
            description="Create a new ticket with title, repo, and optional fields",
            input_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Ticket title"},
                    "repo": {"type": "string", "description": "Repository (owner/repo)"},
                    "description": {"type": "string", "description": "Ticket description"},
                    "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                    "category": {"type": "string"}
                },
                "required": ["title", "repo"]
            }
        ),
        McpTool(
            name="search_tickets",
            description="Search tickets using hybrid (keyword + semantic) search",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "repo": {"type": "string", "description": "Filter by repo"},
                    "status": {"type": "string", "description": "Filter by status"},
                    "limit": {"type": "integer", "default": 10}
                }
            }
        ),
        # ... more tools
    ]
    
    def handle_request(self, request: McpRequest) -> McpResponse:
        """
        Input: McpRequest(method="tools/call", 
                         params={"name": "create_ticket", 
                                "arguments": {"title": "Bug", "repo": "owner/repo"}})
        Action: Create ticket with provided arguments
        Output: McpResponse(result={"content": [{"type": "text", "text": '{"id": "C1", ...}'}]})
        
        Input: McpRequest(method="initialize", params={...})
        Output: McpResponse(result={"protocolVersion": "2024-11-05", 
                                   "capabilities": {"tools": {}},
                                   "serverInfo": {"name": "vtic", "version": "0.1.0"}})
        
        Input: McpRequest(method="tools/list")
        Output: McpResponse(result={"tools": [...]})
        
        Input: McpRequest(method="unknown")
        Output: McpResponse(error={"code": -32601, "message": "Method not found"})
        """

def run_mcp_server(transport: str = "stdio") -> None:
    """
    Start MCP server with specified transport.
    
    Input: transport="stdio"
    Action: Read MCP requests from stdin, write responses to stdout
    Output: (runs until EOF on stdin)
    
    Input: transport="http" (future)
    Action: Start HTTP server for MCP requests
    """
```

### L6: Test
```python
test_mcp_server_initialize()
test_mcp_server_list_tools()
test_mcp_server_create_ticket_tool()
test_mcp_server_get_ticket_tool()
test_mcp_server_update_ticket_tool()
test_mcp_server_delete_ticket_tool()
test_mcp_server_search_tickets_tool()
test_mcp_server_list_tickets_tool()
test_mcp_server_invalid_tool_error()
test_mcp_server_method_not_found_error()
test_mcp_server_stdio_transport()
test_mcp_tool_input_validation()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function(s) |
|---|----|----|----|----|
| 1 | Multi-Repo Support | Statistics | Per-repo stats | `get_stats_by_repo()` |
| 2 | Multi-Repo Support | Operations | Repo isolation | `filter_tickets_by_repo()`, `cli_with_repo_isolation()` |
| 3 | Multi-Repo Support | Configuration | Repo-specific defaults | `get_repo_defaults()`, `apply_repo_defaults()` |
| 4 | Integration | Webhooks | On-create webhook | `trigger_create_webhook()`, `get_webhook_config_for_event()` |
| 5 | Integration | Webhooks | On-update webhook | `trigger_update_webhook()`, `compute_ticket_changes()` |
| 6 | Integration | Webhooks | On-delete webhook | `trigger_delete_webhook()` |
| 7 | Integration | Webhooks | Webhook payload | `build_webhook_payload()`, `sign_webhook_payload()` |
| 8 | Integration | CI/CD | Docker image | `Dockerfile`, `run_vtic_in_docker()` |
| 9 | Integration | CI/CD | GitHub Action | `action.yml`, `run_vtic_action()` |
| 10 | Integration | External Tools | MCP server | `McpServer`, `handle_mcp_request()`, `run_mcp_server()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Set
from datetime import datetime

# Multi-Repo Support
@dataclass
class RepoStats:
    repo: str
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]

@dataclass
class RepoDefaults:
    category: Optional[str] = None
    severity: Optional[str] = None
    status: Optional[str] = None
    tags: List[str] = field(default_factory=list)

# Webhooks
@dataclass
class WebhookEndpoint:
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    retry_count: int = 0

@dataclass
class WebhookResult:
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    response_body: Optional[str] = None
    duration_ms: int = 0

@dataclass
class WebhookPayload:
    event: str
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class FieldChange:
    field: str
    old_value: Any
    new_value: Any

# Docker/CI
@dataclass
class DockerRunConfig:
    image: str = "vtic:latest"
    tickets_dir: str = "./tickets"
    env_vars: Dict[str, str] = field(default_factory=dict)
    port: Optional[int] = None

@dataclass
class ActionInputs:
    command: str
    args: Dict[str, Any]
    tickets_dir: str = "./tickets"
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ActionResult:
    success: bool
    exit_code: int
    output: str
    error: Optional[str] = None
    result_data: Optional[Dict] = None

# MCP
@dataclass
class McpRequest:
    jsonrpc: str = "2.0"
    method: str
    params: Dict[str, Any]
    id: Optional[int] = None

@dataclass
class McpResponse:
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[int] = None

@dataclass
class McpTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
```
