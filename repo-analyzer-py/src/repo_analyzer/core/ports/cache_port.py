"""Cache port (abstract interface).

The cache port abstracts how repository clones and analysis results are
persisted between runs. Adapters (e.g. :class:`SQLiteCacheAdapter`) implement
this port.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey


class CachePort(ABC):
    """Abstract cache interface (Hexagonal secondary port)."""

    @abstractmethod
    def get(self, key: CacheKey) -> CacheEntry | None:
        """Look up a cache entry by key.

        Args:
            key: The cache key.

        Returns:
            The entry if present and not expired, else ``None``.
        """

    @abstractmethod
    def put(self, entry: CacheEntry) -> CacheEntry:
        """Insert or replace a cache entry.

        Args:
            entry: The entry to store.

        Returns:
            The stored entry (with any auto-generated fields filled in).
        """

    @abstractmethod
    def delete(self, key: CacheKey) -> bool:
        """Delete the entry identified by ``key``.

        Args:
            key: The cache key.

        Returns:
            ``True`` if an entry was deleted, ``False`` if it was absent.
        """

    @abstractmethod
    def list_entries(self, entry_type: CacheEntryType | None = None) -> Sequence[CacheEntry]:
        """List cache entries, optionally filtered by type.

        Args:
            entry_type: Optional entry type filter.

        Returns:
            A sequence of :class:`CacheEntry`.
        """

    @abstractmethod
    def clear(self) -> int:
        """Remove all cache entries.

        Returns:
            The number of entries removed.
        """

    @abstractmethod
    def purge_expired(self) -> int:
        """Remove expired entries.

        Returns:
            The number of entries removed.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the cache (e.g. DB connection)."""


__all__ = ["CachePort"]
