"""Engineering Planning Engine.

Transforms a :class:`RootCauseCollection` into an actionable
:class:`EngineeringPlan` with prioritized steps, ROI scores, a sprint
roadmap, quick wins, blockers, and trade-off alternatives.

Pipeline::

    RootCauseCollection
        ↓
    ImpactAnalyzer   → ImpactScore per root cause
        ↓
    ROICalculator    → ROI per root cause (benefit / cost)
        ↓
    PriorityEngine   → deterministic priority ordering
        ↓
    PlanningEngine   → EngineeringPlan (steps + roadmap + quick wins + blockers)

Design:
    - **Read-only**: The engine never modifies the root cause collection.
    - **No I/O**: All computation is in-memory from root cause data.
    - **Deterministic**: Same input → same output, always.
    - **Extensible**: Impact factors and ROI weights are data-driven.

Usage::

    from repo_analyzer.core.evidence import PlanningEngine

    plan = PlanningEngine.plan(root_causes)
    for step in plan.steps:
        print(step.step_number, step.priority.value, step.title, step.roi)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, ClassVar
from uuid import UUID

from repo_analyzer.core.evidence.planning_models import (
    BlockerItem,
    EngineeringBenefit,
    EngineeringEstimate,
    EngineeringPlan,
    EngineeringPriority,
    EngineeringRisk,
    ImpactScore,
    PlanningStep,
    QuickWinItem,
    Roadmap,
    SprintRecommendation,
    TradeOffAlternative,
)
from repo_analyzer.core.evidence.root_cause_models import (
    RootCause,
    RootCauseCategory,
    RootCauseCollection,
    RootCauseRelationshipType,
    RootCauseSeverity,
)
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Default sprint capacity in engineer-hours.
_SPRINT_CAPACITY_HOURS = 80.0  # ~2 developers × 1 week

#: Quick-win threshold: effort ≤ this (in hours) AND benefit above threshold.
_QUICK_WIN_MAX_HOURS = 0.5  # 30 minutes
_QUICK_WIN_MIN_BENEFIT = 30.0

#: Severity → numeric score mapping for impact calculation.
_SEVERITY_SCORES: dict[RootCauseSeverity, float] = {
    RootCauseSeverity.CRITICAL: 100.0,
    RootCauseSeverity.HIGH: 80.0,
    RootCauseSeverity.MEDIUM: 60.0,
    RootCauseSeverity.LOW: 40.0,
    RootCauseSeverity.INFO: 20.0,
}

#: Category → estimated effort (hours) mapping.
_CATEGORY_EFFORT: dict[RootCauseCategory, float] = {
    RootCauseCategory.GOD_CLASS: 40.0,
    RootCauseCategory.GOD_SERVICE: 32.0,
    RootCauseCategory.OVERSIZED_SERVICE: 32.0,
    RootCauseCategory.LARGE_MODULE: 16.0,
    RootCauseCategory.CIRCULAR_DEPENDENCY: 24.0,
    RootCauseCategory.TIGHT_COUPLING: 24.0,
    RootCauseCategory.LOW_COHESION: 20.0,
    RootCauseCategory.DEPENDENCY_EXPLOSION: 16.0,
    RootCauseCategory.SHOTGUN_SURGERY: 12.0,
    RootCauseCategory.ANEMIC_DOMAIN_MODEL: 16.0,
    RootCauseCategory.DUPLICATED_RESPONSIBILITY: 8.0,
    RootCauseCategory.SRP_VIOLATION: 16.0,
    RootCauseCategory.FEATURE_ENVY: 12.0,
    RootCauseCategory.HIGH_INSTABILITY: 20.0,
    RootCauseCategory.OVERSIZED_INTERFACE: 12.0,
    RootCauseCategory.DATA_CLUMPS: 8.0,
    RootCauseCategory.PRIMITIVE_OBSESSION: 6.0,
    RootCauseCategory.MAGIC_CONSTANTS: 4.0,
    RootCauseCategory.LAYER_VIOLATION: 20.0,
    RootCauseCategory.DIP_VIOLATION: 24.0,
    RootCauseCategory.OCP_VIOLATION: 16.0,
    RootCauseCategory.ISP_VIOLATION: 12.0,
    RootCauseCategory.LSP_RISK: 20.0,
}

#: Category → risk level mapping.
_CATEGORY_RISK: dict[RootCauseCategory, EngineeringRisk] = {
    RootCauseCategory.GOD_CLASS: EngineeringRisk.HIGH,
    RootCauseCategory.GOD_SERVICE: EngineeringRisk.HIGH,
    RootCauseCategory.OVERSIZED_SERVICE: EngineeringRisk.HIGH,
    RootCauseCategory.CIRCULAR_DEPENDENCY: EngineeringRisk.HIGH,
    RootCauseCategory.TIGHT_COUPLING: EngineeringRisk.MEDIUM,
    RootCauseCategory.LOW_COHESION: EngineeringRisk.MEDIUM,
    RootCauseCategory.LARGE_MODULE: EngineeringRisk.LOW,
    RootCauseCategory.DEPENDENCY_EXPLOSION: EngineeringRisk.MEDIUM,
    RootCauseCategory.SHOTGUN_SURGERY: EngineeringRisk.LOW,
    RootCauseCategory.ANEMIC_DOMAIN_MODEL: EngineeringRisk.LOW,
    RootCauseCategory.DUPLICATED_RESPONSIBILITY: EngineeringRisk.LOW,
    RootCauseCategory.SRP_VIOLATION: EngineeringRisk.MEDIUM,
    RootCauseCategory.FEATURE_ENVY: EngineeringRisk.LOW,
    RootCauseCategory.HIGH_INSTABILITY: EngineeringRisk.MEDIUM,
    RootCauseCategory.OVERSIZED_INTERFACE: EngineeringRisk.LOW,
    RootCauseCategory.DATA_CLUMPS: EngineeringRisk.MINIMAL,
    RootCauseCategory.PRIMITIVE_OBSESSION: EngineeringRisk.MINIMAL,
    RootCauseCategory.MAGIC_CONSTANTS: EngineeringRisk.MINIMAL,
    RootCauseCategory.LAYER_VIOLATION: EngineeringRisk.HIGH,
    RootCauseCategory.DIP_VIOLATION: EngineeringRisk.HIGH,
    RootCauseCategory.OCP_VIOLATION: EngineeringRisk.MEDIUM,
    RootCauseCategory.ISP_VIOLATION: EngineeringRisk.LOW,
    RootCauseCategory.LSP_RISK: EngineeringRisk.HIGH,
}

#: Category → benefit dimensions (0-100).
_CATEGORY_BENEFITS: dict[RootCauseCategory, dict[str, float]] = {
    RootCauseCategory.GOD_CLASS: {
        "maintainability": 90,
        "testability": 80,
        "developer_experience": 70,
        "security": 30,
        "performance": 20,
    },
    RootCauseCategory.GOD_SERVICE: {
        "maintainability": 85,
        "testability": 75,
        "developer_experience": 65,
        "security": 25,
        "performance": 20,
    },
    RootCauseCategory.OVERSIZED_SERVICE: {
        "maintainability": 80,
        "testability": 70,
        "developer_experience": 60,
        "security": 20,
        "performance": 15,
    },
    RootCauseCategory.CIRCULAR_DEPENDENCY: {
        "maintainability": 85,
        "testability": 80,
        "developer_experience": 50,
        "security": 30,
        "performance": 40,
    },
    RootCauseCategory.TIGHT_COUPLING: {
        "maintainability": 75,
        "testability": 70,
        "developer_experience": 55,
        "security": 20,
        "performance": 25,
    },
    RootCauseCategory.LOW_COHESION: {
        "maintainability": 70,
        "testability": 60,
        "developer_experience": 50,
        "security": 10,
        "performance": 10,
    },
    RootCauseCategory.LARGE_MODULE: {
        "maintainability": 60,
        "testability": 50,
        "developer_experience": 45,
        "security": 10,
        "performance": 15,
    },
    RootCauseCategory.DEPENDENCY_EXPLOSION: {
        "maintainability": 60,
        "testability": 50,
        "developer_experience": 40,
        "security": 70,
        "performance": 30,
    },
    RootCauseCategory.SHOTGUN_SURGERY: {
        "maintainability": 65,
        "testability": 55,
        "developer_experience": 50,
        "security": 15,
        "performance": 10,
    },
    RootCauseCategory.ANEMIC_DOMAIN_MODEL: {
        "maintainability": 55,
        "testability": 40,
        "developer_experience": 35,
        "security": 10,
        "performance": 5,
    },
    RootCauseCategory.DUPLICATED_RESPONSIBILITY: {
        "maintainability": 60,
        "testability": 50,
        "developer_experience": 40,
        "security": 20,
        "performance": 10,
    },
    RootCauseCategory.SRP_VIOLATION: {
        "maintainability": 70,
        "testability": 60,
        "developer_experience": 50,
        "security": 15,
        "performance": 10,
    },
    RootCauseCategory.LAYER_VIOLATION: {
        "maintainability": 75,
        "testability": 65,
        "developer_experience": 55,
        "security": 60,
        "performance": 20,
    },
    RootCauseCategory.DIP_VIOLATION: {
        "maintainability": 70,
        "testability": 75,
        "developer_experience": 50,
        "security": 40,
        "performance": 15,
    },
}

#: Default benefit for categories not in the explicit mapping.
_DEFAULT_BENEFIT = {
    "maintainability": 50,
    "testability": 40,
    "developer_experience": 35,
    "security": 15,
    "performance": 10,
}

#: Category → recommended refactor action title.
_CATEGORY_ACTION_TITLE: dict[RootCauseCategory, str] = {
    RootCauseCategory.GOD_CLASS: "Split God Class into focused, single-responsibility classes",
    RootCauseCategory.GOD_SERVICE: "Decompose God Service into smaller, cohesive services",
    RootCauseCategory.OVERSIZED_SERVICE: "Break oversized service into focused modules",
    RootCauseCategory.CIRCULAR_DEPENDENCY: "Break circular dependency by extracting shared module",
    RootCauseCategory.TIGHT_COUPLING: "Introduce interfaces to decouple tightly coupled modules",
    RootCauseCategory.LOW_COHESION: "Reorganize module around single responsibility",
    RootCauseCategory.LARGE_MODULE: "Split large module into smaller, focused files",
    RootCauseCategory.DEPENDENCY_EXPLOSION: "Consolidate dependencies behind a wrapper interface",
    RootCauseCategory.SHOTGUN_SURGERY: "Extract common pattern into a shared utility",
    RootCauseCategory.ANEMIC_DOMAIN_MODEL: "Move behavior from services into domain model",
    RootCauseCategory.DUPLICATED_RESPONSIBILITY: "Extract shared logic into a reusable module",
    RootCauseCategory.SRP_VIOLATION: "Split class by responsibility (SRP)",
    RootCauseCategory.LAYER_VIOLATION: "Fix layer violation — depend on abstractions, not concretions",
    RootCauseCategory.DIP_VIOLATION: "Apply Dependency Inversion — introduce interface",
}

#: Category → technical description template.
_CATEGORY_TECHNICAL: dict[RootCauseCategory, str] = {
    RootCauseCategory.GOD_CLASS: (
        "Identify the distinct responsibilities in the class. Extract each "
        "into a separate class with a single responsibility. Update all "
        "callers to use the new classes. Add/update tests for each new class."
    ),
    RootCauseCategory.CIRCULAR_DEPENDENCY: (
        "Identify the shared logic causing the cycle. Extract it into a "
        "new lower-level module that both parties can depend on. Update "
        "imports and verify the cycle is broken with a dependency check."
    ),
    RootCauseCategory.TIGHT_COUPLING: (
        "Introduce an interface for the most-depended-upon collaborator. "
        "Update consumers to depend on the interface. Use dependency "
        "injection to provide the concrete implementation."
    ),
}


class ImpactAnalyzer:
    """Compute :class:`ImpactScore` for each root cause.

    The score is a weighted combination of:
        - Severity (0-100)
        - Evidence count (0-100, capped at 10 evidence items)
        - Scope (affected files + modules, 0-100)
        - Dependency centrality (from graph, 0-100)
        - Security/performance/maintainability/testability impact (0-100)
        - Confidence factor (0-1, scales the overall score)
    """

    @classmethod
    def analyze(cls, root_causes: RootCauseCollection) -> list[ImpactScore]:
        """Compute impact scores for all root causes.

        Args:
            root_causes: The :class:`RootCauseCollection` from the detection engine.

        Returns:
            A list of :class:`ImpactScore` items, one per root cause.
        """
        scores: list[ImpactScore] = []
        for rc in root_causes.root_causes:
            scores.append(cls._analyze_one(rc))
        return scores

    @staticmethod
    def _analyze_one(rc: RootCause) -> ImpactScore:
        """Compute the impact score for a single root cause."""
        # Severity score.
        severity_score = _SEVERITY_SCORES.get(rc.severity, 50.0)
        # Evidence score (capped at 10 items).
        evidence_score = min(rc.evidence_count / 10.0, 1.0) * 100.0
        # Scope score: files + modules + classes.
        scope_raw = (
            len(rc.affected_files) * 10
            + len(rc.affected_modules) * 15
            + len(rc.affected_classes) * 10
        )
        scope_score = min(scope_raw, 100.0)
        # Dependency centrality: approximate from evidence_count (proxy).
        dependency_centrality = min(rc.evidence_count * 5.0, 100.0)
        # Category-specific impacts.
        benefits = _CATEGORY_BENEFITS.get(rc.category, _DEFAULT_BENEFIT)
        security_impact = benefits.get("security", 15.0)
        performance_impact = benefits.get("performance", 10.0)
        maintainability_impact = benefits.get("maintainability", 50.0)
        testability_impact = benefits.get("testability", 40.0)
        # Confidence factor.
        confidence_factor = rc.confidence
        # Overall: weighted combination.
        overall = (
            severity_score * 0.25
            + evidence_score * 0.15
            + scope_score * 0.15
            + dependency_centrality * 0.10
            + security_impact * 0.10
            + maintainability_impact * 0.15
            + testability_impact * 0.10
        ) * confidence_factor
        return ImpactScore(
            overall=round(overall, 2),
            severity_score=round(severity_score, 2),
            evidence_score=round(evidence_score, 2),
            scope_score=round(scope_score, 2),
            dependency_centrality=round(dependency_centrality, 2),
            security_impact=round(security_impact, 2),
            performance_impact=round(performance_impact, 2),
            maintainability_impact=round(maintainability_impact, 2),
            testability_impact=round(testability_impact, 2),
            confidence_factor=round(confidence_factor, 3),
            root_cause_id=rc.id,
        )


class ROICalculator:
    """Compute Return on Engineering Investment for each root cause.

    ROI = (expected_benefit / estimated_cost) × risk_adjustment

    - Expected benefit: from :class:`EngineeringBenefit.total` (0-100).
    - Estimated cost: from category-based effort estimates (hours).
    - Risk adjustment: 1.0 for low risk, 0.8 for medium, 0.6 for high.
    """

    @classmethod
    def calculate(
        cls, root_causes: RootCauseCollection, impact_scores: list[ImpactScore]
    ) -> dict[UUID, tuple[float, EngineeringBenefit, EngineeringEstimate]]:
        """Compute ROI for all root causes.

        Returns:
            A dict mapping root_cause_id → (roi, benefit, estimate).
        """
        impact_by_rc: dict[UUID, ImpactScore] = {
            s.root_cause_id: s for s in impact_scores if s.root_cause_id is not None
        }
        results: dict[UUID, tuple[float, EngineeringBenefit, EngineeringEstimate]] = {}
        for rc in root_causes.root_causes:
            benefit = cls._compute_benefit(rc)
            estimate = cls._compute_estimate(rc)
            risk = _CATEGORY_RISK.get(rc.category, EngineeringRisk.MEDIUM)
            risk_adj = {
                EngineeringRisk.MINIMAL: 1.0,
                EngineeringRisk.LOW: 1.0,
                EngineeringRisk.MEDIUM: 0.8,
                EngineeringRisk.HIGH: 0.6,
                EngineeringRisk.CRITICAL: 0.4,
            }.get(risk, 0.8)
            cost = max(estimate.hours, 0.1)  # avoid division by zero
            roi = (benefit.total / cost) * risk_adj
            results[rc.id] = (round(roi, 3), benefit, estimate)
        return results

    @staticmethod
    def _compute_benefit(rc: RootCause) -> EngineeringBenefit:
        """Compute the expected benefit of fixing this root cause."""
        b = _CATEGORY_BENEFITS.get(rc.category, _DEFAULT_BENEFIT)
        return EngineeringBenefit(
            security_benefit=b.get("security", 15.0),
            maintainability_benefit=b.get("maintainability", 50.0),
            testability_benefit=b.get("testability", 40.0),
            performance_benefit=b.get("performance", 10.0),
            developer_experience_benefit=b.get("developer_experience", 35.0),
        )

    @staticmethod
    def _compute_estimate(rc: RootCause) -> EngineeringEstimate:
        """Compute the effort estimate for fixing this root cause."""
        base_hours = _CATEGORY_EFFORT.get(rc.category, 16.0)
        # Adjust by evidence count: more evidence → slightly more work.
        adjusted = base_hours * (1.0 + min(rc.evidence_count * 0.05, 0.5))
        return EngineeringEstimate(
            hours=round(adjusted, 1),
            confidence=0.5,
            developers=2 if adjusted > 24 else 1,
        )


class PriorityEngine:
    """Deterministically order root causes by priority.

    Sorting key (descending):
        1. Impact score overall (higher first).
        2. Severity (critical > high > medium > low > info).
        3. Evidence count (more first).
        4. Confidence (higher first).
        5. Root cause ID (stable tiebreaker).
    """

    _SEVERITY_ORDER: ClassVar[dict[RootCauseSeverity, int]] = {
        RootCauseSeverity.CRITICAL: 5,
        RootCauseSeverity.HIGH: 4,
        RootCauseSeverity.MEDIUM: 3,
        RootCauseSeverity.LOW: 2,
        RootCauseSeverity.INFO: 1,
    }

    @classmethod
    def rank(
        cls,
        root_causes: RootCauseCollection,
        impact_scores: list[ImpactScore],
    ) -> list[tuple[RootCause, ImpactScore, EngineeringPriority]]:
        """Return root causes in priority order.

        Returns:
            A list of (root_cause, impact_score, priority) tuples, sorted
            by priority (highest first).
        """
        impact_by_rc: dict[UUID, ImpactScore] = {
            s.root_cause_id: s for s in impact_scores if s.root_cause_id is not None
        }
        ranked: list[tuple[RootCause, ImpactScore, EngineeringPriority]] = []
        for rc in root_causes.root_causes:
            score = impact_by_rc.get(rc.id, ImpactScore(root_cause_id=rc.id))
            priority = cls._score_to_priority(score.overall, rc.severity)
            ranked.append((rc, score, priority))
        # Sort by: overall desc, severity desc, evidence count desc, confidence desc.
        ranked.sort(
            key=lambda t: (
                -t[1].overall,
                -cls._SEVERITY_ORDER.get(t[0].severity, 0),
                -t[0].evidence_count,
                -t[0].confidence,
                str(t[0].id),  # stable tiebreaker
            )
        )
        return ranked

    @staticmethod
    def _score_to_priority(overall: float, severity: RootCauseSeverity) -> EngineeringPriority:
        """Map an impact score + severity to a :class:`EngineeringPriority`."""
        if severity == RootCauseSeverity.CRITICAL or overall >= 80:
            return EngineeringPriority.CRITICAL
        if severity == RootCauseSeverity.HIGH or overall >= 60:
            return EngineeringPriority.HIGH
        if severity == RootCauseSeverity.MEDIUM or overall >= 40:
            return EngineeringPriority.MEDIUM
        if severity == RootCauseSeverity.LOW or overall >= 20:
            return EngineeringPriority.LOW
        return EngineeringPriority.INFORMATIONAL


class PlanningEngine:
    """Produce an :class:`EngineeringPlan` from a :class:`RootCauseCollection`.

    The engine is stateless and thread-safe. The :meth:`plan` method is
    the single entry point.
    """

    @classmethod
    def plan(cls, root_causes: RootCauseCollection) -> EngineeringPlan:
        """Build a complete engineering plan.

        Args:
            root_causes: The :class:`RootCauseCollection` from the detection engine.

        Returns:
            An :class:`EngineeringPlan` with prioritized steps, roadmap,
            quick wins, blockers, and impact scores.
        """
        engine = cls()

        # 1. Impact analysis.
        impact_scores = ImpactAnalyzer.analyze(root_causes)

        # 2. ROI calculation.
        roi_data = ROICalculator.calculate(root_causes, impact_scores)

        # 3. Priority ranking.
        ranked = PriorityEngine.rank(root_causes, impact_scores)

        # 4. Build planning steps.
        steps = engine._build_steps(ranked, roi_data, root_causes)

        # 5. Build blockers.
        blockers = engine._build_blockers(root_causes, steps)

        # 6. Update step prerequisites based on blockers.
        steps = engine._apply_blockers(steps, blockers)

        # 7. Build quick wins.
        quick_wins = engine._build_quick_wins(steps, roi_data)

        # 8. Build roadmap (sprint batches).
        roadmap = engine._build_roadmap(steps)

        # 9. Statistics.
        stats = engine._build_statistics(steps, quick_wins, blockers, roadmap)

        return EngineeringPlan(
            steps=steps,
            roadmap=roadmap,
            quick_wins=quick_wins,
            blockers=blockers,
            impact_scores=impact_scores,
            statistics=stats,
        )

    # ------------------------------------------------------------------
    # Step building
    # ------------------------------------------------------------------

    def _build_steps(
        self,
        ranked: list[tuple[RootCause, ImpactScore, EngineeringPriority]],
        roi_data: dict[UUID, tuple[float, EngineeringBenefit, EngineeringEstimate]],
        root_causes: RootCauseCollection,
    ) -> list[PlanningStep]:
        """Build :class:`PlanningStep` items from ranked root causes."""
        steps: list[PlanningStep] = []
        step_num = 0
        for rc, score, priority in ranked:
            step_num += 1
            roi, benefit, estimate = roi_data.get(
                rc.id, (0.0, EngineeringBenefit(), EngineeringEstimate(hours=16.0))
            )
            risk = _CATEGORY_RISK.get(rc.category, EngineeringRisk.MEDIUM)
            title = _CATEGORY_ACTION_TITLE.get(
                rc.category, f"Address {rc.category.value.replace('_', ' ').title()}"
            )
            technical = _CATEGORY_TECHNICAL.get(
                rc.category, "Review the affected code and apply appropriate refactoring."
            )
            alternatives = self._build_alternatives(rc)
            outcomes = self._build_outcomes(rc, benefit)
            risk_reason = self._build_risk_reason(rc, risk)
            steps.append(
                PlanningStep(
                    step_number=step_num,
                    title=title,
                    technical_description=technical,
                    root_cause_id=rc.id,
                    root_cause_category=rc.category.value,
                    priority=priority,
                    impact_score=score,
                    benefit=benefit,
                    roi=roi,
                    estimate=estimate,
                    risk=risk,
                    risk_reason=risk_reason,
                    expected_outcomes=outcomes,
                    alternatives=alternatives,
                    affected_files=rc.affected_files[:20],
                    affected_modules=rc.affected_modules[:10],
                    metadata={"root_cause_title": rc.title, "confidence": rc.confidence},
                )
            )
        return steps

    @staticmethod
    def _build_alternatives(rc: RootCause) -> list[TradeOffAlternative]:
        """Build at least two trade-off alternatives for a root cause."""
        cat = rc.category
        # Define alternatives by category.
        alt_map: dict[RootCauseCategory, list[TradeOffAlternative]] = {
            RootCauseCategory.GOD_CLASS: [
                TradeOffAlternative(
                    name="Extract Class",
                    description="Split the God Class into multiple focused classes.",
                    advantages=["Clear responsibilities", "Easier to test", "Better SRP"],
                    disadvantages=["More files to manage", "Requires updating all callers"],
                    risk=EngineeringRisk.MEDIUM,
                    maintenance_cost="low",
                    performance_impact="neutral",
                    migration_difficulty="medium",
                ),
                TradeOffAlternative(
                    name="Facade + Delegate",
                    description="Keep the class as a facade, delegate to internal services.",
                    advantages=["Backward compatible API", "Gradual migration"],
                    disadvantages=["Facade still exists", "Doesn't fully fix SRP"],
                    risk=EngineeringRisk.LOW,
                    maintenance_cost="medium",
                    performance_impact="neutral",
                    migration_difficulty="low",
                ),
            ],
            RootCauseCategory.CIRCULAR_DEPENDENCY: [
                TradeOffAlternative(
                    name="Extract Shared Module",
                    description="Extract the shared logic into a new lower-level module.",
                    advantages=["Clean dependency graph", "Reusability"],
                    disadvantages=["New module to maintain", "Requires careful interface design"],
                    risk=EngineeringRisk.MEDIUM,
                    maintenance_cost="low",
                    performance_impact="neutral",
                    migration_difficulty="medium",
                ),
                TradeOffAlternative(
                    name="Inversion of Control",
                    description="Use DI to invert one direction of the dependency.",
                    advantages=["No new module", "Improves testability"],
                    disadvantages=["More complex setup", "DI container needed"],
                    risk=EngineeringRisk.MEDIUM,
                    maintenance_cost="medium",
                    performance_impact="neutral",
                    migration_difficulty="high",
                ),
            ],
        }
        return alt_map.get(
            cat,
            [
                TradeOffAlternative(
                    name="Full Refactor",
                    description="Address the root cause completely.",
                    advantages=["Eliminates the problem", "Long-term benefit"],
                    disadvantages=["Higher upfront cost", "More risk"],
                    risk=EngineeringRisk.MEDIUM,
                    maintenance_cost="low",
                    performance_impact="neutral",
                    migration_difficulty="medium",
                ),
                TradeOffAlternative(
                    name="Incremental Fix",
                    description="Address the most critical symptoms first, defer the rest.",
                    advantages=["Lower risk", "Faster initial improvement"],
                    disadvantages=["Problem partially remains", "May need future work"],
                    risk=EngineeringRisk.LOW,
                    maintenance_cost="medium",
                    performance_impact="neutral",
                    migration_difficulty="low",
                ),
            ],
        )

    @staticmethod
    def _build_outcomes(rc: RootCause, benefit: EngineeringBenefit) -> list[str]:
        """Build expected outcome strings for a planning step."""
        outcomes: list[str] = []
        if benefit.maintainability_benefit >= 60:
            outcomes.append(f"Improved maintainability (+{benefit.maintainability_benefit:.0f}%)")
        if benefit.testability_benefit >= 60:
            outcomes.append(f"Improved testability (+{benefit.testability_benefit:.0f}%)")
        if benefit.security_benefit >= 50:
            outcomes.append(f"Reduced security risk (+{benefit.security_benefit:.0f}%)")
        if benefit.developer_experience_benefit >= 50:
            outcomes.append(
                f"Better developer experience (+{benefit.developer_experience_benefit:.0f}%)"
            )
        if not outcomes:
            outcomes.append("Reduced technical debt")
        return outcomes

    @staticmethod
    def _build_risk_reason(rc: RootCause, risk: EngineeringRisk) -> str:
        """Build a human-readable risk reason."""
        reasons: dict[EngineeringRisk, str] = {
            EngineeringRisk.CRITICAL: "Changes affect critical paths; thorough testing required.",
            EngineeringRisk.HIGH: "Large-scale refactoring with potential for regressions.",
            EngineeringRisk.MEDIUM: "Moderate changes; ensure test coverage before and after.",
            EngineeringRisk.LOW: "Low risk; isolated changes with minimal blast radius.",
            EngineeringRisk.MINIMAL: "Minimal risk; straightforward mechanical changes.",
        }
        base = reasons.get(risk, "")
        if rc.evidence_count > 5:
            base += " High evidence count suggests widespread impact."
        return base

    # ------------------------------------------------------------------
    # Blockers
    # ------------------------------------------------------------------

    def _build_blockers(
        self, root_causes: RootCauseCollection, steps: list[PlanningStep]
    ) -> list[BlockerItem]:
        """Identify blockers: root causes that CAUSES or AGGRAVATES others.

        A root cause A blocks root cause B if there is a CAUSES or
        LEADS_TO relationship from A to B — meaning A should be fixed
        first.
        """
        blockers: list[BlockerItem] = []
        step_by_rc: dict[UUID, UUID] = {s.root_cause_id: s.id for s in steps}
        # Build: root_cause_id → list of root_cause_ids it blocks.
        blocks_map: dict[UUID, list[UUID]] = defaultdict(list)
        for rel in root_causes.relationships:
            if rel.relationship_type in (
                RootCauseRelationshipType.CAUSES,
                RootCauseRelationshipType.LEADS_TO,
            ):
                blocks_map[rel.source_root_cause_id].append(rel.target_root_cause_id)
        for blocker_rc_id, blocked_ids in blocks_map.items():
            # Deduplicate.
            unique_blocked = list(dict.fromkeys(blocked_ids))
            if not unique_blocked:
                continue
            blocker_rc = root_causes.get_by_id(blocker_rc_id)
            reason = ""
            if blocker_rc:
                reason = (
                    f"{blocker_rc.title} must be addressed first — it causes "
                    f"or leads to {len(unique_blocked)} other root cause(s)."
                )
            blockers.append(
                BlockerItem(
                    blocker_root_cause_id=blocker_rc_id,
                    blocked_root_cause_ids=unique_blocked,
                    reason=reason,
                    planning_step_id=step_by_rc.get(blocker_rc_id)
                    if blocker_rc_id in step_by_rc
                    else None,
                )
            )
        return blockers

    def _apply_blockers(
        self, steps: list[PlanningStep], blockers: list[BlockerItem]
    ) -> list[PlanningStep]:
        """Add prerequisite step IDs to steps that are blocked."""
        # Build: blocked_rc_id → list of blocker_step_ids.
        blocked_to_blocker_steps: dict[UUID, list[UUID]] = defaultdict(list)
        step_id_by_rc: dict[UUID, UUID] = {s.root_cause_id: s.id for s in steps}
        for blocker in blockers:
            blocker_step = blocker.planning_step_id
            if blocker_step is None:
                continue
            for blocked_rc_id in blocker.blocked_root_cause_ids:
                blocked_to_blocker_steps[blocked_rc_id].append(blocker_step)
        # Update steps with prerequisites.
        updated: list[PlanningStep] = []
        for step in steps:
            prereqs = blocked_to_blocker_steps.get(step.root_cause_id, [])
            if prereqs:
                step = step.model_copy(update={"prerequisites": list(prereqs)})
            updated.append(step)
        return updated

    # ------------------------------------------------------------------
    # Quick wins
    # ------------------------------------------------------------------

    def _build_quick_wins(
        self,
        steps: list[PlanningStep],
        roi_data: dict[UUID, tuple[float, EngineeringBenefit, EngineeringEstimate]],
    ) -> list[QuickWinItem]:
        """Extract quick wins: low-effort, high-benefit items."""
        quick_wins: list[QuickWinItem] = []
        for step in steps:
            _roi, benefit, estimate = roi_data.get(
                step.root_cause_id, (0.0, EngineeringBenefit(), EngineeringEstimate(hours=16.0))
            )
            if estimate.hours <= _QUICK_WIN_MAX_HOURS and benefit.total >= _QUICK_WIN_MIN_BENEFIT:
                quick_wins.append(
                    QuickWinItem(
                        title=step.title,
                        description=step.technical_description,
                        effort_minutes=int(estimate.hours * 60),
                        benefit=f"Benefit score: {benefit.total:.0f}/100",
                        planning_step_id=step.id,
                        root_cause_id=step.root_cause_id,
                    )
                )
        # Also check for small categories (magic constants, primitive obsession).
        for step in steps:
            if step.root_cause_category in (
                "magic_constants",
                "primitive_obsession",
                "data_clumps",
            ):
                if not any(qw.planning_step_id == step.id for qw in quick_wins):
                    _roi, benefit, estimate = roi_data.get(
                        step.root_cause_id,
                        (0.0, EngineeringBenefit(), EngineeringEstimate(hours=4.0)),
                    )
                    quick_wins.append(
                        QuickWinItem(
                            title=step.title,
                            description=step.technical_description,
                            effort_minutes=int(estimate.hours * 60),
                            benefit=f"Quick fix: {step.root_cause_category}",
                            planning_step_id=step.id,
                            root_cause_id=step.root_cause_id,
                        )
                    )
        return quick_wins

    # ------------------------------------------------------------------
    # Roadmap
    # ------------------------------------------------------------------

    def _build_roadmap(self, steps: list[PlanningStep]) -> Roadmap:
        """Group planning steps into sprint-sized batches.

        Each sprint targets ~80 engineer-hours (2 developers × 1 week).
        Steps are assigned to sprints in priority order, respecting
        prerequisites (a step can only go in a sprint after its
        prerequisites' sprint).
        """
        if not steps:
            return Roadmap(sprints=[], total_estimated_hours=0.0, total_steps=0)
        sprints: list[SprintRecommendation] = []
        current_sprint_steps: list[PlanningStep] = []
        current_hours = 0.0
        sprint_num = 0
        completed_step_ids: set[UUID] = set()
        step_by_id: dict[UUID, PlanningStep] = {s.id: s for s in steps}
        # Sort steps by step_number (already in priority order).
        sorted_steps = sorted(steps, key=lambda s: s.step_number)
        for step in sorted_steps:
            # Check prerequisites are in completed sprints.
            prereqs_met = all(p in completed_step_ids for p in step.prerequisites)
            if not prereqs_met:
                # Defer to next iteration (will be picked up after prereqs complete).
                continue
            estimate = step.estimate or EngineeringEstimate(hours=8.0)
            # If adding this step exceeds capacity, close the current sprint.
            if current_hours + estimate.hours > _SPRINT_CAPACITY_HOURS and current_sprint_steps:
                sprint_num += 1
                sprints.append(self._make_sprint(sprint_num, current_sprint_steps, current_hours))
                for s in current_sprint_steps:
                    completed_step_ids.add(s.id)
                current_sprint_steps = []
                current_hours = 0.0
            current_sprint_steps.append(step)
            current_hours += estimate.hours
        # Don't forget the last sprint.
        if current_sprint_steps:
            sprint_num += 1
            sprints.append(self._make_sprint(sprint_num, current_sprint_steps, current_hours))
            for s in current_sprint_steps:
                completed_step_ids.add(s.id)
        # Handle deferred steps (prerequisites not yet met — put in last sprint).
        deferred = [s for s in sorted_steps if s.id not in completed_step_ids]
        if deferred:
            sprint_num += 1
            deferred_hours = sum(
                (s.estimate or EngineeringEstimate(hours=8.0)).hours for s in deferred
            )
            sprints.append(
                self._make_sprint(sprint_num, deferred, deferred_hours, "Deferred Steps")
            )
        total_hours = sum(s.total_estimated_hours for s in sprints)
        total_steps = sum(len(s.step_ids) for s in sprints)
        return Roadmap(
            sprints=sprints,
            total_estimated_hours=round(total_hours, 1),
            total_steps=total_steps,
            summary=(
                f"{len(sprints)} sprint(s) covering {total_steps} step(s), "
                f"~{total_hours:.0f} engineer-hours total."
            ),
        )

    @staticmethod
    def _make_sprint(
        num: int,
        steps: list[PlanningStep],
        hours: float,
        title: str = "",
    ) -> SprintRecommendation:
        """Create a :class:`SprintRecommendation` from a list of steps."""
        if not title:
            # Generate a theme from the top priority step.
            top = steps[0] if steps else None
            if top and top.priority in (EngineeringPriority.CRITICAL, EngineeringPriority.HIGH):
                title = f"Sprint {num}: Critical Refactoring"
            elif top and top.priority == EngineeringPriority.MEDIUM:
                title = f"Sprint {num}: Quality Improvements"
            else:
                title = f"Sprint {num}: Cleanup & Maintenance"
        goals: list[str] = []
        for s in steps[:3]:
            goals.append(s.title)
        return SprintRecommendation(
            sprint_number=num,
            title=title,
            step_ids=[s.id for s in steps],
            total_estimated_hours=round(hours, 1),
            goals=goals,
            steps=steps,
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @staticmethod
    def _build_statistics(
        steps: list[PlanningStep],
        quick_wins: list[QuickWinItem],
        blockers: list[BlockerItem],
        roadmap: Roadmap,
    ) -> dict[str, Any]:
        """Build summary statistics for the engineering plan."""
        priority_counts: dict[str, int] = defaultdict(int)
        risk_counts: dict[str, int] = defaultdict(int)
        total_hours = 0.0
        total_roi = 0.0
        for step in steps:
            priority_counts[step.priority.value] += 1
            risk_counts[step.risk.value] += 1
            if step.estimate:
                total_hours += step.estimate.hours
            total_roi += step.roi
        return {
            "total_steps": len(steps),
            "total_quick_wins": len(quick_wins),
            "total_blockers": len(blockers),
            "total_sprints": len(roadmap.sprints) if roadmap.sprints else 0,
            "total_estimated_hours": round(total_hours, 1),
            "average_roi": round(total_roi / max(len(steps), 1), 3),
            "priority_counts": dict(priority_counts),
            "risk_counts": dict(risk_counts),
        }


__all__ = [
    "ImpactAnalyzer",
    "PlanningEngine",
    "ROICalculator",
    "PriorityEngine",
]
