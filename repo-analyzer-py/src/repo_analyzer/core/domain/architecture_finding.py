"""Architecture finding domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.report import Location, Severity


class ArchitectureSmellType(str, Enum):
    """Recognized architecture smell types."""

    CYCLIC_DEPENDENCY = "cyclic_dependency"
    LAYER_VIOLATION = "layer_violation"
    GOD_CLASS = "god_class"
    FEATURE_ENVY = "feature_envy"
    HUB_LIKE = "hub_like"
    UNSTABLE_DEPENDENCY = "unstable_dependency"
    OTHER = "other"


class Layer(BaseModel):
    """A detected architectural layer."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path_patterns: list[str] = Field(default_factory=list)
    modules: list[str] = Field(default_factory=list)


class Cycle(BaseModel):
    """A cyclic dependency between modules."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[str] = Field(min_length=2)
    description: str | None = None

    def __str__(self) -> str:
        return " -> ".join([*self.nodes, self.nodes[0]])


class ArchitectureSmell(BaseModel):
    """A single detected architecture smell."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    type: ArchitectureSmellType
    severity: Severity = Severity.MEDIUM
    message: str
    location: Location | None = None
    affected_modules: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArchitectureFinding(BaseModel):
    """An aggregate architecture report for a repository."""

    model_config = ConfigDict(extra="forbid")

    layers: list[Layer] = Field(default_factory=list)
    cycles: list[Cycle] = Field(default_factory=list)
    smells: list[ArchitectureSmell] = Field(default_factory=list)
    coupling: float = Field(default=0.0, ge=0.0, le=1.0)
    cohesion: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_issues(self) -> bool:
        """``True`` if any cycle or smell was detected."""
        return bool(self.cycles or self.smells)


__all__ = [
    "ArchitectureFinding",
    "ArchitectureSmell",
    "ArchitectureSmellType",
    "Cycle",
    "Layer",
]
