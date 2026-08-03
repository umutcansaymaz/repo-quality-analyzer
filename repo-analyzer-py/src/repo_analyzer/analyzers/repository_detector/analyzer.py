"""Repository detector analyzer.

Reads repository metadata from the working tree and git history:

- Name, owner, description (from README / git remote).
- Stars / forks (only available via API — left as ``None`` for local clones).
- Contributors (from git log authors).
- Default branch, tags, releases.
- License (LICENSE file detection).
- README path.
- Primary language (from language distribution if available).
- Repository size (bytes on disk).
- Last commit SHA + date.
- Total branches, total commits.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import RepositoryMetadata
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class RepositoryDetector(BaseAnalyzer):
    """Detect repository metadata from a cloned working tree."""

    _analyzer_name = "repository-detector"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 0

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run detection and return a :class:`RepositoryMetadata`."""
        meta = RepositoryMetadata(
            name=repository.name,
            owner=repository.owner,
            description=self._read_description(workspace),
            contributors=self._git_contributors(workspace),
            default_branch=self._git_default_branch(workspace),
            tags=self._git_tags(workspace),
            releases=self._git_tags(workspace)[:10],
            license=self._detect_license(workspace),
            readme_path=self._find_readme(workspace),
            primary_language=None,
            size_bytes=self._dir_size(workspace),
            last_commit_sha=self._git_last_commit_sha(workspace),
            last_commit_date=self._git_last_commit_date(workspace),
            total_branches=self._git_branch_count(workspace),
            total_commits=self._git_commit_count(workspace),
        )
        return {"repository_metadata": meta.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    @staticmethod
    def _read_description(workspace: Path) -> str | None:
        """Read the first paragraph of the README as a description."""
        for name in ("README.md", "README.rst", "README.txt", "README"):
            path = workspace / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped and not stripped.startswith("#") and not stripped.startswith("="):
                        return stripped[:200]
        return None

    @staticmethod
    def _git_contributors(workspace: Path) -> list[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "shortlog", "-sne", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        if proc.returncode != 0:
            return []
        contributors: list[str] = []
        for line in proc.stdout.splitlines():
            parts = line.strip().split("\t", 1)
            if len(parts) == 2:
                contributors.append(parts[1].strip())
        return contributors[:50]

    @staticmethod
    def _git_default_branch(workspace: Path) -> str | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "symbolic-ref", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        return "main"

    @staticmethod
    def _git_tags(workspace: Path) -> list[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "tag", "--list"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        if proc.returncode != 0:
            return []
        return [t.strip() for t in proc.stdout.splitlines() if t.strip()][:50]

    @staticmethod
    def _detect_license(workspace: Path) -> str | None:
        for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"):
            path = workspace / name
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if "MIT License" in content:
                    return "MIT"
                if "Apache License" in content:
                    return "Apache-2.0"
                if "GNU GENERAL PUBLIC LICENSE" in content:
                    return "GPL-3.0"
                if "BSD" in content:
                    return "BSD"
                return "Other"
        return None

    @staticmethod
    def _find_readme(workspace: Path) -> str | None:
        for name in ("README.md", "README.rst", "README.txt", "README"):
            path = workspace / name
            if path.exists():
                return name
        return None

    @staticmethod
    def _dir_size(workspace: Path) -> int:
        total = 0
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                try:
                    total += os.path.getsize(Path(root) / name)
                except OSError:
                    pass
        return total

    @staticmethod
    def _git_last_commit_sha(workspace: Path) -> str | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if proc.returncode == 0:
            return proc.stdout.strip()
        return None

    @staticmethod
    def _git_last_commit_date(workspace: Path) -> str | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "log", "-1", "--format=%ad", "--date=short"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
        return None

    @staticmethod
    def _git_branch_count(workspace: Path) -> int | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "branch", "--list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if proc.returncode != 0:
            return None
        return len([line for line in proc.stdout.splitlines() if line.strip()])

    @staticmethod
    def _git_commit_count(workspace: Path) -> int | None:
        try:
            proc = subprocess.run(
                ["git", "-C", str(workspace), "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None
        if proc.returncode == 0 and proc.stdout.strip().isdigit():
            return int(proc.stdout.strip())
        return None


__all__ = ["RepositoryDetector"]
