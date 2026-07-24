"""Git-history analyzer.

Inspects the git history of the working tree to find:

- The most frequently changed files (churn).
- The most active directories.
- The most active contributors.
- Commit distribution (by day / by author).
- Hotspot analysis (files with high churn × complexity proxy).
"""

from __future__ import annotations

import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import GitAnalysis
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class GitAnalyzer(BaseAnalyzer):
    """Analyze the git history of a cloned repository."""

    _analyzer_name = "git-history"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 3

    def __init__(self, *, max_commits: int = 1000) -> None:
        super().__init__()
        self._max_commits = max_commits

    def can_run(self, repository: Repository, workspace: Path) -> bool:
        return workspace.is_dir() and (workspace / ".git").exists()

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run git analysis and return a :class:`GitAnalysis`."""
        file_churn: dict[str, int] = defaultdict(int)
        dir_activity: dict[str, int] = defaultdict(int)
        author_commits: dict[str, int] = defaultdict(int)
        commit_by_day: dict[str, int] = defaultdict(int)
        total_commits = 0

        log_lines = self._git_log(workspace)
        for line in log_lines:
            parts = line.split("\t", 2)
            if len(parts) < 3:
                continue
            author, date, files_str = parts
            total_commits += 1
            author_commits[author] += 1
            day = date.split(" ")[0] if date else "unknown"
            commit_by_day[day] += 1
            for file_path in files_str.split("\n"):
                file_path = file_path.strip()
                if not file_path:
                    continue
                file_churn[file_path] += 1
                parent = str(Path(file_path).parent)
                dir_activity[parent] += 1
            if total_commits >= self._max_commits:
                break

        hotspots = self._compute_hotspots(file_churn)
        analysis = GitAnalysis(
            most_changed_files=sorted(file_churn.items(), key=lambda kv: kv[1], reverse=True)[:30],
            most_active_directories=sorted(
                dir_activity.items(), key=lambda kv: kv[1], reverse=True
            )[:20],
            most_active_contributors=sorted(
                author_commits.items(), key=lambda kv: kv[1], reverse=True
            )[:20],
            commit_distribution=dict(commit_by_day),
            hotspots=hotspots[:20],
            total_commits=total_commits,
            total_authors=len(author_commits),
        )
        return {"git_analysis": analysis.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _git_log(self, workspace: Path) -> list[str]:
        """Return git-log lines in ``author<TAB>date<TAB>files`` format."""
        try:
            proc = subprocess.run(
                [
                    "git",
                    "-C",
                    str(workspace),
                    "log",
                    f"-{self._max_commits}",
                    "--name-only",
                    "--format=%an%x09%ad",
                    "--date=short",
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
            _logger.warning("git log failed: %s", exc)
            return []
        if proc.returncode != 0:
            return []
        # Group commits: each commit block is "author<TAB>date\nfiles...".
        lines = proc.stdout.splitlines()
        blocks: list[str] = []
        current_author = ""
        current_date = ""
        current_files: list[str] = []
        for line in lines:
            if "\t" in line and not line.startswith(" ") and not line.startswith("/"):
                if current_author:
                    blocks.append(f"{current_author}\t{current_date}\t" + "\n".join(current_files))
                parts = line.split("\t", 1)
                current_author = parts[0]
                current_date = parts[1] if len(parts) > 1 else ""
                current_files = []
            else:
                stripped = line.strip()
                if stripped:
                    current_files.append(stripped)
        if current_author:
            blocks.append(f"{current_author}\t{current_date}\t" + "\n".join(current_files))
        return blocks

    @staticmethod
    def _compute_hotspots(file_churn: dict[str, int]) -> list[tuple[str, float]]:
        """Compute a hotspot score (churn × file-size proxy) per file."""
        # Without complexity data, hotspots = churn ranking normalized.
        if not file_churn:
            return []
        max_churn = max(file_churn.values()) or 1
        return [
            (path, round(count / max_churn, 3))
            for path, count in sorted(file_churn.items(), key=lambda kv: kv[1], reverse=True)
        ]


__all__ = ["GitAnalyzer"]
