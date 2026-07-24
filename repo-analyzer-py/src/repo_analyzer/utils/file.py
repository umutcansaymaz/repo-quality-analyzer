"""File I/O utilities."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

from repo_analyzer.utils.path import expand_user_path


def ensure_directory(path: str | Path, mode: int = 0o755) -> Path:
    """Ensure that a directory exists, creating it (and parents) if needed.

    Args:
        path: Directory path to create.
        mode: Octal permission mode for newly created directories.

    Returns:
        The resolved :class:`~pathlib.Path`.
    """
    resolved = expand_user_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    try:
        resolved.chmod(mode)
    except PermissionError:
        # chmod can fail on some filesystems; the directory still exists.
        pass
    return resolved


def read_text_file(path: str | Path, encoding: str = "utf-8") -> str:
    """Read a text file and return its contents.

    Args:
        path: File to read.
        encoding: Text encoding (default ``utf-8``).

    Returns:
        The file contents as a string.

    Raises:
        FileNotFoundError: If the file does not exist.
        OSError: If reading fails.
    """
    resolved = expand_user_path(path)
    with resolved.open("r", encoding=encoding) as handle:
        return handle.read()


def write_text_file(
    path: str | Path,
    content: str,
    encoding: str = "utf-8",
    *,
    atomic: bool = True,
) -> Path:
    """Write text content to a file.

    Args:
        path: Destination file path.
        content: Text to write.
        encoding: Text encoding (default ``utf-8``).
        atomic: If ``True``, write to a temporary file then rename, to avoid
            leaving a partially written file on failure.

    Returns:
        The resolved :class:`~pathlib.Path`.
    """
    resolved = expand_user_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    if atomic:
        tmp = resolved.with_suffix(resolved.suffix + ".tmp")
        with tmp.open("w", encoding=encoding) as handle:
            handle.write(content)
        os.replace(tmp, resolved)
    else:
        with resolved.open("w", encoding=encoding) as handle:
            handle.write(content)
    return resolved


def safe_remove(path: str | Path) -> bool:
    """Remove a file or directory tree, ignoring missing paths.

    Args:
        path: Path to remove.

    Returns:
        ``True`` if something was removed, ``False`` if the path did not exist.
    """
    resolved = expand_user_path(path)
    if not resolved.exists():
        return False
    if resolved.is_dir():
        shutil.rmtree(resolved, ignore_errors=True)
    else:
        try:
            resolved.unlink()
        except FileNotFoundError:
            return False
    return True


def file_checksum(path: str | Path, algorithm: str = "sha256") -> str:
    """Compute the checksum of a file.

    Args:
        path: File to hash.
        algorithm: Hash algorithm name supported by :mod:`hashlib`.

    Returns:
        The hexadecimal digest.
    """
    resolved = expand_user_path(path)
    hasher = hashlib.new(algorithm)
    with resolved.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


__all__ = [
    "ensure_directory",
    "file_checksum",
    "read_text_file",
    "safe_remove",
    "write_text_file",
]
