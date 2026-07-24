"""Configuration-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import FatalError


class ConfigurationException(FatalError):
    """Configuration is invalid or missing.

    Fatal: the application cannot start with an invalid configuration.
    """

    code = "GRA_CFG_001"
    default_message = "Configuration error."

    def __init__(
        self,
        message: str | None = None,
        *,
        field: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if field:
            ctx["field"] = field
        super().__init__(message, context=ctx, **kwargs)
        self.field = field


# Backwards/alias-compatible name used throughout the SDD.
ConfigurationError = ConfigurationException


class ConfigFileNotFoundException(ConfigurationException):
    """The specified config file does not exist."""

    code = "GRA_CFG_002"
    default_message = "Configuration file not found."


class ConfigValidationException(ConfigurationException):
    """Configuration failed schema validation."""

    code = "GRA_CFG_003"
    default_message = "Configuration validation failed."


__all__ = [
    "ConfigFileNotFoundException",
    "ConfigValidationException",
    "ConfigurationError",
    "ConfigurationException",
]
