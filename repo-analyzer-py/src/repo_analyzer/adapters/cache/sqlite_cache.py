"""SQLite-backed cache adapter implementing :class:`CachePort`.

The cache stores metadata in a single ``cache_entries`` table. Repository
clone artifacts are stored on the filesystem (paths referenced from the
table). Analysis results are serialized to JSON in the ``result_json``
column.

This is infrastructure scaffolding: every CRUD operation is fully functional,
but no repository is actually cloned at this stage.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey
from repo_analyzer.core.ports.cache_port import CachePort
from repo_analyzer.infrastructure.errors import CacheException
from repo_analyzer.utils.path import expand_user_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS cache_entries (
    key TEXT PRIMARY KEY,
    repository_url TEXT NOT NULL,
    commit_sha TEXT,
    entry_type TEXT NOT NULL,
    workspace_path TEXT,
    result_json TEXT,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    last_accessed_at TEXT NOT NULL,
    access_count INTEGER NOT NULL DEFAULT 0,
    metadata TEXT
);
CREATE INDEX IF NOT EXISTS idx_cache_entries_type ON cache_entries(entry_type);
CREATE INDEX IF NOT EXISTS idx_cache_entries_expires ON cache_entries(expires_at);
CREATE INDEX IF NOT EXISTS idx_cache_entries_last_access ON cache_entries(last_accessed_at);
"""


def _iso(value: datetime) -> str:
    """Return an ISO-8601 string for ``value``."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _parse_iso(value: str) -> datetime:
    """Parse an ISO-8601 string into an aware :class:`~datetime.datetime`."""
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


class SQLiteCacheAdapter(CachePort):
    """A thread-safe SQLite cache adapter.

    The database file is created on demand. All operations are serialized
    through a re-entrant lock to support concurrent CLI invocations on the
    same database.
    """

    def __init__(self, database_path: str | Path) -> None:
        """Initialize the adapter.

        Args:
            database_path: Path to the SQLite database file. Parent
                directories are created automatically.
        """
        self._db_path = expand_user_path(database_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        # Enforce 0700 on the cache directory to protect cached artifacts.
        try:
            self._db_path.parent.chmod(0o700)
        except OSError:
            pass
        self._lock = threading.RLock()
        self._local = threading.local()
        # Create the schema using a one-shot connection.
        conn = self._connect()
        try:
            self._init_schema(conn)
        finally:
            conn.close()
        # Restrict the database file to owner-only access.
        try:
            os.chmod(self._db_path, 0o600)
        except OSError:
            pass

    # ----- connection management -------------------------------------------------
    def _get_conn(self) -> sqlite3.Connection:
        """Return a thread-local connection.

        Each thread gets its own connection so that SQLite's threading
        constraints are respected without serializing all access through a
        single connection.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = self._connect()
            self._local.conn = conn
        return conn

    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=True,
                isolation_level=None,  # autocommit
                timeout=30.0,
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            return conn
        except sqlite3.Error as exc:
            raise CacheException(
                f"Failed to open cache database: {exc}",
                context={"path": str(self._db_path)},
            ) from exc

    def _init_schema(self, conn: sqlite3.Connection) -> None:
        try:
            conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise CacheException(
                f"Failed to initialize cache schema: {exc}",
                context={"path": str(self._db_path)},
            ) from exc

    # ----- row mapping -----------------------------------------------------------
    def _row_to_entry(self, row: sqlite3.Row) -> CacheEntry:
        metadata: dict[str, Any] = {}
        raw_meta = row["metadata"]
        if raw_meta:
            try:
                metadata = json.loads(raw_meta)
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        return CacheEntry(
            key=row["key"],
            repository_url=row["repository_url"],
            commit_sha=row["commit_sha"],
            entry_type=CacheEntryType(row["entry_type"]),
            workspace_path=row["workspace_path"],
            result_json=row["result_json"],
            size_bytes=row["size_bytes"],
            created_at=_parse_iso(row["created_at"]),
            expires_at=_parse_iso(row["expires_at"]),
            last_accessed_at=_parse_iso(row["last_accessed_at"]),
            access_count=row["access_count"],
            metadata=metadata,
        )

    # ----- CachePort implementation ----------------------------------------------
    def get(self, key: CacheKey) -> CacheEntry | None:
        """Look up an entry by key and update its access metadata.

        Returns ``None`` if the entry is missing or expired (expired entries
        are also deleted as a side effect).
        """
        key_hash = key.to_hash()
        with self._lock:
            try:
                cursor = self._get_conn().execute(
                    "SELECT * FROM cache_entries WHERE key = ?", (key_hash,)
                )
                row = cursor.fetchone()
            except sqlite3.Error as exc:
                raise CacheException(
                    f"Cache read failed: {exc}",
                    cache_key=key_hash,
                ) from exc
            if row is None:
                return None
            entry = self._row_to_entry(row)
            if entry.is_expired:
                self._delete_by_key(key_hash)
                return None
            # Update access metadata.
            now = _iso(datetime.now(tz=UTC))
            try:
                self._get_conn().execute(
                    "UPDATE cache_entries SET last_accessed_at = ?, "
                    "access_count = access_count + 1 WHERE key = ?",
                    (now, key_hash),
                )
            except sqlite3.Error:
                # Non-fatal: the entry is still valid.
                pass
            entry.touch()
            return entry

    def put(self, entry: CacheEntry) -> CacheEntry:
        """Insert or replace an entry."""
        with self._lock:
            try:
                self._get_conn().execute(
                    """
                    INSERT OR REPLACE INTO cache_entries
                    (key, repository_url, commit_sha, entry_type, workspace_path,
                     result_json, size_bytes, created_at, expires_at,
                     last_accessed_at, access_count, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        entry.key,
                        entry.repository_url,
                        entry.commit_sha,
                        entry.entry_type.value,
                        entry.workspace_path,
                        entry.result_json,
                        entry.size_bytes,
                        _iso(entry.created_at),
                        _iso(entry.expires_at),
                        _iso(entry.last_accessed_at),
                        entry.access_count,
                        json.dumps(entry.metadata, default=str),
                    ),
                )
            except sqlite3.Error as exc:
                raise CacheException(
                    f"Cache write failed: {exc}",
                    cache_key=entry.key,
                ) from exc
            return entry

    def delete(self, key: CacheKey) -> bool:
        """Delete the entry identified by ``key``."""
        return self._delete_by_key(key.to_hash())

    def _delete_by_key(self, key_hash: str) -> bool:
        with self._lock:
            try:
                cursor = self._get_conn().execute(
                    "DELETE FROM cache_entries WHERE key = ?", (key_hash,)
                )
            except sqlite3.Error as exc:
                raise CacheException(
                    f"Cache delete failed: {exc}",
                    cache_key=key_hash,
                ) from exc
            return cursor.rowcount > 0

    def list_entries(self, entry_type: CacheEntryType | None = None) -> Sequence[CacheEntry]:
        """List entries, optionally filtered by type."""
        with self._lock:
            if entry_type is None:
                cursor = self._get_conn().execute(
                    "SELECT * FROM cache_entries ORDER BY last_accessed_at DESC"
                )
            else:
                cursor = self._get_conn().execute(
                    "SELECT * FROM cache_entries WHERE entry_type = ? "
                    "ORDER BY last_accessed_at DESC",
                    (entry_type.value,),
                )
            rows = cursor.fetchall()
        return [self._row_to_entry(row) for row in rows]

    def clear(self) -> int:
        """Remove all entries and return the count deleted."""
        with self._lock:
            try:
                cursor = self._get_conn().execute("SELECT COUNT(*) FROM cache_entries")
                count = int(cursor.fetchone()[0])
                self._get_conn().execute("DELETE FROM cache_entries")
            except sqlite3.Error as exc:
                raise CacheException(f"Cache clear failed: {exc}") from exc
            return count

    def purge_expired(self) -> int:
        """Delete all expired entries."""
        now = _iso(datetime.now(tz=UTC))
        with self._lock:
            try:
                cursor = self._get_conn().execute(
                    "DELETE FROM cache_entries WHERE expires_at < ?", (now,)
                )
            except sqlite3.Error as exc:
                raise CacheException(f"Cache purge failed: {exc}") from exc
            return cursor.rowcount

    def close(self) -> None:
        """Close the thread-local database connection (if open)."""
        with self._lock:
            conn = getattr(self._local, "conn", None)
            if conn is not None:
                try:
                    conn.close()
                except sqlite3.Error:  # pragma: no cover - defensive
                    pass
                self._local.conn = None

    # ----- context manager support ----------------------------------------------
    def __enter__(self) -> SQLiteCacheAdapter:
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self.close()


__all__ = ["SQLiteCacheAdapter"]
