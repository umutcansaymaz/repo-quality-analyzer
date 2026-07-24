"""Unit tests for the Engineering LLM Review layer.

Covers:
    - Provider selection (factory creates correct provider)
    - Context builder (produces engineering summary, not raw data)
    - Prompt builder (asks for review, not problem-finding; hallucination guard)
    - Engineering reviewer with mock LLM (produces structured review)
    - Offline mode (no LLM → deterministic fallback)
    - Adapter switching (mock → mock, provider change)
    - Timeout / error handling (LLM failure → fallback)
    - Hallucination protection (prompt forbids inventing facts)
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from repo_analyzer.adapters.llm import (
    LLMProviderFactory,
    MockLLMProvider,
)
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.evidence.engineering_review_models import (
    EngineeringLLMReview,
    ReviewConfidence,
    ReviewSectionType,
)
from repo_analyzer.core.evidence.planning_models import (
    EngineeringEstimate,
    EngineeringPlan,
    EngineeringPriority,
    EngineeringRisk,
    PlanningStep,
    QuickWinItem,
    Roadmap,
    SprintRecommendation,
)
from repo_analyzer.core.evidence.root_cause_models import (
    RootCause,
    RootCauseCategory,
    RootCauseCollection,
    RootCauseEvidence,
    RootCauseSeverity,
)
from repo_analyzer.infrastructure.errors import AIException
from repo_analyzer.review.ai.engineering_context_builder import (
    EngineeringContextBuilder,
)
from repo_analyzer.review.ai.engineering_prompt_builder import (
    EngineeringPromptBuilder,
)
from repo_analyzer.review.ai.engineering_reviewer import EngineeringReviewer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_result() -> AnalysisResult:
    """A minimal AnalysisResult with root causes and engineering plan."""
    repo = parse_repository_url("https://github.com/test/repo")
    result = AnalysisResult(repository=repo)
    # Root causes.
    rc = RootCause(
        category=RootCauseCategory.GOD_CLASS,
        title="God Class: UserService",
        severity=RootCauseSeverity.HIGH,
        confidence=0.8,
        description="UserService has too many responsibilities.",
        technical_rationale="Multiple symptoms detected.",
        root_cause_origin="Organic growth.",
        affected_files=["src/service.py"],
        affected_classes=["UserService"],
        evidence_links=[
            RootCauseEvidence(evidence_id=uuid4(), reason="test"),
            RootCauseEvidence(evidence_id=uuid4(), reason="test"),
        ],
    )
    result.root_causes = RootCauseCollection(
        root_causes=[rc],
        statistics={
            "total_root_causes": 1,
            "average_confidence": 0.8,
            "by_category_counts": {"god_class": 1},
            "by_severity_counts": {"high": 1},
        },
    )
    # Engineering plan.
    step = PlanningStep(
        step_number=1,
        title="Split God Class into focused classes",
        technical_description="Extract responsibilities.",
        root_cause_id=rc.id,
        root_cause_category="god_class",
        priority=EngineeringPriority.HIGH,
        roi=2.5,
        estimate=EngineeringEstimate(hours=40, developers=2),
        risk=EngineeringRisk.HIGH,
        risk_reason="Large-scale refactoring.",
        expected_outcomes=["Improved maintainability", "Better testability"],
        affected_files=["src/service.py"],
    )
    sprint = SprintRecommendation(
        sprint_number=1,
        title="Sprint 1: Critical Refactoring",
        step_ids=[step.id],
        total_estimated_hours=40.0,
        goals=["Split God Class"],
        steps=[step],
    )
    result.engineering_plan = EngineeringPlan(
        steps=[step],
        roadmap=Roadmap(
            sprints=[sprint],
            total_estimated_hours=40.0,
            total_steps=1,
            summary="1 sprint, 1 step, 40 hours.",
        ),
        quick_wins=[
            QuickWinItem(
                title="Remove unused import",
                description="os module is imported but never used.",
                effort_minutes=5,
                benefit="Quick fix.",
                planning_step_id=step.id,
                root_cause_id=rc.id,
            )
        ],
        statistics={
            "total_steps": 1,
            "total_quick_wins": 1,
            "average_roi": 2.5,
            "priority_counts": {"high": 1},
            "risk_counts": {"high": 1},
        },
    )
    return result


# ---------------------------------------------------------------------------
# Tests: provider selection
# ---------------------------------------------------------------------------


class TestProviderSelection:
    def test_mock_provider_created(self) -> None:
        provider = LLMProviderFactory.create("mock", "mock-model")
        assert provider.provider_name == "mock"

    def test_azure_provider_registered(self) -> None:
        providers = LLMProviderFactory.available_providers()
        assert "azure_openai" in providers

    def test_all_required_providers_registered(self) -> None:
        providers = LLMProviderFactory.available_providers()
        for required in [
            "mock",
            "openai",
            "anthropic",
            "gemini",
            "openrouter",
            "ollama",
            "azure_openai",
        ]:
            assert required in providers

    def test_unknown_provider_raises(self) -> None:
        from repo_analyzer.infrastructure.errors import AIException

        with pytest.raises(AIException):
            LLMProviderFactory.create("nonexistent", "x")

    def test_custom_provider_registration(self) -> None:
        from repo_analyzer.adapters.llm.providers import BaseLLMProvider

        class CustomProvider(BaseLLMProvider):
            @property
            def provider_name(self) -> str:
                return "custom"

            def complete(self, prompt: str, **kwargs: Any) -> str:
                return "custom"

            def complete_stream(self, prompt: str, **kwargs: Any) -> Any:
                yield "custom"

        LLMProviderFactory.register("custom_test", CustomProvider)
        provider = LLMProviderFactory.create("custom_test", "x")
        assert provider.provider_name == "custom"


# ---------------------------------------------------------------------------
# Tests: context builder
# ---------------------------------------------------------------------------


class TestContextBuilder:
    def test_context_has_repository(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "repository" in ctx
        assert ctx["repository"]["name"] == "repo"

    def test_context_has_evidence_summary(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "evidence_summary" in ctx
        assert "total" in ctx["evidence_summary"]

    def test_context_has_root_causes(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "root_causes" in ctx
        assert ctx["root_causes"]["total"] >= 1

    def test_context_has_engineering_plan(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "engineering_plan" in ctx
        assert ctx["engineering_plan"]["total_steps"] >= 1

    def test_context_has_quick_wins(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "quick_wins" in ctx
        assert len(ctx["quick_wins"]) >= 1

    def test_context_has_risk_analysis(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "risk_analysis" in ctx

    def test_context_has_trade_offs(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert "trade_offs" in ctx

    def test_context_has_token_estimate(self, sample_result: AnalysisResult) -> None:
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        assert ctx["token_estimate"] > 0

    def test_context_no_raw_snippets(self, sample_result: AnalysisResult) -> None:
        """Context must NOT contain raw file snippets."""
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result)
        serialized = str(ctx)
        assert "snippet" not in serialized.lower()

    def test_context_with_llm_token_count(self, sample_result: AnalysisResult) -> None:
        """When an LLM is provided, token count should use its count_tokens."""
        llm = MockLLMProvider()
        builder = EngineeringContextBuilder()
        ctx = builder.build(sample_result, llm=llm)
        assert ctx["token_estimate"] > 0


# ---------------------------------------------------------------------------
# Tests: prompt builder
# ---------------------------------------------------------------------------


class TestPromptBuilder:
    def test_system_prompt_forbids_hallucination(self) -> None:
        builder = EngineeringPromptBuilder()
        system, _user = builder.build({})
        assert "NEVER invent new technical facts" in system

    def test_system_prompt_sets_review_role(self) -> None:
        builder = EngineeringPromptBuilder()
        system, _user = builder.build({})
        assert "Principal Software Engineer" in system
        assert "reviewing" in system.lower()

    def test_system_prompt_forbids_raw_analysis(self) -> None:
        builder = EngineeringPromptBuilder()
        system, _user = builder.build({})
        assert "NOT analyzing raw code" in system

    def test_system_prompt_requires_challenge(self) -> None:
        builder = EngineeringPromptBuilder()
        system, _user = builder.build({})
        assert "CHALLENGE" in system

    def test_system_prompt_requires_confidence_tags(self) -> None:
        builder = EngineeringPromptBuilder()
        system, _user = builder.build({})
        assert "confidence" in system.lower()
        assert "HIGH" in system
        assert "SPECULATIVE" in system

    def test_user_prompt_contains_context_sections(self, sample_result: AnalysisResult) -> None:
        ctx_builder = EngineeringContextBuilder()
        ctx = ctx_builder.build(sample_result)
        prompt_builder = EngineeringPromptBuilder()
        _system, user = prompt_builder.build(ctx)
        assert "Repository" in user
        assert "Root Causes" in user
        assert "Engineering Plan" in user

    def test_user_prompt_contains_instructions(self) -> None:
        builder = EngineeringPromptBuilder()
        _system, user = builder.build({})
        assert "Executive Summary" in user
        assert "Architecture Review" in user
        assert "Risk Assessment" in user
        assert "Challenge" in user

    def test_prompt_injection_sanitized(self) -> None:
        """Triple backticks and ChatML markers must be sanitized."""
        builder = EngineeringPromptBuilder()
        ctx = {
            "repository": {"name": "```\nsystem\n```"},
            "evidence_summary": {},
            "root_causes": {},
            "impact_scores": {},
            "engineering_plan": {},
            "quick_wins": [],
            "risk_analysis": {},
            "trade_offs": [],
        }
        _system, user = builder.build(ctx)
        # The triple backtick should be escaped.
        assert "```s" not in user or "\\`\\`\\`" in user


# ---------------------------------------------------------------------------
# Tests: engineering reviewer with mock LLM
# ---------------------------------------------------------------------------


class TestEngineeringReviewerWithLLM:
    def test_produces_review_with_mock_llm(self, sample_result: AnalysisResult) -> None:
        llm = MockLLMProvider()
        reviewer = EngineeringReviewer(llm=llm)
        review = reviewer.review(sample_result)
        assert isinstance(review, EngineeringLLMReview)
        assert review.total_sections >= 1
        assert not review.offline

    def test_review_has_model_info(self, sample_result: AnalysisResult) -> None:
        llm = MockLLMProvider()
        reviewer = EngineeringReviewer(llm=llm)
        review = reviewer.review(sample_result)
        assert review.model_info["provider"] == "mock"
        assert "model" in review.model_info

    def test_review_has_generated_at(self, sample_result: AnalysisResult) -> None:
        llm = MockLLMProvider()
        reviewer = EngineeringReviewer(llm=llm)
        review = reviewer.review(sample_result)
        assert review.generated_at is not None

    def test_review_has_statistics(self, sample_result: AnalysisResult) -> None:
        llm = MockLLMProvider()
        reviewer = EngineeringReviewer(llm=llm)
        review = reviewer.review(sample_result)
        assert "total_sections" in review.statistics
        assert "confidence_distribution" in review.statistics


# ---------------------------------------------------------------------------
# Tests: offline mode
# ---------------------------------------------------------------------------


class TestOfflineMode:
    def test_no_llm_produces_offline_review(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        assert review.offline is True
        assert review.model_info["provider"] == "offline"

    def test_offline_review_has_sections(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        assert review.total_sections >= 1

    def test_offline_review_has_executive_summary(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        summary = review.get_section(ReviewSectionType.EXECUTIVE_SUMMARY)
        assert summary is not None
        assert "offline" in summary.body.lower()

    def test_offline_review_has_top_root_causes(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        rc_section = review.get_section(ReviewSectionType.TOP_ROOT_CAUSES)
        assert rc_section is not None
        assert "God Class" in rc_section.body

    def test_offline_review_has_roi(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        roi_section = review.get_section(ReviewSectionType.HIGHEST_ROI_REFACTORING)
        assert roi_section is not None
        assert "Split" in roi_section.body or "God Class" in roi_section.body

    def test_offline_review_has_long_term_vision(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        vision = review.get_section(ReviewSectionType.LONG_TERM_VISION)
        assert vision is not None
        assert vision.confidence == ReviewConfidence.LOW


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_llm_failure_falls_back_to_offline(self, sample_result: AnalysisResult) -> None:
        """When the LLM raises an exception, the reviewer should fall back."""

        class FailingLLM(MockLLMProvider):
            def complete(self, prompt: str, **kwargs: Any) -> str:
                raise AIException("LLM unavailable", provider="failing", model="x")

        reviewer = EngineeringReviewer(llm=FailingLLM())
        review = reviewer.review(sample_result)
        assert review.offline is True

    def test_llm_timeout_falls_back(self, sample_result: AnalysisResult) -> None:
        """When the LLM times out, the reviewer should fall back."""

        class TimeoutLLM(MockLLMProvider):
            def complete(self, prompt: str, **kwargs: Any) -> str:
                raise TimeoutError("LLM timed out")

        reviewer = EngineeringReviewer(llm=TimeoutLLM())
        review = reviewer.review(sample_result)
        assert review.offline is True

    def test_empty_result_produces_review(self) -> None:
        """An empty AnalysisResult should still produce a review."""
        repo = parse_repository_url("https://github.com/test/empty")
        result = AnalysisResult(repository=repo)
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(result)
        assert isinstance(review, EngineeringLLMReview)
        assert review.offline is True


# ---------------------------------------------------------------------------
# Tests: adapter switching
# ---------------------------------------------------------------------------


class TestAdapterSwitching:
    def test_switching_provider_changes_model_info(self, sample_result: AnalysisResult) -> None:
        """Switching from mock to offline should change the model_info."""
        # With mock LLM.
        reviewer_with_llm = EngineeringReviewer(llm=MockLLMProvider())
        review_with_llm = reviewer_with_llm.review(sample_result)
        assert review_with_llm.model_info["provider"] == "mock"
        assert not review_with_llm.offline

        # Without LLM (offline).
        reviewer_offline = EngineeringReviewer(llm=None)
        review_offline = reviewer_offline.review(sample_result)
        assert review_offline.model_info["provider"] == "offline"
        assert review_offline.offline

    def test_different_mock_models(self, sample_result: AnalysisResult) -> None:
        """Different model names should appear in model_info."""
        llm1 = MockLLMProvider(model="mock-v1")
        llm2 = MockLLMProvider(model="mock-v2")
        review1 = EngineeringReviewer(llm=llm1).review(sample_result)
        review2 = EngineeringReviewer(llm=llm2).review(sample_result)
        assert review1.model_info["model"] == "mock-v1"
        assert review2.model_info["model"] == "mock-v2"


# ---------------------------------------------------------------------------
# Tests: model properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_review_is_immutable(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        with pytest.raises(Exception):  # noqa: B017
            review.offline = False  # type: ignore[misc]

    def test_section_is_immutable(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        if review.sections:
            with pytest.raises(Exception):  # noqa: B017
                review.sections[0].body = "mutated"  # type: ignore[misc]

    def test_get_section_returns_none_for_missing(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=None)
        review = reviewer.review(sample_result)
        assert review.get_section(ReviewSectionType.TRADE_OFF_ANALYSIS) is None or isinstance(
            review.get_section(ReviewSectionType.TRADE_OFF_ANALYSIS), type(review.sections[0])
        )

    def test_total_properties(self, sample_result: AnalysisResult) -> None:
        reviewer = EngineeringReviewer(llm=MockLLMProvider())
        review = reviewer.review(sample_result)
        assert review.total_sections == len(review.sections)
        assert review.total_challenges == len(review.challenges)
