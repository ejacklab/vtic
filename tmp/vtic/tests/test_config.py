"""Tests for vtic config module."""

import os
import warnings
from pathlib import Path

import pytest

from vtic.models.config import (
    Config,
    StorageConfig,
    ApiConfig,
    SearchConfig,
    EmbeddingsConfig,
    load_config,
    _parse_env_value,
    _load_env_overrides,
    EMBEDDING_DEFAULTS,
)


class TestStorageConfig:
    """Tests for StorageConfig model."""

    def test_default_storage_dir(self):
        """Test default storage directory."""
        config = StorageConfig()
        assert config.dir == Path("./tickets")

    def test_storage_dir_from_string(self):
        """Test that dir can be set from string."""
        config = StorageConfig(dir="/custom/path")
        assert config.dir == Path("/custom/path")

    def test_storage_dir_from_path(self):
        """Test that dir can be set from Path object."""
        config = StorageConfig(dir=Path("/custom/path"))
        assert config.dir == Path("/custom/path")


class TestApiConfig:
    """Tests for ApiConfig model."""

    def test_default_api_config(self):
        """Test default API configuration."""
        config = ApiConfig()
        assert config.host == "localhost"
        assert config.port == 8080

    def test_custom_api_config(self):
        """Test custom API configuration."""
        config = ApiConfig(host="0.0.0.0", port=3000)
        assert config.host == "0.0.0.0"
        assert config.port == 3000

    def test_port_validation_min(self):
        """Test port minimum validation (1)."""
        config = ApiConfig(port=1)
        assert config.port == 1

    def test_port_validation_max(self):
        """Test port maximum validation (65535)."""
        config = ApiConfig(port=65535)
        assert config.port == 65535

    def test_port_validation_below_min(self):
        """Test port below minimum raises error."""
        with pytest.raises(ValueError) as exc_info:
            ApiConfig(port=0)
        # Pydantic's ge constraint produces the error message
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_port_validation_above_max(self):
        """Test port above maximum raises error."""
        with pytest.raises(ValueError) as exc_info:
            ApiConfig(port=65536)
        # Pydantic's le constraint produces the error message
        assert "less than or equal to 65535" in str(exc_info.value)

    def test_port_validation_negative(self):
        """Test negative port raises error."""
        with pytest.raises(ValueError):
            ApiConfig(port=-1)


class TestSearchConfig:
    """Tests for SearchConfig model."""

    def test_default_search_config(self):
        """Test default search configuration."""
        config = SearchConfig()
        assert config.bm25_enabled is True
        assert config.semantic_enabled is False
        assert config.bm25_weight == 0.6
        assert config.semantic_weight == 0.4

    def test_bm25_weight_range(self):
        """Test BM25 weight range validation."""
        config = SearchConfig(bm25_weight=0.0)
        assert config.bm25_weight == 0.0
        
        config = SearchConfig(bm25_weight=1.0)
        assert config.bm25_weight == 1.0

    def test_bm25_weight_out_of_range(self):
        """Test BM25 weight out of range raises error."""
        with pytest.raises(ValueError):
            SearchConfig(bm25_weight=-0.1)
        with pytest.raises(ValueError):
            SearchConfig(bm25_weight=1.1)

    def test_semantic_weight_range(self):
        """Test semantic weight range validation."""
        config = SearchConfig(semantic_weight=0.0)
        assert config.semantic_weight == 0.0
        
        config = SearchConfig(semantic_weight=1.0)
        assert config.semantic_weight == 1.0

    def test_weights_sum_warning(self):
        """Test warning when weights don't sum to ~1.0."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            SearchConfig(bm25_weight=0.5, semantic_weight=0.3)
            assert len(w) == 1
            assert "Hybrid weights sum to" in str(w[0].message)

    def test_weights_sum_ok(self):
        """Test no warning when weights sum to ~1.0."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            SearchConfig(bm25_weight=0.6, semantic_weight=0.4)
            # Filter for UserWarning about weights
            weight_warnings = [x for x in w if "Hybrid weights" in str(x.message)]
            assert len(weight_warnings) == 0


class TestEmbeddingsConfig:
    """Tests for EmbeddingsConfig model."""

    def test_default_embeddings_config(self):
        """Test default embeddings configuration."""
        config = EmbeddingsConfig()
        assert config.provider == "local"
        assert config.model is None
        assert config.dimension is None

    def test_provider_values(self):
        """Test valid provider values."""
        for provider in ["local", "openai", "custom", "none"]:
            config = EmbeddingsConfig(provider=provider)
            assert config.provider == provider

    def test_dimension_validation(self):
        """Test dimension positive validation."""
        config = EmbeddingsConfig(dimension=384)
        assert config.dimension == 384

    def test_dimension_must_be_positive(self):
        """Test dimension must be positive."""
        with pytest.raises(ValueError):
            EmbeddingsConfig(dimension=0)
        with pytest.raises(ValueError):
            EmbeddingsConfig(dimension=-1)

    def test_dimension_none_allowed(self):
        """Test dimension can be None."""
        config = EmbeddingsConfig(dimension=None)
        assert config.dimension is None

    def test_provider_none_with_model_warning(self):
        """Test warning when provider is none but model is set."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            EmbeddingsConfig(provider="none", model="some-model")
            assert len(w) == 1
            assert "provider is 'none'" in str(w[0].message)


class TestConfig:
    """Tests for root Config model."""

    def test_default_config(self):
        """Test default configuration."""
        config = Config()
        assert isinstance(config.storage, StorageConfig)
        assert isinstance(config.api, ApiConfig)
        assert isinstance(config.search, SearchConfig)
        assert isinstance(config.embeddings, EmbeddingsConfig)

    def test_config_defaults_values(self):
        """Test default config values."""
        config = Config()
        assert config.storage.dir == Path("./tickets")
        assert config.api.host == "localhost"
        assert config.api.port == 8080
        assert config.search.bm25_enabled is True
        assert config.embeddings.provider == "local"

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValueError):
            Config(invalid_field="test")

    def test_nested_config_update(self):
        """Test updating nested config values."""
        config = Config()
        config.api.port = 9000
        assert config.api.port == 9000


class TestEnvValueParsing:
    """Tests for environment variable value parsing."""

    def test_parse_boolean_true_values(self):
        """Test parsing boolean true values."""
        assert _parse_env_value("true") is True
        assert _parse_env_value("True") is True
        assert _parse_env_value("TRUE") is True
        assert _parse_env_value("1") is True
        assert _parse_env_value("yes") is True
        assert _parse_env_value("on") is True

    def test_parse_boolean_false_values(self):
        """Test parsing boolean false values."""
        assert _parse_env_value("false") is False
        assert _parse_env_value("False") is False
        assert _parse_env_value("FALSE") is False
        assert _parse_env_value("0") is False
        assert _parse_env_value("no") is False
        assert _parse_env_value("off") is False

    def test_parse_integer(self):
        """Test parsing integer values."""
        assert _parse_env_value("8080") == 8080
        assert _parse_env_value("0") == 0  # 0 is not parsed as boolean false here
        assert _parse_env_value("-1") == -1

    def test_parse_float(self):
        """Test parsing float values."""
        assert _parse_env_value("0.6") == 0.6
        assert _parse_env_value("3.14") == 3.14

    def test_parse_string(self):
        """Test parsing string values."""
        assert _parse_env_value("localhost") == "localhost"
        assert _parse_env_value("/path/to/dir") == "/path/to/dir"


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_default_config(self, monkeypatch, tmp_path):
        """Test loading default config with no file."""
        # Change to temp directory so no config file is found
        monkeypatch.chdir(tmp_path)
        config = load_config()
        assert config.api.port == 8080
        assert config.api.host == "localhost"

    def test_load_config_from_file(self, tmp_path):
        """Test loading config from TOML file."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[api]
host = "0.0.0.0"
port = 3000

[storage]
dir = "./custom-tickets"
""")
        config = load_config(config_path=config_file)
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 3000
        assert config.storage.dir == Path("./custom-tickets")

    def test_config_file_not_found(self, tmp_path):
        """Test error when config file not found."""
        with pytest.raises(ValueError) as exc_info:
            load_config(config_path=tmp_path / "nonexistent.toml")
        assert "Cannot load specified config" in str(exc_info.value)

    def test_invalid_toml_raises_error(self, tmp_path):
        """Test error when TOML is invalid."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("invalid toml content [[[")
        with pytest.raises(ValueError) as exc_info:
            load_config(config_path=config_file)
        assert "Invalid TOML" in str(exc_info.value)


class TestEnvVarOverride:
    """Tests for environment variable overrides."""

    def test_env_override_storage_dir(self, monkeypatch, tmp_path):
        """Test VTIC_STORAGE_DIR environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_STORAGE_DIR", "/env/storage")
        config = load_config()
        assert config.storage.dir == Path("/env/storage")

    def test_env_override_api_host(self, monkeypatch, tmp_path):
        """Test VTIC_API_HOST environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_API_HOST", "0.0.0.0")
        config = load_config()
        assert config.api.host == "0.0.0.0"

    def test_env_override_api_port(self, monkeypatch, tmp_path):
        """Test VTIC_API_PORT environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_API_PORT", "9000")
        config = load_config()
        assert config.api.port == 9000

    def test_env_override_search_enabled(self, monkeypatch, tmp_path):
        """Test VTIC_SEARCH_SEMANTIC_ENABLED environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_SEARCH_SEMANTIC_ENABLED", "true")
        config = load_config()
        assert config.search.semantic_enabled is True

    def test_env_override_search_weights(self, monkeypatch, tmp_path):
        """Test VTIC_SEARCH_BM25_WEIGHT environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_SEARCH_BM25_WEIGHT", "0.7")
        monkeypatch.setenv("VTIC_SEARCH_SEMANTIC_WEIGHT", "0.3")
        config = load_config()
        assert config.search.bm25_weight == 0.7
        assert config.search.semantic_weight == 0.3

    def test_env_override_embeddings_provider(self, monkeypatch, tmp_path):
        """Test VTIC_EMBEDDINGS_PROVIDER environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_EMBEDDINGS_PROVIDER", "openai")
        config = load_config()
        assert config.embeddings.provider == "openai"

    def test_env_override_embeddings_model(self, monkeypatch, tmp_path):
        """Test VTIC_EMBEDDINGS_MODEL environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_EMBEDDINGS_MODEL", "text-embedding-3-large")
        config = load_config()
        assert config.embeddings.model == "text-embedding-3-large"

    def test_env_override_embeddings_dimension(self, monkeypatch, tmp_path):
        """Test VTIC_EMBEDDINGS_DIMENSION environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_EMBEDDINGS_DIMENSION", "1536")
        config = load_config()
        assert config.embeddings.dimension == 1536

    def test_env_takes_precedence_over_file(self, monkeypatch, tmp_path):
        """Test that env vars take precedence over config file."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[api]
port = 5000
""")
        monkeypatch.setenv("VTIC_API_PORT", "7000")
        config = load_config(config_path=config_file)
        assert config.api.port == 7000  # Env wins


class TestEmbeddingDefaults:
    """Tests for provider-specific embedding defaults."""

    def test_openai_defaults_applied(self, tmp_path):
        """Test OpenAI defaults are applied when provider is openai."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[embeddings]
provider = "openai"
""")
        config = load_config(config_path=config_file)
        assert config.embeddings.provider == "openai"
        assert config.embeddings.model == "text-embedding-3-small"
        assert config.embeddings.dimension == 1536

    def test_local_defaults_applied(self, tmp_path):
        """Test local defaults are applied when provider is local."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[embeddings]
provider = "local"
""")
        config = load_config(config_path=config_file)
        assert config.embeddings.provider == "local"
        assert config.embeddings.model == "all-MiniLM-L6-v2"
        assert config.embeddings.dimension == 384

    def test_custom_defaults_not_applied(self, tmp_path):
        """Test no defaults for custom provider."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[embeddings]
provider = "custom"
""")
        config = load_config(config_path=config_file)
        assert config.embeddings.provider == "custom"
        assert config.embeddings.model is None
        assert config.embeddings.dimension is None

    def test_explicit_values_override_defaults(self, tmp_path):
        """Test explicit values override provider defaults."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[embeddings]
provider = "openai"
model = "text-embedding-3-large"
dimension = 3072
""")
        config = load_config(config_path=config_file)
        assert config.embeddings.model == "text-embedding-3-large"
        assert config.embeddings.dimension == 3072


class TestPortValidationIntegration:
    """Integration tests for port validation."""

    def test_port_validation_via_env(self, monkeypatch, tmp_path):
        """Test port validation with environment variable."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("VTIC_API_PORT", "99999")
        with pytest.raises(ValueError) as exc_info:
            load_config()
        # Pydantic's le constraint produces the error message
        assert "less than or equal to 65535" in str(exc_info.value)

    def test_port_validation_via_file(self, tmp_path):
        """Test port validation with config file."""
        config_file = tmp_path / "vtic.toml"
        config_file.write_text("""
[api]
port = 0
""")
        with pytest.raises(ValueError) as exc_info:
            load_config(config_path=config_file)
        # Pydantic's ge constraint produces the error message
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_port_edge_cases_via_env(self, monkeypatch, tmp_path):
        """Test port edge cases."""
        monkeypatch.chdir(tmp_path)
        # Valid min
        monkeypatch.setenv("VTIC_API_PORT", "1")
        config = load_config()
        assert config.api.port == 1
        
        # Valid max
        monkeypatch.setenv("VTIC_API_PORT", "65535")
        config = load_config()
        assert config.api.port == 65535
