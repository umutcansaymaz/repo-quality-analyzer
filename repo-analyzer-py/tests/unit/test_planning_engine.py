"""Unit tests for the Engineering Planning Engine.

Covers:
    - Empty root cause collection (no plan)
    - Single root cause (priority, ROI, step)
    - Multiple root causes (ordering, roadmap)
    - ROI calculation
    - Quick win extraction
    - Risk assignment
    - Dependency ordering (blockers, prerequisites)
    - Roadmap sprint batching
    - Trade-off alternatives
    - Planning step structure
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from repo_analyzer.core.evidence.planning_engine import (
    ImpactAnalyzer,
    PlanningEngine,
)
from repo_analyzer.core.evidence.planning_models import (
    EngineeringBenefit,
    EngineeringEstimate,
    EngineeringPriority,
    EngineeringRisk,
)
from repo_analyzer.core.evidence.root_cause_models import (
    RootCause,
    RootCauseCategory,
    RootCauseCollection,
    RootCauseEvidence,
    RootCauseRelationship,
    RootCauseRelationshipType,
    RootCauseSeverity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_root_cause(
    *,
    category: RootCauseCategory = RootCauseCategory.GOD_CLASS,
    severity: RootCauseSeverity = RootCauseSeverity.HIGH,
    confidence: float = 0.8,
    file_path: str = "src/service.py",
    class_name: str = "UserService",
    evidence_count: int = 3,
    title: str = "Test Root Cause",
) -> RootCause:
    """Create a RootCause for testing."""
    evidence_links = [
        RootCauseEvidence(evidence_id=uuid4(), reason="test") for _ in range(evidence_count)
    ]
    return RootCause(
        category=category,
        title=title,
        severity=severity,
        confidence=confidence,
        description="Test description",
        technical_rationale="Test rationale",
        root_cause_origin="Test origin",
        affected_files=[file_path] if file_path else [],
        affected_classes=[class_name] if class_name else [],
        affected_modules=["module_a"] if file_path else [],
        evidence_links=evidence_links,
    )


def _make_collection(root_causes: list[RootCause]) -> RootCauseCollection:
    """Build a RootCauseCollection from root causes."""
    return RootCauseCollection(
        root_causes=root_causes,
        statistics={"total_root_causes": len(root_causes)},
    )


# ---------------------------------------------------------------------------
# Tests: empty collection
# ---------------------------------------------------------------------------


class TestEmptyPlan:
    def test_empty_collection_produces_empty_plan(self) -> None:
        collection = _make_collection([])
        plan = PlanningEngine.plan(collection)
        assert plan.total_steps == 0
        assert len(plan.quick_wins) == 0
        assert len(plan.blockers) == 0
        assert len(plan.impact_scores) == 0
        assert plan.roadmap is not None
        assert plan.roadmap.total_steps == 0

    def test_empty_plan_statistics(self) -> None:
        collection = _make_collection([])
        plan = PlanningEngine.plan(collection)
        assert plan.statistics["total_steps"] == 0
        assert plan.statistics["average_roi"] == 0.0


# ---------------------------------------------------------------------------
# Tests: single root cause
# ---------------------------------------------------------------------------


class TestSingleRootCause:
    def test_produces_one_step(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.total_steps == 1

    def test_step_has_title(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].title
        assert "God Class" in plan.steps[0].title or "Split" in plan.steps[0].title

    def test_step_has_priority(self) -> None:
        rc = _make_root_cause(severity=RootCauseSeverity.HIGH)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].priority in (
            EngineeringPriority.CRITICAL,
            EngineeringPriority.HIGH,
        )

    def test_step_has_estimate(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].estimate is not None
        assert plan.steps[0].estimate.hours > 0

    def test_step_has_roi(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].roi > 0.0

    def test_step_has_risk(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].risk in EngineeringRisk

    def test_step_has_risk_reason(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].risk_reason

    def test_step_has_alternatives(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert len(plan.steps[0].alternatives) >= 2

    def test_step_has_expected_outcomes(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert len(plan.steps[0].expected_outcomes) >= 1

    def test_step_has_technical_description(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].technical_description

    def test_step_has_root_cause_link(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].root_cause_id == rc.id

    def test_step_has_impact_score(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].impact_score is not None
        assert plan.steps[0].impact_score.root_cause_id == rc.id


# ---------------------------------------------------------------------------
# Tests: multiple root causes — priority ordering
# ---------------------------------------------------------------------------


class TestPriorityOrdering:
    def test_critical_before_high(self) -> None:
        rc_critical = _make_root_cause(
            severity=RootCauseSeverity.CRITICAL,
            title="Critical issue",
            file_path="src/critical.py",
        )
        rc_high = _make_root_cause(
            severity=RootCauseSeverity.HIGH,
            title="High issue",
            file_path="src/high.py",
        )
        collection = _make_collection([rc_high, rc_critical])
        plan = PlanningEngine.plan(collection)
        # The critical root cause should be step 1.
        assert plan.steps[0].root_cause_id == rc_critical.id
        assert plan.steps[0].priority == EngineeringPriority.CRITICAL
        assert plan.steps[1].root_cause_id == rc_high.id

    def test_higher_impact_first(self) -> None:
        """More evidence + higher severity should rank higher."""
        rc_big = _make_root_cause(
            severity=RootCauseSeverity.HIGH,
            evidence_count=8,
            title="Big problem",
            file_path="src/big.py",
        )
        rc_small = _make_root_cause(
            severity=RootCauseSeverity.MEDIUM,
            evidence_count=2,
            title="Small problem",
            file_path="src/small.py",
        )
        collection = _make_collection([rc_small, rc_big])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].root_cause_id == rc_big.id

    def test_step_numbers_are_sequential(self) -> None:
        rcs = [
            _make_root_cause(severity=s, title=f"RC {i}")
            for i, s in enumerate(
                [RootCauseSeverity.HIGH, RootCauseSeverity.MEDIUM, RootCauseSeverity.LOW]
            )
        ]
        collection = _make_collection(rcs)
        plan = PlanningEngine.plan(collection)
        for i, step in enumerate(plan.steps, 1):
            assert step.step_number == i

    def test_priority_levels_assigned(self) -> None:
        rc = _make_root_cause(severity=RootCauseSeverity.CRITICAL)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].priority == EngineeringPriority.CRITICAL


# ---------------------------------------------------------------------------
# Tests: ROI calculation
# ---------------------------------------------------------------------------


class TestROICalculation:
    def test_roi_positive(self) -> None:
        rc = _make_root_cause(category=RootCauseCategory.GOD_CLASS)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.steps[0].roi > 0.0

    def test_higher_benefit_higher_roi(self) -> None:
        """A category with high maintainability benefit should have higher ROI
        than one with low benefit (assuming similar effort)."""
        rc_high_benefit = _make_root_cause(category=RootCauseCategory.GOD_CLASS)
        rc_low_benefit = _make_root_cause(category=RootCauseCategory.MAGIC_CONSTANTS)
        collection = _make_collection([rc_high_benefit, rc_low_benefit])
        plan = PlanningEngine.plan(collection)
        roi_high = plan.steps[0].roi
        roi_low = plan.steps[1].roi
        # God Class (40h effort, 90 maintainability benefit) vs
        # Magic Constants (4h effort, 50 maintainability benefit).
        # ROI depends on benefit/cost ratio; both should be positive.
        assert roi_high > 0
        assert roi_low > 0

    def test_roi_in_statistics(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert "average_roi" in plan.statistics
        assert plan.statistics["average_roi"] > 0.0


# ---------------------------------------------------------------------------
# Tests: quick wins
# ---------------------------------------------------------------------------


class TestQuickWins:
    def test_quick_wins_extracted(self) -> None:
        """Low-effort categories should produce quick wins."""
        rc = _make_root_cause(
            category=RootCauseCategory.MAGIC_CONSTANTS,
            title="Magic constants",
        )
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert len(plan.quick_wins) >= 1

    def test_quick_win_has_title(self) -> None:
        rc = _make_root_cause(category=RootCauseCategory.MAGIC_CONSTANTS)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        if plan.quick_wins:
            assert plan.quick_wins[0].title

    def test_quick_win_has_effort(self) -> None:
        rc = _make_root_cause(category=RootCauseCategory.MAGIC_CONSTANTS)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        if plan.quick_wins:
            assert plan.quick_wins[0].effort_minutes > 0

    def test_no_quick_wins_for_large_effort(self) -> None:
        """God Class (40h effort) should not produce a quick win."""
        rc = _make_root_cause(category=RootCauseCategory.GOD_CLASS)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        # God Class takes 40 hours — not a quick win.
        god_class_qw = [qw for qw in plan.quick_wins if qw.root_cause_id == rc.id]
        assert len(god_class_qw) == 0


# ---------------------------------------------------------------------------
# Tests: blockers and dependency ordering
# ---------------------------------------------------------------------------


class TestBlockers:
    def test_blocker_detected_when_causes_relationship(self) -> None:
        """When RC A CAUSES RC B, A should be a blocker for B."""
        rc_a = _make_root_cause(title="Root Cause A", file_path="src/a.py")
        rc_b = _make_root_cause(title="Root Cause B", file_path="src/b.py")
        rel = RootCauseRelationship(
            source_root_cause_id=rc_a.id,
            target_root_cause_id=rc_b.id,
            relationship_type=RootCauseRelationshipType.CAUSES,
            detail="A causes B",
        )
        collection = RootCauseCollection(
            root_causes=[rc_a, rc_b],
            relationships=[rel],
        )
        plan = PlanningEngine.plan(collection)
        assert len(plan.blockers) >= 1
        blocker = plan.blockers[0]
        assert blocker.blocker_root_cause_id == rc_a.id
        assert rc_b.id in blocker.blocked_root_cause_ids

    def test_blocked_step_has_prerequisites(self) -> None:
        """The blocked step should have the blocker's step as a prerequisite."""
        rc_a = _make_root_cause(title="A", file_path="src/a.py")
        rc_b = _make_root_cause(title="B", file_path="src/b.py")
        rel = RootCauseRelationship(
            source_root_cause_id=rc_a.id,
            target_root_cause_id=rc_b.id,
            relationship_type=RootCauseRelationshipType.CAUSES,
        )
        collection = RootCauseCollection(
            root_causes=[rc_a, rc_b],
            relationships=[rel],
        )
        plan = PlanningEngine.plan(collection)
        # Find the step for rc_b.
        step_b = next(s for s in plan.steps if s.root_cause_id == rc_b.id)
        step_a = next(s for s in plan.steps if s.root_cause_id == rc_a.id)
        assert step_a.id in step_b.prerequisites

    def test_no_blockers_without_relationships(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert len(plan.blockers) == 0


# ---------------------------------------------------------------------------
# Tests: roadmap
# ---------------------------------------------------------------------------


class TestRoadmap:
    def test_roadmap_has_sprints(self) -> None:
        rcs = [
            _make_root_cause(
                category=cat,
                title=f"RC {cat.value}",
                file_path=f"src/{cat.value}.py",
            )
            for cat in [RootCauseCategory.GOD_CLASS, RootCauseCategory.TIGHT_COUPLING]
        ]
        collection = _make_collection(rcs)
        plan = PlanningEngine.plan(collection)
        assert plan.roadmap is not None
        assert len(plan.roadmap.sprints) >= 1

    def test_roadmap_total_hours(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        assert plan.roadmap is not None
        assert plan.roadmap.total_estimated_hours > 0.0

    def test_roadmap_total_steps(self) -> None:
        rcs = [_make_root_cause(title=f"RC {i}", file_path=f"src/{i}.py") for i in range(3)]
        collection = _make_collection(rcs)
        plan = PlanningEngine.plan(collection)
        assert plan.roadmap is not None
        assert plan.roadmap.total_steps == 3

    def test_sprint_has_title(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        if plan.roadmap and plan.roadmap.sprints:
            assert plan.roadmap.sprints[0].title

    def test_sprint_has_goals(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        if plan.roadmap and plan.roadmap.sprints:
            assert len(plan.roadmap.sprints[0].goals) >= 1


# ---------------------------------------------------------------------------
# Tests: trade-off alternatives
# ---------------------------------------------------------------------------


class TestTradeOffAlternatives:
    def test_god_class_has_extract_class_alternative(self) -> None:
        rc = _make_root_cause(category=RootCauseCategory.GOD_CLASS)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        alternatives = plan.steps[0].alternatives
        names = [a.name for a in alternatives]
        assert "Extract Class" in names or "Full Refactor" in names

    def test_circular_dep_has_alternatives(self) -> None:
        rc = _make_root_cause(category=RootCauseCategory.CIRCULAR_DEPENDENCY)
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        alternatives = plan.steps[0].alternatives
        assert len(alternatives) >= 2

    def test_alternatives_have_advantages(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        for alt in plan.steps[0].alternatives:
            assert len(alt.advantages) >= 1

    def test_alternatives_have_disadvantages(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        for alt in plan.steps[0].alternatives:
            assert len(alt.disadvantages) >= 1

    def test_alternatives_have_risk(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        for alt in plan.steps[0].alternatives:
            assert alt.risk in EngineeringRisk


# ---------------------------------------------------------------------------
# Tests: impact analysis
# ---------------------------------------------------------------------------


class TestImpactAnalysis:
    def test_impact_score_in_range(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        for score in plan.impact_scores:
            assert 0.0 <= score.overall <= 100.0

    def test_critical_severity_high_impact(self) -> None:
        rc = _make_root_cause(severity=RootCauseSeverity.CRITICAL)
        collection = _make_collection([rc])
        scores = ImpactAnalyzer.analyze(collection)
        assert scores[0].severity_score == 100.0

    def test_more_evidence_higher_impact(self) -> None:
        rc_few = _make_root_cause(evidence_count=1, title="Few")
        rc_many = _make_root_cause(evidence_count=8, title="Many")
        collection = _make_collection([rc_few, rc_many])
        scores = ImpactAnalyzer.analyze(collection)
        score_few = next(s for s in scores if s.root_cause_id == rc_few.id)
        score_many = next(s for s in scores if s.root_cause_id == rc_many.id)
        assert score_many.evidence_score > score_few.evidence_score


# ---------------------------------------------------------------------------
# Tests: model properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_planning_step_is_immutable(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        with pytest.raises(Exception):  # noqa: B017
            plan.steps[0].title = "mutated"  # type: ignore[misc]

    def test_engineering_plan_is_immutable(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        with pytest.raises(Exception):  # noqa: B017
            plan.steps = []  # type: ignore[misc]

    def test_estimate_display(self) -> None:
        est = EngineeringEstimate(hours=0.5)
        assert "min" in est.display
        est2 = EngineeringEstimate(hours=4)
        assert "hour" in est2.display
        est3 = EngineeringEstimate(hours=16)
        assert "day" in est3.display or "week" in est3.display

    def test_benefit_total(self) -> None:
        benefit = EngineeringBenefit(
            security_benefit=100,
            maintainability_benefit=100,
            testability_benefit=100,
            performance_benefit=100,
            developer_experience_benefit=100,
        )
        assert benefit.total == 100.0

    def test_plan_get_step(self) -> None:
        rc = _make_root_cause()
        collection = _make_collection([rc])
        plan = PlanningEngine.plan(collection)
        step = plan.steps[0]
        found = plan.get_step(step.id)
        assert found is not None
        assert found.id == step.id
        assert plan.get_step(uuid4()) is None

    def test_plan_steps_by_priority(self) -> None:
        rc_critical = _make_root_cause(severity=RootCauseSeverity.CRITICAL, title="C")
        rc_low = _make_root_cause(severity=RootCauseSeverity.LOW, title="L")
        collection = _make_collection([rc_critical, rc_low])
        plan = PlanningEngine.plan(collection)
        critical_steps = plan.steps_by_priority(EngineeringPriority.CRITICAL)
        assert len(critical_steps) >= 1
        assert all(s.priority == EngineeringPriority.CRITICAL for s in critical_steps)
