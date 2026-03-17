# Good to Have Features (P2) - 6-Level Breakdown

27 P2 features broken down to implementation-ready specifications.

---

## Feature 1: CSV Export Endpoint

### L1: API
### L2: Response Formats
### L3: CSV export endpoint
### L4: `export_tickets_csv(filters: TicketFilters, store: TicketStore) -> StreamingResponse`
  - Accept same filters as GET /tickets endpoint
  - Convert ticket fields to CSV columns
  - Stream response for large datasets
  - Include header row with column names
  - Handle multi-value fields (tags, file_refs) as pipe-separated string

### L5: Spec
```python
def export_tickets_csv(filters: TicketFilters, store: TicketStore) -> StreamingResponse:
    """
    Endpoint: GET /tickets?format=csv
    
    Input: filters={"status": "open", "repo": "ejacklab/*"}
    Output (streaming CSV):
        id,title,repo,category,severity,status,description,tags,file_refs,created,updated
        C1,CORS Bug,ejacklab/open-dsearch,code,critical,open,"Description...",security|api,src/main.py,2026-03-17T10:00:00Z,2026-03-17T10:00:00Z
        S2,Auth Token Leak,ejacklab/open-dsearch,security,high,open,"...",auth|security,,2026-03-17T11:00:00Z,2026-03-17T11:00:00Z
    
    Input: filters={}, empty result set
    Output: Header row only (id,title,repo,...)
    
    Note: Content-Type: text/csv; charset=utf-8
          Content-Disposition: attachment; filename="tickets_export.csv"
    """
```

### L6: Test
```python
test_export_tickets_csv_basic()
test_export_tickets_csv_with_filters()
test_export_tickets_csv_empty_result_header_only()
test_export_tickets_csv_multi_value_fields_pipe_separated()
test_export_tickets_csv_content_type_header()
test_export_tickets_csv_content_disposition_filename()
test_export_tickets_csv_large_dataset_streaming()
```

---

## Feature 2: Content Negotiation

### L1: API
### L2: Response Formats
### L3: Content negotiation
### L4: `negotiate_content_type(accept_header: str, default: str = "application/json") -> str`
  - Parse Accept header with quality values (q=)
  - Support: application/json, text/markdown, text/csv, application/yaml
  - Sort by quality value, return highest priority supported type
  - Fall back to default if no supported type matches

### L5: Spec
```python
SUPPORTED_TYPES = ["application/json", "text/markdown", "text/csv", "application/yaml"]

def negotiate_content_type(accept_header: str, default: str = "application/json") -> str:
    """
    Input: accept_header="application/json"
    Output: "application/json"
    
    Input: accept_header="text/markdown, application/json;q=0.8"
    Output: "text/markdown"  # higher priority
    
    Input: accept_header="text/html, application/xml"
    Output: "application/json"  # fallback to default
    
    Input: accept_header="*/*"
    Output: "application/json"  # wildcard defaults to json
    
    Input: accept_header=""
    Output: "application/json"  # empty defaults to json
    
    Note: Quality values parsed and sorted: q=1.0 > q=0.9 > q=0.8
    """
```

### L6: Test
```python
test_negotiate_content_type_json()
test_negotiate_content_type_markdown()
test_negotiate_content_type_quality_values()
test_negotiate_content_type_unsupported_fallback()
test_negotiate_content_type_wildcard_defaults_json()
test_negotiate_content_type_empty_defaults_json()
test_negotiate_content_type_multiple_with_quality()
```

---

## Feature 3: Error Reference Docs

### L1: API
### L2: Error Handling
### L3: Error reference docs
### L4: `get_error_documentation_link(error_code: str) -> Optional[str]`
  - Map error codes to documentation URLs
  - Return URL to error documentation page
  - Include link in error response `doc_url` field
  - Support versioned docs (link to current version)

### L5: Spec
```python
ERROR_DOCS_BASE = "https://vtic.io/docs/errors"

ERROR_CODE_PATHS = {
    "VALIDATION_ERROR": "/validation",
    "TICKET_NOT_FOUND": "/not-found#ticket",
    "REPO_NOT_FOUND": "/not-found#repo",
    "INVALID_STATUS": "/validation#status",
    "RATE_LIMITED": "/rate-limits",
    "AUTHENTICATION_REQUIRED": "/auth",
    "PERMISSION_DENIED": "/permissions",
}

def get_error_documentation_link(error_code: str, version: str = "latest") -> Optional[str]:
    """
    Input: error_code="TICKET_NOT_FOUND"
    Output: "https://vtic.io/docs/errors/not-found#ticket"
    
    Input: error_code="RATE_LIMITED", version="v0.1"
    Output: "https://vtic.io/docs/v0.1/errors/rate-limits"
    
    Input: error_code="UNKNOWN_ERROR"
    Output: "https://vtic.io/docs/errors"  # fallback to base
    
    Note: Error response includes:
          {
            "error": {
              "code": "TICKET_NOT_FOUND",
              "message": "Ticket C999 not found",
              "doc_url": "https://vtic.io/docs/errors/not-found#ticket"
            }
          }
    """
```

### L6: Test
```python
test_get_error_documentation_link_known_code()
test_get_error_documentation_link_unknown_code_fallback()
test_get_error_documentation_link_versioned()
test_get_error_documentation_link_in_error_response()
```

---

## Feature 4: Rate Limit Headers

### L1: API
### L2: Error Handling
### L3: Rate limit headers
### L4: `add_rate_limit_headers(response: Response, limiter: RateLimiter, key: str) -> Response`
  - Add X-RateLimit-Limit: max requests per window
  - Add X-RateLimit-Remaining: requests remaining in window
  - Add X-RateLimit-Reset: Unix timestamp when window resets
  - Add Retry-After header on 429 responses

### L5: Spec
```python
def add_rate_limit_headers(response: Response, limiter: RateLimiter, key: str) -> Response:
    """
    Input: response with 200 status, limiter with 100 req/min, key has used 45 requests
    Output: Response with headers:
            X-RateLimit-Limit: 100
            X-RateLimit-Remaining: 55
            X-RateLimit-Reset: 1711234567
    
    Input: response with 429 status (rate limited)
    Output: Response with headers:
            X-RateLimit-Limit: 100
            X-RateLimit-Remaining: 0
            X-RateLimit-Reset: 1711234567
            Retry-After: 45  # seconds until reset
    
    Note: Headers added to ALL responses (not just 429)
          Retry-After only on 429 responses
    """
```

### L6: Test
```python
test_add_rate_limit_headers_success_response()
test_add_rate_limit_headers_remaining_decrements()
test_add_rate_limit_headers_429_retry_after()
test_add_rate_limit_headers_reset_timestamp()
test_add_rate_limit_headers_on_all_responses()
```

---

## Feature 5: Link Headers

### L1: API
### L2: Pagination
### L3: Link headers
### L4: `generate_link_headers(pagination: PaginationInfo, request_url: str) -> Dict[str, str]`
  - Generate RFC 5988 Link header for pagination
  - Include rel="next", rel="prev", rel="first", rel="last"
  - Build URLs with cursor/offset parameters
  - Omit rel links when at boundary (no prev on first page)

### L5: Spec
```python
def generate_link_headers(pagination: PaginationInfo, request_url: str) -> Dict[str, str]:
    """
    Input: pagination={total: 100, limit: 20, offset: 20, has_more: true}
           request_url="https://api.vtic.io/tickets?status=open"
    Output: {
        "Link": (
            '<https://api.vtic.io/tickets?status=open&offset=0>; rel="first", '
            '<https://api.vtic.io/tickets?status=open&offset=0>; rel="prev", '
            '<https://api.vtic.io/tickets?status=open&offset=40>; rel="next", '
            '<https://api.vtic.io/tickets?status=open&offset=80>; rel="last"'
        )
    }
    
    Input: pagination={total: 100, limit: 20, offset: 0, has_more: true}  # first page
    Output: Link without "prev" relation
    
    Input: pagination={total: 15, limit: 20, offset: 0, has_more: false}  # single page
    Output: Link with only "first" and "last" (both same URL)
    
    Note: Cursor pagination uses cursor= instead of offset=
    """
```

### L6: Test
```python
test_generate_link_headers_middle_page()
test_generate_link_headers_first_page_no_prev()
test_generate_link_headers_last_page_no_next()
test_generate_link_headers_single_page()
test_generate_link_headers_preserves_query_params()
test_generate_link_headers_cursor_pagination()
test_generate_link_headers_rfc5988_format()
```

---

## Feature 6: Backup Command

### L1: CLI
### L2: Management Commands
### L3: Backup command
### L4: `cli_backup(args: BackupArgs, store: TicketStore) -> int`
  - Create backup of all ticket files and index
  - Support formats: tar.gz, zip
  - Include metadata file with backup info (timestamp, version, count)
  - Option to backup to S3/GCS with --s3 or --gcs flags
  - Verify backup integrity after creation

### L5: Spec
```python
@dataclass
class BackupArgs:
    action: str  # "create" or "restore"
    output: str  # file path or "s3://bucket/path"
    format: str = "tar.gz"  # tar.gz, zip
    include_index: bool = True
    include_trash: bool = False

def cli_backup(args: BackupArgs, store: TicketStore) -> int:
    """
    Input: BackupArgs(action="create", output="backup.tar.gz")
    Action: 
      - Create backup.tar.gz with:
        - tickets/ directory (all .md files)
        - .vtic/ directory (index, if include_index=True)
        - backup.json metadata
    Output (stdout): "Created backup: backup.tar.gz (152 tickets, 2.3 MB)"
    Return: 0
    
    Input: BackupArgs(action="create", output="s3://my-bucket/backups/vtic.tar.gz")
    Action: Create backup locally, upload to S3
    Output (stdout): "Created and uploaded backup: s3://my-bucket/backups/vtic.tar.gz"
    Return: 0
    
    Input: BackupArgs(action="restore", output="backup.tar.gz")
    Action: Extract backup, restore tickets and index
    Output (stdout): "Restored 152 tickets from backup.tar.gz"
    Return: 0
    """
```

### L6: Test
```python
test_cli_backup_create_tar_gz()
test_cli_backup_create_zip()
test_cli_backup_include_index()
test_cli_backup_exclude_trash()
test_cli_backup_metadata_included()
test_cli_backup_restore()
test_cli_backup_s3_upload()
test_cli_backup_integrity_verification()
```

---

## Feature 7: Migrate Command

### L1: CLI
### L2: Management Commands
### L3: Migrate command
### L4: `cli_migrate(args: MigrateArgs, store: TicketStore) -> int`
  - Upgrade ticket file format for new versions
  - Detect current format version
  - Apply migrations sequentially (v1 → v2 → v3)
  - Create backup before migration
  - Support --dry-run to preview changes

### L5: Spec
```python
@dataclass
class MigrateArgs:
    target_version: Optional[str] = None  # default to latest
    dry_run: bool = False
    backup: bool = True
    force: bool = False  # skip confirmation

def cli_migrate(args: MigrateArgs, store: TicketStore) -> int:
    """
    Input: MigrateArgs(target_version=None, dry_run=False)
    Action:
      - Detect current version from .vtic/version
      - Run migrations: v0.1 → v0.2, v0.2 → v0.3, etc.
      - Create backup if backup=True
      - Update each ticket file with new format
      - Update .vtic/version to new version
    Output (stdout): "Migrated 152 tickets from v0.1 to v0.3"
    Return: 0
    
    Input: MigrateArgs(dry_run=True)
    Output (stdout): 
      "Dry run: would migrate 152 tickets from v0.1 to v0.3"
      "Changes: Add 'fix' field to all tickets, rename 'category' values"
    Return: 0
    
    Input: Already at latest version
    Output (stdout): "Already at latest version (v0.3)"
    Return: 0
    """
```

### L6: Test
```python
test_cli_migrate_from_v01_to_v02()
test_cli_migrate_sequential_versions()
test_cli_migrate_dry_run()
test_cli_migrate_creates_backup()
test_cli_migrate_already_latest_version()
test_cli_migrate_preserves_custom_fields()
test_cli_migrate_rollback_on_failure()
```

---

## Feature 8: YAML Output

### L1: CLI
### L2: Output Formats
### L3: YAML output
### L4: `format_yaml(tickets: Union[Ticket, List[Ticket]], pretty: bool = True) -> str`
  - Convert ticket(s) to YAML format
  - Support single ticket and list output
  - Pretty-print by default (indentation, block style)
  - Handle multi-line strings with literal style (|)
  - Preserve field order consistent with JSON output

### L5: Spec
```python
def format_yaml(tickets: Union[Ticket, List[Ticket]], pretty: bool = True) -> str:
    """
    Input: Ticket(id="C1", title="Bug", status="open", tags=["api", "auth"])
    Output:
        id: C1
        title: Bug
        repo: ejacklab/open-dsearch
        status: open
        tags:
          - api
          - auth
    
    Input: List[Ticket] with 2 tickets
    Output:
        - id: C1
          title: Bug 1
          ...
        - id: C2
          title: Bug 2
          ...
    
    Input: Ticket with multi-line description
    Output:
        description: |
          Line 1
          Line 2
          Line 3
    
    Note: Use --format yaml for CLI commands
          API supports Accept: application/yaml
    """
```

### L6: Test
```python
test_format_yaml_single_ticket()
test_format_yaml_ticket_list()
test_format_yaml_multiline_string_literal()
test_format_yaml_empty_list()
test_format_yaml_special_characters_escaped()
test_format_yaml_consistent_field_order()
```

---

## Feature 9: Aliases

### L1: CLI
### L2: Shell Integration
### L3: Command aliases
### L4: `resolve_alias(command: str, aliases: Dict[str, str]) -> str`
  - Define common command shortcuts in vtic.toml
  - Allow multi-word alias expansion
  - Support parameterized aliases with placeholders
  - Built-in aliases: s → search, g → get, ls → list

### L5: Spec
```python
BUILTIN_ALIASES = {
    "s": "search",
    "g": "get",
    "ls": "list",
    "new": "create",
    "rm": "delete",
    "ed": "update",
}

def resolve_alias(command: str, config: Config) -> List[str]:
    """
    Input: command="s", config with no custom aliases
    Output: ["search"]
    
    Input: command="g C1 --json", config with no custom aliases
    Output: ["get", "C1", "--json"]
    
    Input: command="mine", config with aliases={"mine": "search --repo ejacklab/open-dsearch --assignee @me"}
    Output: ["search", "--repo", "ejacklab/open-dsearch", "--assignee", "@me"]
    
    Input: command="critical", config with aliases={"critical": "search --severity critical --status open"}
    Output: ["search", "--severity", "critical", "--status", "open"]
    
    Note: Custom aliases in vtic.toml:
          [aliases]
          mine = "search --repo ejacklab/open-dsearch --assignee @me"
          critical = "search --severity critical --status open"
    """
```

### L6: Test
```python
test_resolve_alias_builtin_s()
test_resolve_alias_builtin_g()
test_resolve_alias_builtin_ls()
test_resolve_alias_custom_alias()
test_resolve_alias_with_arguments()
test_resolve_alias_unknown_returns_original()
test_resolve_alias_chained_not_supported()
```

---

## Feature 10: Interactive Mode

### L1: CLI
### L2: Shell Integration
### L3: Interactive mode
### L4: `run_interactive_shell(store: TicketStore, config: Config) -> None`
  - Start REPL-style interactive shell
  - Support all CLI commands without "vtic" prefix
  - Maintain context (e.g., repo filter) across commands
  - Support tab completion and history (readline)
  - Exit commands: exit, quit, Ctrl+D

### L5: Spec
```python
def run_interactive_shell(store: TicketStore, config: Config) -> None:
    """
    Start interactive REPL session.
    
    Session:
      vtic> create --title "New Bug" --repo ejacklab/open-dsearch
      Created: C10
      
      vtic> repo ejacklab/open-dsearch
      Context set: repo=ejacklab/open-dsearch
      
      vtic> get C10
      # Uses context repo
      ID: C10
      Title: New Bug
      ...
      
      vtic> search "auth error"
      # Search within context repo
      C5: Authentication Error in Login Flow
      
      vtic> exit
      Goodbye!
    
    Context commands:
      repo <repo>      - Set repo filter for subsequent commands
      clear            - Clear all context
      context          - Show current context
      
    Shell features:
      - Tab completion for commands, ticket IDs, repos
      - Up/down arrow for history
      - Ctrl+C to cancel current input
      - Ctrl+D or 'exit' to quit
    """
```

### L6: Test
```python
test_run_interactive_shell_create_ticket()
test_run_interactive_shell_context_repo()
test_run_interactive_shell_context_clear()
test_run_interactive_shell_exit_commands()
test_run_interactive_shell_tab_completion()
test_run_interactive_shell_history_persistence()
```

---

## Feature 11: Config Inheritance

### L1: Configuration
### L2: Configuration Files
### L3: Config inheritance
### L4: `load_config_with_inheritance(config_path: str) -> Config`
  - Support `extends` key to inherit from base config
  - Deep merge child config over parent
  - Support multiple inheritance (extends list)
  - Resolve relative paths for extended configs
  - Detect and error on circular inheritance

### L5: Spec
```python
def load_config_with_inheritance(config_path: str) -> Config:
    """
    Input: ./vtic.toml with extends="../base-vtic.toml"
    Action: Load base-vtic.toml, then merge ./vtic.toml over it
    Output: Merged Config
    
    Input: ./vtic.toml with extends=["../base.toml", "../dev.toml"]
    Action: Load base.toml, merge dev.toml, merge ./vtic.toml
    Output: Merged Config (child overrides parent)
    
    vtic.toml example:
      extends = "../base-vtic.toml"
      
      [tickets]
      default_repo = "myorg/myproject"  # Override base
      
      [search]
      # Inherits from base
      
    Circular inheritance detection:
      a.toml extends b.toml
      b.toml extends a.toml
      Error: Circular inheritance detected: a.toml -> b.toml -> a.toml
    
    Note: Relative paths resolved from config file location
    """
```

### L6: Test
```python
test_load_config_with_inheritance_single()
test_load_config_with_inheritance_multiple()
test_load_config_with_inheritance_deep_merge()
test_load_config_with_inheritance_override()
test_load_config_with_inheritance_relative_paths()
test_load_config_with_inheritance_circular_detection()
test_load_config_with_inheritance_missing_parent_error()
```

---

## Feature 12: Configuration Profiles

### L1: Configuration
### L2: Defaults & Profiles
### L3: Configuration profiles
### L4: `load_profile_config(profile_name: str, base_config: Config) -> Config`
  - Support multiple named profiles in config
  - Profile selected via --profile flag or VTIC_PROFILE env var
  - Profile extends base config (not replaces)
  - Default profile: "default"
  - List available profiles: vtic config profiles

### L5: Spec
```python
def load_profile_config(profile_name: str, base_config: Config) -> Config:
    """
    vtic.toml structure:
      [tickets]
      default_repo = "ejacklab/open-dsearch"
      
      [profiles.work]
      tickets_dir = "~/work-tickets"
      default_repo = "ejacklab/open-dsearch"
      
      [profiles.personal]
      tickets_dir = "~/personal-tickets"
      default_repo = "myuser/myproject"
      
      [profiles.client]
      tickets_dir = "~/client-tickets"
      default_repo = "client/client-repo"
    
    Input: profile_name="work"
    Action: Merge profiles.work over base config
    Output: Config with tickets_dir="~/work-tickets"
    
    Input: CLI flag --profile personal
    Action: Load profiles.personal configuration
    
    Input: VTIC_PROFILE=client
    Action: Load profiles.client configuration
    
    CLI usage:
      vtic --profile work list
      vtic list  # uses default profile
    
    vtic config profiles:
      default
      work
      personal
      client
    """
```

### L6: Test
```python
test_load_profile_config_work()
test_load_profile_config_personal()
test_load_profile_config_default()
test_load_profile_config_cli_flag()
test_load_profile_config_env_var()
test_load_profile_config_list_profiles()
test_load_profile_config_unknown_profile_error()
```

---

## Feature 13: Cost Tracking

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: Cost tracking
### L4: `track_embedding_cost(provider: str, model: str, tokens: int, cost_usd: float) -> CostRecord`
  - Log token usage and cost for each embedding API call
  - Store records in .vtic/costs.jsonl
  - Track by date, provider, model
  - Provide cost summary command: vtic stats --costs

### L5: Spec
```python
@dataclass
class CostRecord:
    timestamp: str
    provider: str
    model: str
    tokens: int
    cost_usd: float
    tickets_count: int

def track_embedding_cost(
    provider: str, 
    model: str, 
    tokens: int, 
    cost_usd: float, 
    tickets_count: int = 1
) -> CostRecord:
    """
    Input: provider="openai", model="text-embedding-3-small", tokens=15000, cost_usd=0.0015
    Action: Append to .vtic/costs.jsonl
    Output: CostRecord(timestamp="2026-03-17T10:00:00Z", provider="openai", ...)
    
    vtic stats --costs output:
      Embedding Costs (Last 30 Days)
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
      Provider: OpenAI
      Model: text-embedding-3-small
      Tokens: 1,250,000
      Cost: $0.125
      
      By Date:
      2026-03-17: 15,000 tokens, $0.0015
      2026-03-16: 32,000 tokens, $0.0032
      ...
    
    Cost calculation:
      text-embedding-3-small: $0.02 / 1M tokens
      text-embedding-3-large: $0.13 / 1M tokens
    """
```

### L6: Test
```python
test_track_embedding_cost_creates_record()
test_track_embedding_cost_appends_to_file()
test_track_embedding_cost_stats_summary()
test_track_embedding_cost_by_date()
test_track_embedding_cost_by_model()
test_track_embedding_cost_file_created_if_missing()
```

---

## Feature 14: GPU Acceleration

### L1: Embedding Providers
### L2: Local Provider
### L3: GPU acceleration
### L4: `configure_gpu_acceleration(config: LocalProviderConfig) -> GPUConfig`
  - Auto-detect available GPU (CUDA, MPS, ROCm)
  - Configure device selection: auto, cuda, mps, cpu
  - Set memory limits for GPU embedding
  - Provide fallback to CPU if GPU unavailable

### L5: Spec
```python
@dataclass
class GPUConfig:
    device: str  # "cuda", "mps", "cpu"
    device_name: str  # "NVIDIA GeForce RTX 3080"
    memory_limit_mb: Optional[int]
    fallback_to_cpu: bool = True

def configure_gpu_acceleration(config: LocalProviderConfig) -> GPUConfig:
    """
    Input: LocalProviderConfig(device="auto")
    Action: Detect available GPU
    Output: GPUConfig(device="cuda", device_name="NVIDIA GeForce RTX 3080", ...)
    
    Input: LocalProviderConfig(device="cuda") on system without CUDA
    Action: Fall back to CPU (if fallback_to_cpu=True) or raise error
    Output: GPUConfig(device="cpu", device_name="CPU", fallback_to_cpu=True)
    
    Input: LocalProviderConfig(device="mps") on Apple Silicon
    Output: GPUConfig(device="mps", device_name="Apple M1 GPU", ...)
    
    Config example:
      [embedding.local]
      device = "auto"  # auto, cuda, mps, cpu
      memory_limit_mb = 4096
      fallback_to_cpu = true
    
    Note: torch.cuda.is_available() for CUDA
          torch.backends.mps.is_available() for Apple Silicon
    """
```

### L6: Test
```python
test_configure_gpu_acceleration_auto_detect_cuda()
test_configure_gpu_acceleration_auto_detect_mps()
test_configure_gpu_acceleration_no_gpu_fallback_cpu()
test_configure_gpu_acceleration_explicit_cuda()
test_configure_gpu_acceleration_memory_limit()
test_configure_gpu_acceleration_fallback_disabled_raises()
```

---

## Feature 15: Custom Local Models

### L1: Embedding Providers
### L2: Local Provider
### L3: Custom local models
### L4: `load_custom_embedding_model(model_path: str, config: ModelConfig) -> EmbeddingModel`
  - Load model from HuggingFace Hub (model_path="org/model-name")
  - Load model from local path (model_path="/path/to/model")
  - Configure pooling strategy: mean, cls, max
  - Configure normalization: True/False
  - Validate model outputs embedding dimension

### L5: Spec
```python
@dataclass
class ModelConfig:
    pooling: str = "mean"  # mean, cls, max
    normalize: bool = True
    max_seq_length: int = 512
    device: str = "auto"

def load_custom_embedding_model(model_path: str, config: ModelConfig) -> EmbeddingModel:
    """
    Input: model_path="sentence-transformers/all-MiniLM-L6-v2", config=ModelConfig()
    Action: Load model from HuggingFace Hub
    Output: EmbeddingModel with embed() method, dimension=384
    
    Input: model_path="~/models/my-custom-model", config=ModelConfig(pooling="cls")
    Action: Load model from local directory
    Output: EmbeddingModel with CLS pooling
    
    Input: model_path="invalid-model-path"
    Error: ModelNotFoundError(f"Could not find model: {model_path}")
    
    Config example:
      [embedding.local]
      model = "BAAI/bge-large-en-v1.5"
      pooling = "cls"
      normalize = true
      max_seq_length = 512
    
    Note: First load caches model to ~/.cache/vtic/models/
    """
```

### L6: Test
```python
test_load_custom_embedding_model_huggingface()
test_load_custom_embedding_model_local_path()
test_load_custom_embedding_model_pooling_mean()
test_load_custom_embedding_model_pooling_cls()
test_load_custom_embedding_model_normalize()
test_load_custom_embedding_model_not_found_error()
test_load_custom_embedding_model_caching()
```

---

## Feature 16: Plugin Interface

### L1: Embedding Providers
### L2: Custom Provider
### L3: Plugin interface
### L4: `register_embedding_plugin(plugin: EmbeddingPlugin) -> None`
  - Define Python interface for custom embedding functions
  - Support plugin discovery from entry points
  - Plugin can override embed() and embed_batch()
  - Plugins registered in vtic.toml

### L5: Spec
```python
from abc import ABC, abstractmethod

class EmbeddingPlugin(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name for configuration."""
        pass
    
    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass
    
    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Embed list of texts, return list of vectors."""
        pass
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """Default batching implementation. Override for custom behavior."""
        results = []
        for i in range(0, len(texts), batch_size):
            results.extend(self.embed(texts[i:i+batch_size]))
        return results

def register_embedding_plugin(plugin: EmbeddingPlugin) -> None:
    """
    Input: MyCustomPlugin with name="my-custom", dimension=768
    Action: Register plugin in plugin registry
    Output: None
    
    Config usage:
      [embedding]
      provider = "plugin"
      plugin = "my-custom"
      
      [embedding.plugins.my-custom]
      # Plugin-specific config passed to plugin
    
    Plugin discovery via entry points (setup.py):
      entry_points={
          "vtic.embedding_plugins": [
              "my-custom = mypackage.plugin:MyCustomPlugin",
          ],
      }
    """
```

### L6: Test
```python
test_register_embedding_plugin()
test_embedding_plugin_interface()
test_embedding_plugin_embed_batch_default()
test_embedding_plugin_from_entry_point()
test_embedding_plugin_config_passed()
test_embedding_plugin_error_handling()
```

---

## Feature 17: Request/Response Mapping

### L1: Embedding Providers
### L2: Custom Provider
### L3: Request/response mapping
### L4: `configure_http_embedding_mapping(config: HTTPMappingConfig) -> HTTPProvider`
  - Configure HTTP request format for custom embedding API
  - Map ticket text to request body field
  - Map response field to embedding vector
  - Support custom headers and authentication

### L5: Spec
```python
@dataclass
class HTTPMappingConfig:
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    request_template: Dict[str, Any] = field(default_factory=dict)
    response_path: str = "embeddings"  # JSONPath to extract vectors

def configure_http_embedding_mapping(config: HTTPMappingConfig) -> HTTPProvider:
    """
    Config example for custom API:
      [embedding.custom]
      endpoint = "https://api.example.com/v1/embeddings"
      method = "POST"
      
      [embedding.custom.headers]
      Authorization = "Bearer ${EMBEDDING_API_KEY}"
      Content-Type = "application/json"
      
      [embedding.custom.request]
      input = "{texts}"  # Placeholder for texts array
      model = "custom-model-v1"
      
      [embedding.custom.response]
      embeddings_path = "data[*].embedding"  # JSONPath
    
    Input: texts=["Hello", "World"]
    Request body:
      {"input": ["Hello", "World"], "model": "custom-model-v1"}
    Response:
      {"data": [{"embedding": [0.1, 0.2, ...]}, {"embedding": [0.3, 0.4, ...]}]}
    Extracted: [[0.1, 0.2, ...], [0.3, 0.4, ...]]
    
    JSONPath examples:
      "embeddings" -> response["embeddings"]
      "data[*].vector" -> [item["vector"] for item in response["data"]]
    """
```

### L6: Test
```python
test_configure_http_embedding_mapping_basic()
test_configure_http_embedding_mapping_custom_headers()
test_configure_http_embedding_mapping_request_template()
test_configure_http_embedding_mapping_jsonpath_simple()
test_configure_http_embedding_mapping_jsonpath_nested()
test_configure_http_embedding_mapping_env_var_substitution()
```

---

## Feature 18: Repo Aliases

### L1: Multi-Repo Support
### L2: Namespacing
### L3: Repo aliases
### L4: `resolve_repo_alias(alias: str, config: Config) -> str`
  - Define short aliases for common repos in vtic.toml
  - Resolve alias to full owner/repo string
  - Support aliases in CLI --repo flag
  - Support aliases in API repo parameter

### L5: Spec
```python
def resolve_repo_alias(alias: str, config: Config) -> str:
    """
    Config example:
      [repo_aliases]
      od = "ejacklab/open-dsearch"
      vtic = "ejacklab/vtic"
      core = "myorg/core-service"
      api = "myorg/api-gateway"
    
    Input: alias="od", config with repo_aliases
    Output: "ejacklab/open-dsearch"
    
    Input: alias="ejacklab/open-dsearch"
    Output: "ejacklab/open-dsearch"  # Not an alias, return as-is
    
    Input: alias="unknown", no matching alias
    Output: "unknown"  # Return as-is (may be valid repo)
    
    CLI usage:
      vtic create --repo od --title "Bug"
      # Resolves to --repo ejacklab/open-dsearch
    
      vtic search --repo od,vtic "auth"
      # Searches both ejacklab/open-dsearch and ejacklab/vtic
    """
```

### L6: Test
```python
test_resolve_repo_alias_known()
test_resolve_repo_alias_unknown_returns_original()
test_resolve_repo_alias_full_repo_unchanged()
test_resolve_repo_alias_in_cli()
test_resolve_repo_alias_in_api()
test_resolve_repo_alias_multiple()
```

---

## Feature 19: Repo-Specific Embedding

### L1: Multi-Repo Support
### L2: Multi-Repo Configuration
### L3: Repo-specific embedding
### L4: `get_repo_embedding_provider(repo: str, config: Config) -> EmbeddingProvider`
  - Configure different embedding providers per repo
  - Fall back to default provider if not configured
  - Support provider override for specific repos
  - Useful for isolating embedding costs by client/project

### L5: Spec
```python
def get_repo_embedding_provider(repo: str, config: Config) -> EmbeddingProvider:
    """
    Config example:
      [embedding]
      provider = "local"  # Default
      local.model = "sentence-transformers/all-MiniLM-L6-v2"
      
      [embedding.repos."ejacklab/open-dsearch"]
      provider = "openai"
      model = "text-embedding-3-small"
      
      [embedding.repos."client/client-repo"]
      provider = "openai"
      model = "text-embedding-3-large"
    
    Input: repo="ejacklab/open-dsearch"
    Output: OpenAIEmbeddingProvider(model="text-embedding-3-small")
    
    Input: repo="ejacklab/other-repo"  # Not in repos config
    Output: LocalEmbeddingProvider(model="all-MiniLM-L6-v2")  # Default
    
    Input: repo="client/client-repo"
    Output: OpenAIEmbeddingProvider(model="text-embedding-3-large")
    
    Note: Used automatically on ticket create/update for repo
          Reindex respects per-repo configuration
    """
```

### L6: Test
```python
test_get_repo_embedding_provider_configured()
test_get_repo_embedding_provider_fallback_default()
test_get_repo_embedding_provider_multiple_repos()
test_get_repo_embedding_provider_provider_switch()
test_get_repo_embedding_provider_reindex_uses_repo_config()
```

---

## Feature 20: Included/Excluded Repos

### L1: Multi-Repo Support
### L2: Multi-Repo Configuration
### L3: Included/excluded repos
### L4: `filter_repo_visibility(repos: List[str], config: Config) -> List[str]`
  - Configure whitelist (only these repos visible)
  - Configure blacklist (these repos excluded)
  - Apply filter to all multi-repo operations
  - Support glob patterns in include/exclude

### L5: Spec
```python
def filter_repo_visibility(repos: List[str], config: Config) -> List[str]:
    """
    Config example - Whitelist:
      [repos]
      include = ["ejacklab/*", "myorg/core"]
      exclude = []
    
    Config example - Blacklist:
      [repos]
      include = []
      exclude = ["*/internal-*", "archived/*"]
    
    Input: repos=["ejacklab/open-dsearch", "ejacklab/vtic", "other/repo"], 
           config with include=["ejacklab/*"]
    Output: ["ejacklab/open-dsearch", "ejacklab/vtic"]
    
    Input: repos=["ejacklab/open-dsearch", "ejacklab/internal-api"],
           config with exclude=["*/internal-*"]
    Output: ["ejacklab/open-dsearch"]
    
    Input: repos=["a/1", "b/2"], config with include=["c/*"]
    Output: []  # No repos match include
    
    Note: Include takes precedence over exclude
          Glob patterns: * matches any characters except /
    """
```

### L6: Test
```python
test_filter_repo_visibility_include_glob()
test_filter_repo_visibility_exclude_glob()
test_filter_repo_visibility_include_exact()
test_filter_repo_visibility_exclude_exact()
test_filter_repo_visibility_include_precedence()
test_filter_repo_visibility_empty_list()
test_filter_repo_visibility_no_config_returns_all()
```

---

## Feature 21: Retry Logic Webhooks

### L1: Integration
### L2: Webhooks
### L3: Retry logic webhooks
### L4: `deliver_webhook_with_retry(event: WebhookEvent, config: WebhookConfig) -> DeliveryResult`
  - Retry failed webhook deliveries with exponential backoff
  - Configure max retries and backoff parameters
  - Store failed deliveries for manual retry
  - Log all delivery attempts

### L5: Spec
```python
@dataclass
class WebhookConfig:
    max_retries: int = 3
    initial_delay_ms: int = 1000
    max_delay_ms: int = 60000
    backoff_multiplier: float = 2.0

@dataclass
class DeliveryResult:
    success: bool
    attempts: int
    last_error: Optional[str]
    last_status_code: Optional[int]

def deliver_webhook_with_retry(
    event: WebhookEvent, 
    config: WebhookConfig
) -> DeliveryResult:
    """
    Input: event with url="https://example.com/webhook", config with max_retries=3
    Action:
      - Attempt 1: POST to url
        - If 200 OK: Return DeliveryResult(success=True, attempts=1)
        - If failure: Wait 1s
      - Attempt 2: POST to url
        - If failure: Wait 2s
      - Attempt 3: POST to url
        - If failure: Wait 4s
      - Attempt 4: POST to url
        - If failure: Store in .vtic/webhook_failures.jsonl
    Output: DeliveryResult(success=False, attempts=4, last_error="Connection timeout")
    
    Retry schedule (exponential backoff):
      Attempt 1: immediate
      Attempt 2: after 1s
      Attempt 3: after 2s
      Attempt 4: after 4s
      ...up to max_delay_ms
    
    Retry on:
      - HTTP 5xx errors
      - Connection errors
      - Timeouts
    
    No retry on:
      - HTTP 4xx errors (except 429)
      - Invalid webhook URL
    """
```

### L6: Test
```python
test_deliver_webhook_with_retry_success_first_try()
test_deliver_webhook_with_retry_success_after_retry()
test_deliver_webhook_with_retry_max_retries_exceeded()
test_deliver_webhook_with_retry_exponential_backoff()
test_deliver_webhook_with_retry_4xx_no_retry()
test_deliver_webhook_with_retry_store_failures()
test_deliver_webhook_with_retry_5xx_retries()
```

---

## Feature 22: Webhook Signatures

### L1: Integration
### L2: Webhooks
### L3: Webhook signatures
### L4: `sign_webhook_payload(payload: str, secret: str) -> str`
  - Generate HMAC-SHA256 signature for webhook payload
  - Include signature in X-Vtic-Signature header
  - Include timestamp in X-Vtic-Timestamp header
  - Support signature verification by receivers

### L5: Spec
```python
def sign_webhook_payload(payload: str, secret: str, timestamp: Optional[int] = None) -> WebhookSignature:
    """
    Input: payload='{"event":"ticket.created","ticket":{"id":"C1"}}', 
           secret="whsec_abc123"
    Action: Generate HMAC-SHA256 signature
    Output: WebhookSignature(
        signature="sha256=7574928...",
        timestamp=1711234567
    )
    
    Webhook headers:
      X-Vtic-Signature: sha256=7574928...
      X-Vtic-Timestamp: 1711234567
      Content-Type: application/json
    
    Verification (receiver side):
      1. Get timestamp from X-Vtic-Timestamp
      2. Reject if timestamp > 5 minutes old (replay attack prevention)
      3. Concatenate timestamp + "." + payload
      4. Compute HMAC-SHA256 with shared secret
      5. Compare with X-Vtic-Signature (constant-time comparison)
    
    Config:
      [webhooks]
      signing_secret = "whsec_abc123"  # Generate with: vtic webhook generate-secret
    """
```

### L6: Test
```python
test_sign_webhook_payload_generates_signature()
test_sign_webhook_payload_includes_timestamp()
test_sign_webhook_payload_hmac_sha256()
test_sign_webhook_payload_verification_success()
test_sign_webhook_payload_verification_wrong_secret()
test_sign_webhook_payload_replay_attack_rejection()
```

---

## Feature 23: Pre-commit Validation

### L1: Integration
### L2: Git Hooks
### L3: Pre-commit validation
### L4: `install_pre_commit_hook(repo_path: str) -> None`
  - Install Git pre-commit hook to validate ticket files
  - Validate YAML frontmatter in ticket markdown files
  - Block commit if validation fails
  - Support --no-verify to skip validation

### L5: Spec
```python
def install_pre_commit_hook(repo_path: str) -> None:
    """
    Action: Create .git/hooks/pre-commit with vtic validation
    
    Hook script:
      #!/bin/bash
      # vtic pre-commit hook
      
      # Get staged ticket files
      TICKETS=$(git diff --cached --name-only --diff-filter=ACM | grep '^tickets/.*\.md$')
      
      if [ -n "$TICKETS" ]; then
          echo "Validating $TICKETS..."
          vtic validate --files $TICKETS
          
          if [ $? -ne 0 ]; then
              echo "Ticket validation failed. Fix errors or use --no-verify"
              exit 1
          fi
      fi
      
      exit 0
    
    Input: git commit with modified tickets/owner/repo/code/C1.md
    Action: Run vtic validate on C1.md
    Output:
      - If valid: Commit proceeds
      - If invalid: Commit blocked with error messages
    
    Installation:
      vtic hooks install pre-commit
      vtic hooks uninstall pre-commit
    
    Note: .git/hooks/pre-commit must be executable (chmod +x)
    """
```

### L6: Test
```python
test_install_pre_commit_hook_creates_file()
test_install_pre_commit_hook_executable()
test_install_pre_commit_hook_valid_tickets_pass()
test_install_pre_commit_hook_invalid_tickets_block()
test_install_pre_commit_hook_no_verify_skips()
test_install_pre_commit_hook_non_ticket_files_ignored()
```

---

## Feature 24: Post-commit Reindex

### L1: Integration
### L2: Git Hooks
### L3: Post-commit reindex
### L4: `install_post_commit_hook(repo_path: str) -> None`
  - Install Git post-commit hook to reindex changed tickets
  - Trigger reindex only for modified ticket files
  - Run asynchronously to not block commit
  - Log reindex results

### L5: Spec
```python
def install_post_commit_hook(repo_path: str) -> None:
    """
    Action: Create .git/hooks/post-commit with vtic reindex
    
    Hook script:
      #!/bin/bash
      # vtic post-commit hook
      
      # Get committed ticket files
      TICKETS=$(git diff --cached --name-only --diff-filter=ACMR | grep '^tickets/.*\.md$')
      
      if [ -n "$TICKETS" ]; then
          # Run reindex in background
          vtic reindex --files $TICKETS --async >> .vtic/hooks.log 2>&1
      fi
      
      exit 0
    
    Input: git commit with modified tickets/owner/repo/code/C1.md
    Action: Trigger vtic reindex for C1.md in background
    Output: Commit completes immediately, reindex runs async
    
    Log file (.vtic/hooks.log):
      2026-03-17T10:00:00Z post-commit: Reindexing C1.md, C2.md
      2026-03-17T10:00:01Z post-commit: Reindexed 2 tickets (0 errors)
    
    Installation:
      vtic hooks install post-commit
      vtic hooks uninstall post-commit
    
    Note: --async flag runs reindex in background process
          Logs written to .vtic/hooks.log for debugging
    """
```

### L6: Test
```python
test_install_post_commit_hook_creates_file()
test_install_post_commit_hook_executable()
test_install_post_commit_hook_triggers_reindex()
test_install_post_commit_hook_async_execution()
test_install_post_commit_hook_logging()
test_install_post_commit_hook_non_ticket_files_ignored()
```

---

## Feature 25: Branch-Specific Tickets

### L1: Integration
### L2: Git Hooks
### L3: Branch-specific tickets
### L4: `get_branch_ticket_namespace(repo_path: str) -> Optional[str]`
  - Separate ticket namespace per git branch
  - Store branch tickets in tickets/branches/{branch}/
  - Auto-detect current branch for ticket operations
  - Support merging branch tickets to main

### L5: Spec
```python
def get_branch_ticket_namespace(repo_path: str) -> Optional[str]:
    """
    Input: repo_path with current branch "feature/auth-fix"
    Action: Detect current git branch
    Output: "feature/auth-fix"
    
    Directory structure:
      tickets/
        ejacklab/
          open-dsearch/
            code/
              C1.md  # Main branch ticket
            branches/
              feature/
                auth-fix/
                  code/
                    C2.md  # Branch-specific ticket
    
    CLI usage:
      # On feature/auth-fix branch
      vtic create --title "Branch Bug"
      # Creates: tickets/.../branches/feature/auth-fix/code/C2.md
      
      vtic list
      # Lists only branch tickets (isolated from main)
      
      vtic list --all-branches
      # Lists tickets from all branches
    
    Merge branch tickets:
      vtic merge-branch-tickets feature/auth-fix --to main
      # Moves tickets from branches/feature/auth-fix/ to main code/
    
    Config:
      [tickets]
      branch_isolation = true  # Enable branch-specific tickets
    """
```

### L6: Test
```python
test_get_branch_ticket_namespace_current_branch()
test_get_branch_ticket_namespace_create_isolated()
test_get_branch_ticket_namespace_list_isolated()
test_get_branch_ticket_namespace_list_all_branches()
test_get_branch_ticket_namespace_merge_to_main()
test_get_branch_ticket_namespace_disabled()
```

---

## Feature 26: Editor Plugins

### L1: Integration
### L2: External Tool Integration
### L3: Editor plugins
### L4: `generate_editor_plugin_config(editor: str, config: Config) -> EditorPluginConfig`
  - Generate configuration for VSCode/Neovim extensions
  - Include schema for ticket YAML frontmatter
  - Configure snippets for ticket creation
  - Set up linting/validation integration

### L5: Spec
```python
def generate_editor_plugin_config(editor: str, config: Config) -> EditorPluginConfig:
    """
    Input: editor="vscode"
    Output:
      .vscode/extensions.json: ["vtic.vtic-vscode"]
      .vscode/settings.json: {vtic.ticketsDir: "./tickets"}
    
    VSCode extension features:
      - Syntax highlighting for vtic markdown files
      - YAML frontmatter schema validation
      - Autocomplete for status, severity, category values
      - Snippets:
        - "vtic-ticket": Create new ticket template
        - "vtic-fix": Add fix section
      - Commands:
        - "Vtic: Create Ticket"
        - "Vtic: Search Tickets"
        - "Vtic: Update Status"
    
    Neovim plugin features (Lua):
      - Treesitter grammar for vtic markdown
      - LSP integration for validation
      - Telescope picker for ticket search
    
    Installation:
      vtic editor setup vscode
      vtic editor setup neovim
    
    Note: Extensions/plugins published separately
          vtic generates workspace configuration
    """
```

### L6: Test
```python
test_generate_editor_plugin_config_vscode()
test_generate_editor_plugin_config_neovim()
test_generate_editor_plugin_config_schema_generation()
test_generate_editor_plugin_config_snippets()
test_generate_editor_plugin_config_autocomplete_values()
```

---

## Feature 27: Slack/Discord Bot

### L1: Integration
### L2: External Tool Integration
### L3: Slack/Discord bot
### L4: `handle_bot_command(platform: str, command: str, args: List[str], config: BotConfig) -> BotResponse`
  - Implement bot commands for ticket operations
  - Support create, search, update, get commands
  - Format responses for chat platforms
  - Handle OAuth and authentication

### L5: Spec
```python
@dataclass
class BotConfig:
    platform: str  # "slack" or "discord"
    command_prefix: str = "/vtic"
    allowed_channels: List[str] = field(default_factory=list)
    permissions: Dict[str, List[str]] = field(default_factory=dict)

def handle_bot_command(
    platform: str, 
    command: str, 
    args: List[str], 
    config: BotConfig
) -> BotResponse:
    """
    Slack commands:
      /vtic create "Bug in auth" --repo ejacklab/open-dsearch --severity high
      /vtic search "auth error" --status open
      /vtic get C1
      /vtic update C1 --status fixed
      /vtic list --severity critical
    
    Discord commands (slash commands):
      /vtic create title:"Bug in auth" repo:ejacklab/open-dsearch severity:high
      /vtic search query:"auth error" status:open
      /vtic get id:C1
    
    Input: platform="slack", command="search", args=["auth", "error", "--status", "open"]
    Action: Execute vtic search "auth error" --status open
    Output: BotResponse(
        text="Found 3 tickets:",
        blocks=[
            {"type": "section", "text": "C1: Authentication Error"},
            {"type": "section", "text": "C5: Login Timeout"},
            {"type": "section", "text": "S2: Token Leak"},
        ]
    )
    
    Response formatting:
      Slack: Block Kit with interactive buttons (View, Update)
      Discord: Embeds with fields (ID, Title, Status, Severity)
    
    Config:
      [bot.slack]
      bot_token = "xoxb-..."
      signing_secret = "..."
      allowed_channels = ["C12345", "C67890"]
      
      [bot.discord]
      bot_token = "..."
      application_id = "..."
      guild_id = "..."
    """
```

### L6: Test
```python
test_handle_bot_command_slack_create()
test_handle_bot_command_slack_search()
test_handle_bot_command_slack_get()
test_handle_bot_command_discord_create()
test_handle_bot_command_discord_search()
test_handle_bot_command_format_response_slack()
test_handle_bot_command_format_response_discord()
test_handle_bot_command_channel_permission()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | API | Response Formats | CSV export endpoint | `export_tickets_csv()` |
| 2 | API | Response Formats | Content negotiation | `negotiate_content_type()` |
| 3 | API | Error Handling | Error reference docs | `get_error_documentation_link()` |
| 4 | API | Error Handling | Rate limit headers | `add_rate_limit_headers()` |
| 5 | API | Pagination | Link headers | `generate_link_headers()` |
| 6 | CLI | Management Commands | Backup command | `cli_backup()` |
| 7 | CLI | Management Commands | Migrate command | `cli_migrate()` |
| 8 | CLI | Output Formats | YAML output | `format_yaml()` |
| 9 | CLI | Shell Integration | Command aliases | `resolve_alias()` |
| 10 | CLI | Shell Integration | Interactive mode | `run_interactive_shell()` |
| 11 | Configuration | Configuration Files | Config inheritance | `load_config_with_inheritance()` |
| 12 | Configuration | Defaults & Profiles | Configuration profiles | `load_profile_config()` |
| 13 | Embedding Providers | OpenAI Provider | Cost tracking | `track_embedding_cost()` |
| 14 | Embedding Providers | Local Provider | GPU acceleration | `configure_gpu_acceleration()` |
| 15 | Embedding Providers | Local Provider | Custom local models | `load_custom_embedding_model()` |
| 16 | Embedding Providers | Custom Provider | Plugin interface | `register_embedding_plugin()` |
| 17 | Embedding Providers | Custom Provider | Request/response mapping | `configure_http_embedding_mapping()` |
| 18 | Multi-Repo Support | Namespacing | Repo aliases | `resolve_repo_alias()` |
| 19 | Multi-Repo Support | Multi-Repo Configuration | Repo-specific embedding | `get_repo_embedding_provider()` |
| 20 | Multi-Repo Support | Multi-Repo Configuration | Included/excluded repos | `filter_repo_visibility()` |
| 21 | Integration | Webhooks | Retry logic webhooks | `deliver_webhook_with_retry()` |
| 22 | Integration | Webhooks | Webhook signatures | `sign_webhook_payload()` |
| 23 | Integration | Git Hooks | Pre-commit validation | `install_pre_commit_hook()` |
| 24 | Integration | Git Hooks | Post-commit reindex | `install_post_commit_hook()` |
| 25 | Integration | Git Hooks | Branch-specific tickets | `get_branch_ticket_namespace()` |
| 26 | Integration | External Tool Integration | Editor plugins | `generate_editor_plugin_config()` |
| 27 | Integration | External Tool Integration | Slack/Discord bot | `handle_bot_command()` |

---

## Category Breakdown

| Category (L1) | Feature Count |
|--------------|---------------|
| API | 5 |
| CLI | 5 |
| Configuration | 2 |
| Embedding Providers | 5 |
| Multi-Repo Support | 3 |
| Integration | 7 |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union, Protocol
from datetime import datetime

# Pagination
@dataclass
class PaginationInfo:
    total: int
    limit: int
    offset: int
    has_more: bool
    cursor: Optional[str] = None

# Rate Limiting
@dataclass
class RateLimiter:
    limit: int
    window_seconds: int
    remaining: int
    reset_timestamp: int

# Webhooks
@dataclass
class WebhookEvent:
    event_type: str  # ticket.created, ticket.updated, ticket.deleted
    ticket: Ticket
    timestamp: str
    url: str

@dataclass
class WebhookSignature:
    signature: str  # sha256=...
    timestamp: int

# Cost Tracking
@dataclass
class CostRecord:
    timestamp: str
    provider: str
    model: str
    tokens: int
    cost_usd: float
    tickets_count: int

# GPU Configuration
@dataclass
class GPUConfig:
    device: str  # "cuda", "mps", "cpu"
    device_name: str
    memory_limit_mb: Optional[int]
    fallback_to_cpu: bool = True

# Model Configuration
@dataclass
class ModelConfig:
    pooling: str = "mean"
    normalize: bool = True
    max_seq_length: int = 512
    device: str = "auto"

# HTTP Mapping
@dataclass
class HTTPMappingConfig:
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = field(default_factory=dict)
    request_template: Dict[str, Any] = field(default_factory=dict)
    response_path: str = "embeddings"

# Bot Configuration
@dataclass
class BotConfig:
    platform: str
    command_prefix: str = "/vtic"
    allowed_channels: List[str] = field(default_factory=list)
    permissions: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class BotResponse:
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None  # Slack Block Kit
    embed: Optional[Dict[str, Any]] = None  # Discord Embed

# Embedding Plugin Interface
class EmbeddingPlugin(Protocol):
    @property
    def name(self) -> str: ...
    
    @property
    def dimension(self) -> int: ...
    
    def embed(self, texts: List[str]) -> List[List[float]]: ...
    
    def embed_batch(self, texts: List[str], batch_size: int) -> List[List[float]]: ...

# Editor Plugin Configuration
@dataclass
class EditorPluginConfig:
    editor: str
    extensions: List[str]
    settings: Dict[str, Any]
    snippets: Dict[str, str]
    schema: Dict[str, Any]
```
