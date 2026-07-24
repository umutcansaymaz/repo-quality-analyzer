"""Analysis orchestrator.

Coordinates the full analysis pipeline:

1. Clone (via :class:`CloneService`) — phase -1.
2. Phase 0: RepositoryDetector, FilesystemAnalyzer, LanguageDetector.
3. Phase 1: ASTAnalyzer, ImportAnalyzer, DependencyAnalyzer.
4. Phase 2: MetricEngine, ComplexityAnalyzer.
5. Phase 3: GitAnalyzer, GraphEngine.
6. Phase 4: DocumentationAnalyzer, TestAnalyzer.

Analyzers within the same phase run in parallel via a
:class:`ThreadPoolExecutor`. Results are merged into a single
:class:`AnalysisResult`.
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from repo_analyzer.adapters.vcs import CloneService, DefaultRepositoryProviderFactory
from repo_analyzer.analyzers import (
    ASTAnalyzer,
    ComplexityAnalyzer,
    DependencyAnalyzer,
    DocumentationAnalyzer,
    FilesystemAnalyzer,
    GitAnalyzer,
    GraphEngine,
    ImportAnalyzer,
    LanguageDetector,
    MetricEngine,
    RepositoryDetector,
    TestAnalyzer,
)
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.core.ports.cache_port import CachePort
from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.infrastructure.progress import ProgressUI
from repo_analyzer.review import AICommentEngine

_logger = get_logger(__name__)


class Orchestrator:
    """Run the analysis pipeline and produce an :class:`AnalysisResult`."""

    def __init__(
        self,
        cache: CachePort,
        *,
        max_workers: int = 4,
        clone_depth: int = 1,
        timeout: int = 120,
        llm: LLMPort | None = None,
    ) -> None:
        self._cache = cache
        self._max_workers = max(1, max_workers)
        self._clone_service = CloneService(
            cache,
            factory=DefaultRepositoryProviderFactory(
                clone_depth=clone_depth,
                timeout=timeout,
            ),
        )
        self._analyzers: list[AnalyzerPort] = self._default_analyzers()
        self._llm = llm
        self._review_engine: AICommentEngine | None = None
        if llm is not None:
            self._review_engine = AICommentEngine(llm)

    def _default_analyzers(self) -> list[AnalyzerPort]:
        return [
            RepositoryDetector(),
            FilesystemAnalyzer(),
            LanguageDetector(),
            ASTAnalyzer(),
            ImportAnalyzer(),
            DependencyAnalyzer(),
            MetricEngine(),
            ComplexityAnalyzer(),
            GitAnalyzer(),
            GraphEngine(),
            DocumentationAnalyzer(),
            TestAnalyzer(),
        ]

    def analyze(
        self,
        repository: Repository,
        *,
        progress: ProgressUI | None = None,
        cancel_event: threading.Event | None = None,
        use_cache: bool = True,
    ) -> AnalysisResult:
        """Run the full analysis and return an :class:`AnalysisResult`.

        Args:
            repository: The repository to analyze.
            progress: Optional :class:`ProgressUI` for status updates.
            cancel_event: Optional event to signal cancellation.
            use_cache: If ``False``, bypass the clone cache.

        Returns:
            A populated :class:`AnalysisResult`.
        """
        result = AnalysisResult(repository=repository)
        result.mark_running()
        try:
            # Phase -1: clone.
            workspace, resolved = self._clone_service.clone(
                repository,
                cancel_event=cancel_event,
                progress=progress,
                use_cache=use_cache,
            )
            result.repository = resolved
            result.commit_sha = resolved.commit_sha

            # Group analyzers by phase.
            phases = self._group_by_phase(self._analyzers)
            for phase in sorted(phases.keys()):
                if cancel_event and cancel_event.is_set():
                    result.add_error({"phase": phase, "error": "cancelled"})
                    break
                self._run_phase(phases[phase], resolved, workspace, result, progress)

            # Phase 5: review (deterministic engines + optional LLM).
            if self._review_engine is not None:
                if progress:
                    progress.info("Running review phase...")
                try:
                    result.ai_review = self._review_engine.review(result, workspace)
                    if progress:
                        progress.success("Review complete")
                except Exception as exc:
                    _logger.warning("Review phase failed: %s", exc)
                    result.add_error({"phase": "review", "error": str(exc)})
                    if progress:
                        progress.warning(f"Review phase failed: {exc}")

            result.mark_completed()
        except Exception as exc:
            _logger.error("Analysis failed: %s", exc)
            result.mark_failed({"error": str(exc), "type": type(exc).__name__})
        return result

    # ----- internal -------------------------------------------------------------

    def _group_by_phase(self, analyzers: Sequence[AnalyzerPort]) -> dict[int, list[AnalyzerPort]]:
        """Group analyzers by their phase."""
        groups: dict[int, list[AnalyzerPort]] = {}
        for analyzer in analyzers:
            groups.setdefault(analyzer.phase, []).append(analyzer)
        return groups

    def _run_phase(
        self,
        analyzers: list[AnalyzerPort],
        repository: Repository,
        workspace: Path,
        result: AnalysisResult,
        progress: ProgressUI | None,
    ) -> None:
        """Run all analyzers in a phase (parallel via thread pool)."""
        if progress:
            progress.info(f"Running phase with {len(analyzers)} analyzer(s)...")
        with ThreadPoolExecutor(max_workers=self._max_workers) as pool:
            futures = {
                pool.submit(self._run_analyzer, analyzer, repository, workspace): analyzer
                for analyzer in analyzers
            }
            for future in as_completed(futures):
                analyzer = futures[future]
                try:
                    output = future.result()
                    if output:
                        self._merge_output(result, output, analyzer.name)
                    if progress:
                        progress.success(f"{analyzer.name} done")
                except Exception as exc:
                    _logger.warning("Analyzer %s failed: %s", analyzer.name, exc)
                    result.add_error({"analyzer": analyzer.name, "error": str(exc)})
                    if progress:
                        progress.warning(f"{analyzer.name} failed: {exc}")

    @staticmethod
    def _run_analyzer(
        analyzer: AnalyzerPort, repository: Repository, workspace: Path
    ) -> dict[str, Any]:
        """Run a single analyzer and return its output dict."""
        try:
            analyzer.initialize({})
            if not analyzer.can_run(repository, workspace):
                return {}
            return analyzer.run(repository, workspace)
        finally:
            try:
                analyzer.dispose()
            except Exception:  # pragma: no cover - defensive
                pass

    @staticmethod
    def _merge_output(result: AnalysisResult, output: dict[str, Any], analyzer_name: str) -> None:
        """Merge an analyzer's output into the :class:`AnalysisResult`."""
        if "repository_metadata" in output:
            from repo_analyzer.core.domain.analysis_outputs import RepositoryMetadata

            result.repository_metadata = RepositoryMetadata.model_validate(
                output["repository_metadata"]
            )
        if "file_inventory" in output:
            from repo_analyzer.core.domain.analysis_outputs import FileInventory

            result.file_inventory = FileInventory.model_validate(output["file_inventory"])
        if "language_distribution" in output:
            from repo_analyzer.core.domain.analysis_outputs import LanguageDistribution

            result.language_distribution = LanguageDistribution.model_validate(
                output["language_distribution"]
            )
        if "symbols" in output:
            from repo_analyzer.core.domain.analysis_outputs import SymbolCollection

            result.symbols = SymbolCollection.model_validate(output["symbols"])
        if "import_analysis" in output:
            from repo_analyzer.core.domain.analysis_outputs import ImportAnalysis

            result.import_analysis = ImportAnalysis.model_validate(output["import_analysis"])
        if "dependency_analysis" in output:
            from repo_analyzer.core.domain.analysis_outputs import DependencyAnalysis

            result.dependency_analysis = DependencyAnalysis.model_validate(
                output["dependency_analysis"]
            )
        if "metrics_report" in output:
            from repo_analyzer.core.domain.analysis_outputs import MetricsReport

            result.metrics_report = MetricsReport.model_validate(output["metrics_report"])
        if "complexity_report" in output:
            from repo_analyzer.core.domain.analysis_outputs import ComplexityReport

            result.complexity_report = ComplexityReport.model_validate(output["complexity_report"])
        if "git_analysis" in output:
            from repo_analyzer.core.domain.analysis_outputs import GitAnalysis

            result.git_analysis = GitAnalysis.model_validate(output["git_analysis"])
        if "documentation_report" in output:
            from repo_analyzer.core.domain.analysis_outputs import DocumentationReport

            result.documentation_report = DocumentationReport.model_validate(
                output["documentation_report"]
            )
        if "test_analysis" in output:
            from repo_analyzer.core.domain.analysis_outputs import TestAnalysis

            result.test_analysis = TestAnalysis.model_validate(output["test_analysis"])
        if "graph_report" in output:
            from repo_analyzer.core.domain.analysis_outputs import GraphReport

            result.graph_report = GraphReport.model_validate(output["graph_report"])


__all__ = ["Orchestrator"]
