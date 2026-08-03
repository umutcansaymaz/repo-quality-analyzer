"""Directory-level review engine."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import DirectoryReview


class DirectoryReviewEngine:
    """Produce :class:`DirectoryReview` items for each top-level directory."""

    #: Max directories to review.
    MAX_DIRECTORIES = 20

    def review(
        self, result: AnalysisResult, workspace: Path | None = None
    ) -> list[DirectoryReview]:
        """Return reviews for the repository's directories."""
        if not result.file_inventory:
            return []
        dir_stats: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"files": 0, "bytes": 0, "langs": set()}
        )
        for file_path in result.file_inventory.files:
            parent = str(Path(file_path).parent)
            if parent == ".":
                parent = "<root>"
            dir_stats[parent]["files"] += 1
        # Aggregate bytes from largest_files.
        for path, size in result.file_inventory.largest_files:
            parent = str(Path(path).parent)
            if parent == ".":
                parent = "<root>"
            dir_stats[parent]["bytes"] += size
        # Rank by file count.
        ranked = sorted(dir_stats.items(), key=lambda kv: kv[1]["files"], reverse=True)
        reviews: list[DirectoryReview] = []
        for dir_path, stats in ranked[: self.MAX_DIRECTORIES]:
            reviews.append(self._review_directory(dir_path, stats, result))
        return reviews

    def _review_directory(
        self, path: str, stats: dict[str, Any], result: AnalysisResult
    ) -> DirectoryReview:
        file_count = stats["files"]
        purpose = self._infer_purpose(path)
        well_organized = file_count < 50
        should_split = file_count > 100
        risks: list[str] = []
        if should_split:
            risks.append("Directory is very large; navigation and ownership are hard.")
        if file_count > 50:
            risks.append("High file count suggests possible mixing of responsibilities.")
        return DirectoryReview(
            path=path,
            purpose=purpose,
            well_organized=well_organized,
            organization_assessment=self._org_assessment(file_count),
            dependency_assessment="See import graph for inter-directory dependencies.",
            size_assessment=self._size_assessment(file_count),
            should_split=should_split,
            split_recommendation=self._split_recommendation(path, should_split)
            if should_split
            else "",
            risks=risks,
        )

    @staticmethod
    def _infer_purpose(path: str) -> str:
        name = path.rsplit("/", 1)[-1].lower()
        mapping = {
            "src": "Source code root.",
            "tests": "Test suite.",
            "test": "Test suite.",
            "docs": "Documentation.",
            "config": "Configuration files.",
            "scripts": "Utility / build scripts.",
            "lib": "Shared library code.",
            "api": "API definitions / handlers.",
            "web": "Frontend / web assets.",
            "public": "Static public assets.",
            "migrations": "Database migrations.",
            ".github": "CI/CD workflows.",
        }
        return mapping.get(name, f"Directory grouping related files ({name}).")

    @staticmethod
    def _org_assessment(file_count: int) -> str:
        if file_count < 20:
            return "Well-organized; reasonable file count."
        if file_count < 50:
            return "Moderately organized; monitor growth."
        return "Dense directory; consider sub-grouping by responsibility."

    @staticmethod
    def _size_assessment(file_count: int) -> str:
        if file_count < 20:
            return "small"
        if file_count < 50:
            return "medium"
        if file_count < 100:
            return "large"
        return "very-large"

    @staticmethod
    def _split_recommendation(path: str, should_split: bool) -> str:
        if not should_split:
            return ""
        return f"Split '{path}' into sub-directories along responsibility boundaries."


__all__ = ["DirectoryReviewEngine"]
