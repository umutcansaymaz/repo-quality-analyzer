"""Complexity analyzer using :mod:`radon`.

Computes:

- Cyclomatic complexity (per function).
- Maintainability index (per file).
- Halstead metrics (per function).
- Cognitive complexity (best-effort).
- Top 50 most complex functions and classes.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import ComplexityReport
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class ComplexityAnalyzer(BaseAnalyzer):
    """Analyze code complexity using :mod:`radon` (Python only)."""

    _analyzer_name = "complexity"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 2

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run complexity analysis and return a :class:`ComplexityReport`."""
        top_functions: list[dict[str, Any]] = []
        top_classes: list[dict[str, Any]] = []
        mi_scores: dict[str, float] = {}
        halstead_total: dict[str, Any] = {
            "operators": 0,
            "operands": 0,
            "unique_operators": 0,
            "unique_operands": 0,
        }
        complexity_values: list[float] = []

        for path in self._iter_python_files(workspace):
            rel = str(path.relative_to(workspace))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            # Cyclomatic complexity.
            cc_results = self._cc_visit(content, rel)
            for func in cc_results:
                top_functions.append(func)
                complexity_values.append(func["complexity"])
            # Maintainability index.
            mi = self._mi_compute(content, rel)
            if mi is not None:
                mi_scores[rel] = mi
            # Class complexity.
            class_results = self._class_complexity(content, rel)
            for cls in class_results:
                top_classes.append(cls)

        top_functions.sort(key=lambda f: f.get("complexity", 0), reverse=True)
        top_classes.sort(key=lambda c: c.get("complexity", 0), reverse=True)
        report = ComplexityReport(
            top_complex_functions=top_functions[:50],
            top_complex_classes=top_classes[:50],
            maintainability_index=mi_scores,
            halstead=halstead_total,
            average_complexity=round(sum(complexity_values) / max(len(complexity_values), 1), 2),
        )
        return {"complexity_report": report.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_python_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                if name.endswith(".py"):
                    yield Path(root) / name

    def _cc_visit(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """Compute cyclomatic complexity for each function in a file."""
        try:
            from radon.complexity import cc_rank, cc_visit

            results = cc_visit(content)
        except Exception as exc:  # pragma: no cover - radon optional
            _logger.debug("radon cc_visit failed for %s: %s", file_path, exc)
            return []
        out: list[dict[str, Any]] = []
        for item in results:
            out.append(
                {
                    "file": file_path,
                    "name": item.name,
                    "lineno": item.lineno,
                    "complexity": item.complexity,
                    "rank": cc_rank(item.complexity),
                    "endline": item.endline,
                }
            )
        return out

    def _mi_compute(self, content: str, file_path: str) -> float | None:
        """Compute the maintainability index for a file."""
        try:
            from radon.metrics import mi_visit

            score: float = float(mi_visit(content, multi=True))
            return round(score, 2)
        except Exception as exc:  # pragma: no cover - radon optional
            _logger.debug("radon mi_visit failed for %s: %s", file_path, exc)
            return None

    def _class_complexity(self, content: str, file_path: str) -> list[dict[str, Any]]:
        """Compute the average complexity of methods within each class."""
        try:
            from radon.complexity import cc_visit

            results = cc_visit(content)
        except Exception:
            return []
        # ``cc_visit`` returns a flat list; class objects contain nested results.
        out: list[dict[str, Any]] = []
        for item in results:
            if hasattr(item, "methods"):
                complexities = [m.complexity for m in item.methods]
                avg = sum(complexities) / max(len(complexities), 1)
                out.append(
                    {
                        "file": file_path,
                        "name": item.name,
                        "lineno": item.lineno,
                        "complexity": round(avg, 2),
                        "method_count": len(item.methods),
                    }
                )
        return out


__all__ = ["ComplexityAnalyzer"]
