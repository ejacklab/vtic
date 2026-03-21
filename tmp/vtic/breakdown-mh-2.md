# Must Have Features (Batch 2) - 6-Level Breakdown

24 Must Have features broken down to implementation-ready specifications.

---

## Feature 1: Error Envelope

### L1: API
### L2: Response Formats
### L3: Error envelope
### L4: `format_error_response(error: VticError, request_id: Optional[str] = None) -> dict`
  - Wrap all API errors in consistent JSON structure
  - Include error code (machine-readable), message (human-readable), and details (optional field-level errors)
  - Include request_id from X-Request-ID header if available
  - Return appropriate HTTP status code based on error type

### L5: Spec
```python
@dataclass
class VticError:
    code: str           # Machine-readable error code
    message: str        # Human-readable error message
    details: Optional[List[FieldError]] = None  # Field-level errors for validation
    http_status: int = 400

@dataclass
class FieldError:
    field: str
    message: str
    code: str

def format_error_response(error: VticError, request_id: Optional[str] = None) -> dict:
    """
    Input: VticError(code="TICKET_NOT_FOUND", message="Ticket C1 not found", http_status=404)
           request_id="req-abc123"
    Output: {
        "error": {
            "code": "TICKET_NOT_FOUND",
            "message": "Ticket C1 not found",
            "request_id": "req-abc123"
        }
    }
    
    Input: VticError(code="VALIDATION_ERROR", message="Invalid input",
                     details=[FieldError("title", "Title is required", "REQUIRED")])
    Output: {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Invalid input",
            "details": [{"field": "title", "message": "Title is required", "code": "REQUIRED"}]
        }
    }
    """
```

### L6: Test
```python
test_format_error_response_basic_error()
test_format_error_response_with_request_id()
test_format_error_response_with_field_errors()
test_format_error_response_excludes_none_details()
test_format_error_response_serializable_to_json()
```

---

## Feature 2: Validation Errors

### L1: API
### L2: Error Handling
### L3: Validation errors
### L4: `validate_and_collect_errors(data: dict, schema: dict) -> ValidationResult`
  - Validate input data against schema definition
  - Collect ALL validation errors, not just first failure
  - Return field-level errors with field name, message, and error code
  - Support required fields, type checking, enum values, min/max constraints

### L5: Spec
```python
@dataclass
class ValidationRule:
    field: str
    required: bool = False
    type: Optional[type] = None
    enum: Optional[List[Any]] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # regex pattern

def validate_and_collect_errors(data: dict, rules: List[ValidationRule]) -> ValidationResult:
    """
    Input: data={"title": "", "severity": "invalid"},
           rules=[ValidationRule("title", required=True, min_length=1),
                  ValidationRule("severity", enum=["low", "medium", "high"])]
    Output: ValidationResult(
        is_valid=False,
        errors=[
            FieldError(field="title", message="Title is required", code="REQUIRED"),
            FieldError(field="severity", message="Must be one of: low, medium, high", code="INVALID_ENUM")
        ]
    )
    
    Input: data={"title": "Valid", "severity": "high"}, rules=[...]
    Output: ValidationResult(is_valid=True, errors=[])
    """
```

### L6: Test
```python
test_validate_required_field_missing()
test_validate_required_field_empty_string()
test_validate_type_mismatch()
test_validate_enum_invalid_value()
test_validate_min_length_violation()
test_validate_pattern_mismatch()
test_validate_collects_all_errors()
test_validate_stops_at_first_error_if_configured()
```

---

## Feature 3: Pagination Metadata

### L1: API
### L2: Pagination
### L3: Pagination metadata
### L4: `build_pagination_response(items: List[Any], total: int, limit: int, offset: int) -> dict`
  - Return pagination metadata with every list endpoint
  - Include total count, limit, offset, and has_more flag
  - Calculate has_more from total, limit, and offset
  - Wrap items in data array with meta object

### L5: Spec
```python
@dataclass
class PaginationMeta:
    total: int
    limit: int
    offset: int
    has_more: bool

def build_pagination_response(items: List[Any], total: int, limit: int, offset: int) -> dict:
    """
    Input: items=[ticket1, ticket2], total=50, limit=20, offset=0
    Output: {
        "data": [ticket1, ticket2],
        "meta": {
            "total": 50,
            "limit": 20,
            "offset": 0,
            "has_more": True
        }
    }
    
    Input: items=[ticket1], total=1, limit=20, offset=0
    Output: {
        "data": [ticket1],
        "meta": {"total": 1, "limit": 20, "offset": 0, "has_more": False}
    }
    
    Input: items=[], total=0, limit=20, offset=0
    Output: {
        "data": [],
        "meta": {"total": 0, "limit": 20, "offset": 0, "has_more": False}
    }
    """
```

### L6: Test
```python
test_build_pagination_response_basic()
test_build_pagination_response_has_more_true()
test_build_pagination_response_has_more_false()
test_build_pagination_response_empty_results()
test_build_pagination_response_last_page()
test_build_pagination_response_meta_values_correct()
```

---

## Feature 4: serve command

### L1: CLI
### L2: Core Commands
### L3: serve command
### L4: `cli_serve(args: ServeArgs, config: Config) -> int`
  - Start HTTP API server using configured host and port
  - Load configuration for tickets directory, embedding provider, etc.
  - Register all REST endpoints (tickets CRUD, search, health)
  - Handle graceful shutdown on SIGINT/SIGTERM
  - Return exit code 0 on clean shutdown, 1 on error

### L5: Spec
```python
@dataclass
class ServeArgs:
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False  # auto-reload on file changes (dev mode)
    workers: int = 1

def cli_serve(args: ServeArgs, config: Config) -> int:
    """
    Input: ServeArgs(host="0.0.0.0", port=3000), config with tickets_dir="./tickets"
    Action: Start HTTP server on 0.0.0.0:3000
            Register endpoints: POST /tickets, GET /tickets/:id, PATCH /tickets/:id,
                               DELETE /tickets/:id, GET /tickets, POST /search, GET /health
            Serve requests until SIGINT received
    Output (stdout): "vtic API server running on http://0.0.0.0:3000"
    Return: 0 (on clean shutdown), 1 (on startup error)
    
    Input: ServeArgs(port=80), config
    Error: PermissionError if port < 1024 without root
    Return: 1
    
    Input: ServeArgs(port=3000), config with port 3000 already in use
    Error: "Port 3000 already in use"
    Return: 1
    """
```

### L6: Test
```python
test_cli_serve_starts_server()
test_cli_serve_responds_to_health_endpoint()
test_cli_serve_responds_to_tickets_endpoints()
test_cli_serve_graceful_shutdown()
test_cli_serve_port_in_use_error()
test_cli_serve_uses_config_values()
test_cli_serve_custom_host_and_port()
```

---

## Feature 5: reindex command

### L1: CLI
### L2: Management Commands
### L3: reindex command
### L4: `cli_reindex(args: ReindexArgs, store: TicketStore, indexer: Indexer) -> int`
  - Rebuild Zvec index from all markdown files in tickets directory
  - Clear existing index before rebuild
  - Scan tickets directory for all .md files
  - Parse frontmatter and content from each file
  - Generate embeddings for semantic search if provider configured
  - Print progress and summary (files processed, errors)

### L5: Spec
```python
@dataclass
class ReindexArgs:
    force: bool = False  # Skip confirmation
    verbose: bool = False  # Show per-file progress

def cli_reindex(args: ReindexArgs, store: TicketStore, indexer: Indexer) -> int:
    """
    Input: ReindexArgs(force=True, verbose=True), store, indexer
    Action: 1. Scan tickets/ directory for all *.md files
            2. Parse each file, extract frontmatter and content
            3. Clear existing Zvec index
            4. Index all tickets (BM25 + optional embeddings)
            5. Persist updated index to .vtic/
    Output (stdout): 
        "Scanning tickets/..."
        "Found 50 tickets"
        "Indexing [==================================================] 100%"
        "Reindex complete: 50 tickets indexed, 0 errors"
    Return: 0
    
    Input: ReindexArgs(force=False)
    Output (stdout): "This will rebuild the index from all ticket files. Continue? [y/N]"
    Input (stdin): "y"
    Return: 0 or 2 if cancelled
    
    Input: store with corrupted/unparseable ticket files
    Output (stdout): "Reindex complete: 48 tickets indexed, 2 errors"
                      "Errors: tickets/owner/repo/bad1.md: Invalid frontmatter"
    Return: 0 (partial success)
    """
```

### L6: Test
```python
test_cli_reindex_rebuilds_index()
test_cli_reindex_clears_existing_index()
test_cli_reindex_handles_parse_errors()
test_cli_reindex_progress_output()
test_cli_reindex_confirmation_prompt()
test_cli_reindex_confirmation_skip_with_force()
test_cli_reindex_reports_error_count()
test_cli_reindex_with_embedding_provider()
test_cli_reindex_without_embedding_provider()
```

---

## Feature 6: Global config

### L1: Configuration
### L2: Configuration Files
### L3: Global config
### L4: `load_global_config() -> dict`
  - Load configuration from `~/.config/vtic/config.toml`
  - Create default config file if it doesn't exist
  - Return empty dict if file missing (not an error)
  - Handle TOML parse errors gracefully with helpful message

### L5: Spec
```python
GLOBAL_CONFIG_PATH = Path.home() / ".config" / "vtic" / "config.toml"

def load_global_config() -> dict:
    """
    Input: ~/.config/vtic/config.toml exists with content:
        [search]
        provider = "openai"
        [tickets]
        default_repo = "ejacklab/open-dsearch"
    Output: {"search": {"provider": "openai"}, "tickets": {"default_repo": "ejacklab/open-dsearch"}}
    
    Input: ~/.config/vtic/config.toml does not exist
    Output: {}  # empty dict, not an error
    
    Input: ~/.config/vtic/config.toml with invalid TOML syntax
    Error: ConfigError(f"Failed to parse {GLOBAL_CONFIG_PATH}: line 5: invalid syntax")
    Output: {}  # return empty and log warning
    """
```

### L6: Test
```python
test_load_global_config_exists()
test_load_global_config_missing_returns_empty()
test_load_global_config_invalid_toml_handles_gracefully()
test_load_global_config_creates_directory_if_missing()
test_load_global_config_expands_home_tilde()
```

---

## Feature 7: Config precedence

### L1: Configuration
### L2: Configuration Files
### L3: Config precedence
### L4: `merge_configs(global_config: dict, project_config: dict, env_vars: dict) -> dict`
  - Merge configurations with defined precedence: env_vars > project_config > global_config
  - Deep merge nested dictionaries (not just top-level replace)
  - Handle array values (replace, not merge)
  - Log which config source provided each value in debug mode

### L5: Spec
```python
def merge_configs(global_config: dict, project_config: dict, env_vars: dict) -> dict:
    """
    Input: 
        global_config = {"search": {"provider": "local"}, "tickets": {"dir": "~/tickets"}}
        project_config = {"search": {"provider": "openai"}, "api": {"port": 3000}}
        env_vars = {"VTIC_API_PORT": "8080"}
    Output: {
        "search": {"provider": "openai"},  # project overrides global
        "tickets": {"dir": "~/tickets"},   # from global (not in project)
        "api": {"port": 8080}              # from env (highest precedence)
    }
    
    Input:
        global_config = {"defaults": {"severity": "medium"}}
        project_config = {}
        env_vars = {"VTIC_DEFAULTS_SEVERITY": "critical"}
    Output: {"defaults": {"severity": "critical"}}  # env var wins
    
    Precedence order (highest to lowest):
    1. Environment variables (VTIC_SECTION_KEY format)
    2. Project config (./vtic.toml)
    3. Global config (~/.config/vtic/config.toml)
    """
```

### L6: Test
```python
test_merge_configs_global_only()
test_merge_configs_project_overrides_global()
test_merge_configs_env_overrides_all()
test_merge_configs_deep_merge_nested()
test_merge_configs_arrays_replace_not_merge()
test_merge_configs_empty_configs()
test_merge_configs_env_var_name_mapping()
```

---

## Feature 8: Config validation

### L1: Configuration
### L2: Configuration Files
### L3: Config validation
### L4: `validate_config(config: dict) -> ValidationResult`
  - Validate configuration structure and values
  - Check for required sections if applicable
  - Validate enum values (e.g., search.provider must be "openai", "local", "none")
  - Validate numeric ranges (e.g., api.port must be 1-65535)
  - Return all validation errors at once

### L5: Spec
```python
VALID_PROVIDERS = ["openai", "local", "none", "custom"]
VALID_LOG_LEVELS = ["debug", "info", "warning", "error"]

def validate_config(config: dict) -> ValidationResult:
    """
    Input: config = {"search": {"provider": "openai"}, "api": {"port": 3000}}
    Output: ValidationResult(is_valid=True, errors=[])
    
    Input: config = {"search": {"provider": "invalid_provider"}}
    Output: ValidationResult(is_valid=False, errors=[
        FieldError(field="search.provider", 
                   message="Must be one of: openai, local, none, custom",
                   code="INVALID_ENUM")
    ])
    
    Input: config = {"api": {"port": 99999}}
    Output: ValidationResult(is_valid=False, errors=[
        FieldError(field="api.port",
                   message="Port must be between 1 and 65535",
                   code="OUT_OF_RANGE")
    ])
    
    Input: config = {"embedding": {"dimension": "not_a_number"}}
    Output: ValidationResult(is_valid=False, errors=[
        FieldError(field="embedding.dimension",
                   message="Expected integer, got string",
                   code="TYPE_ERROR")
    ])
    """
```

### L6: Test
```python
test_validate_config_valid()
test_validate_config_invalid_provider()
test_validate_config_invalid_port_range()
test_validate_config_type_error()
test_validate_config_unknown_field_warning()
test_validate_config_multiple_errors()
test_validate_config_nested_field_errors()
```

---

## Feature 9: Override any config env vars

### L1: Configuration
### L2: Environment Variables
### L3: Override any config env vars
### L4: `parse_env_config(prefix: str = "VTIC_") -> dict`
  - Parse environment variables matching VTIC_ prefix
  - Convert VTIC_SECTION_KEY format to nested dict structure
  - Handle type conversion (strings to int, bool, float based on value)
  - Support nested sections with double underscore separator

### L5: Spec
```python
def parse_env_config(prefix: str = "VTIC_") -> dict:
    """
    Input: os.environ = {
        "VTIC_SEARCH_PROVIDER": "openai",
        "VTIC_API_PORT": "3000",
        "VTIC_EMBEDDING_DIMENSION": "1536",
        "VTIC_DEFAULTS_SEVERITY": "critical"
    }
    Output: {
        "search": {"provider": "openai"},
        "api": {"port": 3000},           # converted to int
        "embedding": {"dimension": 1536}, # converted to int
        "defaults": {"severity": "critical"}
    }
    
    Input: os.environ = {
        "VTIC_DEBUG": "true",
        "VTIC_SEARCH_ENABLE_SEMANTIC": "false"
    }
    Output: {
        "debug": True,                          # converted to bool
        "search": {"enable_semantic": False}    # converted to bool
    }
    
    Type conversion rules:
    - "true", "1", "yes" → True (bool)
    - "false", "0", "no" → False (bool)
    - Numeric strings → int or float
    - JSON arrays/objects → parsed
    - Everything else → string
    """
```

### L6: Test
```python
test_parse_env_config_simple_values()
test_parse_env_config_nested_sections()
test_parse_env_config_type_conversion_int()
test_parse_env_config_type_conversion_bool()
test_parse_env_config_type_conversion_float()
test_parse_env_config_ignores_non_prefix_vars()
test_parse_env_config_empty_returns_empty()
test_parse_env_config_json_values()
```

---

## Feature 10: Default values in config

### L1: Configuration
### L2: Defaults & Profiles
### L3: Default values in config
### L4: `apply_defaults(config: dict, defaults: dict) -> dict`
  - Apply default values for missing configuration keys
  - Deep merge defaults into config (config values take precedence)
  - Define system defaults for all optional configuration
  - Return fully populated config ready for use

### L5: Spec
```python
SYSTEM_DEFAULTS = {
    "tickets": {
        "dir": "./tickets",
        "index_dir": "./.vtic"
    },
    "api": {
        "host": "127.0.0.1",
        "port": 8080
    },
    "search": {
        "provider": "none",
        "bm25_weight": 0.7,
        "semantic_weight": 0.3
    },
    "embedding": {
        "provider": "none",
        "model": None,
        "dimension": 1536
    },
    "defaults": {
        "repo": None,
        "category": "code",
        "severity": "medium",
        "status": "open"
    }
}

def apply_defaults(config: dict, defaults: dict = SYSTEM_DEFAULTS) -> dict:
    """
    Input: config = {"api": {"port": 3000}}
           defaults = SYSTEM_DEFAULTS
    Output: {
        "tickets": {"dir": "./tickets", "index_dir": "./.vtic"},
        "api": {"host": "127.0.0.1", "port": 3000},  # port from config, host from default
        "search": {...},
        "embedding": {...},
        "defaults": {...}
    }
    
    Input: config = {}
    Output: SYSTEM_DEFAULTS (full copy)
    
    Input: config = {"defaults": {"severity": "critical"}}
    Output: {..., "defaults": {"repo": None, "category": "code", 
                               "severity": "critical", "status": "open"}}
    """
```

### L6: Test
```python
test_apply_defaults_empty_config()
test_apply_defaults_partial_config()
test_apply_defaults_config_overrides_defaults()
test_apply_defaults_deep_merge()
test_apply_defaults_no_mutation_of_input()
test_apply_defaults_nested_defaults()
```

---

## Feature 11: Required config check

### L1: Configuration
### L2: Defaults & Profiles
### L3: Required config check
### L4: `check_required_config(config: dict) -> List[ConfigError]`
  - Identify missing required configuration values
  - Different requirements based on enabled features (e.g., OpenAI needs API key)
  - Return list of errors with helpful messages on how to fix
  - Fail fast before operations that would fail anyway

### L5: Spec
```python
def check_required_config(config: dict) -> List[ConfigError]:
    """
    Input: config = {"search": {"provider": "openai"}}
           # Missing OPENAI_API_KEY
    Output: [
        ConfigError(
            field="openai.api_key",
            message="OpenAI API key required when search.provider is 'openai'",
            hint="Set OPENAI_API_KEY environment variable or add [openai] api_key to config"
        )
    ]
    
    Input: config = {"search": {"provider": "local"}}
           # No additional requirements for local provider
    Output: []
    
    Input: config = {"tickets": {"dir": ""}}
           # Empty required field
    Output: [
        ConfigError(
            field="tickets.dir",
            message="Tickets directory is required",
            hint="Set VTIC_TICKETS_DIR or add [tickets] dir to config"
        )
    ]
    
    Conditional requirements:
    - search.provider = "openai" → requires openai.api_key
    - search.provider = "custom" → requires embedding.endpoint
    - api.auth_enabled = true → requires api.auth_key
    """
```

### L6: Test
```python
test_check_required_config_no_requirements()
test_check_required_config_missing_openai_key()
test_check_required_config_missing_custom_endpoint()
test_check_required_config_missing_tickets_dir()
test_check_required_config_all_present()
test_check_required_config_conditional_requirements()
test_check_required_config_helpful_hints()
```

---

## Feature 12: OpenAI embeddings

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: OpenAI embeddings
### L4: `generate_openai_embedding(text: str, config: OpenAIConfig) -> List[float]`
  - Call OpenAI embeddings API with configured model
  - Support text-embedding-3-small and text-embedding-3-large models
  - Handle API key from config or OPENAI_API_KEY env var
  - Return embedding vector as list of floats
  - Respect API rate limits

### L5: Spec
```python
@dataclass
class OpenAIConfig:
    api_key: str
    model: str = "text-embedding-3-small"
    dimension: Optional[int] = None  # for dimension reduction

def generate_openai_embedding(text: str, config: OpenAIConfig) -> List[float]:
    """
    Input: text="CORS wildcard configuration issue in Express.js",
           config=OpenAIConfig(api_key="sk-...", model="text-embedding-3-small")
    Output: [0.0123, -0.0456, 0.0789, ...]  # 1536-dimensional vector
    
    Input: text="", config=...
    Error: EmbeddingError("Text cannot be empty")
    
    Input: text="...", config=OpenAIConfig(api_key="invalid", model="...")
    Error: EmbeddingError("OpenAI API error: Invalid API key", code="AUTH_ERROR")
    
    Input: text with > 8191 tokens
    Error: EmbeddingError("Text exceeds maximum token limit (8191)", code="TOKEN_LIMIT")
    """
```

### L6: Test
```python
test_generate_openai_embedding_returns_vector()
test_generate_openai_embedding_correct_dimension()
test_generate_openai_embedding_empty_text_error()
test_generate_openai_embedding_invalid_api_key_error()
test_generate_openai_embedding_token_limit_error()
test_generate_openai_embedding_small_vs_large_model()
test_generate_openai_embedding_dimension_reduction()
```

---

## Feature 13: Model selection

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: Model selection
### L4: `get_embedding_model_config(provider: str, model_name: Optional[str]) -> ModelConfig`
  - Return model configuration (dimension, max_tokens, cost_per_1k_tokens)
  - Support text-embedding-3-small (default) and text-embedding-3-large
  - Allow custom model names for future OpenAI models
  - Validate model name against known models

### L5: Spec
```python
@dataclass
class ModelConfig:
    name: str
    dimension: int
    max_tokens: int
    cost_per_1k_tokens: float

KNOWN_MODELS = {
    "text-embedding-3-small": ModelConfig(
        name="text-embedding-3-small",
        dimension=1536,
        max_tokens=8191,
        cost_per_1k_tokens=0.00002
    ),
    "text-embedding-3-large": ModelConfig(
        name="text-embedding-3-large",
        dimension=3072,
        max_tokens=8191,
        cost_per_1k_tokens=0.00013
    ),
    "text-embedding-ada-002": ModelConfig(
        name="text-embedding-ada-002",
        dimension=1536,
        max_tokens=8191,
        cost_per_1k_tokens=0.0001
    )
}

def get_embedding_model_config(provider: str, model_name: Optional[str] = None) -> ModelConfig:
    """
    Input: provider="openai", model_name=None
    Output: ModelConfig for "text-embedding-3-small" (default)
    
    Input: provider="openai", model_name="text-embedding-3-large"
    Output: ModelConfig(name="text-embedding-3-large", dimension=3072, ...)
    
    Input: provider="openai", model_name="unknown-model"
    Output: ModelConfig(name="unknown-model", dimension=1536, ...)  # use defaults
    Warning: "Unknown model 'unknown-model', using default dimension 1536"
    
    Input: provider="local", model_name="all-MiniLM-L6-v2"
    Output: ModelConfig(name="all-MiniLM-L6-v2", dimension=384, max_tokens=256, cost=0)
    """
```

### L6: Test
```python
test_get_embedding_model_config_default()
test_get_embedding_model_config_large()
test_get_embedding_model_config_unknown_model()
test_get_embedding_model_config_ada_002()
test_get_embedding_model_config_dimension_matches()
test_get_embedding_model_config_local_model()
```

---

## Feature 14: Rate limit handling

### L1: Embedding Providers
### L2: OpenAI Provider
### L3: Rate limit handling
### L4: `call_with_retry(fn: Callable, max_retries: int = 3, backoff_base: float = 1.0) -> Any`
  - Retry API calls on rate limit errors (HTTP 429)
  - Exponential backoff with jitter
  - Respect Retry-After header if provided
  - Give up after max retries with clear error

### L5: Spec
```python
def call_with_retry(
    fn: Callable[[], T],
    max_retries: int = 3,
    backoff_base: float = 1.0,
    max_backoff: float = 60.0
) -> T:
    """
    Input: fn that calls OpenAI API, max_retries=3
    Action on 429 response:
        - Retry 1: wait backoff_base * (2^0) = 1s + jitter
        - Retry 2: wait backoff_base * (2^1) = 2s + jitter
        - Retry 3: wait backoff_base * (2^2) = 4s + jitter
        - Give up if still failing
    
    Input: API returns 429 with Retry-After: 30
    Action: Wait exactly 30 seconds (respect header), then retry
    
    Input: All retries exhausted
    Error: RateLimitError("Rate limit exceeded after 3 retries. Last error: ...")
    
    Input: Non-rate-limit error (e.g., 401 Unauthorized)
    Error: Re-raise immediately without retry
    """
```

### L6: Test
```python
test_call_with_retry_success_no_retry()
test_call_with_retry_success_after_retry()
test_call_with_retry_exponential_backoff()
test_call_with_retry_respects_retry_after_header()
test_call_with_retry_max_retries_exceeded()
test_call_with_retry_non_rate_limit_error_no_retry()
test_call_with_retry_backoff_with_jitter()
```

---

## Feature 15: Sentence Transformers

### L1: Embedding Providers
### L2: Local Provider
### L3: Sentence Transformers
### L4: `generate_local_embedding(text: str, config: LocalConfig) -> List[float]`
  - Use sentence-transformers library for local embeddings
  - Default model: all-MiniLM-L6-v2 (fast, good quality)
  - Support any HuggingFace model name
  - Auto-download model on first use
  - No external API calls, fully offline

### L5: Spec
```python
@dataclass
class LocalConfig:
    model: str = "all-MiniLM-L6-v2"
    cache_dir: Optional[str] = None  # defaults to ~/.cache/vtic/models/
    device: str = "cpu"  # "cpu" or "cuda"

def generate_local_embedding(text: str, config: LocalConfig) -> List[float]:
    """
    Input: text="CORS wildcard configuration issue",
           config=LocalConfig(model="all-MiniLM-L6-v2")
    Output: [0.0234, -0.0156, 0.0891, ...]  # 384-dimensional vector for MiniLM
    
    Input: text="...", config=LocalConfig(model="sentence-transformers/all-mpnet-base-v2")
    Output: [...]  # 768-dimensional vector
    
    Input: First call with new model
    Action: Download model from HuggingFace Hub to cache_dir
    Output (stderr): "Downloading model all-MiniLM-L6-v2..."
    
    Input: config=LocalConfig(device="cuda"), no GPU available
    Warning: "CUDA requested but not available, falling back to CPU"
    Output: [...]  # works on CPU
    
    Input: config=LocalConfig(model="nonexistent/model")
    Error: EmbeddingError("Failed to load model 'nonexistent/model': Model not found")
    """
```

### L6: Test
```python
test_generate_local_embedding_returns_vector()
test_generate_local_embedding_correct_dimension()
test_generate_local_embedding_default_model()
test_generate_local_embedding_custom_model()
test_generate_local_embedding_model_download()
test_generate_local_embedding_gpu_fallback()
test_generate_local_embedding_invalid_model_error()
```

---

## Feature 16: No API key

### L1: Embedding Providers
### L2: Local Provider
### L3: No API key
### L4: `check_provider_requirements(provider: str, config: dict) -> bool`
  - Verify no API key required for local/none providers
  - Return True if provider can operate with current config
  - Return False if provider requires missing configuration
  - Local provider requires no external credentials

### L5: Spec
```python
def check_provider_requirements(provider: str, config: dict) -> bool:
    """
    Input: provider="local", config={}
    Output: True  # local provider needs no API key
    
    Input: provider="none", config={}
    Output: True  # none provider disables embeddings
    
    Input: provider="openai", config={"openai": {"api_key": "sk-..."}}
    Output: True  # has required API key
    
    Input: provider="openai", config={}
    Output: False  # missing API key
    
    Input: provider="custom", config={"embedding": {"endpoint": "http://..."}}
    Output: True  # has required endpoint
    
    Input: provider="custom", config={}
    Output: False  # missing endpoint
    """
```

### L6: Test
```python
test_check_provider_requirements_local_no_key_needed()
test_check_provider_requirements_none_no_key_needed()
test_check_provider_requirements_openai_has_key()
test_check_provider_requirements_openai_missing_key()
test_check_provider_requirements_custom_has_endpoint()
test_check_provider_requirements_custom_missing_endpoint()
```

---

## Feature 17: Disable semantic

### L1: Embedding Providers
### L2: None Provider (BM25 Only)
### L3: Disable semantic
### L4: `configure_embedding_provider(config: dict) -> Optional[EmbeddingProvider]`
  - Return None when search.provider = "none" or embedding.provider = "none"
  - Skip all embedding operations when disabled
  - Still allow BM25 keyword search
  - Reduce memory usage by not loading embedding models

### L5: Spec
```python
def configure_embedding_provider(config: dict) -> Optional[EmbeddingProvider]:
    """
    Input: config = {"search": {"provider": "none"}}
    Output: None  # embeddings disabled
    
    Input: config = {"embedding": {"provider": "none"}}
    Output: None  # embeddings explicitly disabled
    
    Input: config = {"search": {"provider": "openai"}, "openai": {"api_key": "sk-..."}}
    Output: OpenAIEmbeddingProvider(config)  # embeddings enabled
    
    Input: config = {"search": {"provider": "local"}}
    Output: LocalEmbeddingProvider(config)  # embeddings enabled
    
    When None returned:
    - Search uses BM25 only
    - No embedding generation on ticket create/update
    - Reindex skips embedding step
    """
```

### L6: Test
```python
test_configure_embedding_provider_none_returns_none()
test_configure_embedding_provider_explicit_none_returns_none()
test_configure_embedding_provider_openai_returns_provider()
test_configure_embedding_provider_local_returns_provider()
test_configure_embedding_provider_disabled_no_embeddings_on_create()
test_configure_embedding_provider_disabled_bm25_still_works()
```

---

## Feature 18: Clear error on semantic query

### L1: Embedding Providers
### L2: None Provider (BM25 Only)
### L3: Clear error on semantic query
### L4: `execute_search(query: str, options: SearchOptions, provider: Optional[EmbeddingProvider]) -> SearchResults`
  - Check if semantic search requested but embeddings disabled
  - Return clear, actionable error message
  - Suggest alternatives (use BM25, enable provider)
  - Include documentation link

### L5: Spec
```python
def execute_search(
    query: str,
    options: SearchOptions,
    provider: Optional[EmbeddingProvider]
) -> SearchResults:
    """
    Input: query="auth issue", options=SearchOptions(semantic=True), provider=None
    Error: SearchError(
        code="SEMANTIC_SEARCH_DISABLED",
        message="Semantic search requested but no embedding provider configured",
        hint="Set search.provider to 'openai' or 'local' in config, or remove --semantic flag for BM25-only search",
        docs_url="https://vtic.dev/docs/search#semantic"
    )
    
    Input: query="auth issue", options=SearchOptions(semantic=False), provider=None
    Output: SearchResults using BM25 only (success)
    
    Input: query="auth issue", options=SearchOptions(semantic=True, hybrid=True), provider=None
    Error: SearchError(..., message="Hybrid search requires semantic embeddings...")
    
    Input: query="auth issue", options=SearchOptions(semantic=True), provider=OpenAIProvider(...)
    Output: SearchResults with semantic search (success)
    """
```

### L6: Test
```python
test_execute_search_semantic_without_provider_error()
test_execute_search_bm25_without_provider_success()
test_execute_search_hybrid_without_provider_error()
test_execute_search_semantic_with_provider_success()
test_execute_search_error_message_actionable()
test_execute_search_error_includes_docs_link()
```

---

## Feature 19: Owner/repo structure

### L1: Multi-Repo Support
### L2: Namespacing
### L3: Owner/repo structure
### L4: `get_ticket_path(owner: str, repo: str, category: str, ticket_id: str) -> Path`
  - Generate file path following tickets/{owner}/{repo}/{category}/{id}.md structure
  - Validate owner and repo names (alphanumeric, hyphens, underscores)
  - Sanitize paths to prevent directory traversal
  - Support both CLI and API ticket creation

### L5: Spec
```python
def get_ticket_path(owner: str, repo: str, category: str, ticket_id: str, base_dir: Path) -> Path:
    """
    Input: owner="ejacklab", repo="open-dsearch", category="code", ticket_id="C1",
           base_dir=Path("./tickets")
    Output: Path("./tickets/ejacklab/open-dsearch/code/C1.md")
    
    Input: owner="my-org", repo="my_repo", category="security", ticket_id="S5"
    Output: Path("./tickets/my-org/my_repo/security/S5.md")
    
    Input: owner="../../../etc", repo="...", category="code", ticket_id="X1"
    Error: ValueError("Invalid owner name: contains path traversal")
    
    Input: owner="valid", repo="valid", category="invalid category!", ticket_id="C1"
    Error: ValueError("Invalid category name: must be alphanumeric with hyphens/underscores")
    
    Validation rules:
    - owner: 1-100 chars, alphanumeric, hyphens, underscores
    - repo: 1-100 chars, alphanumeric, hyphens, underscores, dots
    - category: alphanumeric, hyphens, underscores (predefined: code, security, hotfix, maintenance, docs, infra)
    - ticket_id: uppercase letter + digits (e.g., C1, S42)
    """
```

### L6: Test
```python
test_get_ticket_path_basic()
test_get_ticket_path_with_hyphens()
test_get_ticket_path_with_underscores()
test_get_ticket_path_with_dots_in_repo()
test_get_ticket_path_traversal_attack_blocked()
test_get_ticket_path_invalid_owner()
test_get_ticket_path_invalid_repo()
test_get_ticket_path_invalid_category()
```

---

## Feature 20: Multiple owners

### L1: Multi-Repo Support
### L2: Namespacing
### L3: Multiple owners
### L4: `list_owners(store: TicketStore) -> List[str]`
  - Scan tickets directory for all unique owner names
  - Return sorted list of owners
  - Support filtering by pattern

### L5: Spec
```python
def list_owners(store: TicketStore, pattern: Optional[str] = None) -> List[str]:
    """
    Input: store with tickets at:
        - tickets/ejacklab/open-dsearch/code/C1.md
        - tickets/ejacklab/vtic/security/S1.md
        - tickets/acme/ops/maintenance/M1.md
    Output: ["acme", "ejacklab"]
    
    Input: pattern="ej*"
    Output: ["ejacklab"]
    
    Input: store with no tickets
    Output: []
    
    Input: pattern="[invalid regex"
    Error: ValueError("Invalid pattern: ...")
    """
```

### L6: Test
```python
test_list_owners_multiple()
test_list_owners_single()
test_list_owners_empty()
test_list_owners_sorted()
test_list_owners_with_pattern()
test_list_owners_pattern_no_match()
```

---

## Feature 21: Glob repo filter

### L1: Multi-Repo Support
### L2: Cross-Repo Operations
### L3: Glob repo filter
### L4: `match_repo_glob(repo: str, pattern: str) -> bool`
  - Match repo names against glob patterns
  - Support * wildcard (e.g., "ejacklab/*" matches all repos under ejacklab)
  - Support ? single character wildcard
  - Multiple patterns with comma separation

### L5: Spec
```python
def match_repo_glob(repo: str, pattern: str) -> bool:
    """
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/*"
    Output: True
    
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/open-*"
    Output: True
    
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/vtic"
    Output: False
    
    Input: repo="ejacklab/open-dsearch", pattern="*"
    Output: True  # matches everything
    
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/???"
    Output: False  # ??? matches 3-char repos only
    
    Input: repo="ejacklab/open-dsearch", pattern="ejacklab/open-dsearch"
    Output: True  # exact match
    """

def filter_repos_by_glob(repos: List[str], pattern: str) -> List[str]:
    """
    Input: repos=["ejacklab/open-dsearch", "ejacklab/vtic", "acme/ops"],
           pattern="ejacklab/*"
    Output: ["ejacklab/open-dsearch", "ejacklab/vtic"]
    
    Input: repos=[...], pattern="ejacklab/open-dsearch,acme/*"
    Output: ["ejacklab/open-dsearch", "acme/ops"]  # comma-separated patterns
    """
```

### L6: Test
```python
test_match_repo_glob_star_wildcard()
test_match_repo_glob_exact_match()
test_match_repo_glob_question_wildcard()
test_match_repo_glob_no_match()
test_filter_repos_by_glob_single_pattern()
test_filter_repos_by_glob_multiple_patterns()
test_filter_repos_by_glob_empty_list()
```

---

## Feature 22: Multi-repo filter

### L1: Multi-Repo Support
### L2: Cross-Repo Operations
### L3: Multi-repo filter
### L4: `parse_repo_filter(filter_str: str) -> List[str]`
  - Parse comma-separated list of repos
  - Support exact repo names
  - Support glob patterns (delegated to glob filter)
  - Return list of repo names or patterns

### L5: Spec
```python
def parse_repo_filter(filter_str: str) -> List[str]:
    """
    Input: filter_str="ejacklab/open-dsearch"
    Output: ["ejacklab/open-dsearch"]
    
    Input: filter_str="ejacklab/open-dsearch,ejacklab/vtic"
    Output: ["ejacklab/open-dsearch", "ejacklab/vtic"]
    
    Input: filter_str="ejacklab/*,acme/ops"
    Output: ["ejacklab/*", "acme/ops"]  # mix of glob and exact
    
    Input: filter_str=""
    Output: []  # empty filter = all repos
    
    Input: filter_str="  ejacklab/open-dsearch  ,  ejacklab/vtic  "
    Output: ["ejacklab/open-dsearch", "ejacklab/vtic"]  # whitespace trimmed
    """

def apply_repo_filter(tickets: List[Ticket], repo_filter: List[str]) -> List[Ticket]:
    """
    Input: tickets=[t1(repo="a/b"), t2(repo="c/d"), t3(repo="a/e")],
           repo_filter=["a/*"]
    Output: [t1, t3]
    
    Input: repo_filter=[]
    Output: [t1, t2, t3]  # empty filter returns all
    """
```

### L6: Test
```python
test_parse_repo_filter_single()
test_parse_repo_filter_multiple()
test_parse_repo_filter_with_glob()
test_parse_repo_filter_empty()
test_parse_repo_filter_whitespace_trimmed()
test_apply_repo_filter_exact_match()
test_apply_repo_filter_glob_pattern()
test_apply_repo_filter_empty_returns_all()
```

---

## Feature 23: Cross-repo search

### L1: Multi-Repo Support
### L2: Cross-Repo Operations
### L3: Cross-repo search
### L4: `search_all_repos(query: str, options: SearchOptions, store: TicketStore) -> SearchResults`
  - Search across all repos by default when no repo filter specified
  - Include repo name in each result for identification
  - Aggregate results from multiple repos into single ranked list
  - Support optional repo filtering to limit scope

### L5: Spec
```python
def search_all_repos(
    query: str,
    options: SearchOptions,
    store: TicketStore
) -> SearchResults:
    """
    Input: query="CORS issue", options=SearchOptions(), store with tickets in multiple repos
    Action: Search all tickets across all owners/repos
    Output: SearchResults(
        items=[
            SearchResult(ticket=t1, score=0.95, repo="ejacklab/open-dsearch"),
            SearchResult(ticket=t2, score=0.82, repo="acme/webapp"),
            SearchResult(ticket=t3, score=0.71, repo="ejacklab/vtic")
        ],
        total=3,
        query=query
    )
    
    Input: query="CORS issue", options=SearchOptions(repo_filter=["ejacklab/*"])
    Action: Search only tickets in ejacklab/* repos
    Output: SearchResults with only ejacklab tickets
    
    Input: query="CORS issue", options=SearchOptions(limit=10), large result set
    Output: Top 10 results across all repos, ranked by score
    
    Note: Repo name included in each result for display purposes
    """
```

### L6: Test
```python
test_search_all_repos_multiple_owners()
test_search_all_repos_ranked_by_score()
test_search_all_repos_with_repo_filter()
test_search_all_repos_includes_repo_in_result()
test_search_all_repos_respects_limit()
test_search_all_repos_no_results()
test_search_all_repos_aggregates_all_repos()
```

---

## Feature 24: Environment variables CI

### L1: Integration
### L2: CI/CD Integration
### L3: Environment variables CI
### L4: `configure_from_env() -> Config`
  - Load all configuration from environment variables for CI/CD
  - Support zero-config mode with sensible defaults
  - No config files required, everything via env vars
  - Validate configuration on load

### L5: Spec
```python
def configure_from_env(prefix: str = "VTIC_") -> Config:
    """
    Input: os.environ = {
        "VTIC_TICKETS_DIR": "/data/tickets",
        "VTIC_SEARCH_PROVIDER": "none",
        "VTIC_API_HOST": "0.0.0.0",
        "VTIC_API_PORT": "8080",
        "VTIC_LOG_LEVEL": "info"
    }
    Output: Config(
        tickets={"dir": "/data/tickets", "index_dir": "/data/tickets/.vtic"},
        search={"provider": "none", ...},
        api={"host": "0.0.0.0", "port": 8080},
        log_level="info"
    )
    
    Input: os.environ = {}  # no VTIC_ vars
    Output: Config with all system defaults
    Warning: "No VTIC_ environment variables found, using defaults"
    
    Input: os.environ = {"VTIC_SEARCH_PROVIDER": "invalid"}
    Error: ConfigError("Invalid VTIC_SEARCH_PROVIDER: must be openai, local, none, or custom")
    
    CI-friendly features:
    - Exit codes: 0 success, 1 error, 2 validation error
    - JSON output: --format json for parsing
    - No interactive prompts: fail immediately on missing required config
    - Structured logs: JSON log format with VTIC_LOG_FORMAT=json
    """
```

### L6: Test
```python
test_configure_from_env_all_vars()
test_configure_from_env_empty_uses_defaults()
test_configure_from_env_invalid_value_error()
test_configure_from_env_type_conversion()
test_configure_from_env_no_interactive_prompts()
test_configure_from_env_json_log_format()
test_configure_from_env_exit_codes()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | API | Response Formats | Error envelope | `format_error_response()` |
| 2 | API | Error Handling | Validation errors | `validate_and_collect_errors()` |
| 3 | API | Pagination | Pagination metadata | `build_pagination_response()` |
| 4 | CLI | Core Commands | serve command | `cli_serve()` |
| 5 | CLI | Management Commands | reindex command | `cli_reindex()` |
| 6 | Configuration | Configuration Files | Global config | `load_global_config()` |
| 7 | Configuration | Configuration Files | Config precedence | `merge_configs()` |
| 8 | Configuration | Configuration Files | Config validation | `validate_config()` |
| 9 | Configuration | Environment Variables | Override any config env vars | `parse_env_config()` |
| 10 | Configuration | Defaults & Profiles | Default values in config | `apply_defaults()` |
| 11 | Configuration | Defaults & Profiles | Required config check | `check_required_config()` |
| 12 | Embedding Providers | OpenAI Provider | OpenAI embeddings | `generate_openai_embedding()` |
| 13 | Embedding Providers | OpenAI Provider | Model selection | `get_embedding_model_config()` |
| 14 | Embedding Providers | OpenAI Provider | Rate limit handling | `call_with_retry()` |
| 15 | Embedding Providers | Local Provider | Sentence Transformers | `generate_local_embedding()` |
| 16 | Embedding Providers | Local Provider | No API key | `check_provider_requirements()` |
| 17 | Embedding Providers | None Provider | Disable semantic | `configure_embedding_provider()` |
| 18 | Embedding Providers | None Provider | Clear error on semantic query | `execute_search()` |
| 19 | Multi-Repo Support | Namespacing | Owner/repo structure | `get_ticket_path()` |
| 20 | Multi-Repo Support | Namespacing | Multiple owners | `list_owners()` |
| 21 | Multi-Repo Support | Cross-Repo Operations | Glob repo filter | `match_repo_glob()` |
| 22 | Multi-Repo Support | Cross-Repo Operations | Multi-repo filter | `parse_repo_filter()` |
| 23 | Multi-Repo Support | Cross-Repo Operations | Cross-repo search | `search_all_repos()` |
| 24 | Integration | CI/CD Integration | Environment variables CI | `configure_from_env()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set, Callable, TypeVar, Protocol
from pathlib import Path
from datetime import datetime

T = TypeVar('T')

# Error Handling
@dataclass
class FieldError:
    field: str
    message: str
    code: str

@dataclass
class VticError:
    code: str
    message: str
    details: Optional[List[FieldError]] = None
    http_status: int = 400

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[FieldError]

# Pagination
@dataclass
class PaginationMeta:
    total: int
    limit: int
    offset: int
    has_more: bool

# Configuration
@dataclass
class Config:
    tickets: dict
    search: dict
    api: dict
    embedding: dict
    defaults: dict
    log_level: str = "info"

@dataclass
class OpenAIConfig:
    api_key: str
    model: str = "text-embedding-3-small"
    dimension: Optional[int] = None

@dataclass
class LocalConfig:
    model: str = "all-MiniLM-L6-v2"
    cache_dir: Optional[str] = None
    device: str = "cpu"

@dataclass
class ModelConfig:
    name: str
    dimension: int
    max_tokens: int
    cost_per_1k_tokens: float

# Search
@dataclass
class SearchOptions:
    semantic: bool = False
    hybrid: bool = False
    repo_filter: List[str] = field(default_factory=list)
    limit: int = 20
    offset: int = 0

@dataclass
class SearchResult:
    ticket: 'Ticket'
    score: float
    repo: str

@dataclass
class SearchResults:
    items: List[SearchResult]
    total: int
    query: str

# CLI Args
@dataclass
class ServeArgs:
    host: str = "127.0.0.1"
    port: int = 8080
    reload: bool = False
    workers: int = 1

@dataclass
class ReindexArgs:
    force: bool = False
    verbose: bool = False

# Storage Protocol
class TicketStore(Protocol):
    def get(self, ticket_id: str) -> Optional['Ticket']: ...
    def save(self, ticket: 'Ticket') -> None: ...
    def delete(self, ticket_id: str) -> bool: ...
    def list_all(self) -> List['Ticket']: ...

class Indexer(Protocol):
    def clear(self) -> None: ...
    def index(self, ticket: 'Ticket') -> None: ...
    def search(self, query: str, options: SearchOptions) -> SearchResults: ...

class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> List[float]: ...
    def embed_batch(self, texts: List[str]) -> List[List[float]]: ...
```
