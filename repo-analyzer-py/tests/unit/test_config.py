"""Tests for the configuration system."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyzer.infrastructure.config import Config, load_config
from repo_analyzer.infrastructure.errors import (
    ConfigFileNotFoundException,
    ConfigValidationException,
)


def test_load_config_defaults() -> None:
    """Loading with no overrides should return valid defaults."""
    config = load_config(overrides={"cache": {"dir": "/tmp/test"}})
    assert isinstance(config, Config)
    assert config.log_level == "INFO"
    assert config.cache.enabled is True
    assert config.scoring.weights.security == 0.40


def test_load_config_yaml_file(tmp_path: Path) -> None:
    """A YAML file should override defaults."""
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("log_level: WARNING\ncache:\n  enabled: false\n  dir: /tmp/custom\n")
    config = load_config(config_path=yaml_path)
    assert config.log_level == "WARNING"
    assert config.cache.enabled is False


def test_load_config_env_vars_override_yaml(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Env vars should override YAML values."""
    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text("log_level: WARNING\n")
    monkeypatch.setenv("GRA_LOG_LEVEL", "ERROR")
    config = load_config(config_path=yaml_path)
    assert config.log_level == "ERROR"


def test_load_config_overrides_highest_priority(tmp_path: Path) -> None:
    """Programmatic overrides should win over everything."""
    config = load_config(overrides={"log_level": "DEBUG"})
    assert config.log_level == "DEBUG"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    """An explicit missing config path should raise."""
    with pytest.raises(ConfigFileNotFoundException):
        load_config(config_path=tmp_path / "nope.yaml")


def test_load_config_invalid_yaml_raises(tmp_path: Path) -> None:
    """Invalid YAML should raise ConfigValidationException."""
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text(":\n  - invalid: [")
    with pytest.raises(ConfigValidationException):
        load_config(config_path=yaml_path)


def test_load_config_invalid_log_level_raises() -> None:
    """An invalid log level should raise."""
    with pytest.raises(ConfigValidationException):
        load_config(overrides={"log_level": "BOGUS"})


def test_load_config_debug_forces_debug_level() -> None:
    """Debug mode should force DEBUG log level."""
    config = load_config(overrides={"debug": True, "log_level": "INFO"})
    assert config.log_level == "DEBUG"


def test_load_config_scoring_weights_must_sum_to_one() -> None:
    """Scoring weights not summing to 1.0 should raise a validation error."""
    with pytest.raises(ConfigValidationException):
        load_config(
            overrides={
                "scoring": {
                    "weights": {
                        "security": 0.5,
                        "quality": 0.5,
                        "architecture": 0.5,
                        "test": 0.5,
                    }
                }
            }
        )


def test_load_config_scoring_weights_valid_sums() -> None:
    """Valid scoring weights summing to 1.0 should load."""
    config = load_config(
        overrides={
            "scoring": {
                "weights": {
                    "security": 0.3,
                    "quality": 0.3,
                    "architecture": 0.2,
                    "test": 0.2,
                }
            }
        }
    )
    total = (
        config.scoring.weights.security
        + config.scoring.weights.quality
        + config.scoring.weights.architecture
        + config.scoring.weights.test
    )
    assert abs(total - 1.0) < 0.001


def test_load_config_report_formats_validated() -> None:
    """Invalid report formats should raise."""
    with pytest.raises(ConfigValidationException):
        load_config(overrides={"reports": {"formats": ["bogus"]}})


def test_load_config_report_formats_normalized() -> None:
    """Report formats should be lowercased."""
    config = load_config(overrides={"reports": {"formats": ["MARKDOWN", "JSON"]}})
    assert config.reports.formats == ["markdown", "json"]


def test_load_config_path_expansion() -> None:
    """Tilde paths should be expanded."""
    config = load_config(overrides={"cache": {"dir": "~/test-cache-dir"}})
    assert "~" not in config.cache.dir


def test_config_model_dump() -> None:
    """``model_dump`` should serialize the config."""
    config = load_config(overrides={"cache": {"dir": "/tmp/x"}})
    dumped = config.model_dump(mode="json")
    assert "log_level" in dumped
    assert "cache" in dumped
