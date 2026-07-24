"""Repository / VCS exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import (
    FatalError,
    RecoverableError,
    TransientError,
)


class RepositoryException(RecoverableError):
    """A repository operation failed (clone, fetch, resolve...)."""

    code = "GRA_REPO_001"
    default_message = "Repository operation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        repository: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if repository:
            ctx["repository"] = repository
        super().__init__(message, context=ctx, **kwargs)
        self.repository = repository


class RepositoryCloneException(RepositoryException, TransientError):
    """Cloning the repository failed (network or disk)."""

    code = "GRA_REPO_002"
    default_message = "Failed to clone repository."
    retryable = True


class AuthenticationException(FatalError):
    """Authentication against the VCS host failed.

    This is fatal because retrying with the same credentials will not help.
    """

    code = "GRA_REPO_003"
    default_message = "Authentication failed. Check your credentials."

    def __init__(
        self,
        message: str | None = None,
        *,
        host: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if host:
            ctx["host"] = host
        super().__init__(message, context=ctx, **kwargs)
        self.host = host


class RepositoryNotFoundException(RepositoryException):
    """The repository does not exist or is not accessible."""

    code = "GRA_REPO_004"
    default_message = "Repository not found or inaccessible."


class RepositoryTimeoutException(RepositoryException, TransientError):
    """A repository operation timed out."""

    code = "GRA_REPO_005"
    default_message = "Repository operation timed out."
    retryable = True


__all__ = [
    "AuthenticationException",
    "RepositoryCloneException",
    "RepositoryException",
    "RepositoryNotFoundException",
    "RepositoryTimeoutException",
]
