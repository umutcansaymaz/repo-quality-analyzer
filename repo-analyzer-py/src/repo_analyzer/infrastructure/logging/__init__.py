"""Structured logging infrastructure for repo-analyzer.

Provides:

- A :class:`RichConsoleHandler` for colorful terminal output.
- A :class:`RotatingFileHandler` (via stdlib) for persistent file logs.
- :func:`configure_logging` to wire everything up from a :class:`Config`.
- :func:`get_logger` to obtain a configured logger anywhere in the codebase.
- Sensitive-value redaction so credentials never reach logs.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

from rich.logging import RichHandler

from repo_analyzer.infrastructure.config import Config, LoggingSettings

__all__ = [
    "REDUCTED_KEYS",
    "RichConsoleHandler",
    "RotatingFileHandler",
    "configure_logging",
    "get_logger",
    "redact_sensitive",
]


# Keys whose values are redacted from every log record.
REDUCTED_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "password",
        "passwd",
        "secret",
        "api_key",
        "apikey",
        "authorization",
        "credential",
        "private_key",
        "ssh_key",
        "pat",
        "access_token",
        "refresh_token",
    }
)

_REDACTED = "***REDACTED***"

# Numeric level mapping including a custom TRACE level.
TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self: logging.Logger, msg: str, *args: Any, **kwargs: Any) -> None:
    """Log ``msg`` with the custom TRACE level."""
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, args, **kwargs)


# Attach once to the Logger class.
if not hasattr(logging.Logger, "trace"):  # pragma: no cover - guard
    logging.Logger.trace = _trace  # type: ignore[attr-defined]


def redact_sensitive(record_dict: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of ``record_dict`` with sensitive values redacted.

    Args:
        record_dict: The ``extra`` dict attached to a log record.

    Returns:
        A new dict where any key in :data:`REDUCTED_KEYS` has its value
        replaced with ``"***REDACTED***"``.
    """
    cleaned: dict[str, Any] = {}
    for key, value in record_dict.items():
        lowered = key.lower()
        if lowered in REDUCTED_KEYS or any(s in lowered for s in REDUCTED_KEYS):
            cleaned[key] = _REDACTED
        elif isinstance(value, dict):
            cleaned[key] = redact_sensitive(value)
        else:
            cleaned[key] = value
    return cleaned


class _RedactingFilter(logging.Filter):
    """Logging filter that redacts sensitive keys from ``record.__dict__``."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Redact the message args if present.
        if isinstance(record.msg, str) and record.args:
            try:
                if isinstance(record.args, dict):
                    record.args = redact_sensitive(dict(record.args))
            except Exception:  # pragma: no cover - defensive
                pass
        # Redact extra fields.
        for key in list(record.__dict__.keys()):
            if key.lower() in REDUCTED_KEYS:
                record.__dict__[key] = _REDACTED
        return True


class RichConsoleHandler(RichHandler):
    """A :class:`rich.logging.RichHandler` pre-configured for repo-analyzer.

    Shows timestamps, log level and the logger name with color.
    """

    def __init__(self, *, show_time: bool = True, show_path: bool = False) -> None:
        super().__init__(
            show_time=show_time,
            show_path=show_path,
            rich_tracebacks=True,
            markup=True,
            tracebacks_show_locals=False,
        )
        self.addFilter(_RedactingFilter())


def _level_for(name: str) -> int:
    """Translate a level name (incl. ``TRACE``) to its numeric value."""
    upper = name.upper()
    if upper == "TRACE":
        return TRACE_LEVEL
    level = logging.getLevelName(upper)
    return int(level)


def configure_logging(
    config: Config,
    *,
    console_level: str | None = None,
    extra_logger_name: str | None = None,
) -> logging.Logger:
    """Configure root + ``repo_analyzer`` loggers from a :class:`Config`.

    Sets up:

    - A :class:`RichConsoleHandler` on the console (level from
      ``config.log_level`` or ``console_level``).
    - A :class:`RotatingFileHandler` on ``config.logging.file`` (level from
      ``config.logging.level``).

    Args:
        config: The resolved application configuration.
        console_level: Optional override for the console handler level.
        extra_logger_name: Optional name of an additional logger to configure
            (defaults to the ``repo_analyzer`` package logger).

    Returns:
        The configured application logger.
    """
    root = logging.getLogger()
    # Reset handlers so repeated calls (e.g. in tests) don't accumulate.
    for handler in list(root.handlers):
        root.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass
    root.setLevel(logging.DEBUG)  # handlers filter further.

    logger_name = extra_logger_name or "repo_analyzer"
    logger = logging.getLogger(logger_name)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except Exception:  # pragma: no cover - defensive
            pass
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    # Console handler (Rich).
    console_handler = RichConsoleHandler()
    console_level_value = _level_for(console_level or config.log_level or "INFO")
    console_handler.setLevel(console_level_value)
    logger.addHandler(console_handler)

    # File handler (rotating).
    file_settings: LoggingSettings = config.logging
    try:
        file_path = Path(file_settings.file)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=str(file_path),
            maxBytes=file_settings.rotate_max_bytes,
            backupCount=file_settings.rotate_backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(_level_for(file_settings.level))
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        file_handler.addFilter(_RedactingFilter())
        logger.addHandler(file_handler)
    except OSError:
        # File logging is best-effort; if it fails we still log to console.
        logger.warning("Could not configure file logging at %s", file_settings.file)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger.

    If ``name`` is ``None`` or equals the application root, the shared
    ``repo_analyzer`` logger is returned (already configured by
    :func:`configure_logging`). Otherwise a child logger is returned that
    propagates to the root application logger.

    Args:
        name: Optional logger name (e.g. ``"repo_analyzer.cli"``).

    Returns:
        A :class:`logging.Logger`.
    """
    if not name or name == "repo_analyzer":
        return logging.getLogger("repo_analyzer")
    if name.startswith("repo_analyzer."):
        return logging.getLogger(name)
    return logging.getLogger(f"repo_analyzer.{name}")
