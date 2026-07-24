"""Tests for :class:`HealthScoreEngine`."""

from __future__ import annotations

from repo_analyzer.core.domain.health_score import Grade, ScoreWeights
from repo_analyzer.core.health_score_engine import HealthScoreEngine


def test_compute_with_defaults() -> None:
    """Default weights should produce a weighted average."""
    engine = HealthScoreEngine()
    score = engine.compute(
        security_score=100,
        quality_score=100,
        architecture_score=100,
        test_score=100,
    )
    assert score.overall == 100.0
    assert score.grade == Grade.A


def test_compute_with_zeros() -> None:
    engine = HealthScoreEngine()
    score = engine.compute()
    assert score.overall == 0.0
    assert score.grade == Grade.F


def test_compute_clamps_high_values() -> None:
    """Values above 100 should be clamped to 100."""
    engine = HealthScoreEngine()
    score = engine.compute(security_score=150, quality_score=200)
    assert score.security_score == 100.0
    assert score.quality_score == 100.0


def test_compute_clamps_negative_values() -> None:
    """Negative values should be clamped to 0."""
    engine = HealthScoreEngine()
    score = engine.compute(security_score=-10)
    assert score.security_score == 0.0


def test_compute_with_custom_weights() -> None:
    weights = ScoreWeights(security=1.0, quality=0.0, architecture=0.0, test=0.0)
    engine = HealthScoreEngine(weights)
    score = engine.compute(security_score=80, quality_score=0, architecture_score=0, test_score=0)
    assert abs(score.overall - 80.0) < 0.01


def test_compute_stores_breakdown() -> None:
    engine = HealthScoreEngine()
    score = engine.compute(breakdown={"note": "test"})
    assert score.breakdown == {"note": "test"}


def test_grade_for() -> None:
    assert HealthScoreEngine.grade_for(95) == Grade.A
    assert HealthScoreEngine.grade_for(30) == Grade.F


def test_compute_weights_property() -> None:
    weights = ScoreWeights()
    engine = HealthScoreEngine(weights)
    assert engine.weights is weights
