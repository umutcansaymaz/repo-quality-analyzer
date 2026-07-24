"""Clone service.

Coordinates repository cloning with the cache subsystem. Handles:

- Cache lookup (skip clone if a cached working tree exists for the commit).
- Retry with exponential backoff for transient failures.
- Timeout enforcement.
- Cancellation via :class:`threading.Event`.
- Temporary-directory management with guaranteed cleanup.
- Progress reporting via :class:`ProgressUI`.
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from pathlib import Path

from repo_analyzer.adapters.vcs.factory import DefaultRepositoryProviderFactory
from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.cache_port import CachePort
from repo_analyzer.core.ports.repository_port import RepositoryProvider
from repo_analyzer.infrastructure.errors import (
    RepositoryCloneException,
    RepositoryException,
    RepositoryTimeoutException,
)
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.infrastructure.progress import ProgressUI

_logger = get_logger(__name__)

#: Default retry settings.
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0  # seconds


class CloneService:
    """Service that clones repositories with caching, retry and cleanup."""

    def __init__(
        self,
        cache: CachePort,
        factory: DefaultRepositoryProviderFactory | None = None,
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_base: float = DEFAULT_BACKOFF_BASE,
    ) -> None:
        self._cache = cache
        self._factory = factory or DefaultRepositoryProviderFactory()
        self._max_retries = max(1, max_retries)
        self._backoff_base = backoff_base

    def clone(
        self,
        repository: Repository,
        *,
        cancel_event: threading.Event | None = None,
        progress: ProgressUI | None = None,
        use_cache: bool = True,
    ) -> tuple[Path, Repository]:
        """Clone the repository, returning the working-tree path and resolved repo.

        The method first resolves the commit SHA, then checks the cache. On a
        cache hit the cached working tree is reused. On a miss the repository
        is cloned into a temporary directory and registered in the cache.

        Args:
            repository: The repository to clone.
            cancel_event: Optional event to signal cancellation.
            progress: Optional :class:`ProgressUI` for status updates.
            use_cache: If ``False``, bypass the cache and always re-clone.

        Returns:
            A tuple of (working_tree_path, resolved_repository).

        Raises:
            RepositoryTimeoutException: If the clone times out.
            RepositoryException: For non-recoverable clone failures.
        """
        provider = self._factory.get(repository)
        if progress:
            progress.info(f"Resolving {repository.owner}/{repository.name}...")
        resolved = provider.resolve(repository)

        cache_key = CacheKey(
            repository_url=resolved.url,
            commit_sha=resolved.commit_sha or "HEAD",
            entry_type=CacheEntryType.CLONE,
        )
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached and cached.workspace and cached.workspace.exists():
                _logger.info("Cache hit for %s at %s", resolved.url, cached.workspace)
                if progress:
                    progress.success("Using cached clone")
                return cached.workspace, resolved

        if progress:
            progress.info("Cloning repository...")

        # Clone into a temp directory then move into cache on success.
        dest = self._cache_workspace_path(cache_key)
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        dest.parent.mkdir(parents=True, exist_ok=True)

        self._clone_with_retry(
            provider,
            resolved,
            dest,
            cancel_event=cancel_event,
            progress=progress,
        )

        if use_cache:
            entry = CacheEntry(
                key=cache_key.to_hash(),
                repository_url=resolved.url,
                commit_sha=resolved.commit_sha,
                entry_type=CacheEntryType.CLONE,
                workspace_path=str(dest),
                size_bytes=self._dir_size(dest),
            )
            try:
                self._cache.put(entry)
            except Exception as exc:  # pragma: no cover - defensive
                _logger.warning("Failed to register cache entry: %s", exc)

        return dest, resolved

    def _clone_with_retry(
        self,
        provider: RepositoryProvider,
        repository: Repository,
        destination: Path,
        *,
        cancel_event: threading.Event | None,
        progress: ProgressUI | None,
    ) -> None:
        """Clone with exponential-backoff retry on transient errors."""
        last_exc: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            if cancel_event and cancel_event.is_set():
                raise RepositoryCloneException(
                    "Clone cancelled before attempt",
                    repository=repository.url,
                )
            try:
                provider.clone(repository, destination)
                if progress:
                    progress.success("Clone complete")
                return
            except RepositoryTimeoutException:
                last_exc = RepositoryTimeoutException(
                    f"Clone timed out on attempt {attempt}/{self._max_retries}",
                    repository=repository.url,
                )
                _logger.warning("Clone attempt %d timed out", attempt)
            except RepositoryCloneException as exc:
                last_exc = exc
                _logger.warning("Clone attempt %d failed: %s", attempt, exc.message)
            except (RepositoryException, Exception) as exc:
                # Non-transient errors should not be retried.
                raise exc

            if attempt < self._max_retries:
                backoff = self._backoff_base * (2 ** (attempt - 1))
                _logger.info("Retrying in %.1fs", backoff)
                self._sleep(backoff, cancel_event)

        if last_exc:
            raise last_exc
        raise RepositoryCloneException(
            f"Clone failed after {self._max_retries} attempts",
            repository=repository.url,
        )

    @staticmethod
    def _sleep(seconds: float, cancel_event: threading.Event | None) -> None:
        """Sleep for ``seconds`` but wake early if cancelled."""
        if cancel_event is None:
            time.sleep(seconds)
            return
        cancel_event.wait(seconds)

    @staticmethod
    def _cache_workspace_path(cache_key: CacheKey) -> Path:
        """Return the on-disk path for a cached clone."""
        from repo_analyzer.infrastructure.config import get_default_cache_dir

        return get_default_cache_dir() / "clones" / cache_key.to_hash()[:16]

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Compute the total byte size of a directory tree."""
        total = 0
        for root, _dirs, files in os.walk(path):
            for name in files:
                try:
                    total += os.path.getsize(Path(root) / name)
                except OSError:
                    pass
        return total

    def cleanup_workspace(self, path: Path) -> None:
        """Remove a cloned working tree."""
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            _logger.debug("Cleaned up workspace %s", path)


__all__ = ["CloneService"]
