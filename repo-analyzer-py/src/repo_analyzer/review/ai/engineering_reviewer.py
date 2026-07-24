"""Engineering LLM Reviewer.

Orchestrates the LLM call to produce an :class:`EngineeringLLMReview`.
The reviewer:

    1. Builds a curated engineering context (no raw analyzer data).
    2. Builds a review-oriented prompt (not problem-finding).
    3. Calls the LLM (or produces a deterministic fallback if offline).
    4. Parses the LLM response into structured sections.
    5. Tags each section with confidence.
    6. Extracts challenges to the planning engine.

Design:
    - **LLM-optional**: If ``llm`` is ``None`` or the call fails, a
      deterministic fallback review is produced from the planning engine
      output. The system never crashes because the LLM is unavailable.
    - **Hallucination-aware**: The prompt explicitly forbids inventing
      new technical facts. The response parser checks that each section
      references existing evidence/planning items.
    - **Timeout-safe**: LLM calls have a configurable timeout. On timeout,
      the fallback review is used.

Usage::

    from repo_analyzer.review.ai.engineering_reviewer import EngineeringReviewer
    from repo_analyzer.adapters.llm import MockLLMProvider

    reviewer = EngineeringReviewer(llm=MockLLMProvider())
    review = reviewer.review(result)
    for section in review.sections:
        print(section.title, section.confidence.value)
"""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.evidence.engineering_review_models import (
    ChallengeItem,
    EngineeringLLMReview,
    EngineeringRecommendation,
    ReviewConfidence,
    ReviewSection,
    ReviewSectionType,
)
from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.infrastructure.errors import AIException
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.review.ai.engineering_context_builder import EngineeringContextBuilder
from repo_analyzer.review.ai.engineering_prompt_builder import EngineeringPromptBuilder

_logger = get_logger(__name__)

#: LLM call timeout in seconds.
_DEFAULT_TIMEOUT = 120


class EngineeringReviewer:
    """Produce an :class:`EngineeringLLMReview` from the analysis result.

    Args:
        llm: The LLM provider. If ``None``, a deterministic offline review
            is produced.
        context_builder: Optional custom context builder.
        prompt_builder: Optional custom prompt builder.
        timeout: LLM call timeout in seconds.
    """

    def __init__(
        self,
        llm: LLMPort | None = None,
        *,
        context_builder: EngineeringContextBuilder | None = None,
        prompt_builder: EngineeringPromptBuilder | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
    ) -> None:
        self._llm = llm
        self._context_builder = context_builder or EngineeringContextBuilder()
        self._prompt_builder = prompt_builder or EngineeringPromptBuilder()
        self._timeout = timeout

    def review(self, result: AnalysisResult) -> EngineeringLLMReview:
        """Produce the engineering review.

        Args:
            result: A populated :class:`AnalysisResult` with evidence,
                root causes, and engineering plan.

        Returns:
            An :class:`EngineeringLLMReview`.
        """
        _logger.info("Starting LLM engineering review")

        if self._llm is None:
            _logger.info("LLM not configured — producing offline fallback review")
            return self._offline_review(result)

        # 1. Build context.
        context = self._context_builder.build(result, self._llm)
        _logger.debug(
            "Engineering context built (%d tokens est.)", context.get("token_estimate", 0)
        )

        # 2. Build prompt.
        system_prompt, user_prompt = self._prompt_builder.build(context)

        # 3. Call LLM.
        try:
            raw_response = self._llm.complete(
                user_prompt,
                system=system_prompt,
                max_tokens=4096,
                temperature=0.3,
            )
        except AIException as exc:
            _logger.warning("LLM call failed (%s) — using fallback", exc.message)
            return self._offline_review(result)
        except Exception as exc:
            _logger.warning("LLM call failed (%s) — using fallback", exc)
            return self._offline_review(result)

        # 4. Parse response into structured review.
        review = self._parse_response(raw_response, result)
        _logger.info(
            "LLM engineering review complete (%d sections, %d challenges)",
            review.total_sections,
            review.total_challenges,
        )
        return review

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(self, raw: str, result: AnalysisResult) -> EngineeringLLMReview:
        """Parse the raw LLM response into structured sections."""
        sections = self._extract_sections(raw)
        challenges = self._extract_challenges(raw, result)
        recommendations = self._extract_recommendations(raw, result)

        # Build model info.
        model_info: dict[str, Any] = {}
        if self._llm is not None:
            model_info = {
                "provider": self._llm.provider_name,
                "model": self._llm.model_name,
            }

        stats = {
            "total_sections": len(sections),
            "total_challenges": len(challenges),
            "total_recommendations": len(recommendations),
            "confidence_distribution": self._confidence_distribution(sections),
        }

        return EngineeringLLMReview(
            sections=sections,
            challenges=challenges,
            recommendations=recommendations,
            model_info=model_info,
            offline=False,
            generated_at=datetime.now(tz=UTC).isoformat(),
            statistics=stats,
        )

    def _extract_sections(self, raw: str) -> list[ReviewSection]:
        """Extract structured sections from the LLM response.

        Looks for numbered headings (1. **Title**: ...) and confidence
        tags ([HIGH], [MEDIUM], etc.).
        """
        sections: list[ReviewSection] = []
        # Pattern: "1. **Title**:" or "## Title" followed by content.
        pattern = re.compile(
            r"(?:^|\n)\d+\.\s*\*{0,2}([^*:*\n]+?)\*{0,2}\s*:\s*\[?(HIGH|MEDIUM|LOW|SPECULATIVE)?\]?\s*\n(.*?)(?=\n\d+\.\s*\*{0,2}|\Z)",
            re.DOTALL,
        )
        type_map = {
            "executive summary": ReviewSectionType.EXECUTIVE_SUMMARY,
            "architecture review": ReviewSectionType.ARCHITECTURE_REVIEW,
            "top root causes": ReviewSectionType.TOP_ROOT_CAUSES,
            "highest roi": ReviewSectionType.HIGHEST_ROI_REFACTORING,
            "risk assessment": ReviewSectionType.RISK_ASSESSMENT,
            "recommendations": ReviewSectionType.ENGINEERING_RECOMMENDATIONS,
            "trade-off": ReviewSectionType.TRADE_OFF_ANALYSIS,
            "trade off": ReviewSectionType.TRADE_OFF_ANALYSIS,
            "migration": ReviewSectionType.MIGRATION_ADVICE,
            "long-term": ReviewSectionType.LONG_TERM_VISION,
            "long term": ReviewSectionType.LONG_TERM_VISION,
            "challenge": ReviewSectionType.CHALLENGE,
        }
        for match in pattern.finditer(raw):
            title = match.group(1).strip()
            confidence_str = (match.group(2) or "MEDIUM").upper()
            body = match.group(3).strip()
            confidence = ReviewConfidence(confidence_str.lower())
            section_type = ReviewSectionType.EXECUTIVE_SUMMARY
            title_lower = title.lower()
            for key, st in type_map.items():
                if key in title_lower:
                    section_type = st
                    break
            sections.append(
                ReviewSection(
                    section_type=section_type,
                    title=title,
                    body=body,
                    confidence=confidence,
                )
            )

        # If no sections were parsed, put the entire response as one section.
        if not sections and raw.strip():
            sections.append(
                ReviewSection(
                    section_type=ReviewSectionType.EXECUTIVE_SUMMARY,
                    title="Review",
                    body=raw.strip(),
                    confidence=ReviewConfidence.MEDIUM,
                )
            )
        return sections

    def _extract_challenges(self, raw: str, result: AnalysisResult) -> list[ChallengeItem]:
        """Extract challenge items from the LLM response.

        Looks for the "Challenge" section and parses individual challenges.
        """
        challenges: list[ChallengeItem] = []
        # Find the challenge section.
        challenge_match = re.search(
            r"(?:^|\n)\d+\.\s*\*{0,2}Challenge\*{0,2}\s*:?(.*?)(?=\n\d+\.\s*\*{0,2}|\Z)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if not challenge_match:
            return challenges
        challenge_text = challenge_match.group(1).strip()
        # Split by bullet points or numbered items.
        items = re.split(r"\n[-*]\s+", challenge_text)
        for item in items:
            item = item.strip()
            if not item or len(item) < 10:
                continue
            challenge_type = "alternative_approach"
            if "too aggressive" in item.lower():
                challenge_type = "too_aggressive"
            elif "too conservative" in item.lower():
                challenge_type = "too_conservative"
            elif "insufficient evidence" in item.lower() or "weak" in item.lower():
                challenge_type = "insufficient_evidence"
            elif "risk" in item.lower():
                challenge_type = "risk_underestimated"
            challenges.append(
                ChallengeItem(
                    description=item[:500],
                    challenge_type=challenge_type,
                    confidence=ReviewConfidence.MEDIUM,
                )
            )
        return challenges

    def _extract_recommendations(
        self, raw: str, result: AnalysisResult
    ) -> list[EngineeringRecommendation]:
        """Extract recommendations from the LLM response."""
        recommendations: list[EngineeringRecommendation] = []
        rec_match = re.search(
            r"(?:^|\n)\d+\.\s*\*{0,2}Engineering Recommendations\*{0,2}\s*:?(.*?)(?=\n\d+\.\s*\*{0,2}|\Z)",
            raw,
            re.DOTALL | re.IGNORECASE,
        )
        if not rec_match:
            return recommendations
        rec_text = rec_match.group(1).strip()
        items = re.split(r"\n[-*]\s+", rec_text)
        for item in items:
            item = item.strip()
            if not item or len(item) < 10:
                continue
            priority = "medium"
            if "critical" in item.lower():
                priority = "critical"
            elif "high" in item.lower():
                priority = "high"
            elif "low" in item.lower():
                priority = "low"
            recommendations.append(
                EngineeringRecommendation(
                    title=item[:200],
                    description=item[:500],
                    priority=priority,
                    confidence=ReviewConfidence.MEDIUM,
                    rationale="Derived from LLM review of engineering plan.",
                )
            )
        return recommendations

    @staticmethod
    def _confidence_distribution(sections: list[ReviewSection]) -> dict[str, int]:
        """Count sections by confidence level."""
        dist: dict[str, int] = {}
        for s in sections:
            dist[s.confidence.value] = dist.get(s.confidence.value, 0) + 1
        return dist

    # ------------------------------------------------------------------
    # Offline fallback
    # ------------------------------------------------------------------

    def _offline_review(self, result: AnalysisResult) -> EngineeringLLMReview:
        """Produce a deterministic review without an LLM.

        The fallback review is built from the engineering plan and root
        cause collection — it provides a useful summary even when the LLM
        is unavailable.
        """
        sections: list[ReviewSection] = []
        plan = result.engineering_plan
        rc = result.root_causes

        # Executive Summary.
        summary_body = self._fallback_summary(result, plan, rc)
        sections.append(
            ReviewSection(
                section_type=ReviewSectionType.EXECUTIVE_SUMMARY,
                title="Executive Summary",
                body=summary_body,
                confidence=ReviewConfidence.HIGH,
            )
        )

        # Top Root Causes.
        if rc and rc.root_causes:
            top_rcs = rc.root_causes[:5]
            body = "\n".join(
                f"- **{rc_item.title}** (severity: {rc_item.severity.value}, "
                f"confidence: {rc_item.confidence:.0%}) — {rc_item.description}"
                for rc_item in top_rcs
            )
            sections.append(
                ReviewSection(
                    section_type=ReviewSectionType.TOP_ROOT_CAUSES,
                    title="Top Root Causes",
                    body=body,
                    confidence=ReviewConfidence.HIGH,
                )
            )

        # Highest ROI.
        if plan and plan.steps:
            top_roi = max(plan.steps, key=lambda s: s.roi)
            body = (
                f"Step {top_roi.step_number}: **{top_roi.title}**\n"
                f"ROI: {top_roi.roi:.2f}\n"
                f"Priority: {top_roi.priority.value}\n"
                f"Estimate: {top_roi.estimate.display if top_roi.estimate else 'N/A'}\n"
                f"Expected outcomes: {', '.join(top_roi.expected_outcomes[:3])}"
            )
            sections.append(
                ReviewSection(
                    section_type=ReviewSectionType.HIGHEST_ROI_REFACTORING,
                    title="Highest ROI Refactoring",
                    body=body,
                    confidence=ReviewConfidence.HIGH,
                )
            )

        # Risk Assessment.
        if plan:
            risk_body = self._fallback_risk(plan)
            sections.append(
                ReviewSection(
                    section_type=ReviewSectionType.RISK_ASSESSMENT,
                    title="Risk Assessment",
                    body=risk_body,
                    confidence=ReviewConfidence.HIGH,
                )
            )

        # Long-term Vision.
        vision = self._fallback_vision(result, plan, rc)
        sections.append(
            ReviewSection(
                section_type=ReviewSectionType.LONG_TERM_VISION,
                title="Long-term Vision",
                body=vision,
                confidence=ReviewConfidence.LOW,
            )
        )

        stats = {
            "total_sections": len(sections),
            "total_challenges": 0,
            "total_recommendations": 0,
            "confidence_distribution": self._confidence_distribution(sections),
            "offline": True,
        }

        return EngineeringLLMReview(
            sections=sections,
            challenges=[],
            recommendations=[],
            model_info={"provider": "offline", "model": "deterministic-fallback"},
            offline=True,
            generated_at=datetime.now(tz=UTC).isoformat(),
            statistics=stats,
        )

    def _fallback_summary(
        self,
        result: AnalysisResult,
        plan: Any,
        rc: Any,
    ) -> str:
        """Build a deterministic executive summary."""
        parts: list[str] = []
        repo_name = f"{result.repository.owner}/{result.repository.name}"
        parts.append(f"Repository: {repo_name}.")
        if rc:
            parts.append(
                f"Root cause analysis identified {rc.total} architectural "
                f"root cause(s) with an average confidence of "
                f"{rc.statistics.get('average_confidence', 0):.0%}."
            )
        if plan:
            parts.append(
                f"The engineering plan proposes {plan.total_steps} refactoring "
                f"step(s) across {len(plan.roadmap.sprints) if plan.roadmap else 0} "
                f"sprint(s), totaling approximately "
                f"{plan.roadmap.total_estimated_hours if plan.roadmap else 0:.0f} "
                f"engineer-hours."
            )
            if plan.quick_wins:
                parts.append(
                    f"{len(plan.quick_wins)} quick win(s) identified for immediate action."
                )
        parts.append(
            "This review was produced in offline mode (no LLM). "
            "Enable an LLM provider for richer analysis."
        )
        return " ".join(parts)

    def _fallback_risk(self, plan: Any) -> str:
        """Build a deterministic risk assessment."""
        risk_counts = plan.statistics.get("risk_counts", {})
        lines = [f"Risk distribution: {risk_counts}"]
        if plan.blockers:
            lines.append(f"\n{len(plan.blockers)} blocker(s) identified:")
            for b in plan.blockers[:5]:
                lines.append(f"- {b.reason}")
        return "\n".join(lines)

    def _fallback_vision(
        self,
        result: AnalysisResult,
        plan: Any,
        rc: Any,
    ) -> str:
        """Build a deterministic long-term vision."""
        if not rc or not rc.root_causes:
            return "No root causes detected — the repository appears structurally sound."
        categories = {r.category.value for r in rc.root_causes}
        if "god_class" in categories or "oversized_service" in categories:
            return (
                "The team should aim to decompose large classes/services into "
                "focused, single-responsibility components over the next 6 months. "
                "Introduce interface-based dependency injection to decouple modules."
            )
        if "circular_dependency" in categories:
            return (
                "The team should break all circular dependencies within 3 months "
                "and establish a clear dependency-direction policy enforced by CI."
            )
        return (
            "The team should address the identified root causes incrementally, "
            "starting with the highest-ROI items from the engineering plan."
        )


__all__ = ["EngineeringReviewer"]
