"""Engineering LLM Context Builder.

Builds the context payload sent to the LLM. Unlike the existing
:class:`ContextBuilder` (which sends raw analyzer data), this builder
sends **only** the processed engineering outputs:

    - Evidence summary (counts, top items)
    - Root cause list (categories, severity, confidence)
    - Impact scores
    - Engineering plan (steps, priorities, ROI)
    - Quick wins
    - Risk analysis
    - Trade-off alternatives
    - Repository metadata

No raw analyzer output, no file snippets, no AST data is ever sent to
the LLM. The LLM receives a **curated engineering summary**, not a
raw data dump.
"""

from __future__ import annotations

from typing import Any

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.ports.llm_port import LLMPort


class EngineeringContextBuilder:
    """Build a token-budgeted engineering context for the LLM.

    The context contains **processed engineering outputs** only — no raw
    analyzer data. This keeps the LLM focused on interpreting the
    engineering conclusions rather than re-analyzing raw findings.
    """

    def __init__(self, *, max_tokens: int = 8000) -> None:
        self._max_tokens = max_tokens

    def build(
        self,
        result: AnalysisResult,
        llm: LLMPort | None = None,
    ) -> dict[str, Any]:
        """Build the engineering context dict.

        Args:
            result: The :class:`AnalysisResult` with evidence, root causes,
                and engineering plan populated.
            llm: Optional LLM for accurate token counting.

        Returns:
            A dict with sections for each engineering output.
        """
        context: dict[str, Any] = {}
        context["repository"] = self._repository_summary(result)
        context["evidence_summary"] = self._evidence_summary(result)
        context["root_causes"] = self._root_cause_summary(result)
        context["impact_scores"] = self._impact_summary(result)
        context["engineering_plan"] = self._plan_summary(result)
        context["quick_wins"] = self._quick_wins_summary(result)
        context["risk_analysis"] = self._risk_summary(result)
        context["trade_offs"] = self._tradeoff_summary(result)
        context["token_estimate"] = self._estimate_tokens(context, llm)
        return context

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _repository_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Repository metadata — high-level context only."""
        meta = result.repository_metadata
        return {
            "owner": result.repository.owner,
            "name": result.repository.name,
            "host": result.repository.host,
            "license": meta.license if meta else None,
            "total_commits": meta.total_commits if meta else None,
            "contributors": len(meta.contributors) if meta else 0,
            "primary_language": (
                result.language_distribution.primary_language
                if result.language_distribution
                else None
            ),
            "total_loc": (
                result.language_distribution.total_loc if result.language_distribution else 0
            ),
        }

    def _evidence_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Evidence summary — counts and top items, not raw evidence."""
        ev = result.evidence
        if ev is None:
            return {"total": 0, "by_type": {}, "top_items": []}
        stats = ev.statistics if hasattr(ev, "statistics") else {}
        top_items: list[dict[str, Any]] = []
        if hasattr(ev, "evidence"):
            for item in ev.evidence[:10]:
                top_items.append(
                    {
                        "type": item.finding_type.value
                        if hasattr(item, "finding_type")
                        else str(item.finding_type),
                        "category": item.category,
                        "severity": item.severity.value
                        if hasattr(item, "severity")
                        else str(item.severity),
                        "message": item.message,
                        "file": item.file_path,
                        "analyzer": item.analyzer,
                    }
                )
        return {
            "total": stats.get("total_evidence", 0),
            "by_type_counts": stats.get("by_type_counts", {}),
            "by_severity_counts": stats.get("by_severity_counts", {}),
            "by_analyzer_counts": stats.get("by_analyzer_counts", {}),
            "top_items": top_items,
        }

    def _root_cause_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Root cause summary — categories, severity, confidence."""
        rc = result.root_causes
        if rc is None:
            return {"total": 0, "items": []}
        items: list[dict[str, Any]] = []
        for cause in rc.root_causes[:15]:
            items.append(
                {
                    "category": cause.category.value,
                    "title": cause.title,
                    "severity": cause.severity.value,
                    "confidence": cause.confidence,
                    "evidence_count": cause.evidence_count,
                    "affected_files": cause.affected_files[:5],
                    "affected_classes": cause.affected_classes[:3],
                    "description": cause.description,
                }
            )
        return {
            "total": rc.total,
            "by_category": rc.statistics.get("by_category_counts", {}),
            "by_severity": rc.statistics.get("by_severity_counts", {}),
            "average_confidence": rc.statistics.get("average_confidence", 0),
            "items": items,
        }

    def _impact_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Impact scores from the engineering plan."""
        plan = result.engineering_plan
        if plan is None or not plan.impact_scores:
            return {"items": []}
        items: list[dict[str, Any]] = []
        for score in plan.impact_scores[:10]:
            items.append(
                {
                    "root_cause_id": str(score.root_cause_id) if score.root_cause_id else None,
                    "overall": score.overall,
                    "security_impact": score.security_impact,
                    "maintainability_impact": score.maintainability_impact,
                    "testability_impact": score.testability_impact,
                }
            )
        return {"items": items}

    def _plan_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Engineering plan summary — steps with priorities, ROI, estimates."""
        plan = result.engineering_plan
        if plan is None:
            return {"total_steps": 0, "steps": [], "roadmap": {}}
        steps: list[dict[str, Any]] = []
        for step in plan.steps[:15]:
            steps.append(
                {
                    "step_number": step.step_number,
                    "title": step.title,
                    "priority": step.priority.value,
                    "roi": step.roi,
                    "risk": step.risk.value,
                    "estimate_hours": step.estimate.hours if step.estimate else 0,
                    "root_cause_category": step.root_cause_category,
                    "expected_outcomes": step.expected_outcomes[:3],
                    "prerequisites": len(step.prerequisites),
                }
            )
        roadmap: dict[str, Any] = {}
        if plan.roadmap:
            roadmap = {
                "total_sprints": len(plan.roadmap.sprints),
                "total_hours": plan.roadmap.total_estimated_hours,
                "summary": plan.roadmap.summary,
                "sprints": [
                    {
                        "number": s.sprint_number,
                        "title": s.title,
                        "hours": s.total_estimated_hours,
                        "goals": s.goals[:3],
                    }
                    for s in plan.roadmap.sprints[:5]
                ],
            }
        return {
            "total_steps": plan.total_steps,
            "total_quick_wins": len(plan.quick_wins),
            "total_blockers": len(plan.blockers),
            "average_roi": plan.statistics.get("average_roi", 0),
            "priority_counts": plan.statistics.get("priority_counts", {}),
            "steps": steps,
            "roadmap": roadmap,
        }

    def _quick_wins_summary(self, result: AnalysisResult) -> list[dict[str, Any]]:
        """Quick wins — low-effort, high-benefit items."""
        plan = result.engineering_plan
        if plan is None:
            return []
        return [
            {
                "title": qw.title,
                "effort_minutes": qw.effort_minutes,
                "benefit": qw.benefit,
            }
            for qw in plan.quick_wins[:10]
        ]

    def _risk_summary(self, result: AnalysisResult) -> dict[str, Any]:
        """Risk analysis from the engineering plan."""
        plan = result.engineering_plan
        if plan is None:
            return {"risk_counts": {}}
        return {
            "risk_counts": plan.statistics.get("risk_counts", {}),
            "total_blockers": len(plan.blockers),
            "blockers": [
                {
                    "reason": b.reason,
                    "blocked_count": len(b.blocked_root_cause_ids),
                }
                for b in plan.blockers[:5]
            ],
        }

    def _tradeoff_summary(self, result: AnalysisResult) -> list[dict[str, Any]]:
        """Trade-off alternatives from planning steps."""
        plan = result.engineering_plan
        if plan is None:
            return []
        tradeoffs: list[dict[str, Any]] = []
        for step in plan.steps[:5]:
            if not step.alternatives:
                continue
            alts: list[dict[str, Any]] = []
            for alt in step.alternatives:
                alts.append(
                    {
                        "name": alt.name,
                        "advantages": alt.advantages[:3],
                        "disadvantages": alt.disadvantages[:3],
                        "risk": alt.risk.value,
                        "migration_difficulty": alt.migration_difficulty,
                    }
                )
            tradeoffs.append(
                {
                    "step_title": step.title,
                    "alternatives": alts,
                }
            )
        return tradeoffs

    # ------------------------------------------------------------------
    # Token estimation
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_tokens(context: dict[str, Any], llm: LLMPort | None) -> int:
        """Estimate total tokens in the context."""
        import json

        serialized = json.dumps(context, default=str)
        if llm:
            return llm.count_tokens(serialized)
        return max(1, len(serialized) // 4)


__all__ = ["EngineeringContextBuilder"]
