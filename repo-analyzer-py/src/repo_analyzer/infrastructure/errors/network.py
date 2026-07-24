"""Network-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import TransientError


class NetworkException(TransientError):
    """A network operation failed (timeout, connection reset...).

    Transient: retrying with backoff may succeed.
    """

    code = "GRA_NET_001"
    default_message = "Network operation failed."
    retryable = True

    def __init__(
        self,
        message: str | None = None,
        *,
        url: str | None = None,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if url:
            ctx["url"] = url
        if status_code is not None:
            ctx["status_code"] = status_code
        super().__init__(message, context=ctx, **kwargs)
        self.url = url
        self.status_code = status_code


class RateLimitException(NetworkException):
    """The remote host returned a rate-limit response."""

    code = "GRA_NET_002"
    default_message = "Rate limit exceeded."

    def __init__(
        self,
        message: str | None = None,
        *,
        retry_after: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ConnectionTimeoutException(NetworkException):
    """A connection timed out."""

    code = "GRA_NET_003"
    default_message = "Connection timed out."


__all__ = [
    "ConnectionTimeoutException",
    "NetworkException",
    "RateLimitException",
]
