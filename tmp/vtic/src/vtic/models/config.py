"""Configuration models for vtic.

This module defines all configuration structures using Pydantic v2,
providing validation, serialization, and environment variable integration.
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, Field, field_validator, model_validator

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # Fallback for older Python


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
    def _check_weights_sum(self) -> "SearchConfig":
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
    model: Optional[str] = Field(
        default=None,
        description="Embedding model name"
    )
    dimension: Optional[int] = Field(
        default=None,
        gt=0,
        description="Embedding vector dimensions"
    )
    
    @field_validator("dimension")
    @classmethod
    def _validate_positive_dimensions(cls, v: Optional[int]) -> Optional[int]:
        """Ensure dimensions are positive if provided."""
        if v is not None and v <= 0:
            raise ValueError(f"Embedding dimensions must be positive, got {v}")
        return v
    
    @model_validator(mode="after")
    def _validate_provider_consistency(self) -> "EmbeddingsConfig":
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
EMBEDDING_DEFAULTS: Dict[str, Dict[str, str | int]] = {
    "openai": {
        "model": "text-embedding-3-small",
        "dimension": 1536,
    },
    "local": {
        "model": "all-MiniLM-L6-v2",
        "dimension": 384,
    },
}


# Environment variable to config field mapping
# Format: "ENV_VAR_NAME": ("section", "field")
ENV_VAR_MAP: Dict[str, Tuple[str, str]] = {
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
}

# Config file search paths (in priority order)
CONFIG_SEARCH_PATHS: list[Path] = [
    Path("./vtic.toml"),                      # Project-local
    Path.home() / ".config" / "vtic" / "config.toml",  # User global
]


def _parse_env_value(value: str) -> bool | int | float | str:
    """Parse environment variable string to appropriate type."""
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


def _load_env_overrides() -> Dict[str, Dict[str, Any]]:
    """Load configuration overrides from environment variables.
    
    Returns:
        Nested dict with structure: {section: {field: value}}
    """
    overrides: Dict[str, Dict[str, Any]] = {}
    
    for env_var, (section, field) in ENV_VAR_MAP.items():
        if env_var in os.environ:
            value = _parse_env_value(os.environ[env_var])
            
            if section not in overrides:
                overrides[section] = {}
            overrides[section][field] = value
    
    return overrides


def _load_toml_file(path: Path) -> Dict[str, Any]:
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
    except Exception as e:
        raise ValueError(f"Invalid TOML in {path}: {e}") from e


def _find_and_load_config_file(config_path: Optional[Path] = None) -> Dict[str, Any]:
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


def _apply_provider_defaults(config_dict: Dict[str, Any]) -> Dict[str, Any]:
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
    file_config: Dict[str, Any],
    env_config: Dict[str, Any]
) -> Dict[str, Any]:
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


def load_config(config_path: Optional[Path] = None) -> Config:
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
