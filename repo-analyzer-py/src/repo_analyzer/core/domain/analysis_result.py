"""Analysis-result aggregate model.

This is the central object produced by the orchestrator and consumed by the
report generators. It bundles every kind of finding plus all structured
analysis outputs (file inventory, language distribution, AST symbols,
import / dependency graphs, metrics, complexity, git stats, documentation,
tests and graph-engine output).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.ai_review import AIReview
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
from repo_analyzer.core.domain.architecture_finding import ArchitectureFinding
from repo_analyzer.core.domain.dependency import Dependency
from repo_analyzer.core.domain.health_score import HealthScore
from repo_analyzer.core.domain.issue import Issue
from repo_analyzer.core.domain.metric import Metric
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.domain.security_finding import SecurityFinding


class AnalysisStatus(str, Enum):
    """Status of an analysis run."""

    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class AnalysisResult(BaseModel):
    """The aggregate result of analyzing a repository.

    This is the object produced by the orchestrator and consumed by the
    report generators. It bundles every kind of finding plus the computed
    health score, the optional AI review and all structured analysis outputs.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    repository: Repository
    status: AnalysisStatus = AnalysisStatus.INITIALIZED
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    finished_at: datetime | None = None
    commit_sha: str | None = None

    # Findings.
    security_findings: list[SecurityFinding] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    architecture: ArchitectureFinding | None = None
    health_score: HealthScore | None = None
    ai_review: AIReview | None = None

    # Structured analysis outputs.
    repository_metadata: RepositoryMetadata | None = None
    file_inventory: FileInventory | None = None
    language_distribution: LanguageDistribution | None = None
    symbols: SymbolCollection | None = None
    import_analysis: ImportAnalysis | None = None
    dependency_analysis: DependencyAnalysis | None = None
    metrics_report: MetricsReport | None = None
    complexity_report: ComplexityReport | None = None
    git_analysis: GitAnalysis | None = None
    documentation_report: DocumentationReport | None = None
    test_analysis: TestAnalysis | None = None
    graph_report: GraphReport | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)

    # Evidence collection (unified finding model).
    # Populated by EvidenceBuilder after analysis phases complete.
    # Backward compatible: defaults to None, existing consumers are unaffected.
    evidence: Any | None = None

    # Engineering knowledge graph (in-memory graph of engineering relationships).
    # Populated by GraphBuilder after the evidence phase completes.
    # Backward compatible: defaults to None, existing consumers are unaffected.
    knowledge_graph: Any | None = None

    # Root cause collection (architectural root causes derived from the graph).
    # Populated by RootCauseDetectionEngine after the graph phase completes.
    # Backward compatible: defaults to None, existing consumers are unaffected.
    root_causes: Any | None = None

    # Engineering plan (prioritized refactoring roadmap derived from root causes).
    # Populated by PlanningEngine after the root cause phase completes.
    # Backward compatible: defaults to None, existing consumers are unaffected.
    engineering_plan: Any | None = None

    @property
    def total_findings(self) -> int:
        """Total number of findings across all categories."""
        return (
            len(self.security_findings)
            + len(self.issues)
            + (len(self.architecture.smells) if self.architecture else 0)
        )

    def mark_running(self) -> None:
        """Set the status to :attr:`AnalysisStatus.RUNNING`."""
        self.status = AnalysisStatus.RUNNING

    def mark_completed(self) -> None:
        """Mark the analysis as completed and stamp ``finished_at``."""
        self.status = AnalysisStatus.COMPLETED
        self.finished_at = datetime.now(tz=UTC)

    def mark_failed(self, error: dict[str, Any] | None = None) -> None:
        """Mark the analysis as failed."""
        self.status = AnalysisStatus.FAILED
        self.finished_at = datetime.now(tz=UTC)
        if error:
            self.errors.append(error)

    def add_error(self, error: dict[str, Any]) -> None:
        """Record a non-fatal error without changing the status."""
        self.errors.append(error)


__all__ = ["AnalysisResult", "AnalysisStatus"]
