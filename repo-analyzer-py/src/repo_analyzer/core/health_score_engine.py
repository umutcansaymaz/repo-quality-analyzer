"""Health-score engine.

At the infrastructure stage the engine only provides the scaffolding to
construct, combine and serialize :class:`HealthScore` instances. The actual
scoring heuristics (translating findings/metrics into subscores) are added
in a later phase (see SDD v0.1).
"""

from __future__ import annotations

from typing import Any

from repo_analyzer.core.domain.health_score import Grade, HealthScore, ScoreWeights
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class HealthScoreEngine:
    """Computes :class:`HealthScore` from analysis artifacts.

    The engine is intentionally generic: it accepts pre-computed subscores
    (0-100) and combines them using the configured :class:`ScoreWeights`.
    The heuristics that turn raw findings into subscores are plugged in
    during the analysis phase.
    """

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self._weights = weights or ScoreWeights()

    @property
    def weights(self) -> ScoreWeights:
        """The active score weights."""
        return self._weights

    def compute(
        self,
        *,
        security_score: float = 0.0,
        quality_score: float = 0.0,
        architecture_score: float = 0.0,
        test_score: float = 0.0,
        breakdown: dict[str, Any] | None = None,
    ) -> HealthScore:
        """Combine subscores into a :class:`HealthScore`.

        Args:
            security_score: 0-100 security subscore.
            quality_score: 0-100 quality subscore.
            architecture_score: 0-100 architecture subscore.
            test_score: 0-100 test subscore.
            breakdown: Optional diagnostic dict.

        Returns:
            A :class:`HealthScore` with :attr:`~HealthScore.overall` computed.
        """
        score = HealthScore(
            security_score=self._clamp(security_score),
            quality_score=self._clamp(quality_score),
            architecture_score=self._clamp(architecture_score),
            test_score=self._clamp(test_score),
            weights=self._weights,
            breakdown=breakdown or {},
        )
        score.recompute_overall()
        _logger.debug(
            "Computed health score: overall=%.1f grade=%s",
            score.overall,
            score.grade.value,
        )
        return score

    @staticmethod
    def grade_for(score: float) -> Grade:
        """Return the :class:`Grade` for a 0-100 numeric score."""
        return Grade.from_score(score)

    @staticmethod
    def _clamp(value: float) -> float:
        """Clamp a value to the [0, 100] range."""
        return max(0.0, min(100.0, float(value)))


__all__ = ["HealthScoreEngine"]
