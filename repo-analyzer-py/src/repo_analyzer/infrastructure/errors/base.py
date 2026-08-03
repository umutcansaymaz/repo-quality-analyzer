"""Base exception classes and the root of the repo-analyzer exception tree.

This module is intentionally dependency-free so that every other module can
import the base classes without creating circular imports.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class RepoAnalyzerError(Exception):
    """Root exception for all repo-analyzer errors.

    Attributes:
        code: Stable, machine-readable error code (e.g. ``"GRA_CFG_001"``).
        message: Human readable description.
        context: Structured diagnostic key/value pairs.
        cause: Optional chained original exception.
    """

    code: str = "GRA_000"
    default_message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        context: Mapping[str, Any] | None = None,
        cause: BaseException | None = None,
    ) -> None:
        self.message = message if message is not None else self.default_message
        self.code = code if code is not None else self.code
        self.context: dict[str, Any] = dict(context) if context else {}
        self.cause = cause
        formatted = self._format_message()
        super().__init__(formatted)
        if cause is not None:
            self.__cause__ = cause

    def _format_message(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.context:
            ctx = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            parts.append(f" | context: {ctx}")
        return "".join(parts)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the error to a plain dict (for logs / JSON reports)."""
        return {
            "code": self.code,
            "message": self.message,
            "context": self.context,
            "type": type(self).__name__,
            "cause": str(self.cause) if self.cause else None,
        }

    def __repr__(self) -> str:
        return f"{type(self).__name__}(code={self.code!r}, message={self.message!r})"


class FatalError(RepoAnalyzerError):
    """An error from which the application cannot recover.

    The process should abort with a non-zero exit code.
    """

    code = "GRA_FATAL"
    default_message = "A fatal error occurred; the operation cannot continue."


class RecoverableError(RepoAnalyzerError):
    """An error that affects only part of the operation.

    The orchestrator should log the error, skip the affected component and
    continue with the remaining work.
    """

    code = "GRA_RECOVERABLE"
    default_message = "A recoverable error occurred; the operation can continue."


class TransientError(RepoAnalyzerError):
    """A transient error that may succeed on retry (network, rate limit...)."""

    code = "GRA_TRANSIENT"
    default_message = "A transient error occurred; retry may succeed."
    retryable: bool = True


__all__ = [
    "FatalError",
    "RecoverableError",
    "RepoAnalyzerError",
    "TransientError",
]
