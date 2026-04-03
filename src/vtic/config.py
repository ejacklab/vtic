"""Configuration models and loaders for vtic."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from .constants import DEFAULT_CONFIG_FILENAME, DEFAULT_GLOBAL_CONFIG_PATH
from .errors import ConfigError

_ENV_OVERRIDES: dict[str, tuple[str, str]] = {
    "VTIC_TICKETS_DIR": ("tickets", "dir"),
    "VTIC_SERVER_HOST": ("server", "host"),
    "VTIC_SERVER_PORT": ("server", "port"),
    "VTIC_SEARCH_BM25_ENABLED": ("search", "bm25_enabled"),
    "VTIC_SEARCH_SEMANTIC_ENABLED": ("search", "semantic_enabled"),
    "VTIC_SEARCH_EMBEDDING_PROVIDER": ("search", "embedding_provider"),
    "VTIC_SEARCH_EMBEDDING_MODEL": ("search", "embedding_model"),
    "VTIC_SEARCH_EMBEDDING_DIMENSIONS": ("search", "embedding_dimensions"),
}


class TicketsConfig(BaseModel):
    """Ticket storage configuration."""

    model_config = {"validate_default": True}

    dir: Path = Field(default=Path("./tickets"), description="Ticket storage directory path")

    @field_validator("dir")
    @classmethod
    def validate_dir(cls, v: Path) -> Path:
        return v.expanduser().resolve()


class ServerConfig(BaseModel):
    """API server configuration."""

    model_config = {"validate_default": True}

    host: str = Field(default="127.0.0.1", description="Bind address")
    port: int = Field(default=8900, ge=1, le=65535, description="Server port")


class SearchConfig(BaseModel):
    """Search configuration."""

    model_config = {"validate_default": True}

    bm25_enabled: bool = Field(default=True)
    semantic_enabled: bool = Field(default=False)
    embedding_provider: Literal["openai", "local", "none"] = Field(default="openai")
    embedding_model: str = Field(default="text-embedding-3-small")
    embedding_dimensions: int = Field(default=1536, ge=384, le=4096)
    hybrid_weights_bm25: float = Field(default=0.7, ge=0.0, le=1.0)
    hybrid_weights_semantic: float = Field(default=0.3, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_semantic_config(self) -> Self:
        if self.semantic_enabled and self.embedding_provider == "none":
            raise ValueError("Cannot enable semantic search with provider='none'")
        return self

    @model_validator(mode="after")
    def validate_weights_sum(self) -> Self:
        if self.bm25_enabled and self.semantic_enabled:
            total = self.hybrid_weights_bm25 + self.hybrid_weights_semantic
            if abs(total - 1.0) > 0.001:
                raise ValueError(f"Hybrid weights must sum to 1.0, got {total}")
        return self


class VticConfig(BaseModel):
    """Complete vtic configuration."""

    model_config = {"validate_default": True}

    tickets: TicketsConfig = Field(default_factory=TicketsConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)

    @classmethod
    def from_toml(cls, path: Path) -> "VticConfig":
        try:
            with open(path, "rb") as f:
                data = tomllib.load(f)
            if "tickets" in data and "dir" in data["tickets"]:
                ticket_dir = Path(data["tickets"]["dir"])
                if not ticket_dir.is_absolute():
                    data["tickets"]["dir"] = path.parent / ticket_dir
            return cls(**data)
        except (OSError, tomllib.TOMLDecodeError, ValueError) as exc:
            raise ConfigError(f"Invalid config file {path}: {exc}") from exc

    @classmethod
    def from_env(cls) -> "VticConfig":
        try:
            config = cls()

            if tickets_dir := os.getenv("VTIC_TICKETS_DIR"):
                config.tickets.dir = Path(tickets_dir)

            if host := os.getenv("VTIC_SERVER_HOST"):
                config.server.host = host
            if port := os.getenv("VTIC_SERVER_PORT"):
                config.server.port = int(port)

            if bm25 := os.getenv("VTIC_SEARCH_BM25_ENABLED"):
                config.search.bm25_enabled = bm25.lower() in ("true", "1", "yes")
            if semantic := os.getenv("VTIC_SEARCH_SEMANTIC_ENABLED"):
                config.search.semantic_enabled = semantic.lower() in ("true", "1", "yes")
            if provider := os.getenv("VTIC_SEARCH_EMBEDDING_PROVIDER"):
                config.search.embedding_provider = provider
            if model := os.getenv("VTIC_SEARCH_EMBEDDING_MODEL"):
                config.search.embedding_model = model
            if dims := os.getenv("VTIC_SEARCH_EMBEDDING_DIMENSIONS"):
                config.search.embedding_dimensions = int(dims)

            return config
        except ValueError as exc:
            raise ConfigError(f"Invalid environment configuration: {exc}") from exc


def resolve_config_path() -> Path | None:
    """Resolve config path from environment, local project, then global config."""

    if config_env := os.getenv("VTIC_CONFIG"):
        return Path(config_env).expanduser().resolve()

    local_path = Path.cwd() / DEFAULT_CONFIG_FILENAME
    if local_path.exists():
        return local_path.resolve()

    if DEFAULT_GLOBAL_CONFIG_PATH.exists():
        return DEFAULT_GLOBAL_CONFIG_PATH.resolve()

    return None


def load_config(explicit_path: Path | None = None) -> VticConfig:
    """Load config from explicit path, discovered TOML, then environment overrides."""

    path = explicit_path.expanduser().resolve() if explicit_path is not None else resolve_config_path()
    config = VticConfig.from_toml(path) if path is not None else VticConfig()
    env_config = VticConfig.from_env()

    for env_var, (section, field) in _ENV_OVERRIDES.items():
        if env_var not in os.environ:
            continue
        setattr(getattr(config, section), field, getattr(getattr(env_config, section), field))

    return config
