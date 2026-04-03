from __future__ import annotations

from pathlib import Path

import pytest

from vtic.config import VticConfig, load_config
from vtic.errors import ConfigError


def test_config_defaults() -> None:
    config = VticConfig()

    assert config.tickets.dir == Path("./tickets").resolve()
    assert config.server.host == "127.0.0.1"
    assert config.server.port == 8900
    assert config.search.bm25_enabled is True
    assert config.search.semantic_enabled is False
    assert config.search.embedding_provider == "openai"
    assert config.search.embedding_model == "text-embedding-3-small"
    assert config.search.embedding_dimensions == 1536
    assert config.search.hybrid_weights_bm25 == 0.7
    assert config.search.hybrid_weights_semantic == 0.3


def test_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "vtic.toml"
    config_path.write_text(
        """
[tickets]
dir = "./custom-tickets"

[server]
host = "0.0.0.0"
port = 9999

[search]
bm25_enabled = true
semantic_enabled = true
embedding_provider = "local"
embedding_model = "all-MiniLM-L6-v2"
embedding_dimensions = 384
hybrid_weights_bm25 = 0.6
hybrid_weights_semantic = 0.4
""".strip(),
        encoding="utf-8",
    )

    config = VticConfig.from_toml(config_path)

    assert config.tickets.dir == (tmp_path / "custom-tickets").resolve()
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 9999
    assert config.search.semantic_enabled is True
    assert config.search.embedding_provider == "local"
    assert config.search.embedding_model == "all-MiniLM-L6-v2"
    assert config.search.embedding_dimensions == 384
    assert config.search.hybrid_weights_bm25 == 0.6
    assert config.search.hybrid_weights_semantic == 0.4


def test_config_from_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VTIC_TICKETS_DIR", str(tmp_path / "env-tickets"))
    monkeypatch.setenv("VTIC_SERVER_HOST", "0.0.0.0")
    monkeypatch.setenv("VTIC_SERVER_PORT", "7777")
    monkeypatch.setenv("VTIC_SEARCH_BM25_ENABLED", "false")
    monkeypatch.setenv("VTIC_SEARCH_SEMANTIC_ENABLED", "true")
    monkeypatch.setenv("VTIC_SEARCH_EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("VTIC_SEARCH_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    monkeypatch.setenv("VTIC_SEARCH_EMBEDDING_DIMENSIONS", "384")

    config = VticConfig.from_env()

    assert config.tickets.dir == (tmp_path / "env-tickets").resolve()
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 7777
    assert config.search.bm25_enabled is False
    assert config.search.semantic_enabled is True
    assert config.search.embedding_provider == "local"
    assert config.search.embedding_model == "all-MiniLM-L6-v2"
    assert config.search.embedding_dimensions == 384


def test_load_config_explicit_path_and_env_override(monkeypatch, tmp_path: Path) -> None:
    config_path = tmp_path / "vtic.toml"
    config_path.write_text(
        """
[tickets]
dir = "./toml-tickets"

[server]
host = "127.0.0.2"
port = 8901
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("VTIC_SERVER_PORT", "9000")

    config = load_config(config_path)

    assert config.tickets.dir == (tmp_path / "toml-tickets").resolve()
    assert config.server.host == "127.0.0.2"
    assert config.server.port == 9000


def test_config_from_env_invalid_int_raises_config_error(monkeypatch) -> None:
    monkeypatch.setenv("VTIC_SERVER_PORT", "not-a-port")

    with pytest.raises(ConfigError, match="Invalid environment configuration"):
        VticConfig.from_env()


def test_config_from_toml_invalid_value_raises_config_error(tmp_path: Path) -> None:
    config_path = tmp_path / "vtic.toml"
    config_path.write_text(
        """
[server]
port = "bad"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="Invalid config file"):
        VticConfig.from_toml(config_path)
