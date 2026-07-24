"""Domain model for repo-analyzer.

This package contains the Pydantic models that make up the domain layer of
the Hexagonal core. Models are framework-agnostic (pure Pydantic v2) and
carry no external dependencies.
"""

from __future__ import annotations

from repo_analyzer.core.domain.ai_review import AIReview, ModelInfo, Recommendation
from repo_analyzer.core.domain.analysis_outputs import (
    ComplexityReport,
    DependencyAnalysis,
    DocumentationReport,
    FileInventory,
    FileMetrics,
    GitAnalysis,
    GraphReport,
    ImportAnalysis,
    LanguageDistribution,
    MetricsReport,
    RepositoryMetadata,
    SymbolCollection,
    TestAnalysis,
)
from repo_analyzer.core.domain.analysis_result import AnalysisResult, AnalysisStatus
from repo_analyzer.core.domain.architecture_finding import (
    ArchitectureFinding,
    ArchitectureSmell,
    Cycle,
    Layer,
)
from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheKey
from repo_analyzer.core.domain.config import ConfigSnapshot
from repo_analyzer.core.domain.dependency import Dependency, License, Version
from repo_analyzer.core.domain.health_score import Grade, HealthScore, ScoreWeights
from repo_analyzer.core.domain.issue import Issue, IssueType
from repo_analyzer.core.domain.metric import Metric, MetricScope, MetricUnit
from repo_analyzer.core.domain.report import (
    Finding,
    Location,
    Report,
    ReportFormat,
    ReportMeta,
    Severity,
)
from repo_analyzer.core.domain.repository import (
    AccessMode,
    Credential,
    Repository,
    RepositoryRef,
)
from repo_analyzer.core.domain.review_outputs import (
    ArchitectureObservation,
    ArchitectureReview,
    CodeQualityReview,
    CodeSmellFinding,
    DirectoryReview,
    ExtendedHealthScore,
    FileReview,
    ProjectReview,
    QuickWin,
    RefactorItem,
    RefactorPlan,
    RiskItem,
    RiskLevel,
    RiskSummary,
    SecurityFindingDetail,
    SecurityReview,
    TechnicalDebt,
    TechnicalDebtItem,
)
from repo_analyzer.core.domain.review_outputs import (
    Grade as ReviewGrade,
)
from repo_analyzer.core.domain.security_finding import (
    Confidence,
    SecurityCategory,
    SecurityFinding,
)

__all__ = [
    # repository
    "AccessMode",
    "Credential",
    "Repository",
    "RepositoryRef",
    # finding / report
    "Severity",
    "Location",
    "Finding",
    "Report",
    "ReportFormat",
    "ReportMeta",
    # issue
    "Issue",
    "IssueType",
    # metric
    "Metric",
    "MetricScope",
    "MetricUnit",
    # security
    "SecurityFinding",
    "SecurityCategory",
    "Confidence",
    # architecture
    "ArchitectureFinding",
    "ArchitectureSmell",
    "Cycle",
    "Layer",
    # dependency
    "Dependency",
    "License",
    "Version",
    # health score
    "HealthScore",
    "Grade",
    "ScoreWeights",
    # ai review
    "AIReview",
    "ModelInfo",
    "Recommendation",
    # analysis result
    "AnalysisResult",
    "AnalysisStatus",
    # analysis outputs
    "FileInventory",
    "RepositoryMetadata",
    "LanguageDistribution",
    "SymbolCollection",
    "ImportAnalysis",
    "DependencyAnalysis",
    "FileMetrics",
    "MetricsReport",
    "ComplexityReport",
    "GitAnalysis",
    "DocumentationReport",
    "TestAnalysis",
    "GraphReport",
    # review outputs
    "RiskLevel",
    "ReviewGrade",
    "SecurityFindingDetail",
    "SecurityReview",
    "CodeSmellFinding",
    "CodeQualityReview",
    "ArchitectureObservation",
    "ArchitectureReview",
    "FileReview",
    "DirectoryReview",
    "ProjectReview",
    "RiskItem",
    "RiskSummary",
    "TechnicalDebtItem",
    "TechnicalDebt",
    "RefactorItem",
    "RefactorPlan",
    "QuickWin",
    "ExtendedHealthScore",
    # config snapshot
    "ConfigSnapshot",
    # cache
    "CacheEntry",
    "CacheKey",
]
