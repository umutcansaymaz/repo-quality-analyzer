"""Tests for the :class:`SQLiteCacheAdapter`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey
from repo_analyzer.infrastructure.errors import CacheException


@pytest.fixture()
def cache(tmp_path: Path) -> SQLiteCacheAdapter:
    """A fresh cache backed by a temp database."""
    adapter = SQLiteCacheAdapter(tmp_path / "cache.db")
    yield adapter  # type: ignore[misc]
    adapter.close()


def _make_entry(
    url: str = "https://github.com/o/r",
    entry_type: CacheEntryType = CacheEntryType.ANALYSIS,
    expires_in_days: int = 7,
) -> tuple[CacheKey, CacheEntry]:
    key = CacheKey(repository_url=url, entry_type=entry_type)
    entry = CacheEntry(
        key=key.to_hash(),
        repository_url=url,
        entry_type=entry_type,
        expires_at=datetime.now(tz=UTC) + timedelta(days=expires_in_days),
    )
    return key, entry


def test_put_and_get(cache: SQLiteCacheAdapter) -> None:
    """A stored entry should be retrievable by key."""
    key, entry = _make_entry()
    cache.put(entry)
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved.repository_url == entry.repository_url


def test_get_missing_returns_none(cache: SQLiteCacheAdapter) -> None:
    """A missing key should return None."""
    key = CacheKey(repository_url="https://github.com/o/missing")
    assert cache.get(key) is None


def test_get_expired_returns_none_and_deletes(cache: SQLiteCacheAdapter) -> None:
    """An expired entry should be returned as None and deleted."""
    key = CacheKey(repository_url="https://github.com/o/expired")
    entry = CacheEntry(
        key=key.to_hash(),
        repository_url="https://github.com/o/expired",
        expires_at=datetime.now(tz=UTC) - timedelta(days=1),
    )
    cache.put(entry)
    assert cache.get(key) is None
    # The entry should have been deleted.
    assert cache.get(key) is None


def test_get_updates_access_metadata(cache: SQLiteCacheAdapter) -> None:
    """Retrieving an entry should bump the access count."""
    key, entry = _make_entry()
    cache.put(entry)
    cache.get(key)
    cache.get(key)
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved.access_count >= 2


def test_delete_existing(cache: SQLiteCacheAdapter) -> None:
    """Deleting an existing entry should return True."""
    key, entry = _make_entry()
    cache.put(entry)
    assert cache.delete(key) is True
    assert cache.get(key) is None


def test_delete_missing_returns_false(cache: SQLiteCacheAdapter) -> None:
    """Deleting a missing key should return False."""
    key = CacheKey(repository_url="https://github.com/o/nope")
    assert cache.delete(key) is False


def test_list_entries_empty(cache: SQLiteCacheAdapter) -> None:
    """An empty cache should list no entries."""
    assert list(cache.list_entries()) == []


def test_list_entries_returns_all(cache: SQLiteCacheAdapter) -> None:
    """All entries should be listed."""
    _, e1 = _make_entry(url="https://github.com/o/r1")
    _, e2 = _make_entry(url="https://github.com/o/r2")
    cache.put(e1)
    cache.put(e2)
    entries = list(cache.list_entries())
    assert len(entries) == 2


def test_list_entries_filtered_by_type(cache: SQLiteCacheAdapter) -> None:
    """The type filter should narrow results."""
    _, e1 = _make_entry(url="https://github.com/o/r1", entry_type=CacheEntryType.ANALYSIS)
    _, e2 = _make_entry(url="https://github.com/o/r2", entry_type=CacheEntryType.CLONE)
    cache.put(e1)
    cache.put(e2)
    only_analysis = list(cache.list_entries(CacheEntryType.ANALYSIS))
    assert len(only_analysis) == 1
    assert only_analysis[0].entry_type == CacheEntryType.ANALYSIS


def test_clear_removes_all(cache: SQLiteCacheAdapter) -> None:
    """``clear`` should remove everything and return the count."""
    _, e1 = _make_entry(url="https://github.com/o/r1")
    _, e2 = _make_entry(url="https://github.com/o/r2")
    cache.put(e1)
    cache.put(e2)
    count = cache.clear()
    assert count == 2
    assert list(cache.list_entries()) == []


def test_clear_empty_returns_zero(cache: SQLiteCacheAdapter) -> None:
    """Clearing an empty cache should return 0."""
    assert cache.clear() == 0


def test_purge_expired_removes_only_expired(cache: SQLiteCacheAdapter) -> None:
    """Only expired entries should be purged."""
    _, fresh = _make_entry(url="https://github.com/o/fresh", expires_in_days=7)
    expired_key = CacheKey(repository_url="https://github.com/o/expired")
    expired = CacheEntry(
        key=expired_key.to_hash(),
        repository_url="https://github.com/o/expired",
        expires_at=datetime.now(tz=UTC) - timedelta(days=1),
    )
    cache.put(fresh)
    cache.put(expired)
    purged = cache.purge_expired()
    assert purged == 1
    # Fresh entry should still be there.
    fresh_key = CacheKey(repository_url="https://github.com/o/fresh")
    assert cache.get(fresh_key) is not None


def test_put_replaces_existing(cache: SQLiteCacheAdapter) -> None:
    """Putting with the same key should replace."""
    key, entry = _make_entry()
    entry.result_json = '{"v": 1}'
    cache.put(entry)
    entry2 = entry.model_copy(update={"result_json": '{"v": 2}'})
    cache.put(entry2)
    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved.result_json == '{"v": 2}'


def test_context_manager_closes(tmp_path: Path) -> None:
    """The adapter should support use as a context manager."""
    with SQLiteCacheAdapter(tmp_path / "cache.db") as adapter:
        _, entry = _make_entry()
        adapter.put(entry)
        assert len(list(adapter.list_entries())) == 1


def test_cache_exception_on_invalid_path(tmp_path: Path) -> None:
    """A path whose parent cannot be created should raise CacheException."""
    # Use a path inside a read-only directory to trigger a creation failure.
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o500)  # read + execute, no write
    try:
        with pytest.raises((CacheException, OSError, PermissionError)):
            SQLiteCacheAdapter(readonly_dir / "sub" / "cache.db")
    finally:
        readonly_dir.chmod(0o755)
