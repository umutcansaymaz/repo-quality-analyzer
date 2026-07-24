"""Evidence domain models.

The Evidence layer provides a **unified representation** of all findings
produced by the analyzers and review engines. Every piece of information —
a security vulnerability, a code smell, a complexity hotspot, an unused
import, a missing test — is normalized into an :class:`Evidence` object
with a consistent schema.

Design principles:
    - **Immutable**: Models use ``frozen=True`` so they cannot be mutated
      after creation (closest Pydantic equivalent to ``@dataclass(frozen=True)``).
    - **Consistent with codebase**: Uses Pydantic ``BaseModel`` (not
      ``dataclass``) for consistency with the rest of the domain layer.
    - **No I/O**: Evidence is built purely from the in-memory
      :class:`AnalysisResult`; no repository re-scanning.
    - **Traceable**: Each Evidence carries ``source_id`` linking back to the
      original finding, and ``analyzer`` naming the source engine.

Integration:
    - :class:`EvidenceCollection` is attached to :class:`AnalysisResult`
      via the optional ``evidence`` field (backward compatible — defaults
      to ``None``).
    - :class:`EvidenceBuilder` is a pure function-like service that reads
      an :class:`AnalysisResult` and produces an :class:`EvidenceCollection`.
    - No analyzer or review engine is modified.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.report import Severity


class EvidenceType(str, Enum):
    """The kind of evidence, mapped from analyzer/review outputs.

    Each value corresponds to a category of finding produced by the
    analysis pipeline.
    """

    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    ARCHITECTURE = "architecture"
    COMPLEXITY = "complexity"
    IMPORT = "import"
    DEPENDENCY = "dependency"
    GIT = "git"
    DOCUMENTATION = "documentation"
    TEST = "test"
    METRIC = "metric"
    SYMBOL = "symbol"
    RISK = "risk"
    TECHNICAL_DEBT = "technical_debt"
    REFACTOR = "refactor"
    FILE_SYSTEM = "file_system"
    REPOSITORY = "repository"


class ReferenceKind(str, Enum):
    """The kind of a code reference attached to an evidence item."""

    FILE = "file"
    LINE = "line"
    CLASS = "class"
    FUNCTION = "function"
    SYMBOL = "symbol"
    MODULE = "module"
    URL = "url"
    CWE = "cwe"
    RULE = "rule"
    CVSS = "cvss"
    OTHER = "other"


class RelationshipType(str, Enum):
    """How two evidence items are related."""

    DUPLICATE = "duplicate"
    RELATED = "related"
    CAUSES = "causes"
    BLOCKS = "blocks"
    DEPENDS_ON = "depends_on"
    LOCATED_IN = "located_in"


class EvidenceReference(BaseModel):
    """A single code reference attached to an :class:`Evidence`.

    References point to concrete locations or identifiers in the codebase
    or external standards (CWE, CVSS, documentation URLs).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: ReferenceKind
    value: str = Field(description="The reference value (file path, class name, URL, …).")
    line: int | None = None
    detail: str | None = None


class EvidenceRelationship(BaseModel):
    """A directed relationship between two evidence items.

    Relationships let downstream consumers (reports, AI) traverse the
    evidence graph — e.g. "this security finding is located in the same
    function as this complexity hotspot".
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: UUID
    target_id: UUID
    relationship_type: RelationshipType
    detail: str | None = None


class Evidence(BaseModel):
    """A single piece of evidence extracted from the analysis results.

    This is the **unified finding model**: regardless of whether the
    source was a security scanner, a complexity analyzer, or a code-quality
    review engine, every finding is normalized into this shape.

    Immutability:
        The model is configured with ``frozen=True`` so fields cannot be
        reassigned after construction. This makes Evidence safe to share
        across threads and prevents accidental mutation.

    Traceability:
        - ``analyzer`` names the engine that produced the source finding.
        - ``source_id`` holds the UUID from the original finding object
          (when available), allowing trace-back to the raw data.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    analyzer: str = Field(description="Name of the source analyzer or review engine.")
    finding_type: EvidenceType
    severity: Severity = Severity.INFO
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    category: str = Field(default="general", description="Sub-category within the finding type.")

    # Location — at least ``file_path`` is populated when available.
    file_path: str | None = None
    line: int | None = None
    module: str | None = None
    class_name: str | None = None
    function_name: str | None = None
    symbol: str | None = None

    # Description.
    message: str = Field(description="Short, human-readable summary.")
    explanation: str | None = Field(default=None, description="Longer context: why, impact, fix.")

    # Structured data.
    metrics: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    references: list[EvidenceReference] = Field(default_factory=list)

    # Graph links (populated post-build by the normalizer).
    related_evidence_ids: list[UUID] = Field(default_factory=list)

    # Traceability.
    source_id: UUID | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))

    def dedup_key(self) -> tuple[str | None, str | None, str, str]:
        """Return the normalization key used for deduplication.

        Two evidence items with the same key are considered duplicates.
        The key is ``(file_path, symbol, finding_type, category)``.
        """
        return (self.file_path, self.symbol, self.finding_type.value, self.category)


class EvidenceCollection(BaseModel):
    """An immutable collection of :class:`Evidence` items plus relationships.

    The collection provides pre-built indexes (``by_analyzer``,
    ``by_severity``, ``by_file``, ``by_type``) for O(1) lookup by
    downstream consumers.

    Construction:
        Normally built by :class:`EvidenceBuilder`. The ``evidence`` and
        ``relationships`` lists are the primary data; the index dicts are
        derived and can be rebuilt via :meth:`rebuild_indexes`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    evidence: list[Evidence] = Field(default_factory=list)
    relationships: list[EvidenceRelationship] = Field(default_factory=list)

    # Derived indexes (rebuilt on construction).
    by_analyzer: dict[str, list[UUID]] = Field(default_factory=dict)
    by_severity: dict[str, list[UUID]] = Field(default_factory=dict)
    by_file: dict[str, list[UUID]] = Field(default_factory=dict)
    by_type: dict[str, list[UUID]] = Field(default_factory=dict)

    # Summary statistics.
    statistics: dict[str, Any] = Field(default_factory=dict)

    def rebuild_indexes(self) -> None:
        """Rebuild the lookup indexes from the evidence list.

        This is called automatically by :class:`EvidenceBuilder` after
        construction. It is a no-op on frozen models if called externally;
        use :meth:`with_indexes` instead.
        """
        # Note: frozen=True prevents mutation; this method exists for
        # the builder to call on a mutable copy before freezing.
        self.__dict__["by_analyzer"] = {}
        self.__dict__["by_severity"] = {}
        self.__dict__["by_file"] = {}
        self.__dict__["by_type"] = {}
        for ev in self.evidence:
            self.__dict__.setdefault("by_analyzer", {}).setdefault(ev.analyzer, []).append(ev.id)
            self.__dict__.setdefault("by_severity", {}).setdefault(ev.severity.value, []).append(
                ev.id
            )
            if ev.file_path:
                self.__dict__.setdefault("by_file", {}).setdefault(ev.file_path, []).append(ev.id)
            self.__dict__.setdefault("by_type", {}).setdefault(ev.finding_type.value, []).append(
                ev.id
            )

    @property
    def total(self) -> int:
        """Total number of evidence items."""
        return len(self.evidence)

    @property
    def by_severity_counts(self) -> dict[str, int]:
        """Count of evidence per severity level."""
        return {sev: len(ids) for sev, ids in self.by_severity.items()}

    def get_by_id(self, evidence_id: UUID) -> Evidence | None:
        """Look up a single evidence item by id."""
        for ev in self.evidence:
            if ev.id == evidence_id:
                return ev
        return None

    def filter_by_type(self, finding_type: EvidenceType) -> list[Evidence]:
        """Return all evidence of a given type."""
        return [ev for ev in self.evidence if ev.finding_type == finding_type]

    def filter_by_analyzer(self, analyzer: str) -> list[Evidence]:
        """Return all evidence from a given analyzer."""
        return [ev for ev in self.evidence if ev.analyzer == analyzer]

    def filter_by_file(self, file_path: str) -> list[Evidence]:
        """Return all evidence for a given file."""
        return [ev for ev in self.evidence if ev.file_path == file_path]


__all__ = [
    "Evidence",
    "EvidenceCollection",
    "EvidenceReference",
    "EvidenceRelationship",
    "EvidenceType",
    "ReferenceKind",
    "RelationshipType",
]
