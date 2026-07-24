"""Cache-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import RecoverableError


class CacheException(RecoverableError):
    """A cache operation failed (read, write, corruption...).

    Recoverable: the orchestrator can fall back to a cache-less operation.
    """

    code = "GRA_CACHE_001"
    default_message = "Cache operation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        cache_key: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if cache_key:
            ctx["cache_key"] = cache_key
        super().__init__(message, context=ctx, **kwargs)
        self.cache_key = cache_key


class CacheCorruptedException(CacheException):
    """A cache entry failed integrity validation."""

    code = "GRA_CACHE_002"
    default_message = "Cache entry is corrupted."


class CacheExpiredException(CacheException):
    """A cache entry exists but has expired."""

    code = "GRA_CACHE_003"
    default_message = "Cache entry has expired."


__all__ = ["CacheCorruptedException", "CacheException", "CacheExpiredException"]
