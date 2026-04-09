# Should Have Features (P1) - Complete 6-Level Breakdown

35 "Should Have" features broken down to implementation-ready specifications.

**Part 0:** Multi-Repo Support, Webhooks, CI/CD Integration (10 features)
**Part 1:** CLI Management Commands, Bulk Operations, Output Formats (12 features)
**Part 2:** CLI Output/Shell Integration, Configuration, Embedding Providers (13 features)

---

# Part 0: Multi-Repo Support, Webhooks, CI/CD Integration

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

# Part 1: CLI Management Commands, Bulk Operations, Output Formats

---

## Feature 11: Config Command

### L1: CLI
### L2: Management Commands
### L3: config command
### L4: `cli_config(args: ConfigArgs, config_manager: ConfigManager) -> int`
  - Parse CLI arguments for config subcommand (show, set, init, get)
  - `show`: Display current merged configuration (global + project + env)
  - `set`: Update a configuration value in appropriate config file
  - `init`: Create new vtic.toml with sensible defaults in current directory
  - `get`: Retrieve single config value by key path
  - Handle global vs project config scope (--global flag)
  - Output in specified format (table, json, toml)
  - Return exit code: 0 success, 1 key not found (for get), 2 validation error

### L5: Spec
```python
@dataclass
class ConfigArgs:
    subcommand: str  # "show", "set", "init", "get"
    key: Optional[str] = None  # e.g., "search.embedding_provider"
    value: Optional[str] = None  # for set
    global_scope: bool = False  # --global flag
    format: str = "table"  # table, json, toml

def cli_config(args: ConfigArgs, config_manager: ConfigManager) -> int:
    """
    # show subcommand
    Input: ConfigArgs(subcommand="show", format="json")
    Output (stdout): {"tickets_dir": "./tickets", "search": {"provider": "openai", ...}, ...}
    Return: 0
    
    # set subcommand
    Input: ConfigArgs(subcommand="set", key="search.embedding_model", value="text-embedding-3-large")
    Action: Update ./vtic.toml with embedding_model = "text-embedding-3-large"
    Output (stdout): "Updated search.embedding_model = text-embedding-3-large"
    Return: 0
    
    # set with --global
    Input: ConfigArgs(subcommand="set", key="defaults.category", value="security", global_scope=True)
    Action: Update ~/.config/vtic/config.toml
    Output (stdout): "Updated defaults.category = security (global)"
    Return: 0
    
    # init subcommand
    Input: ConfigArgs(subcommand="init")
    Action: Create ./vtic.toml with default configuration
    Output (stdout): "Created vtic.toml in /path/to/project"
    Return: 0
    
    # init when file exists
    Input: ConfigArgs(subcommand="init"), vtic.toml already exists
    Output (stderr): "vtic.toml already exists. Use --force to overwrite."
    Return: 1
    
    # get subcommand
    Input: ConfigArgs(subcommand="get", key="search.provider")
    Output (stdout): "openai"
    Return: 0
    
    # get non-existent key
    Input: ConfigArgs(subcommand="get", key="nonexistent.key")
    Output (stderr): "Configuration key not found: nonexistent.key"
    Return: 1
    
    # invalid key format
    Input: ConfigArgs(subcommand="set", key="invalid", value="test")
    Error: ValueError("Invalid configuration key format. Use dot notation: section.key")
    """
```

### L6: Test
```python
test_cli_config_show_outputs_merged_config()
test_cli_config_show_json_format()
test_cli_config_show_toml_format()
test_cli_config_set_updates_project_config()
test_cli_config_set_global_updates_global_config()
test_cli_config_set_creates_missing_sections()
test_cli_config_init_creates_vtic_toml()
test_cli_config_init_fails_if_file_exists()
test_cli_config_init_force_overwrites_existing()
test_cli_config_get_returns_single_value()
test_cli_config_get_nonexistent_key_returns_1()
test_cli_config_set_validates_value_type()
test_cli_config_invalid_key_format_raises()
```

---

## Feature 12: Stats Command

### L1: CLI
### L2: Management Commands
### L3: stats command
### L4: `cli_stats(args: StatsArgs, store: TicketStore) -> int`
  - Aggregate ticket statistics from store
  - Count tickets by status, severity, category, repo
  - Calculate percentages and totals
  - Support --by-repo, --by-category, --by-severity, --by-status flags
  - Support --json, --table output formats
  - Include counts for: total, open, in_progress, blocked, fixed, wont_fix, closed
  - Return exit code: 0 success, 1 no tickets found, 2 error

### L5: Spec
```python
@dataclass
class StatsArgs:
    by_repo: bool = False
    by_category: bool = False
    by_severity: bool = False
    by_status: bool = False
    repo: Optional[str] = None  # filter to specific repo
    format: str = "table"

@dataclass
class TicketStats:
    total: int
    by_status: Dict[str, int]
    by_severity: Dict[str, int]
    by_category: Dict[str, int]
    by_repo: Dict[str, int]

def cli_stats(args: StatsArgs, store: TicketStore) -> int:
    """
    # default stats (all breakdowns)
    Input: StatsArgs()
    Output (stdout):
    ┌─────────────┬───────┬─────────┐
    │ Status      │ Count │ Percent │
    ├─────────────┼───────┼─────────┤
    │ open        │    45 │   45.0% │
    │ in_progress │    20 │   20.0% │
    │ blocked     │     5 │    5.0% │
    │ fixed       │    25 │   25.0% │
    │ wont_fix    │     3 │    3.0% │
    │ closed      │     2 │    2.0% │
    ├─────────────┼───────┼─────────┤
    │ TOTAL       │   100 │  100.0% │
    └─────────────┴───────┴─────────┘
    
    [Similar tables for severity, category, repo]
    Return: 0
    
    # --by-repo only
    Input: StatsArgs(by_repo=True)
    Output (stdout):
    ┌──────────────────────────┬───────┬─────────┐
    │ Repo                     │ Count │ Percent │
    ├──────────────────────────┼───────┼─────────┤
    │ ejacklab/open-dsearch    │    60 │   60.0% │
    │ ejacklab/other-repo      │    40 │   40.0% │
    └──────────────────────────┴───────┴─────────┘
    Return: 0
    
    # --repo filter
    Input: StatsArgs(repo="ejacklab/open-dsearch")
    Output: Stats for only ejacklab/open-dsearch tickets
    Return: 0
    
    # JSON format
    Input: StatsArgs(format="json")
    Output (stdout):
    {
      "total": 100,
      "by_status": {"open": 45, "in_progress": 20, ...},
      "by_severity": {"critical": 10, "high": 25, ...},
      "by_category": {"code": 60, "security": 15, ...},
      "by_repo": {"ejacklab/open-dsearch": 60, ...}
    }
    Return: 0
    
    # no tickets
    Input: StatsArgs(), empty store
    Output (stdout): "No tickets found"
    Return: 1
    """
```

### L6: Test
```python
test_cli_stats_shows_all_breakdowns()
test_cli_stats_by_repo_only()
test_cli_stats_by_category_only()
test_cli_stats_by_severity_only()
test_cli_stats_by_status_only()
test_cli_stats_repo_filter()
test_cli_stats_json_format()
test_cli_stats_empty_store_returns_1()
test_cli_stats_calculates_percentages_correctly()
test_cli_stats_includes_total_row()
test_cli_stats_handles_multiple_repos()
```

---

## Feature 13: Validate Command

### L1: CLI
### L2: Management Commands
### L3: validate command
### L4: `cli_validate(args: ValidateArgs, store: TicketStore) -> int`
  - Scan all ticket files in storage
  - Validate YAML frontmatter syntax
  - Validate required fields present (id, title, repo)
  - Validate field values against constraints (enum values, formats)
  - Validate file naming convention matches ID
  - Validate directory structure matches repo/category
  - Report errors with file path, line number, and description
  - Support --fix flag to auto-correct fixable issues
  - Return exit code: 0 all valid, 1 validation errors found, 2 system error

### L5: Spec
```python
@dataclass
class ValidateArgs:
    fix: bool = False  # auto-fix issues where possible
    strict: bool = False  # warn on non-critical issues
    format: str = "table"  # table, json

@dataclass
class ValidationError:
    file_path: str
    line: Optional[int]
    field: Optional[str]
    message: str
    severity: str  # "error", "warning"
    fixable: bool

def cli_validate(args: ValidateArgs, store: TicketStore) -> int:
    """
    # all valid
    Input: ValidateArgs(), store with 10 valid tickets
    Output (stdout): "✓ All 10 ticket files are valid"
    Return: 0
    
    # validation errors
    Input: ValidateArgs(), store with errors
    Output (stdout):
    ┌────────────────────────────────────┬──────┬─────────┬───────────────────────────────┬──────────┐
    │ File                               │ Line │ Field   │ Error                         │ Fixable  │
    ├────────────────────────────────────┼──────┼─────────┼───────────────────────────────┼──────────┤
    │ tickets/ejacklab/repo/code/C1.md   │ 3    │ title   │ Required field missing        │ No       │
    │ tickets/ejacklab/repo/code/C2.md   │ 5    │ status  │ Invalid value: unknown_status │ Yes      │
    │ tickets/ejacklab/repo/code/C3.md   │ -    │ -       │ YAML parse error at line 8    │ No       │
    └────────────────────────────────────┴──────┴─────────┴───────────────────────────────┴──────────┘
    
    Found 3 errors in 3 files
    Return: 1
    
    # --fix flag
    Input: ValidateArgs(fix=True), store with fixable errors
    Output (stdout):
    Fixed 2 issues:
      - C2.md: status changed from 'unknown_status' to 'open'
      - C4.md: added missing created timestamp
    
    Remaining 1 error (not fixable):
      - C1.md: Required field 'title' missing
    Return: 1
    
    # JSON format
    Input: ValidateArgs(format="json")
    Output (stdout):
    {
      "valid": false,
      "total_files": 10,
      "errors": [
        {"file": "tickets/.../C1.md", "line": 3, "field": "title", "message": "...", "fixable": false}
      ],
      "warnings": []
    }
    Return: 1
    
    # --strict mode (warnings)
    Input: ValidateArgs(strict=True)
    Output: Includes warnings for non-critical issues (e.g., missing optional fields, unusual values)
    """
```

### L6: Test
```python
test_cli_validate_all_valid_returns_0()
test_cli_validate_missing_required_field()
test_cli_validate_invalid_status_value()
test_cli_validate_invalid_severity_value()
test_cli_validate_yaml_syntax_error()
test_cli_validate_fix_auto_corrects_issues()
test_cli_validate_fix_reports_unfixable()
test_cli_validate_strict_mode_shows_warnings()
test_cli_validate_json_format()
test_cli_validate_file_naming_mismatch()
test_cli_validate_directory_structure_mismatch()
test_cli_validate_multiple_errors_in_one_file()
```

---

## Feature 14: Doctor Command

### L1: CLI
### L2: Management Commands
### L3: doctor command
### L4: `cli_doctor(args: DoctorArgs, config_manager: ConfigManager, store: TicketStore) -> int`
  - Run diagnostic checks for common issues
  - Check 1: Config file exists and is valid TOML
  - Check 2: Tickets directory exists and is accessible
  - Check 3: Zvec index exists and is not corrupted
  - Check 4: Index is in sync with ticket files (no orphan entries, no missing tickets)
  - Check 5: Embedding provider is configured and accessible (if semantic search enabled)
  - Check 6: API keys are set (if using remote embedding provider)
  - Check 7: File permissions allow read/write
  - Report status for each check (✓ pass, ✗ fail, ⚠ warning)
  - Provide actionable suggestions for failed checks
  - Return exit code: 0 all pass, 1 some failures, 2 critical failure

### L5: Spec
```python
@dataclass
class DoctorArgs:
    fix: bool = False  # attempt auto-fix where possible
    check: Optional[str] = None  # run specific check only

@dataclass
class DiagnosticResult:
    check_name: str
    status: str  # "pass", "fail", "warning"
    message: str
    suggestion: Optional[str]
    auto_fixable: bool

def cli_doctor(args: DoctorArgs, config_manager: ConfigManager, store: TicketStore) -> int:
    """
    # all checks pass
    Input: DoctorArgs()
    Output (stdout):
    Running diagnostics...
    
    ✓ Config file: Valid (./vtic.toml)
    ✓ Tickets directory: Exists and accessible (./tickets)
    ✓ Zvec index: Valid and synced (142 tickets indexed)
    ✓ Embedding provider: OpenAI configured
    ✓ API key: OPENAI_API_KEY is set
    ✓ File permissions: Read/write access confirmed
    
    All checks passed!
    Return: 0
    
    # some failures
    Input: DoctorArgs()
    Output (stdout):
    Running diagnostics...
    
    ✓ Config file: Valid (./vtic.toml)
    ✗ Tickets directory: Not found (./tickets)
      → Suggestion: Run 'vtic init' to create tickets directory
    ✗ Zvec index: Not found (.vtic/index)
      → Suggestion: Run 'vtic reindex' to build index
    ⚠ Embedding provider: No provider configured
      → Suggestion: Set search.embedding_provider in vtic.toml (or use BM25 only)
    ✓ API key: N/A (no remote provider configured)
    ✓ File permissions: Read/write access confirmed
    
    2 failures, 1 warning
    Return: 1
    
    # --fix flag
    Input: DoctorArgs(fix=True)
    Action: Auto-create missing directories, reindex if needed
    Output (stdout):
    Running diagnostics with auto-fix...
    
    ✗ Tickets directory: Not found
      → Fixed: Created ./tickets
    ✗ Zvec index: Not found
      → Fixed: Running reindex... Indexed 0 tickets
    ⚠ Embedding provider: No provider configured
      → Cannot auto-fix: Manual configuration required
    
    Fixed 2 issues. 1 warning remains.
    Return: 1
    
    # specific check only
    Input: DoctorArgs(check="index")
    Output (stdout):
    ✓ Zvec index: Valid and synced (142 tickets indexed)
    Return: 0
    """
```

### L6: Test
```python
test_cli_doctor_all_checks_pass()
test_cli_doctor_missing_config_file()
test_cli_doctor_invalid_config_toml()
test_cli_doctor_missing_tickets_directory()
test_cli_doctor_missing_index()
test_cli_doctor_index_out_of_sync()
test_cli_doctor_embedding_provider_not_configured()
test_cli_doctor_missing_api_key()
test_cli_doctor_file_permission_issues()
test_cli_doctor_fix_creates_missing_directories()
test_cli_doctor_fix_reindexes_if_needed()
test_cli_doctor_specific_check_only()
test_cli_doctor_reports_suggestions()
```

---

## Feature 15: Trash Command

### L1: CLI
### L2: Management Commands
### L3: trash command
### L4: `cli_trash(args: TrashArgs, store: TicketStore) -> int`
  - Manage soft-deleted tickets in .trash/ directory
  - `list`: Show all trashed tickets with deletion date
  - `restore`: Move ticket from .trash/ back to active tickets
  - `clean`: Permanently delete old trashed tickets (--older-than)
  - `show`: Display contents of a trashed ticket
  - Support --format for list output (table, json)
  - Return exit code: 0 success, 1 not found, 2 error

### L5: Spec
```python
@dataclass
class TrashArgs:
    subcommand: str  # "list", "restore", "clean", "show"
    ticket_id: Optional[str] = None
    older_than: Optional[str] = None  # e.g., "30d", "1w"
    format: str = "table"
    force: bool = False  # skip confirmation for clean

@dataclass
class TrashedTicket:
    id: str
    original_path: str
    deleted_at: str  # ISO 8601
    metadata: Dict[str, Any]

def cli_trash(args: TrashArgs, store: TicketStore) -> int:
    """
    # list subcommand
    Input: TrashArgs(subcommand="list")
    Output (stdout):
    ┌──────┬────────────────────────────┬─────────────────────────┬──────────────────────────┐
    │ ID   │ Title                      │ Original Path           │ Deleted At               │
    ├──────┼────────────────────────────┼─────────────────────────┼──────────────────────────┤
    │ C5   │ Fix login bug              │ ejacklab/repo/code/C5   │ 2026-03-15T10:30:00Z     │
    │ S2   │ Security vulnerability     │ ejacklab/repo/security  │ 2026-03-10T08:15:00Z     │
    └──────┴────────────────────────────┴─────────────────────────┴──────────────────────────┘
    
    2 trashed tickets
    Return: 0
    
    # restore subcommand
    Input: TrashArgs(subcommand="restore", ticket_id="C5")
    Action: Move .trash/C5.md back to tickets/ejacklab/repo/code/C5.md
            Re-add to Zvec index
    Output (stdout): "Restored C5 to tickets/ejacklab/repo/code/C5.md"
    Return: 0
    
    # restore non-existent
    Input: TrashArgs(subcommand="restore", ticket_id="NONEXISTENT")
    Output (stderr): "Ticket NONEXISTENT not found in trash"
    Return: 1
    
    # show subcommand
    Input: TrashArgs(subcommand="show", ticket_id="C5")
    Output (stdout): Full ticket content (markdown + frontmatter)
    Return: 0
    
    # clean subcommand
    Input: TrashArgs(subcommand="clean", older_than="30d")
    Action: Permanently delete tickets trashed more than 30 days ago
    Output (stdout): "Permanently deleted 3 tickets older than 30 days"
    Return: 0
    
    # clean with confirmation
    Input: TrashArgs(subcommand="clean", older_than="7d", force=False)
    Output (stdout): "Delete 5 tickets older than 7 days? [y/N]: "
    # If user enters 'y': proceed with deletion
    # If user enters 'n': "Cancelled"
    Return: 0 or 2 (if cancelled)
    
    # clean --force (no confirmation)
    Input: TrashArgs(subcommand="clean", older_than="7d", force=True)
    Output (stdout): "Permanently deleted 5 tickets older than 7 days"
    Return: 0
    
    # empty trash
    Input: TrashArgs(subcommand="list"), empty trash
    Output (stdout): "No trashed tickets"
    Return: 0
    """
```

### L6: Test
```python
test_cli_trash_list_shows_trashed_tickets()
test_cli_trash_list_empty_trash()
test_cli_trash_list_json_format()
test_cli_trash_restore_moves_back_to_active()
test_cli_trash_restore_reindexes()
test_cli_trash_restore_nonexistent_returns_1()
test_cli_trash_show_displays_content()
test_cli_trash_clean_deletes_old_tickets()
test_cli_trash_clean_older_than_days()
test_cli_trash_clean_older_than_weeks()
test_cli_trash_clean_prompts_without_force()
test_cli_trash_clean_force_skips_prompt()
test_cli_trash_clean_no_matching_tickets()
test_cli_trash_restore_preserves_original_path()
```

---

## Feature 16: Bulk Create CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk create CLI
### L4: `cli_bulk_create(args: BulkCreateArgs, store: TicketStore) -> int`
  - Read tickets from JSON/JSONL file specified by --from
  - Parse and validate each ticket object
  - Generate IDs for tickets without specified ID
  - Create all tickets in batch with progress indicator
  - Report success/failure count with details
  - Support --dry-run to preview without creating
  - Support --on-error (stop, continue, rollback)
  - Return exit code: 0 all success, 1 partial failure, 2 all failed

### L5: Spec
```python
@dataclass
class BulkCreateArgs:
    from_file: str  # --from, path to JSON/JSONL file
    dry_run: bool = False
    on_error: str = "stop"  # "stop", "continue", "rollback"
    format: str = "table"

@dataclass
class BulkCreateResult:
    total: int
    created: int
    failed: int
    errors: List[Tuple[int, str, str]]  # (index, ticket_id_or_title, error_message)
    created_ids: List[str]

def cli_bulk_create(args: BulkCreateArgs, store: TicketStore) -> int:
    """
    # successful bulk create
    Input: BulkCreateArgs(from_file="tickets.json"), file contains:
    [
      {"title": "Bug 1", "repo": "owner/repo", "severity": "high"},
      {"title": "Bug 2", "repo": "owner/repo", "severity": "medium"},
      {"title": "Bug 3", "repo": "owner/repo", "severity": "low"}
    ]
    Output (stdout):
    Creating tickets from tickets.json...
    ████████████████████████████████████ 100% | 3/3
    
    ✓ Created 3 tickets: C10, C11, C12
    Return: 0
    
    # with validation errors (on_error=stop)
    Input: BulkCreateArgs(from_file="tickets.json", on_error="stop"), file contains:
    [
      {"title": "Valid", "repo": "owner/repo"},
      {"title": "", "repo": "owner/repo"},  # invalid: empty title
      {"title": "Also Valid", "repo": "owner/repo"}
    ]
    Output (stdout):
    Creating tickets from tickets.json...
    ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ 6% | 1/3
    
    ✗ Error at index 1: Title is required
    Stopped on error (use --on-error=continue to skip)
    
    Created: 1
    Failed: 1
    Remaining: 1 (not processed)
    Return: 1
    
    # with validation errors (on_error=continue)
    Input: BulkCreateArgs(from_file="tickets.json", on_error="continue")
    Output (stdout):
    Creating tickets from tickets.json...
    ████████████████████████████████████ 100% | 3/3
    
    ✓ Created 2 tickets: C10, C12
    ✗ Failed 1 ticket:
      - Index 1: Title is required
    
    Created: 2 | Failed: 1
    Return: 1
    
    # --dry-run
    Input: BulkCreateArgs(from_file="tickets.json", dry_run=True)
    Output (stdout):
    Dry run: validating 3 tickets...
    ✓ All 3 tickets valid
    Would create: C10, C11, C12
    No tickets created (dry run)
    Return: 0
    
    # on_error=rollback
    Input: BulkCreateArgs(from_file="tickets.json", on_error="rollback")
    Action: If any error occurs, delete all created tickets in this batch
    Output (stdout):
    Creating tickets from tickets.json...
    Error at index 2. Rolling back 1 created ticket...
    Rolled back C10
    No tickets created (rolled back due to error)
    Return: 2
    """
```

### L6: Test
```python
test_cli_bulk_create_from_json()
test_cli_bulk_create_from_jsonl()
test_cli_bulk_create_generates_ids()
test_cli_bulk_create_preserves_specified_ids()
test_cli_bulk_create_dry_run()
test_cli_bulk_create_on_error_stop()
test_cli_bulk_create_on_error_continue()
test_cli_bulk_create_on_error_rollback()
test_cli_bulk_create_shows_progress()
test_cli_bulk_create_file_not_found()
test_cli_bulk_create_invalid_json()
test_cli_bulk_create_validation_error()
test_cli_bulk_create_all_fail_returns_2()
test_cli_bulk_create_large_batch()
```

---

## Feature 17: Bulk Update CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk update CLI
### L4: `cli_bulk_update(args: BulkUpdateArgs, store: TicketStore) -> int`
  - Filter tickets matching --filter criteria (status, severity, category, repo, etc.)
  - Apply field updates specified by --set flags
  - Support multiple --set flags (e.g., --set status=fixed --set severity=low)
  - Show preview of affected tickets before update
  - Require --yes flag to skip confirmation
  - Support --dry-run to preview without updating
  - Update `updated` timestamp on all modified tickets
  - Report count of updated tickets
  - Return exit code: 0 success, 1 no matches, 2 error

### L5: Spec
```python
@dataclass
class BulkUpdateArgs:
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None  # supports glob patterns
    set_fields: List[str] = field(default_factory=list)  # ["status=fixed", "severity=low"]
    dry_run: bool = False
    yes: bool = False
    limit: Optional[int] = None  # max tickets to update

def cli_bulk_update(args: BulkUpdateArgs, store: TicketStore) -> int:
    """
    # basic bulk update
    Input: BulkUpdateArgs(filter_status="open", set_fields=["status=reviewing"], yes=True)
    Output (stdout):
    Updating tickets with status=open to status=reviewing...
    ████████████████████████████████████ 100% | 15/15
    
    ✓ Updated 15 tickets
    Return: 0
    
    # multiple field updates
    Input: BulkUpdateArgs(
        filter_status="fixed",
        set_fields=["status=closed", "severity=low"],
        yes=True
    )
    Output (stdout):
    Updating tickets with status=fixed...
      - status: fixed → closed
      - severity: <varies> → low
    
    ████████████████████████████████████ 100% | 8/8
    ✓ Updated 8 tickets
    Return: 0
    
    # with confirmation
    Input: BulkUpdateArgs(filter_severity="critical", set_fields=["severity=high"], yes=False)
    Output (stdout):
    Found 5 tickets matching filter:
      - C1: CORS Bug (severity: critical → high)
      - C3: Auth issue (severity: critical → high)
      - C5: Memory leak (severity: critical → high)
      - S1: SQL injection (severity: critical → high)
      - S2: XSS vulnerability (severity: critical → high)
    
    Update these 5 tickets? [y/N]: _
    # If 'y': proceed with update
    # If 'n': "Cancelled"
    Return: 0 or 2
    
    # --dry-run
    Input: BulkUpdateArgs(
        filter_repo="ejacklab/*",
        set_fields=["category=security"],
        dry_run=True
    )
    Output (stdout):
    Dry run: would update 20 tickets in ejacklab/*
      - All would have category set to 'security'
    No tickets updated (dry run)
    Return: 0
    
    # no matches
    Input: BulkUpdateArgs(filter_status="nonexistent", set_fields=["status=fixed"])
    Output (stdout): "No tickets match the specified filters"
    Return: 1
    """
```

### L6: Test
```python
test_cli_bulk_update_by_status()
test_cli_bulk_update_by_severity()
test_cli_bulk_update_by_category()
test_cli_bulk_update_by_repo()
test_cli_bulk_update_by_repo_glob()
test_cli_bulk_update_multiple_fields()
test_cli_bulk_update_confirmation_prompt()
test_cli_bulk_update_yes_skips_prompt()
test_cli_bulk_update_dry_run()
test_cli_bulk_update_no_matches()
test_cli_bulk_update_with_limit()
test_cli_bulk_update_invalid_field()
test_cli_bulk_update_updates_timestamp()
test_cli_bulk_update_combined_filters()
```

---

## Feature 18: Bulk Delete CLI

### L1: CLI
### L2: Bulk Operations
### L3: Bulk delete CLI
### L4: `cli_bulk_delete(args: BulkDeleteArgs, store: TicketStore) -> int`
  - Filter tickets matching --filter criteria
  - Require --all flag to confirm bulk deletion
  - Require --yes flag to skip confirmation prompt
  - Support --force for hard delete (default is soft delete to trash)
  - Show preview of affected tickets
  - Report count of deleted tickets
  - Support --dry-run to preview without deleting
  - Return exit code: 0 success, 1 no matches, 2 cancelled/error

### L5: Spec
```python
@dataclass
class BulkDeleteArgs:
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None
    all: bool = False  # required to confirm bulk delete
    force: bool = False  # hard delete instead of trash
    yes: bool = False  # skip confirmation
    dry_run: bool = False
    limit: Optional[int] = None

def cli_bulk_delete(args: BulkDeleteArgs, store: TicketStore) -> int:
    """
    # basic bulk delete (soft)
    Input: BulkDeleteArgs(filter_status="wont_fix", all=True, yes=True)
    Action: Move all wont_fix tickets to .trash/
    Output (stdout):
    Deleting tickets with status=wont_fix...
    ████████████████████████████████████ 100% | 5/5
    
    ✓ Deleted 5 tickets (moved to trash)
    Return: 0
    
    # hard delete (--force)
    Input: BulkDeleteArgs(filter_status="closed", all=True, force=True, yes=True)
    Action: Permanently delete all closed tickets
    Output (stdout):
    Permanently deleting tickets with status=closed...
    ████████████████████████████████████ 100% | 12/12
    
    ⚠ Permanently deleted 12 tickets
    Return: 0
    
    # missing --all flag
    Input: BulkDeleteArgs(filter_status="closed")
    Output (stderr): "Bulk delete requires --all flag for safety"
    Return: 2
    
    # --dry-run
    Input: BulkDeleteArgs(filter_repo="test/*", all=True, dry_run=True)
    Output (stdout):
    Dry run: would delete 15 tickets in test/*
      - C30: Old feature
      - C31: Deprecated API
      ...
    No tickets deleted (dry run)
    Return: 0
    """
```

### L6: Test
```python
test_cli_bulk_delete_by_status()
test_cli_bulk_delete_by_category()
test_cli_bulk_delete_by_repo()
test_cli_bulk_delete_by_repo_glob()
test_cli_bulk_delete_soft_delete_to_trash()
test_cli_bulk_delete_hard_delete_with_force()
test_cli_bulk_delete_requires_all_flag()
test_cli_bulk_delete_confirmation_prompt()
test_cli_bulk_delete_yes_skips_prompt()
test_cli_bulk_delete_dry_run()
test_cli_bulk_delete_no_matches()
test_cli_bulk_delete_with_limit()
test_cli_bulk_delete_combined_filters()
test_cli_bulk_delete_cancellable()
```

---

## Feature 19: Export CLI

### L1: CLI
### L2: Bulk Operations
### L3: Export CLI
### L4: `cli_export(args: ExportArgs, store: TicketStore) -> int`
  - Export tickets to specified format (json, jsonl, csv, markdown, tar.gz)
  - Support --output to specify output file (default: stdout for text formats)
  - Support --filter to export subset of tickets
  - Support --fields to export only specific fields
  - Support --include-deleted to include trashed tickets
  - For tar.gz: create archive with all markdown files and index metadata
  - Report count of exported tickets
  - Return exit code: 0 success, 1 no tickets, 2 error

### L5: Spec
```python
@dataclass
class ExportArgs:
    format: str  # json, jsonl, csv, markdown, tar.gz
    output: Optional[str] = None  # file path, defaults to stdout
    filter_status: Optional[str] = None
    filter_severity: Optional[str] = None
    filter_category: Optional[str] = None
    filter_repo: Optional[str] = None
    fields: Optional[List[str]] = None  # --fields id,title,status
    include_deleted: bool = False
    pretty: bool = False  # for JSON, pretty-print

def cli_export(args: ExportArgs, store: TicketStore) -> int:
    """
    # JSON export to stdout
    Input: ExportArgs(format="json")
    Output (stdout):
    [
      {"id": "C1", "title": "CORS Bug", "repo": "owner/repo", ...},
      {"id": "C2", "title": "Auth issue", "repo": "owner/repo", ...}
    ]
    Return: 0
    
    # JSON export to file
    Input: ExportArgs(format="json", output="tickets.json")
    Action: Write JSON to tickets.json
    Output (stdout): "Exported 50 tickets to tickets.json"
    Return: 0
    
    # CSV export
    Input: ExportArgs(format="csv", output="tickets.csv")
    Action: Write CSV to tickets.csv with header row
    Output (stdout): "Exported 50 tickets to tickets.csv"
    
    # tar.gz archive
    Input: ExportArgs(format="tar.gz", output="backup.tar.gz")
    Action: Create tar.gz with:
      - All markdown files preserving directory structure
      - .vtic/index metadata
      - manifest.json with export metadata
    Output (stdout): "Created backup.tar.gz with 50 tickets (2.3 MB)"
    Return: 0
    """
```

### L6: Test
```python
test_cli_export_json_to_stdout()
test_cli_export_json_to_file()
test_cli_export_json_pretty()
test_cli_export_jsonl()
test_cli_export_csv()
test_cli_export_csv_with_fields()
test_cli_export_markdown()
test_cli_export_tar_gz()
test_cli_export_with_filter_status()
test_cli_export_with_filter_repo()
test_cli_export_include_deleted()
test_cli_export_no_tickets()
test_cli_export_invalid_format()
test_cli_export_tar_gz_preserves_structure()
test_cli_export_csv_handles_special_chars()
```

---

## Feature 20: Import CLI

### L1: CLI
### L2: Bulk Operations
### L3: Import CLI
### L4: `cli_import(args: ImportArgs, store: TicketStore) -> int`
  - Import tickets from JSON, JSONL, CSV, or tar.gz archive
  - Detect format from file extension or --format flag
  - For tar.gz: extract and import markdown files
  - Handle duplicate IDs: skip, error, or rename (--on-duplicate)
  - Generate new IDs for tickets without IDs
  - Support --id-map to export mapping of old→new IDs
  - Support --dry-run to validate without importing
  - Validate all tickets before import
  - Report success/failure with details
  - Return exit code: 0 success, 1 partial failure, 2 all failed

### L5: Spec
```python
@dataclass
class ImportArgs:
    file: str  # path to import file
    format: Optional[str] = None  # auto-detect from file extension if not specified
    on_duplicate: str = "error"  # "skip", "error", "rename"
    dry_run: bool = False
    id_map: Optional[str] = None  # --id-map file to write ID mappings
    validate_only: bool = False  # validate but don't import

@dataclass
class ImportResult:
    total: int
    imported: int
    skipped: int
    errors: List[Tuple[int, str, str]]  # (index, id, error)
    id_mappings: Dict[str, str]  # old_id -> new_id

def cli_import(args: ImportArgs, store: TicketStore) -> int:
    """
    # JSON import
    Input: ImportArgs(file="tickets.json"), file contains valid tickets
    Output (stdout):
    Importing from tickets.json...
    ████████████████████████████████████ 100% | 20/20
    
    ✓ Imported 20 tickets
    Return: 0
    
    # duplicate handling: rename
    Input: ImportArgs(file="tickets.json", on_duplicate="rename")
    Output (stdout):
    Importing from tickets.json...
    ⚠ Renamed 3 duplicate IDs:
      - C1 → C20
      - C5 → C21
      - S2 → S10
    ✓ Imported 20 tickets
    Return: 0
    
    # --dry-run
    Input: ImportArgs(file="tickets.json", dry_run=True)
    Output (stdout):
    Dry run: validating 20 tickets...
    ✓ All 20 tickets valid
    Would import: C1, C2, C3, ...
    No tickets imported (dry run)
    Return: 0
    """
```

### L6: Test
```python
test_cli_import_from_json()
test_cli_import_from_jsonl()
test_cli_import_from_csv()
test_cli_import_from_csv_with_column_mapping()
test_cli_import_from_tar_gz()
test_cli_import_duplicate_error()
test_cli_import_duplicate_skip()
test_cli_import_duplicate_rename()
test_cli_import_id_map()
test_cli_import_dry_run()
test_cli_import_validation_error()
test_cli_import_file_not_found()
test_cli_import_invalid_json()
test_cli_import_generates_missing_ids()
test_cli_import_preserves_existing_ids()
test_cli_import_csv_handles_quotes()
```

---

## Feature 21: Markdown Output

### L1: CLI
### L2: Output Formats
### L3: Markdown output
### L4: `format_markdown(tickets: Union[Ticket, List[Ticket]], mode: str = "single") -> str`
  - Format single ticket or list of tickets as Markdown
  - Single ticket mode: full markdown with frontmatter and content
  - List mode: summary table with links/details
  - Support --template for custom markdown templates
  - Include all ticket fields in structured format
  - Generate clickable links for repo, file_refs
  - Format tags as markdown links or badges
  - Support syntax highlighting for code in description/fix

### L5: Spec
```python
@dataclass
class MarkdownFormatOptions:
    mode: str = "single"  # "single", "list", "summary"
    template: Optional[str] = None  # path to custom template
    include_frontmatter: bool = True
    include_content: bool = True
    syntax_highlight: bool = True

def format_markdown(
    tickets: Union[Ticket, List[Ticket]], 
    options: MarkdownFormatOptions = MarkdownFormatOptions()
) -> str:
    """
    # single ticket (default)
    Input: Ticket(id="C1", title="CORS Bug", repo="owner/repo", 
                  description="The API returns `Access-Control-Allow-Origin: *`",
                  severity="critical", status="open", category="code",
                  tags=["security", "api"], created="2026-03-15T10:00:00Z")
    Output:
    ---
    id: C1
    title: CORS Bug
    repo: owner/repo
    category: code
    severity: critical
    status: open
    tags:
      - security
      - api
    created: "2026-03-15T10:00:00Z"
    updated: "2026-03-15T10:00:00Z"
    ---
    
    # CORS Bug
    
    The API returns `Access-Control-Allow-Origin: *`
    
    **Severity:** critical  
    **Status:** open  
    **Repo:** [owner/repo](https://github.com/owner/repo)
    
    **Tags:** `security` `api`
    
    # list mode
    Input: List of 3 tickets, options.mode="list"
    Output:
    # Tickets (3)
    
    | ID | Title | Status | Severity | Repo |
    |----|-------|--------|----------|------|
    | C1 | CORS Bug | open | critical | owner/repo |
    | C2 | Auth issue | in_progress | high | owner/repo |
    | S1 | SQL injection | fixed | critical | owner/repo |
    """
```

### L6: Test
```python
test_format_markdown_single_ticket()
test_format_markdown_single_with_all_fields()
test_format_markdown_list_mode()
test_format_markdown_summary_mode()
test_format_markdown_with_frontmatter()
test_format_markdown_without_frontmatter()
test_format_markdown_with_code_blocks()
test_format_markdown_syntax_highlighting()
test_format_markdown_tags_as_badges()
test_format_markdown_repo_links()
test_format_markdown_file_ref_links()
test_format_markdown_custom_template()
test_format_markdown_empty_list()
test_format_markdown_special_characters_escaped()
```

---

## Feature 22: CSV Output

### L1: CLI
### L2: Output Formats
### L3: CSV output
### L4: `format_csv(tickets: List[Ticket], options: CSVFormatOptions) -> str`
  - Format list of tickets as CSV with header row
  - Support --fields to select specific columns
  - Support --delimiter for custom delimiter (default: comma)
  - Handle special characters (quotes, commas, newlines) with proper escaping
  - Support --no-header to omit header row
  - Flatten complex fields (tags as semicolon-separated)
  - Include all standard fields by default
  - Support custom column names via --column-names

### L5: Spec
```python
@dataclass
class CSVFormatOptions:
    fields: Optional[List[str]] = None  # specific fields to include
    delimiter: str = ","
    quote_char: str = '"'
    include_header: bool = True
    column_names: Optional[Dict[str, str]] = None  # field -> column name mapping
    flatten_arrays: str = ";"  # delimiter for array fields like tags

def format_csv(tickets: List[Ticket], options: CSVFormatOptions = CSVFormatOptions()) -> str:
    """
    # default CSV output
    Input: List of 2 tickets
    Output:
    id,title,repo,category,severity,status,description,tags,created,updated
    C1,CORS Bug,owner/repo,code,critical,open,"The API returns *",security;api,2026-03-15T10:00:00Z,2026-03-15T10:00:00Z
    C2,Auth issue,owner/repo,security,high,in_progress,"Auth bypass in login",security,2026-03-14T09:00:00Z,2026-03-16T11:00:00Z
    
    # with --fields
    Input: options.fields=["id", "title", "status"]
    Output:
    id,title,status
    C1,CORS Bug,open
    C2,Auth issue,in_progress
    
    # custom delimiter (tab-separated)
    Input: options.delimiter="\t"
    Output:
    id	title	repo	category	...
    C1	CORS Bug	owner/repo	code	...
    """
```

### L6: Test
```python
test_format_csv_default()
test_format_csv_with_fields()
test_format_csv_custom_delimiter()
test_format_csv_tab_separated()
test_format_csv_quotes_escaping()
test_format_csv_comma_in_value()
test_format_csv_newline_in_value()
test_format_csv_flatten_tags()
test_format_csv_flatten_file_refs()
test_format_csv_custom_column_names()
test_format_csv_no_header()
test_format_csv_empty_list()
test_format_csv_all_fields()
test_format_csv_unicode_handling()
test_format_csv_empty_optional_fields()
```

---

# Part 2: CLI Output/Shell Integration, Configuration, Embedding Providers

---

## Feature 23: Quiet Mode

### L1: CLI
### L2: Output Formats
### L3: Quiet mode
### L4: `configure_quiet_mode(args: Namespace) -> OutputConfig`
  - Parse `-q` / `--quiet` flag from CLI arguments
  - When enabled: suppress all non-essential output (progress bars, spinners, status messages)
  - Output only essential data: IDs, single results, exit codes
  - Affects: create (outputs ID only), list (outputs IDs only), search (outputs IDs + scores only)
  - Does NOT suppress errors (stderr still shows errors)
  - Returns OutputConfig with `quiet: bool` flag for downstream functions

### L5: Spec
```python
@dataclass
class OutputConfig:
    quiet: bool = False
    verbose: bool = False
    color: str = "auto"  # "auto", "always", "never"
    format: str = "table"

def configure_quiet_mode(args: Namespace) -> OutputConfig:
    """
    Input: Namespace(quiet=True, format="table")
    Output: OutputConfig(quiet=True, verbose=False, color="auto", format="table")
    
    Input: Namespace(quiet=False)
    Output: OutputConfig(quiet=False, ...)
    
    Note: quiet=True + verbose=True is invalid → quiet takes precedence
    """

def format_output_for_quiet(data: Any, command: str, config: OutputConfig) -> str:
    """
    Input: data=[Ticket(id="C1"), Ticket(id="C2")], command="list", config.quiet=True
    Output: "C1\nC2"
    
    Input: data=Ticket(id="C1", title="Bug"), command="create", config.quiet=True
    Output: "C1"
    """
```

### L6: Test
```python
test_quiet_mode_flag_sets_output_config()
test_quiet_mode_list_outputs_ids_only()
test_quiet_mode_create_outputs_id_only()
test_quiet_mode_search_outputs_id_score_only()
test_quiet_mode_errors_still_output_to_stderr()
test_quiet_mode_overrides_verbose_if_both_set()
test_quiet_mode_with_json_format_outputs_compact_json()
```

---

## Feature 24: Verbose Mode

### L1: CLI
### L2: Output Formats
### L3: Verbose mode
### L4: `configure_verbose_mode(args: Namespace) -> OutputConfig`
  - Parse `-v` / `--verbose` flag from CLI arguments
  - When enabled: output detailed operation logs to stderr
  - Logs include: file paths being read/written, API calls made, timing info, internal state
  - Format: `[VERBOSE] <timestamp> <message>`
  - Does NOT affect stdout (data output remains same)
  - Compatible with all commands for debugging/audit

### L5: Spec
```python
import sys
from datetime import datetime

VERBOSE_PREFIX = "[VERBOSE]"

def configure_verbose_mode(args: Namespace) -> OutputConfig:
    """
    Input: Namespace(verbose=True)
    Output: OutputConfig(quiet=False, verbose=True, ...)
    """

def verbose_log(message: str, config: OutputConfig) -> None:
    """
    Log message to stderr if verbose mode enabled.
    
    Input: message="Reading file: tickets/owner/repo/C1.md", config.verbose=True
    Output (stderr): "[VERBOSE] 2026-03-17T10:00:00Z Reading file: tickets/owner/repo/C1.md"
    """
```

### L6: Test
```python
test_verbose_mode_flag_sets_output_config()
test_verbose_mode_outputs_to_stderr_not_stdout()
test_verbose_mode_includes_timestamp()
test_verbose_mode_logs_file_operations()
test_verbose_mode_logs_api_calls()
test_verbose_mode_disabled_outputs_nothing()
test_verbose_mode_with_quiet_uses_quiet_precedence()
test_verbose_format_includes_prefix()
```

---

## Feature 25: Color Control

### L1: CLI
### L2: Output Formats
### L3: Color control
### L4: `configure_color_output(args: Namespace) -> ColorConfig`
  - Parse `--color` flag with values: `auto` (default), `always`, `never`
  - `auto`: enable colors if stdout is TTY, disable if piped/redirected
  - `always`: force colors even when piped (useful for `| less -R`)
  - `never`: disable colors (for scripts, logs, colorblind users)
  - Apply to all ANSI color codes in output (status colors, severity colors, highlights)
  - Store in ColorConfig for use by formatting functions

### L5: Spec
```python
import sys
from typing import Literal

ColorMode = Literal["auto", "always", "never"]

@dataclass
class ColorConfig:
    enabled: bool
    mode: ColorMode

# ANSI color codes
COLORS = {
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "gray": "\033[90m",
    "reset": "\033[0m",
    "bold": "\033[1m",
}

STATUS_COLORS = {
    "open": "blue",
    "in_progress": "yellow",
    "blocked": "red",
    "fixed": "green",
    "wont_fix": "gray",
    "closed": "gray",
}

SEVERITY_COLORS = {
    "critical": "red",
    "high": "yellow",
    "medium": "yellow",
    "low": "blue",
}

def configure_color_output(args: Namespace) -> ColorConfig:
    """
    Input: Namespace(color="auto"), sys.stdout.isatty()=True
    Output: ColorConfig(enabled=True, mode="auto")
    
    Input: Namespace(color="never")
    Output: ColorConfig(enabled=False, mode="never")
    """

def colorize(text: str, color: str, config: ColorConfig) -> str:
    """
    Input: text="open", color="blue", config.enabled=True
    Output: "\033[34mopen\033[0m"
    
    Input: text="open", color="blue", config.enabled=False
    Output: "open"
    """
```

### L6: Test
```python
test_color_auto_enables_on_tty()
test_color_auto_disables_on_pipe()
test_color_always_enables_regardless_of_tty()
test_color_never_disables_regardless_of_tty()
test_colorize_returns_colored_text_when_enabled()
test_colorize_returns_plain_text_when_disabled()
test_colorize_status_uses_correct_mapping()
test_colorize_severity_uses_correct_mapping()
test_color_codes_are_valid_ansi()
test_color_reset_appended_correctly()
```

---

## Feature 26: Tab Completion

### L1: CLI
### L2: Shell Integration
### L3: Tab completion
### L4: `generate_completion_script(shell: str) -> str`
  - Generate shell completion script for Bash, Zsh, Fish
  - Complete: commands (init, create, get, update, delete, list, search, serve, etc.)
  - Complete: options (--status, --severity, --repo, --format, etc.)
  - Complete: option values where finite (--status open|in_progress|blocked|...)
  - Complete: ticket IDs dynamically by reading from store (for get, update, delete)
  - Use argparse's built-in completion metadata where possible
  - Output shell-specific script to stdout

### L5: Spec
```python
from typing import Literal

ShellType = Literal["bash", "zsh", "fish", "powershell"]

COMMANDS = [
    "init", "create", "get", "update", "delete", "list", "search", "serve",
    "reindex", "config", "stats", "validate", "doctor", "trash", "backup",
    "migrate", "completion", "export", "import",
]

COMMAND_OPTIONS = {
    "create": ["--title", "--description", "--repo", "--category", "--severity", ...],
    "get": ["--format", "--fields", "--raw", ...],
    "update": ["--status", "--severity", "--title", ...],
    ...
}

OPTION_VALUES = {
    "--status": ["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"],
    "--severity": ["critical", "high", "medium", "low"],
    "--category": ["code", "security", "hotfix", "maintenance", "docs", "infra"],
    "--format": ["table", "json", "markdown", "yaml", "csv"],
    "--color": ["auto", "always", "never"],
}

def generate_completion_script(shell: ShellType) -> str:
    """
    Input: shell="bash"
    Output: Bash completion script using complete -F _vtic vtic
    
    Input: shell="zsh"
    Output: Zsh completion script with #compdef vtic
    
    Input: shell="fish"
    Output: Fish completion script with complete -c vtic
    """

def get_dynamic_completions(completion_type: str, store: TicketStore) -> List[str]:
    """
    Input: completion_type="ids", store with tickets C1, C2, S1
    Output: ["C1", "C2", "S1"]
    """
```

### L6: Test
```python
test_generate_completion_script_bash()
test_generate_completion_script_zsh()
test_generate_completion_script_fish()
test_bash_script_contains_all_commands()
test_bash_script_contains_command_options()
test_bash_script_contains_option_values()
test_zsh_script_valid_syntax()
test_fish_script_valid_syntax()
test_get_dynamic_completions_returns_ids()
test_get_dynamic_completions_returns_repos()
test_cli_complete_outputs_ids_for_get_command()
test_completion_script_includes_description_for_commands()
```

---

## Feature 27: Completion Install

### L1: CLI
### L2: Shell Integration
### L3: Completion install
### L4: `cli_completion_install(args: CompletionInstallArgs) -> int`
  - Implement `vtic completion install` command
  - Detect current shell from $SHELL environment variable
  - Install completion script to appropriate location:
    - Bash: `~/.bash_completion.d/vtic` or append to `~/.bashrc`
    - Zsh: `~/.zsh/completion/_vtic` or fpath directory
    - Fish: `~/.config/fish/completions/vtic.fish`
  - Create directories if they don't exist
  - Handle `--shell` override flag for cross-shell install
  - Handle `--output` flag to write to custom location
  - Print success message with reload instructions
  - Return exit code: 0 success, 1 unsupported shell, 2 write error

### L5: Spec
```python
import os
from pathlib import Path

@dataclass
class CompletionInstallArgs:
    shell: Optional[str] = None  # Override detected shell
    output: Optional[str] = None  # Custom output path
    dry_run: bool = False  # Show what would be done

INSTALL_LOCATIONS = {
    "bash": ["~/.bash_completion.d/vtic", "~/.bash_completion"],
    "zsh": ["~/.zsh/completion/_vtic", "~/.oh-my-zsh/completions/_vtic"],
    "fish": ["~/.config/fish/completions/vtic.fish"],
}

RELOAD_INSTRUCTIONS = {
    "bash": "Run: source ~/.bashrc  # or restart your terminal",
    "zsh": "Run: exec zsh  # or restart your terminal",
    "fish": "Completions loaded automatically",
}

def detect_shell() -> Optional[str]:
    """
    Input: os.environ["SHELL"] = "/bin/bash"
    Output: "bash"
    """

def cli_completion_install(args: CompletionInstallArgs) -> int:
    """
    Input: CompletionInstallArgs(shell=None)  # auto-detect bash
    Output (stdout): "Installed vtic completion for bash"
                     "Run: source ~/.bashrc"
    Return: 0
    
    Input: CompletionInstallArgs(shell="unknown")
    Output (stderr): "Unsupported shell: unknown. Supported: bash, zsh, fish"
    Return: 1
    """
```

### L6: Test
```python
test_detect_shell_bash()
test_detect_shell_zsh()
test_detect_shell_fish()
test_detect_shell_unknown_returns_none()
test_get_install_location_returns_valid_path()
test_cli_completion_install_auto_detects_shell()
test_cli_completion_install_creates_directory_if_missing()
test_cli_completion_install_custom_output_path()
test_cli_completion_install_dry_run_no_write()
test_cli_completion_install_unsupported_shell_returns_1()
test_cli_completion_install_outputs_reload_instructions()
test_uninstall_completion_removes_file()
```

---

## Feature 28: Standard Env Names

### L1: Configuration
### L2: Environment Variables
### L3: Standard env names
### L4: `parse_env_config() -> Dict[str, Any]`
  - Define standard naming convention: `VTIC_<SECTION>_<KEY>` 
  - Map environment variables to nested config structure
  - Examples:
    - `VTIC_TICKETS_DIR` → `tickets_dir`
    - `VTIC_SEARCH_PROVIDER` → `search.provider`
    - `VTIC_EMBEDDING_PROVIDER` → `embedding.provider`
    - `VTIC_SERVER_HOST` → `server.host`
  - Handle type coercion (string to int, bool, etc.)
  - Return dict matching config structure

### L5: Spec
```python
import os
from typing import Any, Dict

ENV_MAPPING = {
    # Core
    "VTIC_TICKETS_DIR": ("tickets_dir", str),
    "VTIC_INDEX_DIR": ("index_dir", str),
    
    # Search
    "VTIC_SEARCH_PROVIDER": ("search.provider", str),
    "VTIC_SEARCH_BM25_WEIGHT": ("search.bm25_weight", float),
    
    # Embedding
    "VTIC_EMBEDDING_PROVIDER": ("embedding.provider", str),
    "VTIC_EMBEDDING_MODEL": ("embedding.model", str),
    "VTIC_EMBEDDING_DIMENSIONS": ("embedding.dimensions", int),
    
    # OpenAI
    "OPENAI_API_KEY": ("embedding.openai.api_key", str),
    
    # Server
    "VTIC_SERVER_HOST": ("server.host", str),
    "VTIC_SERVER_PORT": ("server.port", int),
    
    # API
    "VTIC_API_KEY": ("api.key", str),
}

def parse_env_config() -> Dict[str, Any]:
    """
    Input: os.environ = {
        "VTIC_TICKETS_DIR": "/data/tickets",
        "VTIC_SEARCH_PROVIDER": "hybrid",
        "VTIC_SERVER_PORT": "8080",
    }
    Output: {
        "tickets_dir": "/data/tickets",
        "search": {"provider": "hybrid"},
        "server": {"port": 8080},
    }
    """

def coerce_value(value: str, target_type: type) -> Any:
    """
    Input: value="8080", target_type=int
    Output: 8080
    
    Input: value="true", target_type=bool
    Output: True
    """
```

### L6: Test
```python
test_parse_env_config_empty_returns_empty_dict()
test_parse_env_config_single_var()
test_parse_env_config_multiple_vars()
test_parse_env_config_nested_path()
test_parse_env_config_ignores_non_vtic_vars()
test_coerce_value_int()
test_coerce_value_float()
test_coerce_value_bool_true()
test_coerce_value_bool_false()
test_coerce_value_string_passthrough()
test_set_nested_dict_creates_nested_structure()
test_get_env_var_name_simple()
```

---

## Feature 29: Env File Support

### L1: Configuration
### L2: Environment Variables
### L3: Env file support
### L4: `load_env_file(path: str = ".env") -> Dict[str, str]`
  - Load `.env` file from project directory automatically
  - Parse `KEY=value` format (same as python-dotenv)
  - Support quoted values: `KEY="value with spaces"` and `KEY='single'`
  - Support comments: lines starting with `#`
  - Support inline comments: `KEY=value # comment`
  - Support multiline values with `\` continuation
  - Support variable expansion: `KEY=${OTHER_KEY}` or `$OTHER_KEY`
  - Do NOT override existing environment variables (env vars take precedence)
  - Return loaded key-value pairs

### L5: Spec
```python
def find_env_file(start_dir: str = ".") -> Optional[Path]:
    """
    Find .env file in current or parent directories.
    """

def parse_env_content(content: str) -> Dict[str, str]:
    """
    Input: content='KEY=value\nOTHER="quoted value"'
    Output: {"KEY": "value", "OTHER": "quoted value"}
    """

def load_env_file(path: str = ".env") -> Dict[str, str]:
    """
    Load .env file and return key-values.
    
    Note: Does NOT set os.environ, just returns dict
    """

def apply_env_file(path: str = ".env", override: bool = False) -> None:
    """
    Load .env and apply to os.environ.
    
    Input: override=False
    Action: Only set vars that don't already exist
    """
```

### L6: Test
```python
test_find_env_file_current_directory()
test_find_env_file_parent_directory()
test_parse_env_content_simple_key_value()
test_parse_env_content_quoted_values()
test_parse_env_content_comments_ignored()
test_parse_env_content_inline_comments()
test_parse_env_content_multiline_backslash()
test_load_env_file_returns_dict()
test_apply_env_file_sets_new_vars()
test_apply_env_file_no_override_by_default()
test_expand_variables_dollar_brace()
test_strip_quotes_double()
```

---

## Feature 30: Dimension Config OpenAI

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: Dimension config
### L4: `configure_openai_dimensions(config: EmbeddingConfig) -> int`
  - Support configurable embedding dimensions for OpenAI models
  - OpenAI `text-embedding-3-small`: supports 512, 1536 (default)
  - OpenAI `text-embedding-3-large`: supports 256, 1024, 3072 (default)
  - Read dimension from config: `embedding.openai.dimensions`
  - Validate dimension is valid for selected model
  - Pass dimension to OpenAI API call via `dimensions` parameter
  - Return configured dimension value

### L5: Spec
```python
MODEL_DIMENSIONS = {
    "text-embedding-3-small": {"default": 1536, "supported": [512, 1536]},
    "text-embedding-3-large": {"default": 3072, "supported": [256, 1024, 3072]},
    "text-embedding-ada-002": {"default": 1536, "supported": [1536]},
}

def validate_dimensions(model: str, dimensions: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Input: model="text-embedding-3-small", dimensions=512
    Output: (True, None)
    
    Input: model="text-embedding-3-small", dimensions=1024
    Output: (False, "text-embedding-3-small supports dimensions [512, 1536], got 1024")
    """

def configure_openai_dimensions(config: OpenAIEmbeddingConfig) -> int:
    """
    Input: config.dimensions=512, config.model="text-embedding-3-small"
    Output: 512
    
    Input: config.dimensions=None, config.model="text-embedding-3-large"
    Output: 3072  # model default
    """
```

### L6: Test
```python
test_validate_dimensions_small_model_valid()
test_validate_dimensions_small_model_invalid()
test_validate_dimensions_large_model_valid()
test_validate_dimensions_ada002_only_1536()
test_configure_openai_dimensions_explicit()
test_configure_openai_dimensions_default()
test_create_openai_embedding_request_includes_dimensions()
test_model_dimensions_constants_complete()
```

---

## Feature 31: Batch Embedding

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: Batch embedding
### L4: `batch_embed_texts(texts: List[str], config: OpenAIEmbeddingConfig) -> List[List[float]]`
  - Embed multiple texts in single API call for efficiency
  - Read batch size from config: `embedding.openai.batch_size` (default: 100)
  - Split input texts into batches if exceeds batch size
  - Call OpenAI embeddings API with array of texts
  - Merge results maintaining original order
  - Track token usage across batches
  - Handle rate limiting with exponential backoff

### L5: Spec
```python
DEFAULT_BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0

@dataclass
class BatchEmbedResult:
    embeddings: List[List[float]]
    total_tokens: int
    batch_count: int
    errors: List[str]

def split_into_batches(texts: List[str], batch_size: int) -> List[List[str]]:
    """
    Input: texts=["a", "b", "c", "d"], batch_size=2
    Output: [["a", "b"], ["c", "d"]]
    """

def batch_embed_texts(texts: List[str], config: OpenAIEmbeddingConfig) -> BatchEmbedResult:
    """
    Input: texts=["a", "b", "c", "d", "e"], config.batch_size=2
    Action: Call API 3 times with batches
    Output: BatchEmbedResult(embeddings=[...], total_tokens=45, batch_count=3, errors=[])
    """
```

### L6: Test
```python
test_split_into_batches_even_split()
test_split_into_batches_uneven_split()
test_batch_embed_texts_single_batch()
test_batch_embed_texts_multiple_batches()
test_batch_embed_texts_maintains_order()
test_embed_with_retry_success_no_retry()
test_embed_with_retry_retries_on_rate_limit()
test_batch_embed_with_progress_calls_callback()
```

---

## Feature 32: Model Download (Local Provider)

### L1: Embedding Providers
### L2: Local Provider
### L3: Model download
### L4: `download_model(model_name: str, cache_dir: str) -> str`
  - Auto-download Sentence Transformers model on first use
  - Use `sentence_transformers.SentenceTransformer` for download
  - Download from HuggingFace Hub (https://huggingface.co/)
  - Default model: `all-MiniLM-L6-v2` (fast, good quality)
  - Cache downloaded models in `~/.cache/vtic/models/` (configurable)
  - Support offline mode: fail gracefully if model not cached and no network
  - Show download progress to stderr
  - Return path to downloaded model

### L5: Spec
```python
DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_CACHE_DIR = "~/.cache/vtic/models"

RECOMMENDED_MODELS = {
    "all-MiniLM-L6-v2": {"dimensions": 384, "description": "Fast, good quality"},
    "all-mpnet-base-v2": {"dimensions": 768, "description": "Higher quality, slower"},
}

def download_model(model_name: str, cache_dir: str, offline: bool = False) -> str:
    """
    Input: model_name="all-MiniLM-L6-v2", offline=False
    Action: Download model, show progress
    Output: "/home/user/.cache/vtic/models/all-MiniLM-L6-v2"
    
    Input: model_name="all-MiniLM-L6-v2", offline=True, not cached
    Error: ModelNotCachedError
    """

def is_model_cached(model_name: str, cache_dir: str) -> bool:
    """Check if model is already cached."""
```

### L6: Test
```python
test_get_model_cache_path_expands_home()
test_is_model_cached_true_when_exists()
test_download_model_creates_cache_dir()
test_download_model_offline_not_cached_raises()
test_ensure_model_available_returns_cached()
test_list_cached_models_returns_names()
```

---

## Feature 33: Model Caching (Local Provider)

### L1: Embedding Providers
### L2: Local Provider
### L3: Model caching
### L4: `cache_embedding(text_hash: str, embedding: List[float], cache_dir: str) -> None`
  - Cache computed embeddings to avoid re-computation
  - Cache key: hash of text content (SHA256 truncated)
  - Cache location: `~/.cache/vtic/embeddings/{model_name}/{hash}.npy`
  - Use numpy for efficient binary storage (.npy format)
  - Check cache before computing embedding
  - Return cached embedding if available
  - Invalidate cache when model changes

### L5: Spec
```python
def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash of text (first 16 chars)."""

def compute_cache_key(text: str, model_name: str, dimensions: int) -> str:
    """
    Input: text="Hello", model_name="all-MiniLM-L6-v2", dimensions=384
    Output: "315f5bdb76d078_v1_all-MiniLM-L6-v2_384"
    """

def cache_embedding(cache_key: str, embedding: List[float], cache_dir: str) -> None:
    """Store embedding in cache as numpy array."""

def get_cached_embedding(cache_key: str, cache_dir: str) -> Optional[List[float]]:
    """Retrieve embedding from cache."""

def embed_with_cache(text: str, model, config) -> List[float]:
    """
    Embed text with caching.
    1. Check cache
    2. If cached, return
    3. If not, compute, cache, return
    """
```

### L6: Test
```python
test_compute_text_hash_consistent()
test_cache_embedding_creates_file()
test_get_cached_embedding_returns_embedding()
test_embed_with_cache_uses_cache()
test_batch_embed_with_cache_mixed_cached_uncached()
test_clear_embedding_cache_removes_files()
test_get_cache_stats_returns_counts()
```

---

## Feature 34: HTTP Endpoint Custom Provider

### L1: Embedding Providers
### L2: Custom Provider
### L3: HTTP endpoint
### L4: `embed_via_http(texts: List[str], config: CustomEmbeddingConfig) -> List[List[float]]`
  - Support custom embedding API via HTTP endpoint
  - Configure endpoint URL in `embedding.custom.endpoint`
  - Send POST request with JSON body
  - Default request format: `{"input": ["text1", "text2"], "model": "custom"}`
  - Configurable request format via `embedding.custom.request_template`
  - Parse response to extract embeddings
  - Default response path: `response["data"][i]["embedding"]`
  - Configurable response path via `embedding.custom.response_path`
  - Support timeout configuration

### L5: Spec
```python
@dataclass
class CustomEmbeddingConfig:
    endpoint: str  # e.g., "https://api.custom.com/v1/embeddings"
    model: str = "custom"
    auth_header: str = "Authorization"
    auth_token: Optional[str] = None
    request_template: Optional[str] = None
    response_path: str = "data.{i}.embedding"
    dimensions: int = 1536
    timeout: int = 30

def build_request_body(texts: List[str], config: CustomEmbeddingConfig) -> Dict:
    """
    Input: texts=["hello"], config.request_template=None
    Output: {"input": ["hello"], "model": "custom"}
    """

def extract_embeddings(response: Dict, config: CustomEmbeddingConfig) -> List[List[float]]:
    """
    Input: response={"data": [{"embedding": [0.1, 0.2]}]}
    Output: [[0.1, 0.2]]
    """

def embed_via_http(texts: List[str], config: CustomEmbeddingConfig) -> List[List[float]]:
    """
    Embed texts via custom HTTP endpoint.
    """
```

### L6: Test
```python
test_build_request_body_default_template()
test_build_headers_with_auth()
test_extract_embeddings_default_path()
test_embed_via_http_success()
test_embed_via_http_timeout()
test_validate_custom_config_valid()
test_test_custom_endpoint_success()
```

---

## Feature 35: Custom Auth

### L1: Embedding Providers
### L2: Custom Provider
### L3: Custom auth
### L4: `configure_custom_auth(config: CustomAuthConfig) -> Dict[str, str]`
  - Support flexible authentication for custom embedding providers
  - Auth types: `bearer` (default), `header`, `api_key`, `basic`, `query`
  - Configure via `embedding.custom.auth_type` and `embedding.custom.auth_value`
  - Bearer: `Authorization: Bearer <token>`
  - Header: Custom header name and value
  - API Key: `X-API-Key: <key>` or in query params
  - Basic: `Authorization: Basic base64(user:pass)`
  - Read auth token from environment variable: `VTIC_CUSTOM_AUTH_TOKEN`

### L5: Spec
```python
AuthType = Literal["bearer", "header", "api_key", "basic", "query"]

@dataclass
class CustomAuthConfig:
    auth_type: AuthType = "bearer"
    auth_header: str = "Authorization"
    auth_value: Optional[str] = None
    auth_env_var: Optional[str] = None

def build_bearer_auth(token: str) -> Dict[str, str]:
    """Output: {"Authorization": "Bearer abc123"}"""

def build_basic_auth(username: str, password: str) -> Dict[str, str]:
    """Output: {"Authorization": "Basic dXNlcjpwYXNz"}"""

def configure_custom_auth(config: CustomAuthConfig) -> Dict[str, str]:
    """
    Build auth headers based on auth type.
    """
```

### L6: Test
```python
test_resolve_auth_value_direct()
test_resolve_auth_value_from_env()
test_build_bearer_auth()
test_build_header_auth()
test_build_api_key_auth()
test_build_basic_auth()
test_build_query_auth_no_existing_params()
test_configure_custom_auth_bearer()
test_validate_auth_config_bearer_valid()
test_validate_auth_config_missing_value()
```

---

# Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | Multi-Repo Support | Statistics | Per-repo stats | `get_stats_by_repo()` |
| 2 | Multi-Repo Support | Operations | Repo isolation | `filter_tickets_by_repo()`, `cli_with_repo_isolation()` |
| 3 | Multi-Repo Support | Configuration | Repo-specific defaults | `get_repo_defaults()`, `apply_repo_defaults()` |
| 4 | Integration | Webhooks | On-create webhook | `trigger_create_webhook()` |
| 5 | Integration | Webhooks | On-update webhook | `trigger_update_webhook()` |
| 6 | Integration | Webhooks | On-delete webhook | `trigger_delete_webhook()` |
| 7 | Integration | Webhooks | Webhook payload | `build_webhook_payload()`, `sign_webhook_payload()` |
| 8 | Integration | CI/CD | Docker image | `Dockerfile`, `run_vtic_in_docker()` |
| 9 | Integration | CI/CD | GitHub Action | `action.yml`, `run_vtic_action()` |
| 10 | Integration | External Tools | MCP server | `McpServer`, `run_mcp_server()` |
| 11 | CLI | Management Commands | config command | `cli_config()` |
| 12 | CLI | Management Commands | stats command | `cli_stats()` |
| 13 | CLI | Management Commands | validate command | `cli_validate()` |
| 14 | CLI | Management Commands | doctor command | `cli_doctor()` |
| 15 | CLI | Management Commands | trash command | `cli_trash()` |
| 16 | CLI | Bulk Operations | Bulk create CLI | `cli_bulk_create()` |
| 17 | CLI | Bulk Operations | Bulk update CLI | `cli_bulk_update()` |
| 18 | CLI | Bulk Operations | Bulk delete CLI | `cli_bulk_delete()` |
| 19 | CLI | Bulk Operations | Export CLI | `cli_export()` |
| 20 | CLI | Bulk Operations | Import CLI | `cli_import()` |
| 21 | CLI | Output Formats | Markdown output | `format_markdown()` |
| 22 | CLI | Output Formats | CSV output | `format_csv()` |
| 23 | CLI | Output Formats | Quiet mode | `configure_quiet_mode()` |
| 24 | CLI | Output Formats | Verbose mode | `configure_verbose_mode()` |
| 25 | CLI | Output Formats | Color control | `configure_color_output()` |
| 26 | CLI | Shell Integration | Tab completion | `generate_completion_script()` |
| 27 | CLI | Shell Integration | Completion install | `cli_completion_install()` |
| 28 | Configuration | Environment Variables | Standard env names | `parse_env_config()` |
| 29 | Configuration | Environment Variables | Env file support | `load_env_file()` |
| 30 | Embedding Providers | OpenAI Provider | Dimension config | `configure_openai_dimensions()` |
| 31 | Embedding Providers | OpenAI Provider | Batch embedding | `batch_embed_texts()` |
| 32 | Embedding Providers | Local Provider | Model download | `download_model()` |
| 33 | Embedding Providers | Local Provider | Model caching | `cache_embedding()` |
| 34 | Embedding Providers | Custom Provider | HTTP endpoint | `embed_via_http()` |
| 35 | Embedding Providers | Custom Provider | Custom auth | `configure_custom_auth()` |

---

# Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Literal, Callable, Union, Set
from datetime import datetime

# Core Ticket
@dataclass
class Ticket:
    id: str
    title: str
    repo: str
    description: Optional[str] = None
    category: str = "code"
    severity: str = "medium"
    status: str = "open"
    tags: List[str] = field(default_factory=list)
    file_refs: List[str] = field(default_factory=list)
    fix: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None

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

# CLI Output Config
@dataclass
class OutputConfig:
    quiet: bool = False
    verbose: bool = False
    color: str = "auto"
    format: str = "table"

# Color Config
@dataclass
class ColorConfig:
    enabled: bool
    mode: Literal["auto", "always", "never"]

# Embedding Configs
@dataclass
class OpenAIEmbeddingConfig:
    api_key: str
    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None
    batch_size: int = 100

@dataclass
class BatchEmbedResult:
    embeddings: List[List[float]]
    total_tokens: int
    batch_count: int
    errors: List[str]

@dataclass
class LocalEmbeddingConfig:
    model: str = "all-MiniLM-L6-v2"
    cache_dir: str = "~/.cache/vtic/models"
    device: str = "cpu"
    offline: bool = False

@dataclass
class CustomEmbeddingConfig:
    endpoint: str
    model: str = "custom"
    auth_header: str = "Authorization"
    auth_token: Optional[str] = None
    request_template: Optional[str] = None
    response_path: str = "data.{i}.embedding"
    dimensions: int = 1536
    timeout: int = 30
    batch_size: int = 100

@dataclass
class CustomAuthConfig:
    auth_type: Literal["bearer", "header", "api_key", "basic", "query"] = "bearer"
    auth_header: str = "Authorization"
    auth_value: Optional[str] = None
    auth_env_var: Optional[str] = None
    api_key_header: str = "X-API-Key"
    api_key_query_param: str = "api_key"

# Storage Protocol
class TicketStore(Protocol):
    def get(self, ticket_id: str) -> Optional[Ticket]: ...
    def save(self, ticket: Ticket) -> None: ...
    def delete(self, ticket_id: str, force: bool = False) -> bool: ...
    def move_to_trash(self, ticket_id: str) -> bool: ...
    def restore_from_trash(self, ticket_id: str) -> bool: ...
    def list_trash(self) -> List[Ticket]: ...
    def clean_trash(self, older_than_days: int) -> int: ...
    def list_ids(self) -> Set[str]: ...
    def list_all(self, filters: Optional[Dict[str, Any]] = None) -> List[Ticket]: ...
    def bulk_create(self, tickets: List[Ticket]) -> Tuple[int, List[Tuple[int, str, str]]]: ...
    def bulk_update(self, filters: Dict[str, Any], updates: Dict[str, Any], limit: Optional[int] = None) -> int: ...
    def bulk_delete(self, filters: Dict[str, Any], force: bool = False, limit: Optional[int] = None) -> int: ...

# Validation
@dataclass
class ValidationError:
    file_path: str
    line: Optional[int]
    field: Optional[str]
    message: str
    severity: str
    fixable: bool

# Diagnostics
@dataclass
class DiagnosticResult:
    check_name: str
    status: str
    message: str
    suggestion: Optional[str]
    auto_fixable: bool

# Import/Export
@dataclass
class BulkCreateResult:
    total: int
    created: int
    failed: int
    errors: List[Tuple[int, str, str]]
    created_ids: List[str]

@dataclass
class ImportResult:
    total: int
    imported: int
    skipped: int
    errors: List[Tuple[int, str, str]]
    id_mappings: Dict[str, str]

# Format Options
@dataclass
class MarkdownFormatOptions:
    mode: str = "single"
    template: Optional[str] = None
    include_frontmatter: bool = True
    include_content: bool = True
    syntax_highlight: bool = True

@dataclass
class CSVFormatOptions:
    fields: Optional[List[str]] = None
    delimiter: str = ","
    quote_char: str = '"'
    include_header: bool = True
    column_names: Optional[Dict[str, str]] = None
    flatten_arrays: str = ";"
```

---

*Total: 35 Should Have (P1) features across 8 categories*
