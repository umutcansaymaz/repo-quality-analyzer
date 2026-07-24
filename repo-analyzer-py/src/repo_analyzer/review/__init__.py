"""Review engines: the interpretation layer.

These engines run on top of the :class:`AnalysisResult` produced by the
analyzers (Prompt 3) and produce structured engineering reviews plus the
LLM-generated :class:`AIReview`.
"""

from __future__ import annotations

from repo_analyzer.review.ai.context_builder import ContextBuilder
from repo_analyzer.review.ai.engine import AICommentEngine
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

__all__ = [
    "AICommentEngine",
    "ContextBuilder",
    "PromptBuilder",
    "SecurityReviewEngine",
    "CodeQualityEngine",
    "ArchitectureReviewEngine",
    "FileReviewEngine",
    "DirectoryReviewEngine",
    "ProjectReviewEngine",
    "HealthScoreReviewEngine",
    "RiskEngine",
    "TechnicalDebtEngine",
    "RefactorEngine",
]
