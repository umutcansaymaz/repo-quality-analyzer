"""Security-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import RecoverableError


class SecurityException(RecoverableError):
    """A security-related error (secret handling, plugin trust...).

    Recoverable: typically the affected operation is skipped rather than
    aborting the whole run.
    """

    code = "GRA_SEC_001"
    default_message = "Security violation."

    def __init__(
        self,
        message: str | None = None,
        *,
        category: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if category:
            ctx["category"] = category
        super().__init__(message, context=ctx, **kwargs)
        self.category = category


class CredentialNotFoundException(SecurityException):
    """A required credential was not provided."""

    code = "GRA_SEC_002"
    default_message = "Required credential not found."


class PluginTrustException(SecurityException):
    """An untrusted plugin attempted to execute."""

    code = "GRA_SEC_003"
    default_message = "Untrusted plugin execution blocked."


__all__ = [
    "CredentialNotFoundException",
    "PluginTrustException",
    "SecurityException",
]
