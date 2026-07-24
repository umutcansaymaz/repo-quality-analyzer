"""Analysis-result aggregate model."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.ai_review import AIReview
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
    health score and the optional AI review.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    repository: Repository
    status: AnalysisStatus = AnalysisStatus.INITIALIZED
    started_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    finished_at: datetime | None = None
    commit_sha: str | None = None

    security_findings: list[SecurityFinding] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    metrics: list[Metric] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    architecture: ArchitectureFinding | None = None
    health_score: HealthScore | None = None
    ai_review: AIReview | None = None

    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)

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
