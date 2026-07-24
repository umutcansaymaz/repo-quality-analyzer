"""Root Cause Detection domain models.

The Root Cause layer analyzes the :class:`EngineeringGraph` to discover
**architectural root causes** — patterns where many individual findings
share a common underlying problem.

Design principles:
    - **Immutable**: All models use ``frozen=True``.
    - **Graph-native**: Root causes are derived from graph traversal, not
      from re-scanning the repository.
    - **Evidence-backed**: Every root cause links to the specific
      :class:`Evidence` items that support it.
    - **Confidence-scored**: Each root cause carries a confidence score
      reflecting evidence count, analyzer diversity, and graph strength.

Integration:
    - :class:`RootCauseCollection` is attached to :class:`AnalysisResult`
      via the optional ``root_causes`` field (backward compatible).
    - :class:`RootCauseDetectionEngine` reads an :class:`EngineeringGraph`
      and produces a :class:`RootCauseCollection`.
    - No evidence builder, graph builder, analyzer, or review engine is
      modified.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class RootCauseCategory(str, Enum):
    """The architectural category of a root cause.

    Each value corresponds to a recognized architectural anti-pattern
    or design smell that the detection engine can identify.
    """

    GOD_CLASS = "god_class"
    GOD_SERVICE = "god_service"
    LARGE_MODULE = "large_module"
    FEATURE_ENVY = "feature_envy"
    SHOTGUN_SURGERY = "shotgun_surgery"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    TIGHT_COUPLING = "tight_coupling"
    LOW_COHESION = "low_cohesion"
    HIGH_INSTABILITY = "high_instability"
    DEPENDENCY_EXPLOSION = "dependency_explosion"
    OVERSIZED_INTERFACE = "oversized_interface"
    ANEMIC_DOMAIN_MODEL = "anemic_domain_model"
    DATA_CLUMPS = "data_clumps"
    PRIMITIVE_OBSESSION = "primitive_obsession"
    MAGIC_CONSTANTS = "magic_constants"
    DUPLICATED_RESPONSIBILITY = "duplicated_responsibility"
    LAYER_VIOLATION = "layer_violation"
    DIP_VIOLATION = "dip_violation"
    SRP_VIOLATION = "srp_violation"
    OCP_VIOLATION = "ocp_violation"
    ISP_VIOLATION = "isp_violation"
    LSP_RISK = "lsp_risk"
    OVERSIZED_SERVICE = "oversized_service"


class RootCauseSeverity(str, Enum):
    """Severity of a root cause — drives prioritization."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RootCauseRelationshipType(str, Enum):
    """How two root causes are related."""

    CAUSES = "causes"
    LEADS_TO = "leads_to"
    AGGRAVATES = "aggravates"
    MITIGATES = "mitigates"
    CO_OCCURS_WITH = "co_occurs_with"


class RootCauseEvidence(BaseModel):
    """A link from a root cause to a specific piece of evidence.

    Records *why* this evidence supports the root cause and how strongly
    it contributes to the confidence score.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: UUID
    contribution: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="How strongly this evidence supports the root cause (0-1).",
    )
    reason: str = Field(description="Why this evidence supports the root cause.")


class RootCauseRelationship(BaseModel):
    """A directed relationship between two root causes.

    For example: ``Oversized Service → causes → Tight Coupling``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_root_cause_id: UUID
    target_root_cause_id: UUID
    relationship_type: RootCauseRelationshipType
    detail: str | None = None


class RootCause(BaseModel):
    """A single architectural root cause discovered by the engine.

    A root cause groups multiple evidence items that share a common
    underlying problem. For example, if a class has high complexity,
    many long methods, low testability, and duplicate logic, these are
    all symptoms of the root cause **God Class**.

    Immutability:
        Configured with ``frozen=True``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    id: UUID = Field(default_factory=uuid4)
    category: RootCauseCategory
    title: str = Field(description="Human-readable name (e.g. 'God Class: UserService').")
    severity: RootCauseSeverity = RootCauseSeverity.MEDIUM
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score (0-1) based on evidence count, diversity, and graph strength.",
    )

    # Explanation.
    description: str = Field(default="", description="What this root cause means.")
    technical_rationale: str = Field(
        default="", description="Why the evidence supports this conclusion."
    )
    root_cause_origin: str = Field(
        default="",
        description="Likely reason this problem exists (e.g. 'organic growth without refactoring').",
    )

    # Affected scope.
    affected_modules: list[str] = Field(default_factory=list)
    affected_classes: list[str] = Field(default_factory=list)
    affected_files: list[str] = Field(default_factory=list)

    # Supporting evidence.
    evidence_links: list[RootCauseEvidence] = Field(default_factory=list)

    # Graph node IDs that are at the center of this root cause.
    central_node_ids: list[UUID] = Field(default_factory=list)

    # Metadata for downstream consumers.
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def evidence_count(self) -> int:
        """Number of evidence items supporting this root cause."""
        return len(self.evidence_links)

    @property
    def evidence_ids(self) -> list[UUID]:
        """List of evidence IDs linked to this root cause."""
        return [link.evidence_id for link in self.evidence_links]


class RootCauseCollection(BaseModel):
    """An immutable collection of :class:`RootCause` items plus relationships.

    Provides indexes for fast lookup by category, severity, and affected file.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    root_causes: list[RootCause] = Field(default_factory=list)
    relationships: list[RootCauseRelationship] = Field(default_factory=list)

    # Derived indexes.
    by_category: dict[str, list[UUID]] = Field(default_factory=dict)
    by_severity: dict[str, list[UUID]] = Field(default_factory=dict)
    by_file: dict[str, list[UUID]] = Field(default_factory=dict)
    by_evidence: dict[str, list[UUID]] = Field(default_factory=dict)

    # Summary statistics.
    statistics: dict[str, Any] = Field(default_factory=dict)

    @property
    def total(self) -> int:
        """Total number of root causes."""
        return len(self.root_causes)

    def get_by_id(self, root_cause_id: UUID) -> RootCause | None:
        """Look up a root cause by ID."""
        for rc in self.root_causes:
            if rc.id == root_cause_id:
                return rc
        return None

    def filter_by_category(self, category: RootCauseCategory) -> list[RootCause]:
        """Return all root causes of a given category."""
        return [rc for rc in self.root_causes if rc.category == category]

    def filter_by_severity(self, severity: RootCauseSeverity) -> list[RootCause]:
        """Return all root causes of a given severity."""
        return [rc for rc in self.root_causes if rc.severity == severity]

    def for_file(self, file_path: str) -> list[RootCause]:
        """Return all root causes affecting a given file."""
        return [rc for rc in self.root_causes if file_path in rc.affected_files]

    def for_evidence(self, evidence_id: UUID) -> list[RootCause]:
        """Return all root causes that reference a given evidence item."""
        return [rc for rc in self.root_causes if evidence_id in rc.evidence_ids]


__all__ = [
    "RootCause",
    "RootCauseCategory",
    "RootCauseCollection",
    "RootCauseEvidence",
    "RootCauseRelationship",
    "RootCauseRelationshipType",
    "RootCauseSeverity",
]
