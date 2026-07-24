"""Cache infrastructure for repo-analyzer.

Provides a SQLite-backed :class:`CacheService` implementing the
:class:`CachePort`. The cache stores repository clones (filesystem) and
analysis results (serialized JSON) keyed by a deterministic
:class:`CacheKey`.

Implements the strategy described in ADR-003 of the SDD.
"""

from __future__ import annotations

from repo_analyzer.adapters.cache.sqlite_cache import SQLiteCacheAdapter
from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey
from repo_analyzer.core.ports.cache_port import CachePort

__all__ = [
    "CacheEntry",
    "CacheEntryType",
    "CacheKey",
    "CachePort",
    "SQLiteCacheAdapter",
]
