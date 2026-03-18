# Stage 5: Configuration System Data Models

This document defines the complete configuration system for vtic, including Pydantic models, loading logic, and validation rules.

---

## 1. Config Model

### 1.1 Pydantic Model Definition

```python
"""Configuration models for vtic.

This module defines all configuration structures using Pydantic v2,
providing validation, serialization, and environment variable integration.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TicketsConfig(BaseModel):
    """Configuration for ticket storage.
    
    Attributes:
        dir: Directory path where tickets are stored.
            Relative paths are resolved from the project root.
            Defaults to "./tickets".
    """
    
    dir: Path = Field(
        default=Path("./tickets"),
        description="Directory path for ticket storage"
    )
    
    @field_validator("dir", mode="before")
    @classmethod
    def _validate_dir(cls, v: str | Path) -> Path:
        """Convert string to Path object."""
        return Path(v) if isinstance(v, str) else v


class ApiConfig(BaseModel):
    """Configuration for the API server.
    
    Attributes:
        host: Host address to bind the server to.
            Defaults to "127.0.0.1" for security (localhost only).
        port: Port number for the server.
            Must be in range 1-65535.
            Defaults to 8900.
    """
    
    host: str = Field(
        default="127.0.0.1",
        description="API server host address"
    )
    port: int = Field(
        default=8900,
        ge=1,
        le=65535,
        description="API server port (1-65535)"
    )
    
    @field_validator("port")
    @classmethod
    def _validate_port_range(cls, v: int) -> int:
        """Ensure port is within valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {v}")
        return v


class SearchConfig(BaseModel):
    """Configuration for search functionality.
    
    Attributes:
        bm25_enabled: Whether BM25 keyword search is enabled.
            Always enabled by default (zero config).
        enable_semantic: Whether semantic (dense embedding) search is enabled.
            Requires an embedding provider when enabled.
        embedding_provider: Provider for embeddings.
            Options: "openai" (OpenAI API), "local" (sentence-transformers),
            "none" (no embeddings, BM25 only).
        embedding_model: Model name for embeddings.
            Provider-specific model identifier.
        embedding_dimensions: Vector dimensions for embeddings.
            Must match the model's output dimensions.
        hybrid_weights_bm25: Weight for BM25 scores in hybrid ranking.
            Range 0.0-1.0. Default 0.7.
        hybrid_weights_semantic: Weight for semantic scores in hybrid ranking.
            Range 0.0-1.0. Default 0.3.
            Weights should sum to 1.0 for normalized hybrid scoring.
    """
    
    bm25_enabled: bool = Field(
        default=True,
        description="Enable BM25 keyword search"
    )
    enable_semantic: bool = Field(
        default=False,
        description="Enable semantic/dense embedding search"
    )
    embedding_provider: Literal["openai", "local", "none"] = Field(
        default="openai",
        description="Embedding provider: openai | local | none"
    )
    embedding_model: str = Field(
        default="text-embedding-3-small",
        description="Embedding model name"
    )
    embedding_dimensions: int = Field(
        default=1536,
        gt=0,
        description="Embedding vector dimensions"
    )
    hybrid_weights_bm25: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="BM25 weight in hybrid scoring (0.0-1.0)"
    )
    hybrid_weights_semantic: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Semantic weight in hybrid scoring (0.0-1.0)"
    )
    
    @field_validator("embedding_dimensions")
    @classmethod
    def _validate_positive_dimensions(cls, v: int) -> int:
        """Ensure dimensions are positive."""
        if v <= 0:
            raise ValueError(f"Embedding dimensions must be positive, got {v}")
        return v
    
    @field_validator("hybrid_weights_bm25", "hybrid_weights_semantic")
    @classmethod
    def _validate_weight_range(cls, v: float) -> float:
        """Ensure weights are within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v
    
    @model_validator(mode="after")
    def _validate_provider_consistency(self) -> SearchConfig:
        """Validate provider matches enable_semantic flag."""
        if not self.enable_semantic:
            # When semantic is disabled, provider should be "none" or ignored
            return self
        
        if self.enable_semantic and self.embedding_provider == "none":
            raise ValueError(
                "embedding_provider cannot be 'none' when enable_semantic is true. "
                "Use 'openai' or 'local' instead."
            )
        
        return self
    
    @model_validator(mode="after")
    def _check_weights_sum(self) -> SearchConfig:
        """Warn if weights don't sum to approximately 1.0."""
        total = self.hybrid_weights_bm25 + self.hybrid_weights_semantic
        if not 0.99 <= total <= 1.01:  # Allow small floating point variance
            warnings.warn(
                f"Hybrid weights sum to {total}, expected ~1.0. "
                f"BM25: {self.hybrid_weights_bm25}, Semantic: {self.hybrid_weights_semantic}",
                UserWarning,
                stacklevel=2
            )
        return self


class Config(BaseModel):
    """Root configuration for vtic.
    
    This is the top-level configuration object that aggregates
    all sub-configurations: tickets, api, and search.
    
    Attributes:
        tickets: Ticket storage configuration.
        api: API server configuration.
        search: Search and embedding configuration.
    
    Example:
        >>> config = Config()
        >>> config.tickets.dir
        PosixPath('tickets')
        >>> config.api.port
        8900
    """
    
    tickets: TicketsConfig = Field(
        default_factory=TicketsConfig,
        description="Ticket storage configuration"
    )
    api: ApiConfig = Field(
        default_factory=ApiConfig,
        description="API server configuration"
    )
    search: SearchConfig = Field(
        default_factory=SearchConfig,
        description="Search configuration"
    )
    
    model_config = {
        "validate_assignment": True,
        "extra": "forbid",  # Prevent unexpected fields
    }


# Embedding model defaults by provider
EMBEDDING_DEFAULTS: dict[str, dict[str, str | int]] = {
    "openai": {
        "model": "text-embedding-3-small",
        "dimensions": 1536,
    },
    "local": {
        "model": "all-MiniLM-L6-v2",
        "dimensions": 384,
    },
}
```

---

## 2. Config Loading Logic

### 2.1 Environment Variable Mapping

```python
"""Environment variable to config field mapping.

Priority order (highest to lowest):
1. Environment variables (VTIC_*)
2. Project-local config (./vtic.toml)
3. User global config (~/.config/vtic/config.toml)
4. Hardcoded defaults (in Pydantic models)
"""

from pathlib import Path

# Environment variable names and their target config paths
# Format: "ENV_VAR_NAME": ("section", "field")
ENV_VAR_MAP: dict[str, tuple[str, str]] = {
    # Tickets section
    "VTIC_TICKETS_DIR": ("tickets", "dir"),
    
    # API section
    "VTIC_API_HOST": ("api", "host"),
    "VTIC_API_PORT": ("api", "port"),
    
    # Search section
    "VTIC_SEARCH_ENABLE_SEMANTIC": ("search", "enable_semantic"),
    "VTIC_SEARCH_EMBEDDING_PROVIDER": ("search", "embedding_provider"),
    "VTIC_SEARCH_EMBEDDING_MODEL": ("search", "embedding_model"),
    "VTIC_SEARCH_EMBEDDING_DIMENSIONS": ("search", "embedding_dimensions"),
    "VTIC_SEARCH_BM25_ENABLED": ("search", "bm25_enabled"),
    "VTIC_SEARCH_HYBRID_BM25_WEIGHT": ("search", "hybrid_weights_bm25"),
    "VTIC_SEARCH_HYBRID_SEMANTIC_WEIGHT": ("search", "hybrid_weights_semantic"),
    
    # API keys (not part of Config model, but used for validation)
    "OPENAI_API_KEY": ("_api_keys", "openai"),
}

# Config file search paths (in priority order)
CONFIG_SEARCH_PATHS: list[Path] = [
    Path("./vtic.toml"),                      # Project-local
    Path.home() / ".config" / "vtic" / "config.toml",  # User global
]
```

### 2.2 Config Loading Functions

```python
"""Configuration loading utilities.

Provides functions to load configuration from multiple sources
with proper precedence handling.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any

import tomllib  # Python 3.11+ (or tomli for older versions)

from .models import Config, EMBEDDING_DEFAULTS


def _parse_env_value(value: str) -> bool | int | float | str:
    """Parse environment variable string to appropriate type.
    
    Attempts to parse as: bool -> int -> float -> str
    
    Args:
        value: Raw environment variable value.
        
    Returns:
        Parsed value in appropriate type.
    """
    # Boolean parsing
    lowered = value.lower()
    if lowered in ("true", "1", "yes", "on"):
        return True
    if lowered in ("false", "0", "no", "off"):
        return False
    
    # Integer parsing
    try:
        return int(value)
    except ValueError:
        pass
    
    # Float parsing
    try:
        return float(value)
    except ValueError:
        pass
    
    # Return as string
    return value


def _load_env_overrides() -> dict[str, dict[str, Any]]:
    """Load configuration overrides from environment variables.
    
    Reads VTIC_* environment variables and maps them to config
    section/field structure.
    
    Returns:
        Nested dict with structure: {section: {field: value}}
    """
    overrides: dict[str, dict[str, Any]] = {}
    
    for env_var, (section, field) in ENV_VAR_MAP.items():
        if env_var in os.environ:
            value = _parse_env_value(os.environ[env_var])
            
            if section not in overrides:
                overrides[section] = {}
            overrides[section][field] = value
    
    return overrides


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load and parse a TOML configuration file.
    
    Args:
        path: Path to the TOML file.
        
    Returns:
        Parsed TOML content as dict.
        
    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If TOML parsing fails.
    """
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    content = path.read_text(encoding="utf-8")
    
    try:
        return tomllib.loads(content)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"Invalid TOML in {path}: {e}") from e


def _find_and_load_config_file(config_path: Path | None = None) -> dict[str, Any]:
    """Find and load the first available config file.
    
    Search order:
    1. Explicit config_path if provided
    2. ./vtic.toml (project-local)
    3. ~/.config/vtic/config.toml (user global)
    
    Args:
        config_path: Optional explicit path to config file.
        
    Returns:
        Parsed config dict, or empty dict if no file found.
    """
    # If explicit path provided, use it exclusively
    if config_path is not None:
        try:
            return _load_toml_file(config_path)
        except (FileNotFoundError, ValueError) as e:
            raise ValueError(f"Cannot load specified config: {e}") from e
    
    # Search default paths
    for path in CONFIG_SEARCH_PATHS:
        try:
            return _load_toml_file(path)
        except FileNotFoundError:
            continue
    
    # No config file found - return empty (will use defaults)
    return {}


def _apply_provider_defaults(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Apply provider-specific defaults for embedding configuration.
    
    When embedding_provider is set but model/dimensions are not,
    apply the appropriate defaults for that provider.
    
    Args:
        config_dict: Configuration dictionary to modify.
        
    Returns:
        Modified configuration dictionary.
    """
    search = config_dict.get("search", {})
    provider = search.get("embedding_provider")
    
    if provider and provider in EMBEDDING_DEFAULTS:
        defaults = EMBEDDING_DEFAULTS[provider]
        
        # Apply model default if not set
        if "embedding_model" not in search:
            search["embedding_model"] = defaults["model"]
        
        # Apply dimensions default if not set
        if "embedding_dimensions" not in search:
            search["embedding_dimensions"] = defaults["dimensions"]
        
        config_dict["search"] = search
    
    return config_dict


def _merge_configs(
    file_config: dict[str, Any],
    env_config: dict[str, Any]
) -> dict[str, Any]:
    """Merge file and environment configs with env taking precedence.
    
    Args:
        file_config: Config loaded from file.
        env_config: Config loaded from environment variables.
        
    Returns:
        Merged configuration dictionary.
    """
    result = file_config.copy()
    
    for section, fields in env_config.items():
        if section not in result:
            result[section] = {}
        result[section].update(fields)
    
    return result


def load_config(config_path: Path | None = None) -> Config:
    """Load vtic configuration from all sources.
    
    Loads configuration with the following precedence:
    1. Environment variables (highest priority)
    2. Explicit config_path if provided
    3. ./vtic.toml (project-local)
    4. ~/.config/vtic/config.toml (user global)
    5. Hardcoded defaults (lowest priority)
    
    Environment variables:
        VTIC_TICKETS_DIR: Ticket directory path
        VTIC_API_HOST: API server host address
        VTIC_API_PORT: API server port number
        VTIC_SEARCH_ENABLE_SEMANTIC: Enable semantic search (bool)
        VTIC_SEARCH_EMBEDDING_PROVIDER: Embedding provider
        VTIC_SEARCH_EMBEDDING_MODEL: Embedding model name
        VTIC_SEARCH_EMBEDDING_DIMENSIONS: Embedding dimensions
        VTIC_SEARCH_BM25_ENABLED: Enable BM25 (bool)
        VTIC_SEARCH_HYBRID_BM25_WEIGHT: BM25 weight (0.0-1.0)
        VTIC_SEARCH_HYBRID_SEMANTIC_WEIGHT: Semantic weight (0.0-1.0)
        OPENAI_API_KEY: OpenAI API key (for validation)
    
    Args:
        config_path: Optional explicit path to a TOML config file.
            If provided, only this file is loaded (before env vars).
            
    Returns:
        Fully populated and validated Config instance.
        
    Raises:
        ValueError: If configuration is invalid or file cannot be loaded.
    """
    # Load from config file(s)
    file_config = _find_and_load_config_file(config_path)
    
    # Apply provider-specific defaults based on file config
    file_config = _apply_provider_defaults(file_config)
    
    # Load environment overrides
    env_config = _load_env_overrides()
    
    # Merge with env taking precedence
    merged = _merge_configs(file_config, env_config)
    
    # Create and validate Config instance
    try:
        config = Config.model_validate(merged)
    except Exception as e:
        raise ValueError(f"Configuration validation failed: {e}") from e
    
    return config


def get_openai_api_key() -> str | None:
    """Get OpenAI API key from environment.
    
    Returns:
        API key if set, None otherwise.
    """
    return os.environ.get("OPENAI_API_KEY")
```

---

## 3. Config Validation

### 3.1 Post-Load Validation Logic

```python
"""Post-load configuration validation and initialization.

Validates runtime configuration requirements and performs
necessary setup operations like directory creation.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path

from .models import Config, SearchConfig
from .loader import get_openai_api_key


class ConfigValidationError(ValueError):
    """Raised when configuration validation fails critically."""
    pass


def validate_port_range(port: int) -> None:
    """Validate server port is within valid range.
    
    Args:
        port: Port number to validate.
        
    Raises:
        ConfigValidationError: If port is out of valid range (1-65535).
    """
    if not 1 <= port <= 65535:
        raise ConfigValidationError(
            f"Invalid server port: {port}. "
            f"Port must be between 1 and 65535."
        )


def validate_and_create_ticket_dir(dir_path: Path) -> Path:
    """Validate ticket directory and create if needed.
    
    Args:
        dir_path: Path to ticket directory.
        
    Returns:
        Resolved absolute path to ticket directory.
        
    Raises:
        ConfigValidationError: If directory cannot be created or accessed.
    """
    # Resolve to absolute path
    abs_path = dir_path.resolve()
    
    if abs_path.exists():
        # Path exists - verify it's a directory
        if not abs_path.is_dir():
            raise ConfigValidationError(
                f"Ticket path exists but is not a directory: {abs_path}"
            )
    else:
        # Path doesn't exist - create it
        try:
            abs_path.mkdir(parents=True, exist_ok=True)
            warnings.warn(
                f"Created ticket directory: {abs_path}",
                UserWarning,
                stacklevel=2
            )
        except OSError as e:
            raise ConfigValidationError(
                f"Cannot create ticket directory {abs_path}: {e}"
            ) from e
    
    # Verify we have read/write access
    if not os.access(abs_path, os.R_OK | os.W_OK | os.X_OK):
        raise ConfigValidationError(
            f"Insufficient permissions for ticket directory: {abs_path}. "
            f"Need read, write, and execute permissions."
        )
    
    return abs_path


def validate_search_config(search_config: SearchConfig) -> SearchConfig:
    """Validate search configuration and handle semantic search requirements.
    
    Performs the following validations:
    - If enable_semantic is true and provider is "openai", verify API key exists
    - If API key missing, emit warning and disable semantic search
    
    Args:
        search_config: Search configuration to validate.
        
    Returns:
        Potentially modified search configuration.
    """
    if not search_config.enable_semantic:
        # Semantic search disabled - nothing to validate
        return search_config
    
    if search_config.embedding_provider == "openai":
        api_key = get_openai_api_key()
        
        if not api_key:
            warnings.warn(
                "Semantic search is enabled with 'openai' provider, "
                "but OPENAI_API_KEY environment variable is not set. "
                "Semantic search will be disabled. "
                "Set OPENAI_API_KEY or change embedding_provider to 'local' or 'none'.",
                UserWarning,
                stacklevel=2
            )
            # Disable semantic search due to missing API key
            search_config.enable_semantic = False
    
    elif search_config.embedding_provider == "local":
        # Local provider - verify sentence-transformers is available
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            warnings.warn(
                "Semantic search is enabled with 'local' provider, "
                "but 'sentence-transformers' is not installed. "
                "Install with: pip install sentence-transformers "
                "Semantic search will be disabled.",
                UserWarning,
                stacklevel=2
            )
            search_config.enable_semantic = False
    
    return search_config


def validate_and_initialize_config(config: Config) -> Config:
    """Perform full post-load validation and initialization.
    
    This function should be called immediately after load_config()
    to ensure the configuration is valid and runtime requirements are met.
    
    Validation steps:
    1. Validate server port range (raises ValueError if invalid)
    2. Create ticket directory if it doesn't exist
    3. Validate search config (disable semantic if API key missing)
    
    Args:
        config: Loaded configuration to validate.
        
    Returns:
        Validated and potentially modified configuration.
        
    Raises:
        ConfigValidationError: If critical validation fails.
        ValueError: If port is out of range (via validate_port_range).
    """
    # 1. Validate server port
    validate_port_range(config.server.port)
    
    # 2. Validate and create ticket directory
    resolved_dir = validate_and_create_ticket_dir(config.tickets.dir)
    config.tickets.dir = resolved_dir
    
    # 3. Validate search configuration
    config.search = validate_search_config(config.search)
    
    return config


# Convenience function for full load + validate
def load_and_validate_config(config_path: Path | None = None) -> Config:
    """Load configuration and perform full validation.
    
    This is the recommended entry point for loading configuration
    in production code.
    
    Args:
        config_path: Optional explicit path to config file.
        
    Returns:
        Fully loaded, validated, and initialized configuration.
        
    Raises:
        ConfigValidationError: If configuration is invalid.
        ValueError: If port is out of range.
    """
    config = load_config(config_path)
    return validate_and_initialize_config(config)
```

---

## 4. Usage Examples

### 4.1 Basic Usage

```python
from vtic.config import load_config, load_and_validate_config

# Load config with default search paths
config = load_config()

# Or load from explicit path
config = load_config(Path("/path/to/vtic.toml"))

# Full load + validate (recommended)
config = load_and_validate_config()

# Access configuration values
print(config.tickets.dir)           # PosixPath('/absolute/path/to/tickets')
print(config.api.host)              # "127.0.0.1"
print(config.api.port)              # 8900
print(config.search.bm25_enabled)   # True
print(config.search.enable_semantic)  # False (if no API key)
```

### 4.2 Environment Variable Override

```bash
# Override via environment
export VTIC_TICKETS_DIR="/var/vtic/tickets"
export VTIC_API_PORT=8080
export VTIC_SEARCH_ENABLE_SEMANTIC=true
export VTIC_SEARCH_EMBEDDING_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

```python
from vtic.config import load_config

# Environment variables take precedence over config files
config = load_config()
assert config.api.port == 8080
assert config.search.enable_semantic is True
```

### 4.3 Validation Behavior Examples

```python
from vtic.config import load_and_validate_config
from pydantic import ValidationError

# Example 1: Port out of range
import os
os.environ["VTIC_API_PORT"] = "99999"

try:
    config = load_and_validate_config()
except ValueError as e:
    print(e)  # "Invalid server port: 99999. Port must be between 1 and 65535."

# Example 2: Missing API key with semantic enabled
os.environ["VTIC_SEARCH_ENABLE_SEMANTIC"] = "true"
os.environ["VTIC_SEARCH_EMBEDDING_PROVIDER"] = "openai"
# Note: OPENAI_API_KEY not set

config = load_and_validate_config()
# Warning emitted: "Semantic search is enabled... but OPENAI_API_KEY..."
assert config.search.enable_semantic is False  # Auto-disabled

# Example 3: Directory auto-creation
os.environ["VTIC_TICKETS_DIR"] = "./new-tickets-dir"
config = load_and_validate_config()
# Warning emitted: "Created ticket directory: /absolute/path/to/new-tickets-dir"
assert config.tickets.dir.exists()  # Directory was created
```

---

## 5. Complete Module Structure

```
vtic/
├── config/
│   ├── __init__.py          # Public exports: load_config, load_and_validate_config, Config
│   ├── models.py            # Pydantic models (Config, TicketsConfig, ServerConfig, SearchConfig)
│   ├── loader.py            # load_config(), _load_env_overrides(), _find_and_load_config_file()
│   └── validation.py        # validate_and_initialize_config(), validate_search_config()
```

### 5.1 `__init__.py` Public API

```python
"""vtic configuration system.

Public API for loading and validating vtic configuration.
"""

from .loader import load_config, get_openai_api_key
from .models import Config, TicketsConfig, ApiConfig, SearchConfig
from .validation import load_and_validate_config, ConfigValidationError

__all__ = [
    # Functions
    "load_config",
    "load_and_validate_config",
    "get_openai_api_key",
    # Models
    "Config",
    "TicketsConfig",
    "ApiConfig",
    "SearchConfig",
    # Exceptions
    "ConfigValidationError",
]
```

---

## 6. Summary

| Validation Rule | Behavior |
|----------------|----------|
| `dir` doesn't exist | Create directory on init, emit warning |
| Port out of range (1-65535) | Raise `ValueError` |
| `embedding_provider` set but no API key | Emit warning, disable semantic search |
| `enable_semantic=true` with `provider="none"` | Raise `ValueError` (Pydantic) |
| Hybrid weights don't sum to ~1.0 | Emit warning, continue |
| Invalid TOML syntax | Raise `ValueError` |
| Config file not found | Use defaults, no error |

| Precedence | Source |
|-----------|--------|
| 1 (highest) | Environment variables (`VTIC_*`) |
| 2 | Explicit `config_path` argument |
| 3 | Project `./vtic.toml` |
| 4 | User `~/.config/vtic/config.toml` |
| 5 (lowest) | Hardcoded Pydantic defaults |
