"""File-level review engine.

Reviews each important file (entry points, large files, complex files) and
produces a :class:`FileReview` with purpose, responsibilities, strengths,
weaknesses, risks and refactor suggestions.
"""

from __future__ import annotations

from typing import Any

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import FileReview, RiskLevel


class FileReviewEngine:
    """Produce :class:`FileReview` items for the repository's key files."""

    #: Max number of files to review individually.
    MAX_FILES = 30

    def review(self, result: AnalysisResult) -> list[FileReview]:
        """Return reviews for the most important files."""
        candidates = self._select_important_files(result)
        reviews: list[FileReview] = []
        for path, metrics in candidates:
            reviews.append(self._review_file(path, metrics, result))
        return reviews

    def _select_important_files(self, result: AnalysisResult) -> list[tuple[str, dict[str, Any]]]:
        """Select the most important files by size and complexity."""
        if not result.metrics_report:
            return []
        scored: list[tuple[str, dict[str, Any], float]] = []
        for fm in result.metrics_report.per_file:
            # Score by SLOC + function count (proxy for importance).
            score = fm.sloc + fm.function_count * 5
            if score > 0:
                scored.append((fm.path, fm.model_dump(), score))
        scored.sort(key=lambda x: x[2], reverse=True)
        return [(path, m) for path, m, _ in scored[: self.MAX_FILES]]

    def _review_file(
        self, path: str, metrics: dict[str, Any], result: AnalysisResult
    ) -> FileReview:
        """Build a single :class:`FileReview`."""
        sloc = metrics.get("sloc", 0)
        func_count = metrics.get("function_count", 0)
        class_count = metrics.get("class_count", 0)
        complexity = self._file_complexity(path, result)
        purpose = self._infer_purpose(path)
        responsibilities = self._infer_responsibilities(path, func_count, class_count)
        strengths: list[str] = []
        weaknesses: list[str] = []
        risks: list[str] = []
        suggestions: list[str] = []
        if sloc < 200:
            strengths.append("Reasonable file size.")
        else:
            weaknesses.append(f"Large file ({sloc} SLOC); consider splitting.")
            suggestions.append("Split into focused modules.")
        if complexity and complexity > 10:
            weaknesses.append(f"High cyclomatic complexity ({complexity}).")
            risks.append("High complexity increases defect probability.")
            suggestions.append("Extract complex logic into helper functions.")
        else:
            strengths.append("Manageable complexity.")
        if metrics.get("comment_ratio", 0) > 0.15:
            strengths.append("Good comment ratio.")
        else:
            weaknesses.append("Low comment ratio.")
            suggestions.append("Add docstrings to public functions.")
        if func_count > 20:
            weaknesses.append(f"Many functions ({func_count}); possible SRP violation.")
            suggestions.append("Group functions into cohesive classes or modules.")
        priority = (
            RiskLevel.HIGH
            if complexity and complexity > 15
            else RiskLevel.MEDIUM
            if sloc > 300
            else RiskLevel.LOW
        )
        return FileReview(
            path=path,
            purpose=purpose,
            responsibilities=responsibilities,
            code_quality=self._quality_label(metrics, complexity),
            strengths=strengths,
            weaknesses=weaknesses,
            risks=risks,
            refactor_suggestions=suggestions,
            priority=priority,
            estimated_effort=self._effort(sloc, complexity),
            maintenance_cost=self._maintenance_cost(sloc, complexity),
        )

    @staticmethod
    def _file_complexity(path: str, result: AnalysisResult) -> float | None:
        if not result.complexity_report:
            return None
        funcs = [f for f in result.complexity_report.top_complex_functions if f.get("file") == path]
        if not funcs:
            return None
        return float(max(f.get("complexity", 0) for f in funcs))

    @staticmethod
    def _infer_purpose(path: str) -> str:
        name = path.rsplit("/", 1)[-1].lower()
        if name in {"main.py", "__main__.py", "app.py", "index.js", "main.go"}:
            return "Application entry point."
        if "test" in name:
            return "Test module."
        if name in {"models.py", "model.py"}:
            return "Data / domain model definitions."
        if name in {"views.py", "controllers.py", "routes.py"}:
            return "Request handling / controller layer."
        if name in {"services.py", "service.py"}:
            return "Business-logic service layer."
        if name in {"utils.py", "helpers.py", "common.py"}:
            return "Shared utility functions."
        if name.endswith("__init__.py"):
            return "Package initialization."
        if "config" in name:
            return "Configuration."
        return "Source module."

    @staticmethod
    def _infer_responsibilities(path: str, func_count: int, class_count: int) -> list[str]:
        resp: list[str] = []
        if class_count > 0:
            resp.append(f"Defines {class_count} class(es).")
        if func_count > 0:
            resp.append(f"Contains {func_count} function(s).")
        resp.append("Participates in the module's import graph.")
        return resp

    @staticmethod
    def _quality_label(metrics: dict[str, Any], complexity: float | None) -> str:
        sloc = metrics.get("sloc", 0)
        if sloc < 200 and (complexity is None or complexity < 10):
            return "good"
        if sloc > 500 or (complexity and complexity > 15):
            return "poor"
        return "fair"

    @staticmethod
    def _effort(sloc: int, complexity: float | None) -> str:
        if sloc > 500 or (complexity and complexity > 15):
            return "high"
        if sloc > 200:
            return "medium"
        return "low"

    @staticmethod
    def _maintenance_cost(sloc: int, complexity: float | None) -> str:
        if sloc > 500 or (complexity and complexity > 15):
            return "high"
        if sloc > 200:
            return "medium"
        return "low"


__all__ = ["FileReviewEngine"]
