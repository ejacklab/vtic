# Should Have Features (P1) - 6-Level Breakdown

13 Should Have features broken down to implementation-ready specifications.

---

## Feature 1: Quiet Mode

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
    
    Input: data=[Ticket(id="C1"), ...], command="list", config.quiet=False
    Output: (formatted table with all fields)
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

## Feature 2: Verbose Mode

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
    
    Input: Namespace(verbose=False)
    Output: OutputConfig(verbose=False, ...)
    """

def verbose_log(message: str, config: OutputConfig) -> None:
    """
    Log message to stderr if verbose mode enabled.
    
    Input: message="Reading file: tickets/owner/repo/C1.md", config.verbose=True
    Output (stderr): "[VERBOSE] 2026-03-17T10:00:00Z Reading file: tickets/owner/repo/C1.md"
    
    Input: message="...", config.verbose=False
    Output: (nothing)
    """

def verbose_log_operation(operation: str, details: Dict[str, Any], config: OutputConfig) -> None:
    """
    Log structured operation details.
    
    Input: operation="api_call", details={"endpoint": "/embeddings", "tokens": 150}, config.verbose=True
    Output (stderr): "[VERBOSE] 2026-03-17T10:00:00Z api_call: endpoint=/embeddings tokens=150"
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

## Feature 3: Color Control

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

# Status color mapping
STATUS_COLORS = {
    "open": "blue",
    "in_progress": "yellow",
    "blocked": "red",
    "fixed": "green",
    "wont_fix": "gray",
    "closed": "gray",
}

# Severity color mapping
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
    
    Input: Namespace(color="auto"), sys.stdout.isatty()=False (piped)
    Output: ColorConfig(enabled=False, mode="auto")
    
    Input: Namespace(color="always")
    Output: ColorConfig(enabled=True, mode="always")
    
    Input: Namespace(color="never")
    Output: ColorConfig(enabled=False, mode="never")
    """

def colorize(text: str, color: str, config: ColorConfig) -> str:
    """
    Apply ANSI color code if colors enabled.
    
    Input: text="open", color="blue", config.enabled=True
    Output: "\033[34mopen\033[0m"
    
    Input: text="open", color="blue", config.enabled=False
    Output: "open"
    """

def colorize_status(status: str, config: ColorConfig) -> str:
    """
    Input: status="fixed", config.enabled=True
    Output: "\033[32mfixed\033[0m" (green)
    """

def colorize_severity(severity: str, config: ColorConfig) -> str:
    """
    Input: severity="critical", config.enabled=True
    Output: "\033[31mcritical\033[0m" (red)
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

## Feature 4: Tab Completion

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

# All available commands
COMMANDS = [
    "init", "create", "get", "update", "delete", "list", "search", "serve",
    "reindex", "config", "stats", "validate", "doctor", "trash", "backup",
    "migrate", "completion", "export", "import",
]

# Options per command
COMMAND_OPTIONS = {
    "create": ["--title", "--description", "--repo", "--category", "--severity", 
               "--status", "--tags", "--file-refs", "--format", "--quiet", "--verbose"],
    "get": ["--format", "--fields", "--raw", "--quiet", "--verbose"],
    "update": ["--status", "--severity", "--title", "--description", "--category",
               "--tags", "--file-refs", "--fix", "--append", "--clear", "--quiet", "--verbose"],
    "delete": ["--force", "--yes", "--quiet", "--verbose"],
    "list": ["--status", "--severity", "--category", "--repo", "--sort", "--limit",
             "--offset", "--format", "--quiet", "--verbose"],
    "search": ["--semantic", "--bm25", "--hybrid", "--status", "--severity",
               "--category", "--repo", "--limit", "--format", "--quiet", "--verbose"],
    "serve": ["--host", "--port", "--reload", "--quiet", "--verbose"],
}

# Finite option values
OPTION_VALUES = {
    "--status": ["open", "in_progress", "blocked", "fixed", "wont_fix", "closed"],
    "--severity": ["critical", "high", "medium", "low"],
    "--category": ["code", "security", "hotfix", "maintenance", "docs", "infra"],
    "--format": ["table", "json", "markdown", "yaml", "csv"],
    "--color": ["auto", "always", "never"],
}

def generate_completion_script(shell: ShellType) -> str:
    """
    Generate shell completion script.
    
    Input: shell="bash"
    Output: Bash completion script using complete -F _vtic vtic
            - _vtic() function with COMPREPLY
            - Completes commands, options, and option values
    
    Input: shell="zsh"
    Output: Zsh completion script with #compdef vtic
            - _vtic() function with _arguments and _values
            - Uses _describe for commands/options
    
    Input: shell="fish"
    Output: Fish completion script with complete -c vtic
            - complete -c vtic -n __fish_use_subcommand -a 'init' -d 'Initialize'
            - complete -c vtic -n '__fish_seen_subcommand_from get' -a '(vtic __complete ids)'
    """

def get_dynamic_completions(completion_type: str, store: TicketStore) -> List[str]:
    """
    Get dynamic completions (e.g., ticket IDs from store).
    
    Input: completion_type="ids", store with tickets C1, C2, S1
    Output: ["C1", "C2", "S1"]
    
    Input: completion_type="repos", store with repos owner/repo1, owner/repo2
    Output: ["owner/repo1", "owner/repo2"]
    """

def cli_complete(args: List[str], store: TicketStore) -> int:
    """
    Handle `vtic __complete <context>` for dynamic completion.
    
    Input: args=["ids", "get"], store with C1, C2
    Output (stdout): "C1\nC2"
    Return: 0
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

## Feature 5: Completion Install

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

# Shell detection patterns
SHELL_PATTERNS = {
    "bash": ["/bash", "/bashrc"],
    "zsh": ["/zsh", "/zshrc"],
    "fish": ["/fish"],
}

# Default install locations
INSTALL_LOCATIONS = {
    "bash": [
        "~/.bash_completion.d/vtic",
        "~/.bash_completion",
    ],
    "zsh": [
        "~/.zsh/completion/_vtic",
        "~/.oh-my-zsh/completions/_vtic",
    ],
    "fish": [
        "~/.config/fish/completions/vtic.fish",
    ],
}

# Reload instructions
RELOAD_INSTRUCTIONS = {
    "bash": "Run: source ~/.bashrc  # or restart your terminal",
    "zsh": "Run: exec zsh  # or restart your terminal",
    "fish": "Completions loaded automatically",
}

def detect_shell() -> Optional[str]:
    """
    Detect current shell from $SHELL env var.
    
    Input: os.environ["SHELL"] = "/bin/bash"
    Output: "bash"
    
    Input: os.environ["SHELL"] = "/usr/bin/zsh"
    Output: "zsh"
    
    Input: os.environ.get("SHELL") = None
    Output: None
    """

def get_install_location(shell: str) -> Path:
    """
    Get first writable install location for shell.
    
    Input: shell="bash"
    Output: Path("~/.bash_completion.d/vtic") or fallback
    
    Input: shell="fish"
    Output: Path("~/.config/fish/completions/vtic.fish")
    """

def cli_completion_install(args: CompletionInstallArgs) -> int:
    """
    Install completion script.
    
    Input: CompletionInstallArgs(shell=None)  # auto-detect bash
    Action: Detect bash, write script to ~/.bash_completion.d/vtic
    Output (stdout): "Installed vtic completion for bash"
                     "Run: source ~/.bashrc"
    Return: 0
    
    Input: CompletionInstallArgs(shell="zsh", output="/tmp/_vtic")
    Action: Write zsh script to /tmp/_vtic
    Output (stdout): "Wrote zsh completion to /tmp/_vtic"
    Return: 0
    
    Input: CompletionInstallArgs(shell="unknown")
    Output (stderr): "Unsupported shell: unknown. Supported: bash, zsh, fish"
    Return: 1
    
    Input: CompletionInstallArgs(shell="bash", dry_run=True)
    Output (stdout): "Would write bash completion to ~/.bash_completion.d/vtic"
    Return: 0
    """

def uninstall_completion(shell: str) -> bool:
    """
    Remove installed completion script.
    
    Input: shell="bash"
    Action: Remove ~/.bash_completion.d/vtic if exists
    Output: True if removed, False if not found
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

## Feature 6: Standard Env Names

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
    - `VTIC_EMBEDDING_MODEL` → `embedding.model`
    - `VTIC_EMBEDDING_DIMENSIONS` → `embedding.dimensions`
    - `VTIC_SERVER_HOST` → `server.host`
    - `VTIC_SERVER_PORT` → `server.port`
  - Handle type coercion (string to int, bool, etc.)
  - Return dict matching config structure

### L5: Spec
```python
import os
from typing import Any, Dict

# Environment variable to config path mapping
ENV_MAPPING = {
    # Core
    "VTIC_TICKETS_DIR": ("tickets_dir", str),
    "VTIC_INDEX_DIR": ("index_dir", str),
    "VTIC_CONFIG_FILE": ("config_file", str),
    
    # Search
    "VTIC_SEARCH_PROVIDER": ("search.provider", str),
    "VTIC_SEARCH_BM25_WEIGHT": ("search.bm25_weight", float),
    "VTIC_SEARCH_SEMANTIC_WEIGHT": ("search.semantic_weight", float),
    
    # Embedding
    "VTIC_EMBEDDING_PROVIDER": ("embedding.provider", str),
    "VTIC_EMBEDDING_MODEL": ("embedding.model", str),
    "VTIC_EMBEDDING_DIMENSIONS": ("embedding.dimensions", int),
    "VTIC_EMBEDDING_BATCH_SIZE": ("embedding.batch_size", int),
    
    # OpenAI
    "OPENAI_API_KEY": ("embedding.openai.api_key", str),
    "VTIC_OPENAI_MODEL": ("embedding.openai.model", str),
    
    # Local
    "VTIC_LOCAL_MODEL": ("embedding.local.model", str),
    "VTIC_LOCAL_CACHE_DIR": ("embedding.local.cache_dir", str),
    
    # Custom
    "VTIC_CUSTOM_ENDPOINT": ("embedding.custom.endpoint", str),
    "VTIC_CUSTOM_AUTH_HEADER": ("embedding.custom.auth_header", str),
    "VTIC_CUSTOM_AUTH_TOKEN": ("embedding.custom.auth_token", str),
    
    # Server
    "VTIC_SERVER_HOST": ("server.host", str),
    "VTIC_SERVER_PORT": ("server.port", int),
    "VTIC_SERVER_RELOAD": ("server.reload", bool),
    
    # API
    "VTIC_API_KEY": ("api.key", str),
}

def parse_env_config() -> Dict[str, Any]:
    """
    Parse all VTIC_* env vars into nested config dict.
    
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
    
    Input: os.environ = {}  # no VTIC vars
    Output: {}
    """

def coerce_value(value: str, target_type: type) -> Any:
    """
    Convert string env var to target type.
    
    Input: value="8080", target_type=int
    Output: 8080
    
    Input: value="3.14", target_type=float
    Output: 3.14
    
    Input: value="true", target_type=bool
    Output: True
    
    Input: value="yes", target_type=bool
    Output: True
    
    Input: value="0", target_type=bool
    Output: False
    
    Error: ValueError if coercion fails
    """

def set_nested_dict(d: Dict, path: str, value: Any) -> None:
    """
    Set value at nested path in dict.
    
    Input: d={}, path="search.provider", value="hybrid"
    Result: d = {"search": {"provider": "hybrid"}}
    
    Input: d={"search": {}}, path="search.bm25_weight", value=0.7
    Result: d = {"search": {"bm25_weight": 0.7}}
    """

def get_env_var_name(path: str) -> str:
    """
    Convert config path to env var name.
    
    Input: path="search.provider"
    Output: "VTIC_SEARCH_PROVIDER"
    
    Input: path="embedding.openai.api_key"
    Output: "VTIC_EMBEDDING_OPENAI_API_KEY"
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
test_coerce_value_bool_various_formats()
test_coerce_value_string_passthrough()
test_coerce_value_invalid_int_raises()
test_set_nested_dict_creates_nested_structure()
test_set_nested_dict_preserves_existing()
test_get_env_var_name_simple()
test_get_env_var_name_nested()
```

---

## Feature 7: Env File Support

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
import os
import re
from pathlib import Path

ENV_FILE_PATTERNS = [".env", ".env.local", ".env.development", ".env.production"]

def find_env_file(start_dir: str = ".") -> Optional[Path]:
    """
    Find .env file in current or parent directories.
    
    Input: start_dir=".", file "./.env" exists
    Output: Path(".env")
    
    Input: start_dir=".", no .env in current, exists in parent
    Output: Path("../.env")
    
    Input: start_dir=".", no .env anywhere
    Output: None
    """

def parse_env_content(content: str) -> Dict[str, str]:
    """
    Parse .env file content into key-value dict.
    
    Input: content='KEY=value\nOTHER="quoted value"'
    Output: {"KEY": "value", "OTHER": "quoted value"}
    
    Input: content='# comment\nKEY=value  # inline comment'
    Output: {"KEY": "value"}
    
    Input: content='MULTI=line 1\\\nline 2'
    Output: {"MULTI": "line 1line 2"}
    """

def load_env_file(path: str = ".env") -> Dict[str, str]:
    """
    Load .env file and return key-values.
    
    Input: path=".env", file contains "VTIC_TICKETS_DIR=/data/tickets"
    Output: {"VTIC_TICKETS_DIR": "/data/tickets"}
    
    Input: path=".env.nonexistent"
    Output: {}  # no error, return empty
    
    Note: Does NOT set os.environ, just returns dict
    """

def apply_env_file(path: str = ".env", override: bool = False) -> None:
    """
    Load .env and apply to os.environ.
    
    Input: path=".env", file has "NEW_VAR=value", override=False
    Action: os.environ["NEW_VAR"] = "value" only if not already set
    
    Input: path=".env", file has "EXISTING=new", override=True
    Action: os.environ["EXISTING"] = "new" (overwrites)
    
    Input: path=".env", file has "EXISTING=new", override=False
    Action: (no change to os.environ["EXISTING"])
    """

def expand_variables(value: str, env: Dict[str, str]) -> str:
    """
    Expand ${VAR} and $VAR references in value.
    
    Input: value="${HOME}/tickets", env={"HOME": "/home/user"}
    Output: "/home/user/tickets"
    
    Input: value="$HOME/${USER}", env={"HOME": "/home", "USER": "alice"}
    Output: "/home/alice"
    
    Input: value="${UNDEFINED}", env={}
    Output: ""  # undefined vars expand to empty
    """

def strip_quotes(value: str) -> str:
    """
    Remove surrounding quotes from value.
    
    Input: value='"double quoted"'
    Output: "double quoted"
    
    Input: value="'single quoted'"
    Output: "single quoted"
    
    Input: value="no quotes"
    Output: "no quotes"
    
    Input: value='"mismatched\'"
    Output: '"mismatched\''  # no stripping if mismatched
    """
```

### L6: Test
```python
test_find_env_file_current_directory()
test_find_env_file_parent_directory()
test_find_env_file_not_found_returns_none()
test_parse_env_content_simple_key_value()
test_parse_env_content_quoted_values()
test_parse_env_content_single_quoted()
test_parse_env_content_comments_ignored()
test_parse_env_content_inline_comments()
test_parse_env_content_multiline_backslash()
test_parse_env_content_empty_lines_ignored()
test_load_env_file_returns_dict()
test_load_env_file_missing_returns_empty()
test_apply_env_file_sets_new_vars()
test_apply_env_file_no_override_by_default()
test_apply_env_file_override_when_true()
test_expand_variables_dollar_brace()
test_expand_variables_dollar_only()
test_expand_variables_undefined_empty()
test_strip_quotes_double()
test_strip_quotes_single()
test_strip_quotes_none()
```

---

## Feature 8: Dimension Config OpenAI

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
from typing import Optional

# Model dimension specifications
MODEL_DIMENSIONS = {
    "text-embedding-3-small": {
        "default": 1536,
        "supported": [512, 1536],
    },
    "text-embedding-3-large": {
        "default": 3072,
        "supported": [256, 1024, 3072],
    },
    "text-embedding-ada-002": {
        "default": 1536,
        "supported": [1536],  # fixed dimension
    },
}

@dataclass
class OpenAIEmbeddingConfig:
    api_key: str
    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None  # None = use model default
    batch_size: int = 100

def validate_dimensions(model: str, dimensions: Optional[int]) -> Tuple[bool, Optional[str]]:
    """
    Validate dimensions for model.
    
    Input: model="text-embedding-3-small", dimensions=512
    Output: (True, None)
    
    Input: model="text-embedding-3-small", dimensions=1024
    Output: (False, "text-embedding-3-small supports dimensions [512, 1536], got 1024")
    
    Input: model="text-embedding-ada-002", dimensions=1536
    Output: (True, None)
    
    Input: model="text-embedding-ada-002", dimensions=512
    Output: (False, "text-embedding-ada-002 supports dimensions [1536], got 512")
    
    Input: model="unknown-model", dimensions=128
    Output: (True, None)  # unknown model, allow any dimensions
    """

def configure_openai_dimensions(config: OpenAIEmbeddingConfig) -> int:
    """
    Get effective dimensions for config.
    
    Input: config.dimensions=512, config.model="text-embedding-3-small"
    Output: 512
    
    Input: config.dimensions=None, config.model="text-embedding-3-large"
    Output: 3072  # model default
    
    Input: config.dimensions=1024, config.model="text-embedding-3-large"
    Output: 1024
    
    Error: ValueError if dimensions invalid for model
    """

def create_openai_embedding_request(texts: List[str], config: OpenAIEmbeddingConfig) -> Dict:
    """
    Build OpenAI API request body.
    
    Input: texts=["hello"], config.model="text-embedding-3-small", config.dimensions=512
    Output: {
        "input": ["hello"],
        "model": "text-embedding-3-small",
        "dimensions": 512,
    }
    
    Input: texts=["hello"], config.model="text-embedding-ada-002", config.dimensions=None
    Output: {
        "input": ["hello"],
        "model": "text-embedding-ada-002",
        # no dimensions param (ada-002 doesn't support it)
    }
    """

def get_embedding_dimension(config: OpenAIEmbeddingConfig) -> int:
    """
    Get dimension for index initialization.
    
    Input: config with dimensions=512
    Output: 512
    
    Used by Zvec index to configure vector dimension.
    """
```

### L6: Test
```python
test_validate_dimensions_small_model_valid()
test_validate_dimensions_small_model_invalid()
test_validate_dimensions_large_model_valid()
test_validate_dimensions_large_model_invalid()
test_validate_dimensions_ada002_only_1536()
test_validate_dimensions_unknown_model_allows_any()
test_configure_openai_dimensions_explicit()
test_configure_openai_dimensions_default()
test_configure_openai_dimensions_invalid_raises()
test_create_openai_embedding_request_includes_dimensions()
test_create_openai_embedding_request_ada002_no_dimensions()
test_get_embedding_dimension_returns_configured()
test_model_dimensions_constants_complete()
```

---

## Feature 9: Batch Embedding

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
import time
from typing import List, Tuple

@dataclass
class BatchEmbedResult:
    embeddings: List[List[float]]
    total_tokens: int
    batch_count: int
    errors: List[str]

DEFAULT_BATCH_SIZE = 100
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0  # seconds

def split_into_batches(texts: List[str], batch_size: int) -> List[List[str]]:
    """
    Split texts into batches.
    
    Input: texts=["a", "b", "c", "d"], batch_size=2
    Output: [["a", "b"], ["c", "d"]]
    
    Input: texts=["a", "b", "c"], batch_size=5
    Output: [["a", "b", "c"]]
    
    Input: texts=[], batch_size=100
    Output: []
    """

def embed_batch(batch: List[str], config: OpenAIEmbeddingConfig) -> Tuple[List[List[float]], int]:
    """
    Embed single batch via OpenAI API.
    
    Input: batch=["hello", "world"], config with valid api_key
    Output: ([[0.1, 0.2, ...], [0.3, 0.4, ...]], 15)  # embeddings, token count
    
    Error: OpenAIError on API failure
    """

def batch_embed_texts(texts: List[str], config: OpenAIEmbeddingConfig) -> BatchEmbedResult:
    """
    Embed all texts with batching.
    
    Input: texts=["a", "b", "c", "d", "e"], config.batch_size=2
    Action: Call API 3 times with batches [["a","b"], ["c","d"], ["e"]]
    Output: BatchEmbedResult(
        embeddings=[[...], [...], [...], [...], [...]],
        total_tokens=45,
        batch_count=3,
        errors=[]
    )
    
    Input: texts=[], config
    Output: BatchEmbedResult(embeddings=[], total_tokens=0, batch_count=0, errors=[])
    """

def embed_with_retry(batch: List[str], config: OpenAIEmbeddingConfig, max_retries: int = MAX_RETRIES) -> Tuple[List[List[float]], int]:
    """
    Embed with exponential backoff on rate limit.
    
    Input: batch=[...], config, API returns 429 rate limit
    Action: Wait 1s, retry, wait 2s, retry, wait 4s, retry
    Output: (embeddings, tokens) or raise after max_retries
    
    Error: OpenAIRateLimitError after max_retries exceeded
    """

def estimate_tokens(texts: List[str]) -> int:
    """
    Estimate token count for texts (rough: 4 chars per token).
    
    Input: texts=["hello world", "test"]
    Output: 4  # (11 + 4) / 4 ≈ 4
    
    Note: Use tiktoken for accurate count if available
    """

def batch_embed_with_progress(texts: List[str], config: OpenAIEmbeddingConfig, 
                               progress_callback: Callable[[int, int], None]) -> BatchEmbedResult:
    """
    Embed with progress callback.
    
    Input: progress_callback=lambda done, total: print(f"{done}/{total}")
    Output: BatchEmbedResult(...)
    Side effect: Calls progress_callback(0, 5), progress_callback(2, 5), etc.
    """
```

### L6: Test
```python
test_split_into_batches_even_split()
test_split_into_batches_uneven_split()
test_split_into_batches_empty_list()
test_split_into_batches_single_batch()
test_embed_batch_returns_embeddings_and_tokens()
test_batch_embed_texts_single_batch()
test_batch_embed_texts_multiple_batches()
test_batch_embed_texts_empty_returns_empty()
test_batch_embed_texts_maintains_order()
test_batch_embed_texts_total_tokens_accumulated()
test_embed_with_retry_success_no_retry()
test_embed_with_retry_retries_on_rate_limit()
test_embed_with_retry_fails_after_max_retries()
test_estimate_tokens_approximation()
test_batch_embed_with_progress_calls_callback()
```

---

## Feature 10: Model Download

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
import os
from pathlib import Path
from typing import Optional

DEFAULT_MODEL = "all-MiniLM-L6-v2"
DEFAULT_CACHE_DIR = "~/.cache/vtic/models"

# Recommended models with their specs
RECOMMENDED_MODELS = {
    "all-MiniLM-L6-v2": {
        "dimensions": 384,
        "description": "Fast, good quality, 384 dimensions",
        "size_mb": 80,
    },
    "all-mpnet-base-v2": {
        "dimensions": 768,
        "description": "Higher quality, slower, 768 dimensions",
        "size_mb": 420,
    },
    "multi-qa-MiniLM-L6-cos-v1": {
        "dimensions": 384,
        "description": "Optimized for semantic search",
        "size_mb": 80,
    },
}

@dataclass
class LocalEmbeddingConfig:
    model: str = DEFAULT_MODEL
    cache_dir: str = DEFAULT_CACHE_DIR
    device: str = "cpu"  # "cpu", "cuda", "mps"
    offline: bool = False

def get_model_cache_path(model_name: str, cache_dir: str) -> Path:
    """
    Get cache path for model.
    
    Input: model_name="all-MiniLM-L6-v2", cache_dir="~/.cache/vtic/models"
    Output: Path("/home/user/.cache/vtic/models/all-MiniLM-L6-v2")
    """

def is_model_cached(model_name: str, cache_dir: str) -> bool:
    """
    Check if model is already cached.
    
    Input: model_name="all-MiniLM-L6-v2", cache_dir exists with model
    Output: True
    
    Input: model_name="unknown-model", cache_dir
    Output: False
    """

def download_model(model_name: str, cache_dir: str, offline: bool = False) -> str:
    """
    Download model from HuggingFace Hub.
    
    Input: model_name="all-MiniLM-L6-v2", cache_dir="~/.cache/vtic/models", offline=False
    Action: Download model to cache_dir
            Show progress: "Downloading all-MiniLM-L6-v2 (80MB)..."
    Output: "/home/user/.cache/vtic/models/all-MiniLM-L6-v2"
    
    Input: model_name="all-MiniLM-L6-v2", offline=True, not cached
    Error: ModelNotCachedError("Model all-MiniLM-L6-v2 not cached and offline mode enabled")
    
    Input: model_name="invalid-model-xyz", offline=False
    Error: ModelNotFoundError("Model invalid-model-xyz not found on HuggingFace Hub")
    """

def ensure_model_available(config: LocalEmbeddingConfig) -> str:
    """
    Ensure model is available (cached or downloaded).
    
    Input: config with model="all-MiniLM-L6-v2", cached=True
    Output: path to cached model (no download)
    
    Input: config with model="all-MiniLM-L6-v2", cached=False, offline=False
    Action: Download model
    Output: path to downloaded model
    """

def list_cached_models(cache_dir: str) -> List[str]:
    """
    List all cached models.
    
    Input: cache_dir with models "all-MiniLM-L6-v2", "all-mpnet-base-v2"
    Output: ["all-MiniLM-L6-v2", "all-mpnet-base-v2"]
    """

def clear_model_cache(cache_dir: str, model_name: Optional[str] = None) -> int:
    """
    Clear model cache.
    
    Input: cache_dir, model_name="all-MiniLM-L6-v2"
    Action: Remove ~/.cache/vtic/models/all-MiniLM-L6-v2
    Output: 1  # number of models removed
    
    Input: cache_dir, model_name=None
    Action: Remove all models in cache
    Output: 2  # total models removed
    """
```

### L6: Test
```python
test_get_model_cache_path_expands_home()
test_is_model_cached_true_when_exists()
test_is_model_cached_false_when_missing()
test_download_model_creates_cache_dir()
test_download_model_returns_path()
test_download_model_offline_not_cached_raises()
test_download_model_invalid_raises()
test_ensure_model_available_returns_cached()
test_ensure_model_available_downloads_if_missing()
test_list_cached_models_returns_names()
test_clear_model_cache_removes_specific()
test_clear_model_cache_removes_all()
test_recommended_models_have_valid_specs()
```

---

## Feature 11: Model Caching

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
import hashlib
import json
import numpy as np
from pathlib import Path
from typing import Optional, List

EMBEDDING_CACHE_DIR = "~/.cache/vtic/embeddings"
CACHE_VERSION = 1  # Increment if cache format changes

def compute_text_hash(text: str) -> str:
    """
    Compute SHA256 hash of text (first 16 chars).
    
    Input: text="Hello, world!"
    Output: "315f5bdb76d078"  # truncated SHA256
    
    Note: Truncated for shorter filenames
    """

def get_embedding_cache_path(text_hash: str, model_name: str, cache_dir: str) -> Path:
    """
    Get cache file path for embedding.
    
    Input: text_hash="315f5bdb76d078", model_name="all-MiniLM-L6-v2", 
           cache_dir="~/.cache/vtic/embeddings"
    Output: Path("~/.cache/vtic/embeddings/all-MiniLM-L6-v2/315f5bdb76d078.npy")
    """

def compute_cache_key(text: str, model_name: str, dimensions: int) -> str:
    """
    Compute cache key including model and dimension info.
    
    Input: text="Hello", model_name="all-MiniLM-L6-v2", dimensions=384
    Output: "315f5bdb76d078_v1_all-MiniLM-L6-v2_384"
    
    Note: Includes version, model name, and dimensions for invalidation
    """

def cache_embedding(cache_key: str, embedding: List[float], cache_dir: str) -> None:
    """
    Store embedding in cache.
    
    Input: cache_key="abc123_v1_model_384", embedding=[0.1, 0.2, ...], 
           cache_dir="~/.cache/vtic/embeddings"
    Action: Write numpy array to cache_dir/model/abc123_v1_model_384.npy
    """

def get_cached_embedding(cache_key: str, cache_dir: str) -> Optional[List[float]]:
    """
    Retrieve embedding from cache.
    
    Input: cache_key="abc123_v1_model_384", cache exists
    Output: [0.1, 0.2, ...]
    
    Input: cache_key="xyz789_v1_model_384", cache missing
    Output: None
    """

def embed_with_cache(text: str, model: SentenceTransformer, config: LocalEmbeddingConfig) -> List[float]:
    """
    Embed text with caching.
    
    Input: text="Hello", model, config
    Action: 
      1. Compute cache key
      2. Check cache
      3. If cached, return cached embedding
      4. If not cached, compute embedding, cache it, return it
    Output: [0.1, 0.2, ...]
    """

def batch_embed_with_cache(texts: List[str], model: SentenceTransformer, 
                           config: LocalEmbeddingConfig) -> List[List[float]]:
    """
    Batch embed with caching.
    
    Input: texts=["Hello", "World"], model, config
    Action:
      1. Check cache for each text
      2. Embed only uncached texts
      3. Cache new embeddings
      4. Return all embeddings in order
    Output: [[0.1, ...], [0.2, ...]]
    """

def clear_embedding_cache(cache_dir: str, model_name: Optional[str] = None) -> int:
    """
    Clear embedding cache.
    
    Input: cache_dir, model_name="all-MiniLM-L6-v2"
    Action: Remove ~/.cache/vtic/embeddings/all-MiniLM-L6-v2/
    Output: 150  # number of cache files removed
    
    Input: cache_dir, model_name=None
    Action: Remove all embedding caches
    Output: 500  # total files removed
    """

def get_cache_stats(cache_dir: str) -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Input: cache_dir with cached embeddings
    Output: {
        "total_files": 500,
        "total_size_mb": 25.5,
        "models": {
            "all-MiniLM-L6-v2": {"files": 300, "size_mb": 15.0},
            "all-mpnet-base-v2": {"files": 200, "size_mb": 10.5},
        }
    }
    """
```

### L6: Test
```python
test_compute_text_hash_consistent()
test_compute_text_hash_different_for_different_text()
test_get_embedding_cache_path_includes_model()
test_compute_cache_key_includes_version_model_dimensions()
test_cache_embedding_creates_file()
test_cache_embedding_stores_correct_values()
test_get_cached_embedding_returns_embedding()
test_get_cached_embedding_missing_returns_none()
test_embed_with_cache_uses_cache()
test_embed_with_cache_stores_new()
test_batch_embed_with_cache_mixed_cached_uncached()
test_batch_embed_with_cache_maintains_order()
test_clear_embedding_cache_removes_files()
test_clear_embedding_cache_by_model()
test_get_cache_stats_returns_counts()
test_cache_version_invalidation()
```

---

## Feature 12: HTTP Endpoint Custom Provider

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
import requests
from typing import Dict, Any, Optional, List
import json

@dataclass
class CustomEmbeddingConfig:
    endpoint: str  # e.g., "https://api.custom.com/v1/embeddings"
    model: str = "custom"
    auth_header: str = "Authorization"  # header name for auth
    auth_token: Optional[str] = None  # token value
    request_template: Optional[str] = None  # JSON template for request
    response_path: str = "data.{i}.embedding"  # path to embedding in response
    dimensions: int = 1536
    timeout: int = 30  # seconds
    batch_size: int = 100

# Default request template (JSON string with placeholders)
DEFAULT_REQUEST_TEMPLATE = '{"input": {{texts}}, "model": "{{model}}"}'

def build_request_body(texts: List[str], config: CustomEmbeddingConfig) -> Dict[str, Any]:
    """
    Build request body from template.
    
    Input: texts=["hello", "world"], config.model="custom", 
           config.request_template=None (use default)
    Output: {"input": ["hello", "world"], "model": "custom"}
    
    Input: texts=["hello"], config.request_template='{"texts": {{texts}}, "dim": {{dimensions}}}'
    Output: {"texts": ["hello"], "dim": 1536}
    
    Note: Template placeholders:
      - {{texts}}: JSON array of texts
      - {{model}}: model name
      - {{dimensions}}: embedding dimensions
    """

def build_headers(config: CustomEmbeddingConfig) -> Dict[str, str]:
    """
    Build HTTP headers for request.
    
    Input: config.auth_header="Authorization", config.auth_token="Bearer abc123"
    Output: {
        "Content-Type": "application/json",
        "Authorization": "Bearer abc123"
    }
    
    Input: config.auth_token=None
    Output: {"Content-Type": "application/json"}
    """

def extract_embeddings(response: Dict[str, Any], config: CustomEmbeddingConfig) -> List[List[float]]:
    """
    Extract embeddings from response.
    
    Input: response={"data": [{"embedding": [0.1, 0.2]}, {"embedding": [0.3, 0.4]}]},
           config.response_path="data.{i}.embedding"
    Output: [[0.1, 0.2], [0.3, 0.4]]
    
    Input: response={"embeddings": [[0.1, 0.2], [0.3, 0.4]]},
           config.response_path="embeddings"
    Output: [[0.1, 0.2], [0.3, 0.4]]
    
    Input: response={"results": [{"vector": [...]}]},
           config.response_path="results.{i}.vector"
    Output: [[...]]
    """

def embed_via_http(texts: List[str], config: CustomEmbeddingConfig) -> List[List[float]]:
    """
    Embed texts via custom HTTP endpoint.
    
    Input: texts=["hello", "world"], config with valid endpoint
    Action:
      1. Build request body
      2. Build headers
      3. POST to endpoint
      4. Parse response
      5. Extract embeddings
    Output: [[0.1, 0.2, ...], [0.3, 0.4, ...]]
    
    Error: CustomProviderError on HTTP error
    Error: CustomProviderError on response parse error
    """

def validate_custom_config(config: CustomEmbeddingConfig) -> Tuple[bool, Optional[str]]:
    """
    Validate custom provider config.
    
    Input: config.endpoint="https://api.example.com/embeddings"
    Output: (True, None)
    
    Input: config.endpoint=""
    Output: (False, "endpoint is required")
    
    Input: config.endpoint="not-a-url"
    Output: (False, "endpoint must be a valid URL")
    """

def test_custom_endpoint(config: CustomEmbeddingConfig) -> Tuple[bool, str]:
    """
    Test custom endpoint connectivity.
    
    Input: config with valid endpoint and auth
    Action: Send single test embedding request
    Output: (True, "Successfully connected, embedding dimension: 1536")
    
    Input: config with invalid endpoint
    Output: (False, "Connection failed: Connection refused")
    """
```

### L6: Test
```python
test_build_request_body_default_template()
test_build_request_body_custom_template()
test_build_request_body_escapes_json()
test_build_headers_with_auth()
test_build_headers_without_auth()
test_extract_embeddings_default_path()
test_extract_embeddings_custom_path()
test_extract_embeddings_simple_array()
test_embed_via_http_success()
test_embed_via_http_auth_error()
test_embed_via_http_timeout()
test_embed_via_http_invalid_response()
test_validate_custom_config_valid()
test_validate_custom_config_missing_endpoint()
test_validate_custom_config_invalid_url()
test_test_custom_endpoint_success()
test_test_custom_endpoint_failure()
test_custom_provider_batching()
```

---

## Feature 13: Custom Auth

### L1: Embedding Providers
### L2: Custom Provider
### L3: Custom auth
### L4: `configure_custom_auth(config: CustomEmbeddingConfig) -> Dict[str, str]`
  - Support flexible authentication for custom embedding providers
  - Auth types: `bearer` (default), `header`, `api_key`, `basic`
  - Configure via `embedding.custom.auth_type` and `embedding.custom.auth_value`
  - Bearer: `Authorization: Bearer <token>`
  - Header: Custom header name and value
  - API Key: `X-API-Key: <key>` or in query params
  - Basic: `Authorization: Basic base64(user:pass)`
  - Read auth token from environment variable: `VTIC_CUSTOM_AUTH_TOKEN`
  - Support dynamic header generation with interpolation

### L5: Spec
```python
import base64
import os
from typing import Dict, Optional, Literal
from urllib.parse import urlencode

AuthType = Literal["bearer", "header", "api_key", "basic", "query"]

@dataclass
class CustomAuthConfig:
    auth_type: AuthType = "bearer"
    auth_header: str = "Authorization"  # for header type
    auth_value: Optional[str] = None  # token, key, or "user:pass"
    auth_env_var: Optional[str] = None  # env var name to read from
    # Convenience fields for common patterns
    api_key_header: str = "X-API-Key"  # for api_key type
    api_key_query_param: str = "api_key"  # for query type

def resolve_auth_value(config: CustomAuthConfig) -> Optional[str]:
    """
    Resolve auth value from config or env var.
    
    Input: config.auth_value="token123", config.auth_env_var=None
    Output: "token123"
    
    Input: config.auth_value=None, config.auth_env_var="MY_API_KEY", 
           os.environ["MY_API_KEY"]="envtoken"
    Output: "envtoken"
    
    Input: config.auth_value=None, config.auth_env_var=None
    Output: None
    """

def build_bearer_auth(token: str) -> Dict[str, str]:
    """
    Build Bearer auth headers.
    
    Input: token="abc123"
    Output: {"Authorization": "Bearer abc123"}
    """

def build_header_auth(header_name: str, header_value: str) -> Dict[str, str]:
    """
    Build custom header auth.
    
    Input: header_name="X-Custom-Auth", header_value="secret123"
    Output: {"X-Custom-Auth": "secret123"}
    """

def build_api_key_auth(api_key: str, header_name: str = "X-API-Key") -> Dict[str, str]:
    """
    Build API key auth headers.
    
    Input: api_key="key123", header_name="X-API-Key"
    Output: {"X-API-Key": "key123"}
    """

def build_basic_auth(username: str, password: str) -> Dict[str, str]:
    """
    Build Basic auth headers.
    
    Input: username="user", password="pass"
    Action: base64("user:pass") = "dXNlcjpwYXNz"
    Output: {"Authorization": "Basic dXNlcjpwYXNz"}
    """

def build_query_auth(endpoint: str, api_key: str, param_name: str = "api_key") -> str:
    """
    Add API key to endpoint URL as query param.
    
    Input: endpoint="https://api.example.com/embeddings", 
           api_key="key123", param_name="api_key"
    Output: "https://api.example.com/embeddings?api_key=key123"
    
    Input: endpoint="https://api.example.com/embeddings?model=x",
           api_key="key123", param_name="key"
    Output: "https://api.example.com/embeddings?model=x&key=key123"
    """

def configure_custom_auth(config: CustomAuthConfig) -> Dict[str, str]:
    """
    Build auth headers based on auth type.
    
    Input: config.auth_type="bearer", resolved token="abc123"
    Output: {"Authorization": "Bearer abc123"}
    
    Input: config.auth_type="api_key", api_key="xyz", api_key_header="X-API-Key"
    Output: {"X-API-Key": "xyz"}
    
    Input: config.auth_type="basic", auth_value="user:pass"
    Output: {"Authorization": "Basic dXNlcjpwYXNz"}
    
    Input: config.auth_type="header", auth_header="X-Token", auth_value="secret"
    Output: {"X-Token": "secret"}
    
    Input: config.auth_type="query" (handled separately in URL building)
    Output: {}  # auth added to URL, not headers
    """

def apply_auth_to_request(endpoint: str, body: Dict, headers: Dict, 
                          config: CustomAuthConfig) -> Tuple[str, Dict, Dict]:
    """
    Apply authentication to HTTP request components.
    
    Input: endpoint="https://api.example.com/embed", config.auth_type="query"
    Output: ("https://api.example.com/embed?api_key=xyz", body, headers)
    
    Input: endpoint="https://api.example.com/embed", config.auth_type="bearer"
    Output: (endpoint, body, headers with Authorization)
    """

def validate_auth_config(config: CustomAuthConfig) -> Tuple[bool, Optional[str]]:
    """
    Validate auth configuration.
    
    Input: config.auth_type="bearer", auth_value="token"
    Output: (True, None)
    
    Input: config.auth_type="basic", auth_value="user:pass"
    Output: (True, None)
    
    Input: config.auth_type="basic", auth_value="invalid-no-colon"
    Output: (False, "Basic auth value must be in format 'username:password'")
    
    Input: config.auth_type="bearer", auth_value=None, auth_env_var=None
    Output: (False, "Auth value or auth_env_var required for bearer auth")
    """
```

### L6: Test
```python
test_resolve_auth_value_direct()
test_resolve_auth_value_from_env()
test_resolve_auth_value_none()
test_build_bearer_auth()
test_build_header_auth()
test_build_api_key_auth_default_header()
test_build_api_key_auth_custom_header()
test_build_basic_auth()
test_build_query_auth_no_existing_params()
test_build_query_auth_with_existing_params()
test_configure_custom_auth_bearer()
test_configure_custom_auth_header()
test_configure_custom_auth_api_key()
test_configure_custom_auth_basic()
test_configure_custom_auth_query()
test_apply_auth_to_request_query_type()
test_apply_auth_to_request_header_type()
test_validate_auth_config_bearer_valid()
test_validate_auth_config_basic_valid()
test_validate_auth_config_basic_invalid_format()
test_validate_auth_config_missing_value()
```

---

## Summary

| # | L1 | L2 | L3 | L4 Function |
|---|----|----|----|----|
| 1 | CLI | Output Formats | Quiet mode | `configure_quiet_mode()` |
| 2 | CLI | Output Formats | Verbose mode | `configure_verbose_mode()` |
| 3 | CLI | Output Formats | Color control | `configure_color_output()` |
| 4 | CLI | Shell Integration | Tab completion | `generate_completion_script()` |
| 5 | CLI | Shell Integration | Completion install | `cli_completion_install()` |
| 6 | Configuration | Environment Variables | Standard env names | `parse_env_config()` |
| 7 | Configuration | Environment Variables | Env file support | `load_env_file()` |
| 8 | Embedding Providers | OpenAI Provider | Dimension config | `configure_openai_dimensions()` |
| 9 | Embedding Providers | OpenAI Provider | Batch embedding | `batch_embed_texts()` |
| 10 | Embedding Providers | Local Provider | Model download | `download_model()` |
| 11 | Embedding Providers | Local Provider | Model caching | `cache_embedding()` |
| 12 | Embedding Providers | Custom Provider | HTTP endpoint | `embed_via_http()` |
| 13 | Embedding Providers | Custom Provider | Custom auth | `configure_custom_auth()` |

---

## Data Structures Reference

```python
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple, Literal, Callable
from datetime import datetime

# CLI Output Config
@dataclass
class OutputConfig:
    quiet: bool = False
    verbose: bool = False
    color: str = "auto"  # "auto", "always", "never"
    format: str = "table"

# Color Config
@dataclass
class ColorConfig:
    enabled: bool
    mode: Literal["auto", "always", "never"]

# Completion Config
@dataclass
class CompletionInstallArgs:
    shell: Optional[str] = None
    output: Optional[str] = None
    dry_run: bool = False

# OpenAI Embedding Config
@dataclass
class OpenAIEmbeddingConfig:
    api_key: str
    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None
    batch_size: int = 100

# Batch Embed Result
@dataclass
class BatchEmbedResult:
    embeddings: List[List[float]]
    total_tokens: int
    batch_count: int
    errors: List[str]

# Local Embedding Config
@dataclass
class LocalEmbeddingConfig:
    model: str = "all-MiniLM-L6-v2"
    cache_dir: str = "~/.cache/vtic/models"
    device: str = "cpu"
    offline: bool = False

# Custom Embedding Config
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

# Custom Auth Config
@dataclass
class CustomAuthConfig:
    auth_type: Literal["bearer", "header", "api_key", "basic", "query"] = "bearer"
    auth_header: str = "Authorization"
    auth_value: Optional[str] = None
    auth_env_var: Optional[str] = None
    api_key_header: str = "X-API-Key"
    api_key_query_param: str = "api_key"
```
