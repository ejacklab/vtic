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


class StorageConfig(BaseModel):
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
            Defaults to "localhost".
        port: Port number for the server.
            Must be in range 1-65535.
            Defaults to 8080.
    """
    
    host: str = Field(
        default="localhost",
        description="API server host address"
    )
    port: int = Field(
        default=8080,
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
        semantic_enabled: Whether semantic (dense embedding) search is enabled.
            Requires an embedding provider when enabled.
        bm25_weight: Weight for BM25 scores in hybrid ranking.
            Range 0.0-1.0. Default 0.6.
        semantic_weight: Weight for semantic scores in hybrid ranking.
            Range 0.0-1.0. Default 0.4.
            Weights should sum to 1.0 for normalized hybrid scoring.
    """
    
    bm25_enabled: bool = Field(
        default=True,
        description="Enable BM25 keyword search"
    )
    semantic_enabled: bool = Field(
        default=False,
        description="Enable semantic/dense embedding search"
    )
    bm25_weight: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="BM25 weight in hybrid scoring (0.0-1.0)"
    )
    semantic_weight: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Semantic weight in hybrid scoring (0.0-1.0)"
    )
    
    @field_validator("bm25_weight", "semantic_weight")
    @classmethod
    def _validate_weight_range(cls, v: float) -> float:
        """Ensure weights are within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0.0 and 1.0, got {v}")
        return v
    
    @model_validator(mode="after")
    def _check_weights_sum(self) -> SearchConfig:
        """Warn if weights don't sum to approximately 1.0."""
        total = self.bm25_weight + self.semantic_weight
        if not 0.99 <= total <= 1.01:  # Allow small floating point variance
            warnings.warn(
                f"Hybrid weights sum to {total}, expected ~1.0. "
                f"BM25: {self.bm25_weight}, Semantic: {self.semantic_weight}",
                UserWarning,
                stacklevel=2
            )
        return self


class EmbeddingsConfig(BaseModel):
    """Configuration for embedding providers.
    
    Attributes:
        provider: Provider for embeddings.
            Options: "openai" (OpenAI API), "local" (sentence-transformers),
            "custom" (user-provided), "none" (no embeddings, BM25 only).
        model: Model name for embeddings.
            Provider-specific model identifier.
        dimension: Vector dimensions for embeddings.
            Must match the model's output dimensions.
    """
    
    provider: Literal["local", "openai", "custom", "none"] = Field(
        default="local",
        description="Embedding provider: local | openai | custom | none"
    )
    model: str | None = Field(
        default=None,
        description="Embedding model name"
    )
    dimension: int | None = Field(
        default=None,
        gt=0,
        description="Embedding vector dimensions"
    )
    
    @field_validator("dimension")
    @classmethod
    def _validate_positive_dimensions(cls, v: int | None) -> int | None:
        """Ensure dimensions are positive if provided."""
        if v is not None and v <= 0:
            raise ValueError(f"Embedding dimensions must be positive, got {v}")
        return v
    
    @model_validator(mode="after")
    def _validate_provider_consistency(self) -> EmbeddingsConfig:
        """Validate provider settings."""
        if self.provider == "none" and self.model is not None:
            warnings.warn(
                "Embedding model is set but provider is 'none'. Model will be ignored.",
                UserWarning,
                stacklevel=2
            )
        return self


class Config(BaseModel):
    """Root configuration for vtic.
    
    This is the top-level configuration object that aggregates
    all sub-configurations: storage, api, search, and embeddings.
    
    Attributes:
        storage: Ticket storage configuration.
        api: API server configuration.
        search: Search configuration (weights, enabled flags).
        embeddings: Embedding provider configuration.
    
    Example:
        >>> config = Config()
        >>> config.storage.dir
        PosixPath('tickets')
        >>> config.api.port
        8080
    """
    
    storage: StorageConfig = Field(
        default_factory=StorageConfig,
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
    embeddings: EmbeddingsConfig = Field(
        default_factory=EmbeddingsConfig,
        description="Embedding provider configuration"
    )
    
    model_config = {
        "validate_assignment": True,
        "extra": "forbid",  # Prevent unexpected fields
    }


# Embedding model defaults by provider
EMBEDDING_DEFAULTS: dict[str, dict[str, str | int]] = {
    "openai": {
        "model": "text-embedding-3-small",
        "dimension": 1536,
    },
    "local": {
        "model": "all-MiniLM-L6-v2",
        "dimension": 384,
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
    # Storage section
    "VTIC_STORAGE_DIR": ("storage", "dir"),
    
    # API section
    "VTIC_API_HOST": ("api", "host"),
    "VTIC_API_PORT": ("api", "port"),
    
    # Search section
    "VTIC_SEARCH_BM25_ENABLED": ("search", "bm25_enabled"),
    "VTIC_SEARCH_SEMANTIC_ENABLED": ("search", "semantic_enabled"),
    "VTIC_SEARCH_BM25_WEIGHT": ("search", "bm25_weight"),
    "VTIC_SEARCH_SEMANTIC_WEIGHT": ("search", "semantic_weight"),
    
    # Embeddings section
    "VTIC_EMBEDDINGS_PROVIDER": ("embeddings", "provider"),
    "VTIC_EMBEDDINGS_MODEL": ("embeddings", "model"),
    "VTIC_EMBEDDINGS_DIMENSION": ("embeddings", "dimension"),
    
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
    
    When embeddings.provider is set but model/dimension are not,
    apply the appropriate defaults for that provider.
    
    Args:
        config_dict: Configuration dictionary to modify.
        
    Returns:
        Modified configuration dictionary.
    """
    embeddings = config_dict.get("embeddings", {})
    provider = embeddings.get("provider")
    
    if provider and provider in EMBEDDING_DEFAULTS:
        defaults = EMBEDDING_DEFAULTS[provider]
        
        # Apply model default if not set
        if "model" not in embeddings:
            embeddings["model"] = defaults["model"]
        
        # Apply dimension default if not set
        if "dimension" not in embeddings:
            embeddings["dimension"] = defaults["dimension"]
        
        config_dict["embeddings"] = embeddings
    
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
        VTIC_STORAGE_DIR: Ticket directory path
        VTIC_API_HOST: API server host address
        VTIC_API_PORT: API server port number
        VTIC_SEARCH_BM25_ENABLED: Enable BM25 (bool)
        VTIC_SEARCH_SEMANTIC_ENABLED: Enable semantic search (bool)
        VTIC_SEARCH_BM25_WEIGHT: BM25 weight (0.0-1.0)
        VTIC_SEARCH_SEMANTIC_WEIGHT: Semantic weight (0.0-1.0)
        VTIC_EMBEDDINGS_PROVIDER: Embedding provider
        VTIC_EMBEDDINGS_MODEL: Embedding model name
        VTIC_EMBEDDINGS_DIMENSION: Embedding dimensions
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

from .models import Config, SearchConfig, EmbeddingsConfig
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


def validate_embeddings_config(
    embeddings_config: EmbeddingsConfig,
    search_config: SearchConfig
) -> tuple[EmbeddingsConfig, SearchConfig]:
    """Validate embeddings configuration and handle semantic search requirements.
    
    Performs the following validations:
    - If semantic_enabled is true and provider is "openai", verify API key exists
    - If API key missing, emit warning and disable semantic search
    
    Args:
        embeddings_config: Embeddings configuration to validate.
        search_config: Search configuration to validate.
        
    Returns:
        Potentially modified (embeddings_config, search_config) tuple.
    """
    if not search_config.semantic_enabled:
        # Semantic search disabled - nothing to validate
        return embeddings_config, search_config
    
    if embeddings_config.provider == "none":
        warnings.warn(
            "Semantic search is enabled but embeddings provider is 'none'. "
            "Semantic search will be disabled. "
            "Set embeddings.provider to 'openai', 'local', or 'custom'.",
            UserWarning,
            stacklevel=2
        )
        search_config.semantic_enabled = False
        return embeddings_config, search_config
    
    if embeddings_config.provider == "openai":
        api_key = get_openai_api_key()
        
        if not api_key:
            warnings.warn(
                "Semantic search is enabled with 'openai' provider, "
                "but OPENAI_API_KEY environment variable is not set. "
                "Semantic search will be disabled. "
                "Set OPENAI_API_KEY or change embeddings.provider to 'local' or 'none'.",
                UserWarning,
                stacklevel=2
            )
            # Disable semantic search due to missing API key
            search_config.semantic_enabled = False
    
    elif embeddings_config.provider == "local":
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
            search_config.semantic_enabled = False
    
    return embeddings_config, search_config


def validate_and_initialize_config(config: Config) -> Config:
    """Perform full post-load validation and initialization.
    
    This function should be called immediately after load_config()
    to ensure the configuration is valid and runtime requirements are met.
    
    Validation steps:
    1. Validate server port range (raises ValueError if invalid)
    2. Create ticket directory if it doesn't exist
    3. Validate embeddings config (disable semantic if API key missing)
    
    Args:
        config: Loaded configuration to validate.
        
    Returns:
        Validated and potentially modified configuration.
        
    Raises:
        ConfigValidationError: If critical validation fails.
        ValueError: If port is out of range (via validate_port_range).
    """
    # 1. Validate server port
    validate_port_range(config.api.port)
    
    # 2. Validate and create ticket directory
    resolved_dir = validate_and_create_ticket_dir(config.storage.dir)
    config.storage.dir = resolved_dir
    
    # 3. Validate embeddings and search configuration
    config.embeddings, config.search = validate_embeddings_config(
        config.embeddings, config.search
    )
    
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
print(config.storage.dir)           # PosixPath('/absolute/path/to/tickets')
print(config.api.host)              # "localhost"
print(config.api.port)              # 8080
print(config.search.bm25_enabled)   # True
print(config.search.semantic_enabled)  # False (if no API key)
print(config.embeddings.provider)   # "local"
```

### 4.2 Environment Variable Override

```bash
# Override via environment
export VTIC_STORAGE_DIR="/var/vtic/tickets"
export VTIC_API_PORT=8080
export VTIC_API_HOST="localhost"
export VTIC_SEARCH_SEMANTIC_ENABLED=true
export VTIC_EMBEDDINGS_PROVIDER="openai"
export OPENAI_API_KEY="sk-..."
```

```python
from vtic.config import load_config

# Environment variables take precedence over config files
config = load_config()
assert config.api.port == 8080
assert config.api.host == "localhost"
assert config.search.semantic_enabled is True
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
os.environ["VTIC_SEARCH_SEMANTIC_ENABLED"] = "true"
os.environ["VTIC_EMBEDDINGS_PROVIDER"] = "openai"
# Note: OPENAI_API_KEY not set

config = load_and_validate_config()
# Warning emitted: "Semantic search is enabled... but OPENAI_API_KEY..."
assert config.search.semantic_enabled is False  # Auto-disabled

# Example 3: Directory auto-creation
os.environ["VTIC_STORAGE_DIR"] = "./new-tickets-dir"
config = load_and_validate_config()
# Warning emitted: "Created ticket directory: /absolute/path/to/new-tickets-dir"
assert config.storage.dir.exists()  # Directory was created
```

---

## 5. Complete Module Structure

```
vtic/
├── config/
│   ├── __init__.py          # Public exports: load_config, load_and_validate_config, Config
│   ├── models.py            # Pydantic models (Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig)
│   ├── loader.py            # load_config(), _load_env_overrides(), _find_and_load_config_file()
│   └── validation.py        # validate_and_initialize_config(), validate_embeddings_config()
```

### 5.1 `__init__.py` Public API

```python
"""vtic configuration system.

Public API for loading and validating vtic configuration.
"""

from .loader import load_config, get_openai_api_key
from .models import Config, StorageConfig, ApiConfig, SearchConfig, EmbeddingsConfig
from .validation import load_and_validate_config, ConfigValidationError

__all__ = [
    # Functions
    "load_config",
    "load_and_validate_config",
    "get_openai_api_key",
    # Models
    "Config",
    "StorageConfig",
    "ApiConfig",
    "SearchConfig",
    "EmbeddingsConfig",
    # Exceptions
    "ConfigValidationError",
]
```

---

## 6. TOML Configuration Example

```toml
# vtic.toml - Project configuration

[storage]
dir = "./tickets"

[api]
host = "localhost"
port = 8080

[search]
bm25_enabled = true
semantic_enabled = true
bm25_weight = 0.6
semantic_weight = 0.4

[embeddings]
provider = "local"
model = "all-MiniLM-L6-v2"
dimension = 384
```

---

## 7. ConfigResponse Schema (from OpenAPI)

The API `/config` endpoint returns a `ConfigResponse` matching this structure:

```python
class ConfigResponse(BaseModel):
    """Current configuration response from /config endpoint."""
    
    storage: StorageConfig
    search: SearchConfig
    embeddings: EmbeddingsConfig
    api: ApiConfig
    request_id: str | None = None
```

---

## 8. Summary

| Validation Rule | Behavior |
|----------------|----------|
| `storage.dir` doesn't exist | Create directory on init, emit warning |
| Port out of range (1-65535) | Raise `ValueError` |
| `embeddings.provider` set but no API key (openai) | Emit warning, disable semantic search |
| `semantic_enabled=true` with `provider="none"` | Emit warning, disable semantic search |
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

| Field | OpenAPI Name | Default |
|-------|--------------|---------|
| Ticket directory | `storage.dir` | `"./tickets"` |
| API host | `api.host` | `"localhost"` |
| API port | `api.port` | `8080` |
| BM25 enabled | `search.bm25_enabled` | `true` |
| Semantic enabled | `search.semantic_enabled` | `false` |
| BM25 weight | `search.bm25_weight` | `0.6` |
| Semantic weight | `search.semantic_weight` | `0.4` |
| Embedding provider | `embeddings.provider` | `"local"` |
| Embedding model | `embeddings.model` | `null` |
| Embedding dimension | `embeddings.dimension` | `null` |
