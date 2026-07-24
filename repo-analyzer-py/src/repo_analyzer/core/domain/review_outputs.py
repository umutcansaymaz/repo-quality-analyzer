"""Structured review-output domain models.

These models are produced by the review engines (security, code quality,
architecture, file/directory/project review, risk, technical debt, refactor)
and consumed by the AI comment engine to build the final :class:`AIReview`.

Every model emphasizes *engineering judgment*: each finding carries the
"why it is risky", "real-world impact", "solution" and "safe code example"
fields rather than being a bare metric.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    """Qualitative risk level."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Grade(str, Enum):
    """Letter grade with ``+`` / ``-`` modifiers."""

    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    C_PLUS = "C+"
    C = "C"
    C_MINUS = "C-"
    D_PLUS = "D+"
    D = "D"
    D_MINUS = "D-"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> Grade:
        """Map a 0-100 score to a :class:`Grade`."""
        if score >= 97:
            return cls.A_PLUS
        if score >= 93:
            return cls.A
        if score >= 90:
            return cls.A_MINUS
        if score >= 87:
            return cls.B_PLUS
        if score >= 83:
            return cls.B
        if score >= 80:
            return cls.B_MINUS
        if score >= 77:
            return cls.C_PLUS
        if score >= 73:
            return cls.C
        if score >= 70:
            return cls.C_MINUS
        if score >= 67:
            return cls.D_PLUS
        if score >= 63:
            return cls.D
        if score >= 60:
            return cls.D_MINUS
        return cls.F


# ---------------------------------------------------------------------------
# Security review
# ---------------------------------------------------------------------------


class SecurityFindingDetail(BaseModel):
    """A rich security finding with engineering context.

    Every field is populated so that the finding is actionable: the developer
    understands *why* it is risky, what could happen in production, and how to
    fix it — including a safe-code example.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    title: str
    category: str = Field(description="e.g. 'hardcoded_password', 'sql_injection'.")
    severity: RiskLevel
    cvss_estimate: float = Field(default=0.0, ge=0.0, le=10.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    file: str
    line: int | None = None
    code_snippet: str | None = None
    why_risky: str = Field(description="Why this pattern is dangerous.")
    real_world_risk: str = Field(description="What could happen in production.")
    solution: str = Field(description="How to fix it.")
    safe_code_example: str | None = None
    references: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    tool: str = Field(default="custom", description="Source tool: bandit/detect-secrets/custom.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecurityReview(BaseModel):
    """Aggregate security review."""

    model_config = ConfigDict(extra="forbid")

    findings: list[SecurityFindingDetail] = Field(default_factory=list)
    overall_severity: RiskLevel = RiskLevel.INFO
    security_score: float = Field(default=100.0, ge=0.0, le=100.0)
    summary: str = ""
    owasp_top10_coverage: list[str] = Field(default_factory=list)
    credential_exposure_count: int = 0
    injection_risk_count: int = 0
    misconfiguration_count: int = 0


# ---------------------------------------------------------------------------
# Code quality review
# ---------------------------------------------------------------------------


class CodeSmellFinding(BaseModel):
    """A code-quality smell with engineering context."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    smell_type: str = Field(description="e.g. 'god_class', 'long_method'.")
    title: str
    severity: RiskLevel = RiskLevel.MEDIUM
    file: str
    line: int | None = None
    description: str
    impact: str = Field(description="Maintenance / readability impact.")
    recommendation: str
    effort: str = Field(default="medium", description="low/medium/high.")
    metadata: dict[str, Any] = Field(default_factory=dict)


class CodeQualityReview(BaseModel):
    """Aggregate code-quality review."""

    model_config = ConfigDict(extra="forbid")

    smells: list[CodeSmellFinding] = Field(default_factory=list)
    quality_score: float = Field(default=100.0, ge=0.0, le=100.0)
    summary: str = ""
    duplicate_code_percentage: float = 0.0
    dead_code_count: int = 0
    complexity_hotspots: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Architecture review
# ---------------------------------------------------------------------------


class ArchitectureObservation(BaseModel):
    """A single architectural observation."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    topic: str = Field(description="e.g. 'layer_separation', 'solid_dip'.")
    assessment: str = Field(description="What was found.")
    impact: str = Field(description="Why it matters architecturally.")
    recommendation: str
    severity: RiskLevel = RiskLevel.MEDIUM


class ArchitectureReview(BaseModel):
    """Aggregate architecture review."""

    model_config = ConfigDict(extra="forbid")

    observations: list[ArchitectureObservation] = Field(default_factory=list)
    architecture_score: float = Field(default=100.0, ge=0.0, le=100.0)
    summary: str = ""
    layer_separation: str = Field(default="unknown")
    dependency_direction: str = Field(default="unknown")
    modularity: str = Field(default="unknown")
    solid_assessment: dict[str, str] = Field(default_factory=dict)
    dry_assessment: str = ""
    kiss_assessment: str = ""
    yagni_assessment: str = ""
    composition_vs_inheritance: str = ""
    di_assessment: str = ""
    abstraction_level: str = ""
    technical_debt_areas: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# File / directory / project reviews
# ---------------------------------------------------------------------------


class FileReview(BaseModel):
    """Review of a single important file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    purpose: str = ""
    responsibilities: list[str] = Field(default_factory=list)
    code_quality: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    refactor_suggestions: list[str] = Field(default_factory=list)
    priority: RiskLevel = RiskLevel.LOW
    estimated_effort: str = Field(default="low")
    maintenance_cost: str = Field(default="low")


class DirectoryReview(BaseModel):
    """Review of a single directory."""

    model_config = ConfigDict(extra="forbid")

    path: str
    purpose: str = ""
    well_organized: bool = True
    organization_assessment: str = ""
    dependency_assessment: str = ""
    size_assessment: str = ""
    should_split: bool = False
    split_recommendation: str = ""
    risks: list[str] = Field(default_factory=list)


class ProjectReview(BaseModel):
    """Project-level review."""

    model_config = ConfigDict(extra="forbid")

    code_readability: str = ""
    maintainability: str = ""
    onboarding_difficulty: str = ""
    testability: str = ""
    long_term_sustainability: str = ""
    architectural_maturity: str = ""
    technical_debt_summary: str = ""
    development_velocity: str = ""
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Risk / technical debt / refactor
# ---------------------------------------------------------------------------


class RiskItem(BaseModel):
    """A single ranked risk."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    title: str
    level: RiskLevel
    probability: str = Field(default="medium", description="low/medium/high.")
    impact: str = Field(default="medium", description="low/medium/high.")
    fix_cost: str = Field(default="medium", description="low/medium/high.")
    recommended_timeline: str = Field(default="1-2 weeks")
    description: str = ""
    affected_files: list[str] = Field(default_factory=list)


class RiskSummary(BaseModel):
    """Aggregate risk summary."""

    model_config = ConfigDict(extra="forbid")

    critical: list[RiskItem] = Field(default_factory=list)
    high: list[RiskItem] = Field(default_factory=list)
    medium: list[RiskItem] = Field(default_factory=list)
    low: list[RiskItem] = Field(default_factory=list)
    overall_risk_level: RiskLevel = RiskLevel.LOW


class TechnicalDebtItem(BaseModel):
    """A single technical-debt item."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    category: str = Field(description="architecture/code/documentation/testing/security.")
    title: str
    description: str
    estimated_hours: float = 0.0
    estimated_developers: int = 1
    priority: RiskLevel = RiskLevel.MEDIUM
    affected_areas: list[str] = Field(default_factory=list)


class TechnicalDebt(BaseModel):
    """Aggregate technical-debt analysis."""

    model_config = ConfigDict(extra="forbid")

    architecture_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    code_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    documentation_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    testing_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    security_debt: list[TechnicalDebtItem] = Field(default_factory=list)
    total_estimated_hours: float = 0.0
    summary: str = ""


class RefactorItem(BaseModel):
    """A single refactor suggestion."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    impact: str = Field(default="medium", description="low/medium/high.")
    effort: str = Field(default="medium", description="low/medium/high.")
    affected_files: list[str] = Field(default_factory=list)
    breaking: bool = False


class RefactorPlan(BaseModel):
    """Aggregated refactor plan."""

    model_config = ConfigDict(extra="forbid")

    quick_wins: list[RefactorItem] = Field(default_factory=list)
    high_impact: list[RefactorItem] = Field(default_factory=list)
    long_term: list[RefactorItem] = Field(default_factory=list)
    breaking_changes: list[RefactorItem] = Field(default_factory=list)
    architecture_improvements: list[RefactorItem] = Field(default_factory=list)


class QuickWin(BaseModel):
    """A quick-win improvement."""

    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    effort_minutes: int = 0
    impact: str = "low"


# ---------------------------------------------------------------------------
# Health score (extended)
# ---------------------------------------------------------------------------


class ExtendedHealthScore(BaseModel):
    """Health score with 10 sub-scores and a letter grade."""

    model_config = ConfigDict(extra="forbid")

    overall: float = Field(default=0.0, ge=0.0, le=100.0)
    security: float = Field(default=0.0, ge=0.0, le=100.0)
    architecture: float = Field(default=0.0, ge=0.0, le=100.0)
    maintainability: float = Field(default=0.0, ge=0.0, le=100.0)
    performance: float = Field(default=0.0, ge=0.0, le=100.0)
    documentation: float = Field(default=0.0, ge=0.0, le=100.0)
    testing: float = Field(default=0.0, ge=0.0, le=100.0)
    developer_experience: float = Field(default=0.0, ge=0.0, le=100.0)
    scalability: float = Field(default=0.0, ge=0.0, le=100.0)
    code_quality: float = Field(default=0.0, ge=0.0, le=100.0)
    grade: Grade = Grade.F

    def compute_grade(self) -> None:
        """Recompute the letter grade from :attr:`overall`."""
        self.grade = Grade.from_score(self.overall)


__all__ = [
    "RiskLevel",
    "Grade",
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
]
