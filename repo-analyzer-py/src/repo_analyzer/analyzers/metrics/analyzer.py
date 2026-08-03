"""Metric engine.

Computes per-file and repository-wide code metrics:

- LOC (total lines)
- SLOC (source lines of code, non-blank non-comment)
- Comment lines
- Blank lines
- Comment ratio
- Function count
- Class count
- Average function length
- Average class length
- Average nesting depth
"""

from __future__ import annotations

import ast
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import FileMetrics, MetricsReport
from repo_analyzer.core.domain.repository import Repository


class MetricEngine(BaseAnalyzer):
    """Compute code metrics for each source file."""

    _analyzer_name = "metrics"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 2

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run the metric engine and return a :class:`MetricsReport`."""
        per_file: list[FileMetrics] = []
        total_loc = total_sloc = total_comment = total_blank = 0
        total_functions = total_classes = 0
        function_lengths: list[int] = []
        class_lengths: list[int] = []
        nesting_depths: list[int] = []

        for path in self._iter_source_files(workspace):
            language = self._language_for_file(path)
            if language is None:
                continue
            rel = str(path.relative_to(workspace))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            metrics = self._compute_file(rel, content, language)
            per_file.append(metrics)
            total_loc += metrics.loc
            total_sloc += metrics.sloc
            total_comment += metrics.comment_lines
            total_blank += metrics.blank_lines
            total_functions += metrics.function_count
            total_classes += metrics.class_count
            if metrics.avg_function_length > 0:
                function_lengths.append(int(metrics.avg_function_length))
            if metrics.avg_class_length > 0:
                class_lengths.append(int(metrics.avg_class_length))
            if metrics.avg_nesting > 0:
                nesting_depths.append(int(metrics.avg_nesting))

        report = MetricsReport(
            total_loc=total_loc,
            total_sloc=total_sloc,
            total_comment_lines=total_comment,
            total_blank_lines=total_blank,
            overall_comment_ratio=round(total_comment / max(total_sloc, 1), 4),
            total_functions=total_functions,
            total_classes=total_classes,
            avg_function_length=round(sum(function_lengths) / max(len(function_lengths), 1), 2),
            avg_class_length=round(sum(class_lengths) / max(len(class_lengths), 1), 2),
            avg_nesting=round(sum(nesting_depths) / max(len(nesting_depths), 1), 2),
            per_file=per_file,
        )
        return {"metrics_report": report.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_source_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                yield Path(root) / name

    @staticmethod
    def _language_for_file(path: Path) -> str | None:
        ext = path.suffix.lower().lstrip(".")
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "go": "go",
            "rs": "rust",
            "java": "java",
            "kt": "kotlin",
            "c": "c",
            "cpp": "cpp",
            "cs": "csharp",
            "rb": "ruby",
            "php": "php",
        }
        return lang_map.get(ext)

    def _compute_file(self, path: str, content: str, language: str) -> FileMetrics:
        """Compute metrics for a single file."""
        lines = content.splitlines()
        loc = len(lines)
        blank = sum(1 for line in lines if not line.strip())
        comment = self._count_comments(lines, language)
        sloc = loc - blank - comment
        functions, classes, func_lengths, class_lengths, nestings = self._extract_symbols(
            content, language
        )
        return FileMetrics(
            path=path,
            loc=loc,
            sloc=max(sloc, 0),
            comment_lines=comment,
            blank_lines=blank,
            comment_ratio=round(comment / max(loc, 1), 4),
            function_count=len(functions),
            class_count=len(classes),
            avg_function_length=round(sum(func_lengths) / max(len(func_lengths), 1), 2),
            avg_class_length=round(sum(class_lengths) / max(len(class_lengths), 1), 2),
            avg_nesting=round(sum(nestings) / max(len(nestings), 1), 2),
        )

    @staticmethod
    def _count_comments(lines: Sequence[str], language: str) -> int:
        """Count comment lines for the given language."""
        count = 0
        if language in {"python", "ruby", "php", "bash"}:
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#"):
                    count += 1
        elif language in {
            "javascript",
            "typescript",
            "java",
            "kotlin",
            "c",
            "cpp",
            "csharp",
            "go",
            "rust",
        }:
            in_block = False
            for line in lines:
                stripped = line.strip()
                if in_block:
                    count += 1
                    if "*/" in stripped:
                        in_block = False
                    continue
                if stripped.startswith("//"):
                    count += 1
                elif stripped.startswith("/*"):
                    count += 1
                    if "*/" not in stripped:
                        in_block = True
        return count

    def _extract_symbols(
        self, content: str, language: str
    ) -> tuple[list[str], list[str], list[int], list[int], list[int]]:
        """Extract functions/classes and their lengths + nesting depths."""
        if language == "python":
            return self._python_symbols(content)
        return [], [], [], [], []

    @staticmethod
    def _python_symbols(
        content: str,
    ) -> tuple[list[str], list[str], list[int], list[int], list[int]]:
        """Extract Python functions/classes via :mod:`ast`."""
        functions: list[str] = []
        classes: list[str] = []
        func_lengths: list[int] = []
        class_lengths: list[int] = []
        nestings: list[int] = []
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return functions, classes, func_lengths, class_lengths, nestings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(node.name)
                length = node.end_lineno - node.lineno + 1 if node.end_lineno else 1
                func_lengths.append(length)
                nestings.append(MetricEngine._nesting_depth(node))
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
                length = node.end_lineno - node.lineno + 1 if node.end_lineno else 1
                class_lengths.append(length)
        return functions, classes, func_lengths, class_lengths, nestings

    @staticmethod
    def _nesting_depth(node: ast.AST) -> int:
        """Compute the maximum nesting depth of a function."""
        depth = 0
        for child in ast.walk(node):
            if isinstance(
                child, (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
            ):
                depth += 1
        return depth


__all__ = ["MetricEngine"]
