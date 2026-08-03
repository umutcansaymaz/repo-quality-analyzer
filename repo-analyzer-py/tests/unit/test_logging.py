"""Tests for the logging infrastructure."""

from __future__ import annotations

import logging
from pathlib import Path

from repo_analyzer.infrastructure.config import load_config
from repo_analyzer.infrastructure.logging import (
    REDUCTED_KEYS,
    configure_logging,
    get_logger,
    redact_sensitive,
)


def test_get_logger_returns_named_logger() -> None:
    """``get_logger`` should return a logger with the expected name."""
    logger = get_logger("repo_analyzer.test")
    assert logger.name == "repo_analyzer.test"


def test_get_logger_default_returns_root_app_logger() -> None:
    """With no name, the application root logger is returned."""
    logger = get_logger()
    assert logger.name == "repo_analyzer"


def test_get_logger_prefixes_non_app_names() -> None:
    """Non-app names should be prefixed."""
    logger = get_logger("foo")
    assert logger.name == "repo_analyzer.foo"


def test_redact_sensitive_replaces_known_keys() -> None:
    """Known sensitive keys should be redacted."""
    data = {"token": "secret", "name": "public"}
    result = redact_sensitive(data)
    assert result["token"] == "***REDACTED***"
    assert result["name"] == "public"


def test_redact_sensitive_handles_nested() -> None:
    """Nested dicts should be redacted recursively."""
    data = {"outer": {"password": "p", "ok": 1}}
    result = redact_sensitive(data)
    assert result["outer"]["password"] == "***REDACTED***"
    assert result["outer"]["ok"] == 1


def test_redact_sensitive_handles_partial_matches() -> None:
    """Partial key matches (e.g. 'api_key') should be redacted."""
    data = {"github_api_key": "ghp_xxx"}
    result = redact_sensitive(data)
    assert result["github_api_key"] == "***REDACTED***"


def test_configure_logging_attaches_handlers(tmp_path: Path) -> None:
    """``configure_logging`` should attach console + file handlers."""
    config = load_config(
        overrides={
            "cache": {"dir": str(tmp_path / "cache")},
            "logging": {"file": str(tmp_path / "ra.log")},
        }
    )
    logger = configure_logging(config)
    assert len(logger.handlers) >= 2


def test_configure_logging_writes_to_file(tmp_path: Path) -> None:
    """Log messages should be written to the configured file."""
    log_file = tmp_path / "ra.log"
    config = load_config(
        overrides={
            "cache": {"dir": str(tmp_path / "cache")},
            "logging": {"file": str(log_file), "level": "DEBUG"},
        }
    )
    logger = configure_logging(config)
    logger.info("test-message-12345")
    # Flush handlers.
    for handler in logger.handlers:
        handler.flush()
    content = log_file.read_text()
    assert "test-message-12345" in content


def test_configure_logging_redacts_sensitive_in_file(tmp_path: Path) -> None:
    """Sensitive values passed as extra should be redacted from the record."""
    log_file = tmp_path / "ra.log"
    config = load_config(
        overrides={
            "cache": {"dir": str(tmp_path / "cache")},
            "logging": {"file": str(log_file), "level": "DEBUG"},
        }
    )
    logger = configure_logging(config)
    # Log with a sensitive extra key; the redaction filter should replace
    # its value on the log record with ***REDACTED***.
    logger.info("authenticating", extra={"token": "super-secret-value"})
    for handler in logger.handlers:
        handler.flush()
    content = log_file.read_text()
    # The secret must never appear in the file.
    assert "super-secret-value" not in content
    # The message itself should still be logged.
    assert "authenticating" in content


def test_redact_sensitive_function_directly() -> None:
    """The ``redact_sensitive`` helper should redact known keys."""
    from repo_analyzer.infrastructure.logging import redact_sensitive

    cleaned = redact_sensitive({"token": "x", "ok": 1})
    assert cleaned["token"] == "***REDACTED***"
    assert cleaned["ok"] == 1


def test_reducted_keys_contains_expected_entries() -> None:
    """The redaction set should include common credential keys."""
    for key in ("token", "password", "secret", "api_key"):
        assert key in REDUCTED_KEYS


def test_configure_logging_console_level_override(tmp_path: Path) -> None:
    """The ``console_level`` argument should override the config level."""
    config = load_config(
        overrides={
            "cache": {"dir": str(tmp_path / "cache")},
            "logging": {"file": str(tmp_path / "ra.log")},
        }
    )
    logger = configure_logging(config, console_level="DEBUG")
    console_handlers = [h for h in logger.handlers if isinstance(h, logging.Handler)]
    assert any(h.level == logging.DEBUG for h in console_handlers)
