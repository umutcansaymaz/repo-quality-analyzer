"""File-system scanner analyzer.

Walks the repository working tree and produces a :class:`FileInventory`:
file/directory counts, total bytes, empty/binary/generated/duplicate/symlink
/hidden files, extension distribution and the largest files/directories.

The scanner respects ``.gitignore`` rules (when ``pathspec`` is available)
and skips the ``.git`` directory. It uses streaming iteration so that very
large repositories do not exhaust memory.
"""

from __future__ import annotations

import hashlib
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import FileInventory
from repo_analyzer.core.domain.repository import Repository

#: Extensions considered "generated" files (not hand-written).
_GENERATED_EXTENSIONS = frozenset(
    {
        "pyc",
        "pyo",
        "pyd",
        "class",
        "o",
        "obj",
        "so",
        "dll",
        "exe",
        "lock",
        "map",
    }
)

#: Files commonly produced by build tools / generators.
_GENERATED_FILENAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "Cargo.lock",
        "go.sum",
        "composer.lock",
        "Gemfile.lock",
        "poetry.lock",
        "uv.lock",
    }
)

#: First bytes that indicate a binary file.
_BINARY_THRESHOLD = 0.30  # 30% non-text bytes → binary


class FilesystemAnalyzer(BaseAnalyzer):
    """Scan the working tree and build a :class:`FileInventory`."""

    _analyzer_name = "filesystem"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 0

    def __init__(self, *, max_file_size_bytes: int = 50 * 1024 * 1024) -> None:
        super().__init__()
        self._max_file_size = max_file_size_bytes

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run the scan and return a serialized :class:`FileInventory`."""
        inventory = FileInventory()
        size_by_dir: dict[str, int] = defaultdict(int)
        file_hashes: dict[str, list[str]] = defaultdict(list)

        for root, dirs, files in self._walk(workspace):
            rel_root = self._rel(root, workspace)
            if rel_root != ".":
                inventory.add_directory()
            for name in files:
                file_path = root / name
                try:
                    size = file_path.stat().st_size
                except OSError:
                    continue
                inventory.add_file(file_path.relative_to(workspace), size)
                size_by_dir[rel_root] += size
                # Track hidden / symlink / binary / generated.
                if name.startswith("."):
                    inventory.hidden_files += 1
                if file_path.is_symlink():
                    inventory.symlinks += 1
                if self._is_generated(name):
                    inventory.generated_files += 1
                if size > 0 and self._is_binary(file_path):
                    inventory.binary_files += 1
                # Duplicate detection (only for small-ish text files).
                if 0 < size <= self._max_file_size and not self._is_binary_fast(file_path, size):
                    digest = self._hash_file(file_path)
                    if digest:
                        file_hashes[digest].append(str(file_path.relative_to(workspace)))

        # Largest directories.
        inventory.largest_directories = sorted(
            size_by_dir.items(), key=lambda kv: kv[1], reverse=True
        )[:20]
        # Largest files.
        largest = sorted(
            ((f, self._safe_size(workspace / f)) for f in inventory.files),
            key=lambda kv: kv[1],
            reverse=True,
        )[:20]
        inventory.largest_files = [(p, s) for p, s in largest if s > 0]
        # Duplicate groups.
        inventory.duplicate_groups = [
            (h, paths) for h, paths in file_hashes.items() if len(paths) > 1
        ]
        inventory.duplicate_files = sum(len(paths) for _, paths in inventory.duplicate_groups)
        return {"file_inventory": inventory.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _walk(self, workspace: Path):  # type: ignore[no-untyped-def]
        """Walk the workspace, skipping ``.git`` and respecting gitignore."""
        gitignore = workspace / ".gitignore"
        patterns: list[str] = []
        if gitignore.exists():
            try:
                patterns = [
                    line.strip()
                    for line in gitignore.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.strip() and not line.startswith("#")
                ]
            except OSError:
                patterns = []
        for root, dirs, files in os.walk(workspace):
            # Skip .git in-place.
            if ".git" in dirs:
                dirs.remove(".git")
            # Apply gitignore-like filtering on directories.
            dirs[:] = [d for d in dirs if not self._is_ignored(d, patterns)]
            files = [f for f in files if not self._is_ignored(f, patterns)]
            yield Path(root), dirs, files

    @staticmethod
    def _is_ignored(name: str, patterns: list[str]) -> bool:
        """Naive gitignore match (exact / suffix)."""
        for pat in patterns:
            if pat == name:
                return True
            if pat.startswith("*"):
                if name.endswith(pat[1:]):
                    return True
            if pat.endswith("/"):
                if name == pat[:-1]:
                    return True
        return False

    @staticmethod
    def _rel(path: Path, base: Path) -> str:
        try:
            return str(path.relative_to(base))
        except ValueError:
            return str(path)

    @staticmethod
    def _is_generated(name: str) -> bool:
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        return ext in _GENERATED_EXTENSIONS or name in _GENERATED_FILENAMES

    @staticmethod
    def _is_binary_fast(path: Path, size: int) -> bool:
        """Quick binary check based on extension."""
        ext = path.suffix.lower().lstrip(".")
        return ext in _GENERATED_EXTENSIONS

    def _is_binary(self, path: Path) -> bool:
        """Heuristic: read first 8KB and check for null bytes / non-text ratio."""
        try:
            with path.open("rb") as handle:
                chunk = handle.read(8192)
        except OSError:
            return False
        if not chunk:
            return False
        if b"\x00" in chunk:
            return True
        non_text = sum(1 for b in chunk if b < 9 or (13 < b < 32 and b != 10))
        return (non_text / len(chunk)) > _BINARY_THRESHOLD

    @staticmethod
    def _hash_file(path: Path) -> str | None:
        """Return the SHA-256 of a small file, or ``None`` on error."""
        try:
            hasher = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(65536), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except OSError:
            return None

    @staticmethod
    def _safe_size(path: Path) -> int:
        try:
            return path.stat().st_size
        except OSError:
            return 0


__all__ = ["FilesystemAnalyzer"]
