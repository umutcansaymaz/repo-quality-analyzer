"""Context builder for the AI comment engine.

Selects the most important files, builds compact chunks and produces a
context payload that fits within the LLM's token budget. This minimizes token
cost while giving the LLM enough signal to produce an engineering review.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.ports.llm_port import LLMPort


class ContextBuilder:
    """Build a token-budgeted context payload for the LLM."""

    def __init__(self, *, max_tokens: int = 8000, max_files: int = 10) -> None:
        self._max_tokens = max_tokens
        self._max_files = max_files

    def build(
        self,
        result: AnalysisResult,
        workspace: Path | None = None,
        llm: LLMPort | None = None,
    ) -> dict[str, Any]:
        """Build the context dict.

        Args:
            result: The full :class:`AnalysisResult`.
            workspace: Optional workspace path (to read file snippets).
            llm: Optional LLM for accurate token counting.

        Returns:
            A dict with ``summary``, ``metrics``, ``findings``, ``files`` and
            ``token_estimate`` keys.
        """
        context: dict[str, Any] = {}
        context["repository"] = self._repo_summary(result)
        context["metrics"] = self._metrics_summary(result)
        context["findings"] = self._findings_summary(result)
        context["files"] = self._select_files(result, workspace, llm)
        context["token_estimate"] = self._estimate_tokens(context, llm)
        return context

    def _repo_summary(self, result: AnalysisResult) -> dict[str, Any]:
        meta = result.repository_metadata
        return {
            "url": result.repository.url,
            "owner": result.repository.owner,
            "name": result.repository.name,
            "default_branch": meta.default_branch if meta else None,
            "total_commits": meta.total_commits if meta else None,
            "contributors": len(meta.contributors) if meta else 0,
            "license": meta.license if meta else None,
            "size_bytes": meta.size_bytes if meta else None,
        }

    def _metrics_summary(self, result: AnalysisResult) -> dict[str, Any]:
        m = result.metrics_report
        c = result.complexity_report
        return {
            "total_loc": m.total_loc if m else 0,
            "total_sloc": m.total_sloc if m else 0,
            "total_functions": m.total_functions if m else 0,
            "total_classes": m.total_classes if m else 0,
            "avg_complexity": c.average_complexity if c else 0,
            "comment_ratio": m.overall_comment_ratio if m else 0,
            "languages": (result.language_distribution.loc if result.language_distribution else {}),
            "test_files": (result.test_analysis.total_test_files if result.test_analysis else 0),
            "test_frameworks": (result.test_analysis.frameworks if result.test_analysis else []),
        }

    def _findings_summary(self, result: AnalysisResult) -> dict[str, Any]:
        return {
            "security_findings_count": len(result.security_findings),
            "top_security": [
                {"rule": f.rule_id, "severity": f.severity.value, "message": f.message}
                for f in result.security_findings[:10]
            ],
            "circular_imports": (
                result.import_analysis.circular_imports[:5] if result.import_analysis else []
            ),
            "unused_dependencies": (
                result.dependency_analysis.unused_dependencies[:10]
                if result.dependency_analysis
                else []
            ),
            "complex_functions": (
                [
                    {"name": f.get("name"), "complexity": f.get("complexity")}
                    for f in result.complexity_report.top_complex_functions[:10]
                ]
                if result.complexity_report
                else []
            ),
            "duplicate_files": (
                result.file_inventory.duplicate_files if result.file_inventory else 0
            ),
        }

    def _select_files(
        self,
        result: AnalysisResult,
        workspace: Path | None,
        llm: LLMPort | None,
    ) -> list[dict[str, Any]]:
        """Select the most important files and include a short snippet."""
        if not result.metrics_report:
            return []
        # Rank by SLOC + function count.
        scored = sorted(
            result.metrics_report.per_file,
            key=lambda fm: fm.sloc + fm.function_count * 5,
            reverse=True,
        )
        selected: list[dict[str, Any]] = []
        budget = self._max_tokens
        for fm in scored[: self._max_files * 2]:
            if budget <= 0:
                break
            snippet = ""
            if workspace:
                try:
                    full = (workspace / fm.path).read_text(encoding="utf-8", errors="ignore")
                    snippet = full[:2000]  # cap snippet at 2KB
                except OSError:
                    snippet = ""
            tokens = self._count(snippet, llm)
            if tokens > budget:
                continue
            budget -= tokens
            selected.append(
                {
                    "path": fm.path,
                    "sloc": fm.sloc,
                    "functions": fm.function_count,
                    "complexity": self._file_complexity(fm.path, result),
                    "snippet": snippet,
                }
            )
            if len(selected) >= self._max_files:
                break
        return selected

    @staticmethod
    def _file_complexity(path: str, result: AnalysisResult) -> float | None:
        if not result.complexity_report:
            return None
        funcs = [f for f in result.complexity_report.top_complex_functions if f.get("file") == path]
        if not funcs:
            return None
        return float(max(f.get("complexity", 0) for f in funcs))

    @staticmethod
    def _count(text: str, llm: LLMPort | None) -> int:
        if llm:
            return llm.count_tokens(text)
        return max(1, len(text) // 4)

    def _estimate_tokens(self, context: dict[str, Any], llm: LLMPort | None) -> int:
        """Estimate total tokens in the context."""
        import json

        serialized = json.dumps(context, default=str)
        return self._count(serialized, llm)


__all__ = ["ContextBuilder"]
