"""AI comment engine.

Orchestrates the review phase: runs all deterministic review engines
(security, quality, architecture, file/directory/project, health, risk,
debt, refactor), builds a token-budgeted context, calls the LLM and
assembles the final :class:`AIReview`.

The LLM call is fully mockable: pass a :class:`MockLLMProvider` in tests to
exercise the whole pipeline offline.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.ai_review import AIReview, ModelInfo
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.infrastructure.errors import AIException
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.review.ai.context_builder import ContextBuilder
from repo_analyzer.review.ai.prompt_builder import PromptBuilder
from repo_analyzer.review.architecture.engine import ArchitectureReviewEngine
from repo_analyzer.review.debt.engine import TechnicalDebtEngine
from repo_analyzer.review.directory_level.engine import DirectoryReviewEngine
from repo_analyzer.review.file_level.engine import FileReviewEngine
from repo_analyzer.review.health.engine import HealthScoreReviewEngine
from repo_analyzer.review.project_level.engine import ProjectReviewEngine
from repo_analyzer.review.quality.engine import CodeQualityEngine
from repo_analyzer.review.refactor.engine import RefactorEngine
from repo_analyzer.review.risk.engine import RiskEngine
from repo_analyzer.review.security.engine import SecurityReviewEngine

_logger = get_logger(__name__)


class AICommentEngine:
    """Run the full review phase and produce an :class:`AIReview`."""

    def __init__(
        self,
        llm: LLMPort,
        *,
        context_builder: ContextBuilder | None = None,
        prompt_builder: PromptBuilder | None = None,
        security_engine: SecurityReviewEngine | None = None,
    ) -> None:
        self._llm = llm
        self._context_builder = context_builder or ContextBuilder()
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._security_engine = security_engine or SecurityReviewEngine()
        self._quality_engine = CodeQualityEngine()
        self._architecture_engine = ArchitectureReviewEngine()
        self._file_engine = FileReviewEngine()
        self._directory_engine = DirectoryReviewEngine()
        self._project_engine = ProjectReviewEngine()
        self._health_engine = HealthScoreReviewEngine()
        self._risk_engine = RiskEngine()
        self._debt_engine = TechnicalDebtEngine()
        self._refactor_engine = RefactorEngine()

    def review(
        self,
        result: AnalysisResult,
        workspace: Path | None = None,
    ) -> AIReview:
        """Produce the :class:`AIReview` for ``result``.

        Args:
            result: The populated :class:`AnalysisResult`.
            workspace: Optional workspace path for file snippet reading.

        Returns:
            A fully-populated :class:`AIReview`.
        """
        _logger.info("Starting review phase")

        # 1. Deterministic review engines.
        security_review = self._security_engine.review(result.repository, workspace or Path("."))
        # Augment the AnalysisResult security_findings with the rich findings.
        result.security_findings = [
            *result.security_findings,
            *self._to_security_findings(security_review),
        ]
        code_quality = self._quality_engine.review(result)
        architecture = self._architecture_engine.review(result)
        file_reviews = self._file_engine.review(result)
        directory_reviews = self._directory_engine.review(result, workspace)
        project_review = self._project_engine.review(result)
        health_score = self._health_engine.compute(result)
        risk_summary = self._risk_engine.summarize(result)
        technical_debt = self._debt_engine.analyze(result)
        refactor_plan, quick_wins = self._refactor_engine.plan(result)

        # 2. Build LLM context + prompt.
        context = self._context_builder.build(result, workspace, self._llm)
        system, user = self._prompt_builder.build(context)

        # 3. Call the LLM (mockable).
        try:
            commentary = self._llm.complete(user, system=system, temperature=0.2)
        except AIException as exc:
            _logger.warning("LLM call failed; using deterministic summary: %s", exc.message)
            commentary = self._fallback_commentary(result, project_review, risk_summary)

        # 4. Assemble the AIReview.
        review = AIReview(
            summary=self._extract_summary(commentary, project_review),
            strengths=project_review.strengths,
            risks=[r.title for r in [*risk_summary.critical, *risk_summary.high]],
            recommendations=[],
            confidence=80,
            model=ModelInfo(
                provider=self._llm.provider_name,
                model=self._llm.model_name,
            ),
            generated_at=datetime.now(tz=UTC).isoformat(),
            metadata={
                "commentary": commentary,
                "token_estimate": context.get("token_estimate", 0),
            },
            project_review=project_review,
            directory_reviews=directory_reviews,
            file_reviews=file_reviews,
            security_review=security_review,
            architecture_review=architecture,
            code_quality_review=code_quality,
            technical_debt=technical_debt,
            risk_summary=risk_summary,
            health_score=health_score,
            refactor_plan=refactor_plan,
            quick_wins=quick_wins,
        )
        _logger.info("Review phase complete (grade=%s)", health_score.grade.value)
        return review

    # ----- helpers -------------------------------------------------------------

    @staticmethod
    def _to_security_findings(security_review: Any) -> list[Any]:
        """Convert :class:`SecurityFindingDetail` to core :class:`SecurityFinding`."""
        from repo_analyzer.core.domain.report import Location, Severity
        from repo_analyzer.core.domain.security_finding import (
            Confidence,
            SecurityCategory,
            SecurityFinding,
        )

        out: list[SecurityFinding] = []
        for detail in security_review.findings:
            sev = {
                "critical": Severity.CRITICAL,
                "high": Severity.HIGH,
                "medium": Severity.MEDIUM,
                "low": Severity.LOW,
                "info": Severity.INFO,
            }.get(detail.severity.value, Severity.MEDIUM)
            out.append(
                SecurityFinding(
                    rule_id=detail.category,
                    category=SecurityCategory.OTHER,
                    severity=sev,
                    confidence=Confidence.MEDIUM,
                    message=detail.title,
                    location=Location(file=detail.file, line=detail.line) if detail.line else None,
                    description=detail.why_risky,
                    fix_suggestion=detail.solution,
                    references=detail.references,
                )
            )
        return out

    @staticmethod
    def _extract_summary(commentary: str, project_review: Any) -> str:
        """Extract a short summary from the LLM commentary."""
        if project_review and project_review.summary:
            return str(project_review.summary)
        # Take the first paragraph of the commentary.
        return commentary.split("\n\n")[0][:500]

    @staticmethod
    def _fallback_commentary(result: AnalysisResult, project_review: Any, risk_summary: Any) -> str:
        """Deterministic fallback when the LLM is unavailable."""
        lines = ["## Engineering Review (deterministic fallback)"]
        if project_review:
            lines.append(f"\n{project_review.summary}")
        if risk_summary:
            critical = len(risk_summary.critical)
            high = len(risk_summary.high)
            lines.append(f"\nRisk profile: {critical} critical, {high} high-severity item(s).")
        lines.append(
            "\nThe LLM was unavailable; this review is based on deterministic "
            "analysis only. Re-run with a configured LLM provider for richer commentary."
        )
        return "\n".join(lines)


__all__ = ["AICommentEngine"]
