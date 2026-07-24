"""Engineering Planning domain models.

The Planning layer transforms root causes into an actionable engineering
roadmap. It answers: "Given these root causes, what should we fix first,
in what order, and what will we gain?"

Design principles:
    - **Immutable**: All models use ``frozen=True``.
    - **Evidence-backed**: Every planning step links back to the root
      causes and evidence that motivated it.
    - **Deterministic**: The priority ordering is reproducible — same
      input always produces the same output.
    - **Extensible**: Impact factors and ROI weights are data-driven,
      not hardcoded in conditionals.

Integration:
    - :class:`EngineeringPlan` is attached to :class:`AnalysisResult`
      via the optional ``engineering_plan`` field (backward compatible).
    - :class:`PlanningEngine` reads a :class:`RootCauseCollection` and
      produces an :class:`EngineeringPlan`.
    - No root cause engine, graph builder, or analyzer is modified.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EngineeringPriority(str, Enum):
    """Priority level for a planning step — drives ordering."""

    CRITICAL = "critical"  # ★★★★★ — must fix before release
    HIGH = "high"  # ★★★★☆ — fix this sprint
    MEDIUM = "medium"  # ★★★☆☆ — fix next sprint
    LOW = "low"  # ★★☆☆☆ — fix when time allows
    INFORMATIONAL = "info"  # ★☆☆☆☆ — nice to have


class EngineeringRisk(str, Enum):
    """Risk level of executing a planning step."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class EstimationUnit(str, Enum):
    """Unit for engineering effort estimation."""

    MINUTES = "minutes"
    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class ImpactDimension(str, Enum):
    """Dimensions along which a root cause impacts the codebase."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    MAINTAINABILITY = "maintainability"
    TESTABILITY = "testability"
    ARCHITECTURE = "architecture"
    DEVELOPER_EXPERIENCE = "developer_experience"


class EngineeringEstimate(BaseModel):
    """Effort estimation for a planning step.

    Estimates are intentionally rough — they give a ballpark, not a
    commitment. The ``hours`` field is the canonical unit; other fields
    are derived for readability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    hours: float = Field(ge=0.0, description="Estimated effort in engineer-hours.")
    confidence: float = Field(
        default=0.5, ge=0.0, le=1.0, description="How confident we are in the estimate."
    )
    developers: int = Field(default=1, ge=1, description="Suggested team size.")

    @property
    def display(self) -> str:
        """Human-readable estimation string."""
        if self.hours < 1:
            return f"{int(self.hours * 60)} min"
        if self.hours < 8:
            return f"{self.hours:.0f} hours"
        if self.hours < 40:
            return f"{self.hours / 8:.0f} days"
        return f"{self.hours / 40:.0f} weeks"


class EngineeringBenefit(BaseModel):
    """Expected benefit of fixing a root cause.

    Each dimension is scored 0-100 (higher = more benefit from fixing).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    security_benefit: float = Field(default=0.0, ge=0.0, le=100.0)
    maintainability_benefit: float = Field(default=0.0, ge=0.0, le=100.0)
    testability_benefit: float = Field(default=0.0, ge=0.0, le=100.0)
    performance_benefit: float = Field(default=0.0, ge=0.0, le=100.0)
    developer_experience_benefit: float = Field(default=0.0, ge=0.0, le=100.0)

    @property
    def total(self) -> float:
        """Weighted total benefit score (0-100)."""
        return (
            self.security_benefit * 0.25
            + self.maintainability_benefit * 0.25
            + self.testability_benefit * 0.20
            + self.performance_benefit * 0.15
            + self.developer_experience_benefit * 0.15
        )


class ImpactScore(BaseModel):
    """Impact of a root cause on the codebase.

    Computed by :class:`ImpactAnalyzer` from root cause properties and
    graph topology. Each dimension is scored 0-100 (higher = worse impact).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    overall: float = Field(default=0.0, ge=0.0, le=100.0)
    severity_score: float = Field(default=0.0, ge=0.0, le=100.0)
    evidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    scope_score: float = Field(default=0.0, ge=0.0, le=100.0)
    dependency_centrality: float = Field(default=0.0, ge=0.0, le=100.0)
    security_impact: float = Field(default=0.0, ge=0.0, le=100.0)
    performance_impact: float = Field(default=0.0, ge=0.0, le=100.0)
    maintainability_impact: float = Field(default=0.0, ge=0.0, le=100.0)
    testability_impact: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence_factor: float = Field(default=1.0, ge=0.0, le=1.0)

    #: The root cause this score belongs to.
    root_cause_id: UUID | None = None


class TradeOffAlternative(BaseModel):
    """An alternative solution for a planning step.

    Each planning step should have at least two alternatives so the
    team can make an informed trade-off.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Short name (e.g. 'Extract Service', 'Inline Class').")
    description: str = ""
    advantages: list[str] = Field(default_factory=list)
    disadvantages: list[str] = Field(default_factory=list)
    risk: EngineeringRisk = EngineeringRisk.MEDIUM
    maintenance_cost: str = Field(default="medium", description="low/medium/high")
    performance_impact: str = Field(default="neutral", description="positive/neutral/negative")
    migration_difficulty: str = Field(default="medium", description="low/medium/high")
    estimated_effort: EngineeringEstimate | None = None


class PlanningStep(BaseModel):
    """A single step in the engineering plan.

    Each step corresponds to one root cause and describes what to do,
    why, what the expected benefit is, how long it will take, what the
    risks are, and what prerequisites must be met first.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    step_number: int = Field(ge=1, description="1-based position in the plan.")
    title: str = Field(
        description="Action title (e.g. 'Refactor UserService into 3 focused services')."
    )
    technical_description: str = Field(description="What specifically to do.")
    root_cause_id: UUID = Field(description="The root cause this step addresses.")
    root_cause_category: str = ""

    # Priority + scoring.
    priority: EngineeringPriority = EngineeringPriority.MEDIUM
    impact_score: ImpactScore | None = None
    benefit: EngineeringBenefit | None = None
    roi: float = Field(
        default=0.0, description="Return on Engineering Investment (benefit / cost)."
    )

    # Effort + risk.
    estimate: EngineeringEstimate | None = None
    risk: EngineeringRisk = EngineeringRisk.MEDIUM
    risk_reason: str = Field(default="", description="Why this risk level was assigned.")

    # Dependencies.
    prerequisites: list[UUID] = Field(
        default_factory=list, description="Step IDs that must complete first."
    )
    blocked_by: list[UUID] = Field(
        default_factory=list, description="Root cause IDs that block this step."
    )

    # Expected outcomes.
    expected_outcomes: list[str] = Field(default_factory=list)

    # Alternatives (trade-off analysis).
    alternatives: list[TradeOffAlternative] = Field(default_factory=list)

    # Affected scope.
    affected_files: list[str] = Field(default_factory=list)
    affected_modules: list[str] = Field(default_factory=list)

    # Metadata.
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuickWinItem(BaseModel):
    """A quick win — low effort, high benefit item.

    Quick wins are extracted from planning steps where the effort is
    ≤ 30 minutes and the benefit is above a threshold.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str = ""
    effort_minutes: int = Field(ge=1)
    benefit: str = ""
    planning_step_id: UUID | None = None
    root_cause_id: UUID | None = None


class BlockerItem(BaseModel):
    """A blocker — a root cause that prevents other refactoring.

    For example, "Authentication Refactoring must complete before
    Session Refactoring can begin."
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    blocker_root_cause_id: UUID
    blocked_root_cause_ids: list[UUID] = Field(default_factory=list)
    reason: str = ""
    planning_step_id: UUID | None = None


class SprintRecommendation(BaseModel):
    """A sprint-sized batch of planning steps.

    The planning engine groups steps into sprints so the team can
    execute them incrementally. Each sprint has a target effort budget.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    sprint_number: int = Field(ge=1)
    title: str = Field(description="Sprint theme (e.g. 'Security Hardening').")
    step_ids: list[UUID] = Field(default_factory=list)
    total_estimated_hours: float = Field(default=0.0, ge=0.0)
    goals: list[str] = Field(default_factory=list)
    steps: list[PlanningStep] = Field(default_factory=list)


class Roadmap(BaseModel):
    """An ordered sequence of sprint recommendations.

    The roadmap is the top-level output of the planning engine — it
    tells the team "do this first, then this, then this."
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    sprints: list[SprintRecommendation] = Field(default_factory=list)
    total_estimated_hours: float = Field(default=0.0, ge=0.0)
    total_steps: int = Field(default=0, ge=0)
    summary: str = ""


class EngineeringPlan(BaseModel):
    """The complete engineering plan produced by :class:`PlanningEngine`.

    Contains:
        - Ordered :class:`PlanningStep` list (priority-sorted).
        - :class:`Roadmap` (steps grouped into sprints).
        - :class:`QuickWinItem` list (low-effort high-benefit items).
        - :class:`BlockerItem` list (dependency blockers).
        - :class:`ImpactScore` for each root cause.
        - Summary statistics.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    steps: list[PlanningStep] = Field(default_factory=list)
    roadmap: Roadmap | None = None
    quick_wins: list[QuickWinItem] = Field(default_factory=list)
    blockers: list[BlockerItem] = Field(default_factory=list)
    impact_scores: list[ImpactScore] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_steps(self) -> int:
        """Total number of planning steps."""
        return len(self.steps)

    def get_step(self, step_id: UUID) -> PlanningStep | None:
        """Look up a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def steps_by_priority(self, priority: EngineeringPriority) -> list[PlanningStep]:
        """Return all steps of a given priority."""
        return [s for s in self.steps if s.priority == priority]


__all__ = [
    "BlockerItem",
    "EngineeringBenefit",
    "EngineeringEstimate",
    "EngineeringPlan",
    "EngineeringPriority",
    "EngineeringRisk",
    "EstimationUnit",
    "ImpactDimension",
    "ImpactScore",
    "PlanningStep",
    "QuickWinItem",
    "Roadmap",
    "SprintRecommendation",
    "TradeOffAlternative",
]
