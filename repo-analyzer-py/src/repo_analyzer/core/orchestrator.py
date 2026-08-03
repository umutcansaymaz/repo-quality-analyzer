"""Analysis orchestrator.

Coordinates the full analysis pipeline:

1. Clone (via :class:`CloneService`) — phase -1.
2. Phase 0: RepositoryDetector, FilesystemAnalyzer, LanguageDetector.
3. Phase 1: ASTAnalyzer, ImportAnalyzer, DependencyAnalyzer.
4. Phase 2: MetricEngine, ComplexityAnalyzer.
5. Phase 3: GitAnalyzer, GraphEngine.
6. Phase 4: DocumentationAnalyzer, TestAnalyzer.
7. Phase 5: Review engines + optional LLM.

Analyzers are loaded through the :class:`PluginManager` — both built-in
and third-party analyzers are registered via the same mechanism. The
orchestrator depends on the :class:`AnalyzerPort` interface, not on
concrete analyzer classes.

Review engines + optional LLM are injected via constructor (ports).
"""

from __future__ import annotations

import threading
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from repo_analyzer.adapters.vcs.clone_service import CloneService
from repo_analyzer.adapters.vcs.factory import DefaultRepositoryProviderFactory
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.core.ports.cache_port import CachePort
from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.infrastructure.progress import ProgressUI
from repo_analyzer.plugins import PluginManager
from repo_analyzer.review import AICommentEngine

_logger = get_logger(__name__)


def _register_builtin_analyzers(manager: PluginManager) -> None:
    """Register the built-in analyzers with the plugin manager.

    This function imports the concrete analyzer classes and registers them.
    It is the **only** place in the core layer that imports concrete
    analyzers — the orchestrator itself depends only on
    :class:`AnalyzerPort`.
    """
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

    for analyzer_cls in [
        RepositoryDetector,
        FilesystemAnalyzer,
        LanguageDetector,
        ASTAnalyzer,
        ImportAnalyzer,
        DependencyAnalyzer,
        MetricEngine,
        ComplexityAnalyzer,
        GitAnalyzer,
        GraphEngine,
        DocumentationAnalyzer,
        TestAnalyzer,
    ]:
        instance = analyzer_cls()
        try:
            manager.registry.register(instance, metadata={"source": "builtin"})
        except Exception as exc:
            _logger.warning("Failed to register %s: %s", analyzer_cls.__name__, exc)


class Orchestrator:
    """Run the analysis pipeline and produce an :class:`AnalysisResult`.

    Args:
        cache: The cache port (injected).
        max_workers: Thread-pool size for parallel analyzer execution.
        clone_depth: Shallow-clone depth.
        timeout: Clone / fetch timeout in seconds.
        llm: Optional LLM port for the AI review phase.
        plugin_manager: Optional pre-configured plugin manager. If
            ``None``, a fresh one is created and built-in analyzers are
            registered.
    """

    def __init__(
        self,
        cache: CachePort,
        *,
        max_workers: int = 4,
        clone_depth: int = 1,
        timeout: int = 120,
        llm: LLMPort | None = None,
        plugin_manager: PluginManager | None = None,
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
        # Use the plugin manager for analyzer discovery.
        self._plugin_manager = plugin_manager or PluginManager()
        if not self._plugin_manager.initialized:
            _register_builtin_analyzers(self._plugin_manager)
            self._plugin_manager.initialize_all({})
        self._llm = llm
        self._review_engine: AICommentEngine | None = None
        if llm is not None:
            self._review_engine = AICommentEngine(llm)

    @property
    def analyzers(self) -> Sequence[AnalyzerPort]:
        """All registered analyzers (from the plugin manager)."""
        return self._plugin_manager.all()

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

            # Group analyzers by phase (from the plugin manager).
            analyzers = list(self._plugin_manager.all())
            phases = self._group_by_phase(analyzers)
            for phase in sorted(phases.keys()):
                if cancel_event and cancel_event.is_set():
                    result.add_error({"phase": phase, "error": "cancelled"})
                    break
                self._run_phase(phases[phase], resolved, workspace, result, progress)

            # Derive ArchitectureFinding from the graph report so review
            # engines that check ``result.architecture`` have data to work
            # with.
            self._populate_architecture_finding(result)

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

            # Phase 6: evidence collection (unified finding model).
            # This is a non-breaking post-processing step: if it fails,
            # the analysis result is still valid (evidence stays None).
            try:
                from repo_analyzer.core.evidence import EvidenceBuilder

                result.evidence = EvidenceBuilder.build(result)
                if progress:
                    progress.success("Evidence collection built")
            except Exception as exc:
                _logger.warning("Evidence build failed: %s", exc)
                result.add_error({"phase": "evidence", "error": str(exc)})

            # Phase 7: engineering knowledge graph.
            # Non-breaking: if it fails, knowledge_graph stays None.
            try:
                from repo_analyzer.core.evidence import GraphBuilder

                if result.evidence is not None:
                    result.knowledge_graph = GraphBuilder.build(result.evidence, result)
                    if progress:
                        progress.success("Knowledge graph built")
            except Exception as exc:
                _logger.warning("Knowledge graph build failed: %s", exc)
                result.add_error({"phase": "graph", "error": str(exc)})

            # Phase 8: root cause detection.
            # Non-breaking: if it fails, root_causes stays None.
            try:
                from repo_analyzer.core.evidence import RootCauseDetectionEngine

                if result.knowledge_graph is not None and result.evidence is not None:
                    result.root_causes = RootCauseDetectionEngine.detect(
                        result.knowledge_graph, result.evidence
                    )
                    if progress:
                        progress.success("Root cause detection complete")
            except Exception as exc:
                _logger.warning("Root cause detection failed: %s", exc)
                result.add_error({"phase": "root_cause", "error": str(exc)})

            # Phase 9: engineering planning.
            # Non-breaking: if it fails, engineering_plan stays None.
            try:
                from repo_analyzer.core.evidence import PlanningEngine

                if result.root_causes is not None:
                    result.engineering_plan = PlanningEngine.plan(result.root_causes)
                    if progress:
                        progress.success("Engineering plan built")
            except Exception as exc:
                _logger.warning("Engineering planning failed: %s", exc)
                result.add_error({"phase": "planning", "error": str(exc)})

            # Phase 10: LLM engineering review.
            # Non-breaking: if it fails, engineering_review stays None.
            # The LLM is optional — offline mode produces a fallback review.
            try:
                from repo_analyzer.review.ai.engineering_reviewer import (
                    EngineeringReviewer,
                )

                reviewer = EngineeringReviewer(llm=self._llm)
                result.engineering_review = reviewer.review(result)
                if progress:
                    if result.engineering_review and result.engineering_review.offline:
                        progress.info("Engineering review (offline fallback)")
                    else:
                        progress.success("Engineering review complete")
            except Exception as exc:
                _logger.warning("Engineering review failed: %s", exc)
                result.add_error({"phase": "llm_review", "error": str(exc)})

            if cancel_event and cancel_event.is_set():
                result.add_error({"phase": "post", "error": "cancelled"})
            result.mark_completed()
        except Exception as exc:
            _logger.error("Analysis failed: %s", exc)
            result.mark_failed({"error": str(exc), "type": type(exc).__name__})
        finally:
            self._cache.purge_expired()
        return result

    # ----- internal -------------------------------------------------------------

    @staticmethod
    def _populate_architecture_finding(result: AnalysisResult) -> None:
        """Derive an :class:`ArchitectureFinding` from the graph report.

        Review engines (quality, architecture, health, refactor) check
        ``result.architecture`` for coupling/cohesion/cycles. This method
        populates that field from the graph engine's output so the review
        engines have real data to work with.
        """
        if result.architecture is not None:
            return  # Already populated.
        if not result.graph_report:
            return
        from repo_analyzer.core.domain.architecture_finding import (
            ArchitectureFinding,
            ArchitectureSmell,
            ArchitectureSmellType,
            Cycle,
        )
        from repo_analyzer.core.domain.report import Severity

        cycles = [Cycle(nodes=cycle) for cycle in result.graph_report.cycles]
        smells: list[ArchitectureSmell] = []
        for cycle in cycles:
            smells.append(
                ArchitectureSmell(
                    type=ArchitectureSmellType.CYCLIC_DEPENDENCY,
                    severity=Severity.HIGH,
                    message=f"Circular dependency: {cycle}",
                    affected_modules=cycle.nodes,
                )
            )
        # Compute simple coupling proxy: number of edges / number of nodes.
        graph = result.graph_report.import_graph
        nodes = graph.get("nodes", 0)
        edges = graph.get("edges", 0)
        coupling = min(1.0, edges / max(nodes, 1)) if nodes > 0 else 0.0
        # Cohesion proxy: inverse of coupling (more edges = lower cohesion).
        cohesion = max(0.0, 1.0 - coupling)
        result.architecture = ArchitectureFinding(
            cycles=cycles,
            smells=smells,
            coupling=round(coupling, 2),
            cohesion=round(cohesion, 2),
        )

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
        """Merge an analyzer's output into the :class:`AnalysisResult`.

        This is a data-driven merge: the mapping from output key to
        AnalysisResult field is defined in :data:`_OUTPUT_MAPPING`.
        """
        for key, field_name in _OUTPUT_MAPPING.items():
            if key in output:
                model_cls = _OUTPUT_MODELS.get(key)
                if model_cls is not None:
                    setattr(result, field_name, model_cls.model_validate(output[key]))


#: Mapping from analyzer output key → AnalysisResult field name.
_OUTPUT_MAPPING: dict[str, str] = {
    "repository_metadata": "repository_metadata",
    "file_inventory": "file_inventory",
    "language_distribution": "language_distribution",
    "symbols": "symbols",
    "import_analysis": "import_analysis",
    "dependency_analysis": "dependency_analysis",
    "metrics_report": "metrics_report",
    "complexity_report": "complexity_report",
    "git_analysis": "git_analysis",
    "documentation_report": "documentation_report",
    "test_analysis": "test_analysis",
    "graph_report": "graph_report",
}

#: Mapping from output key → Pydantic model class (lazy-loaded).
_OUTPUT_MODELS: dict[str, Any] = {}


def _init_output_models() -> None:
    """Populate :data:`_OUTPUT_MODELS` lazily to avoid circular imports."""
    from repo_analyzer.core.domain.analysis_outputs import (
        ComplexityReport,
        DependencyAnalysis,
        DocumentationReport,
        FileInventory,
        GitAnalysis,
        GraphReport,
        ImportAnalysis,
        LanguageDistribution,
        MetricsReport,
        RepositoryMetadata,
        SymbolCollection,
        TestAnalysis,
    )

    _OUTPUT_MODELS.update(
        {
            "repository_metadata": RepositoryMetadata,
            "file_inventory": FileInventory,
            "language_distribution": LanguageDistribution,
            "symbols": SymbolCollection,
            "import_analysis": ImportAnalysis,
            "dependency_analysis": DependencyAnalysis,
            "metrics_report": MetricsReport,
            "complexity_report": ComplexityReport,
            "git_analysis": GitAnalysis,
            "documentation_report": DocumentationReport,
            "test_analysis": TestAnalysis,
            "graph_report": GraphReport,
        }
    )


# Initialize the model mapping at import time (safe — no circular deps).
_init_output_models()


__all__ = ["Orchestrator"]
