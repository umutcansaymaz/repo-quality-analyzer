"""Health-score domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Grade(str, Enum):
    """Letter grade corresponding to a numeric health score."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"

    @classmethod
    def from_score(cls, score: float) -> Grade:
        """Map a 0-100 score to a :class:`Grade`."""
        if score >= 90:
            return cls.A
        if score >= 80:
            return cls.B
        if score >= 70:
            return cls.C
        if score >= 60:
            return cls.D
        if score >= 50:
            return cls.E
        return cls.F


class ScoreWeights(BaseModel):
    """Weights used to combine subscores into the overall health score.

    Mirrors the JS scoring engine (src/lib/local-analysis.ts): the web
    dashboard uses an 8-dimension weighted model where security=0.15,
    architecture=0.20, quality=0.25, test=0.15, docs=0.10, performance=0.05,
    dx=0.05, scalability=0.05. The four core weights below are normalized
    to the same relative balance when combined with the remaining signals.

    Weights are normalized to sum to 1.0 during validation.
    """

    model_config = ConfigDict(extra="forbid")

    security: float = Field(default=0.15, ge=0.0, le=1.0)
    quality: float = Field(default=0.25, ge=0.0, le=1.0)
    architecture: float = Field(default=0.20, ge=0.0, le=1.0)
    test: float = Field(default=0.15, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _normalize(self) -> ScoreWeights:
        total = self.security + self.quality + self.architecture + self.test
        if total <= 0:
            raise ValueError("Score weights must be positive")
        if abs(total - 1.0) > 0.001:
            self.security = self.security / total
            self.quality = self.quality / total
            self.architecture = self.architecture / total
            self.test = self.test / total
        return self


class HealthScore(BaseModel):
    """The overall health score of an analyzed repository.

    The structure is complete; the actual computation lives in the metrics
    engine and is wired in later phases. At this stage the model only carries
    the infrastructure to hold and validate scores.
    """

    model_config = ConfigDict(extra="forbid")

    overall: float = Field(default=0.0, ge=0.0, le=100.0)
    security_score: float = Field(default=0.0, ge=0.0, le=100.0)
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0)
    architecture_score: float = Field(default=0.0, ge=0.0, le=100.0)
    test_score: float = Field(default=0.0, ge=0.0, le=100.0)
    weights: ScoreWeights = Field(default_factory=ScoreWeights)
    breakdown: dict[str, Any] = Field(default_factory=dict)

    @field_validator("overall")
    @classmethod
    def _clamp_overall(cls, value: float) -> float:
        return max(0.0, min(100.0, value))

    @property
    def grade(self) -> Grade:
        """Letter grade derived from :attr:`overall`."""
        return Grade.from_score(self.overall)

    def recompute_overall(self) -> None:
        """Recompute :attr:`overall` from the subscores and weights.

        This is the only computation this model performs at the infrastructure
        stage; full scoring logic is added in later phases by the metrics
        engine.
        """
        w = self.weights
        self.overall = (
            self.security_score * w.security
            + self.quality_score * w.quality
            + self.architecture_score * w.architecture
            + self.test_score * w.test
        )


__all__ = ["Grade", "HealthScore", "ScoreWeights"]
