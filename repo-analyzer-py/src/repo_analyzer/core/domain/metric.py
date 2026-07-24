"""Metric domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class MetricUnit(str, Enum):
    """Units for metric values."""

    COUNT = "count"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    SECONDS = "seconds"
    BYTES = "bytes"
    LINES = "lines"
    SCORE = "score"
    INDEX = "index"
    NONE = "none"


class MetricScope(str, Enum):
    """Scope at which a metric applies."""

    REPOSITORY = "repository"
    MODULE = "module"
    FILE = "file"
    FUNCTION = "function"
    CLASS = "class"


class Metric(BaseModel):
    """A single metric measurement."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(description="Metric name, e.g. 'cyclomatic_complexity'.")
    value: float
    unit: MetricUnit = MetricUnit.NONE
    scope: MetricScope = MetricScope.REPOSITORY
    target: str | None = Field(default=None, description="Path or symbol the metric applies to.")
    threshold: float | None = Field(default=None, description="Pass/fail threshold.")
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def passes_threshold(self) -> bool:
        """``True`` if the metric is within its threshold (if set).

        For metrics where lower is better (e.g. complexity) the threshold is
        treated as a maximum; for metrics where higher is better (e.g.
        coverage) it is treated as a minimum. The direction is inferred from
        ``metadata['lower_is_better']`` (default ``True``).
        """
        if self.threshold is None:
            return True
        lower_is_better = self.metadata.get("lower_is_better", True)
        if lower_is_better:
            return self.value <= self.threshold
        return self.value >= self.threshold


__all__ = ["Metric", "MetricScope", "MetricUnit"]
