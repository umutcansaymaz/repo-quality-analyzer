"""Filesystem path utilities."""

from __future__ import annotations

import contextlib
import os
import tempfile
from collections.abc import Iterator
from pathlib import Path


def expand_user_path(path: str | Path) -> Path:
    """Expand ``~`` and environment variables in a path.

    Args:
        path: A path possibly containing ``~`` or ``$VAR`` references.

    Returns:
        An absolute :class:`~pathlib.Path`.
    """
    return Path(os.path.expandvars(os.path.expanduser(str(path)))).resolve(strict=False)


def normalize_path(path: str | Path) -> Path:
    """Normalize a path by expanding the user, resolving ``.``/``..`` and
    collapsing redundant separators.

    Unlike :meth:`Path.resolve`, this does **not** require the path to exist.
    """
    expanded = os.path.expanduser(os.path.expandvars(str(path)))
    return Path(os.path.normpath(expanded))


def repo_cache_dir(base_dir: str | Path, repo_url: str) -> Path:
    """Compute a stable cache directory for a repository URL.

    The directory name is a short hash of the normalized URL so that the same
    repository always maps to the same path.

    Args:
        base_dir: The cache root directory.
        repo_url: The repository URL (any form).

    Returns:
        A :class:`~pathlib.Path` under ``base_dir`` unique to the repository.
    """
    import hashlib

    normalized = repo_url.strip().rstrip("/")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    return Path(base_dir) / digest


@contextlib.contextmanager
def temp_directory(prefix: str = "repo-analyzer-") -> Iterator[Path]:
    """Context manager that creates a temporary directory and removes it on exit.

    Args:
        prefix: Filename prefix for the temporary directory.

    Yields:
        The :class:`~pathlib.Path` to the created directory.
    """
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    try:
        yield tmp
    finally:
        import shutil

        shutil.rmtree(tmp, ignore_errors=True)


__all__ = [
    "expand_user_path",
    "normalize_path",
    "repo_cache_dir",
    "temp_directory",
]
