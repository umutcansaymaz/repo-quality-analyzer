"""Project-level review engine."""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import ProjectReview


class ProjectReviewEngine:
    """Produce a :class:`ProjectReview` summarizing the whole repository."""

    def review(self, result: AnalysisResult) -> ProjectReview:
        """Run the project-level review."""
        return ProjectReview(
            code_readability=self._readability(result),
            maintainability=self._maintainability(result),
            onboarding_difficulty=self._onboarding(result),
            testability=self._testability(result),
            long_term_sustainability=self._sustainability(result),
            architectural_maturity=self._maturity(result),
            technical_debt_summary=self._debt_summary(result),
            development_velocity=self._velocity(result),
            summary=self._summary(result),
            strengths=self._strengths(result),
            weaknesses=self._weaknesses(result),
        )

    def _readability(self, result: AnalysisResult) -> str:
        if not result.metrics_report:
            return "unknown"
        avg_func = result.metrics_report.avg_function_length
        if avg_func < 20:
            return "good — functions are concise and readable."
        if avg_func < 40:
            return "fair — some functions are long but manageable."
        return "poor — many long functions reduce readability."

    def _maintainability(self, result: AnalysisResult) -> str:
        if not result.complexity_report:
            return "unknown"
        avg_cc = result.complexity_report.average_complexity
        if avg_cc < 5:
            return "high — low complexity makes changes safe."
        if avg_cc < 10:
            return "medium — moderate complexity; refactor hotspots."
        return "low — high complexity increases change risk."

    def _onboarding(self, result: AnalysisResult) -> str:
        if not result.documentation_report:
            return "unknown"
        score = result.documentation_report.readme_score
        if score > 0.7:
            return "easy — good README and contribution guide."
        if score > 0.4:
            return "moderate — partial documentation; new developers need guidance."
        return "hard — sparse documentation; onboarding will be slow."

    def _testability(self, result: AnalysisResult) -> str:
        if not result.test_analysis:
            return "unknown"
        if result.test_analysis.total_test_files == 0:
            return "low — no tests detected."
        coverage = result.test_analysis.estimated_coverage
        if coverage is not None and coverage > 70:
            return "high — good test coverage."
        if coverage is not None and coverage > 40:
            return "medium — partial coverage."
        return "medium — tests exist but coverage is low or unknown."

    def _sustainability(self, result: AnalysisResult) -> str:
        if not result.git_analysis:
            return "unknown"
        contributors = result.git_analysis.total_authors
        if contributors > 5:
            return "strong — multiple active contributors."
        if contributors > 1:
            return "moderate — small contributor base."
        return "at-risk — bus factor of one."

    def _maturity(self, result: AnalysisResult) -> str:
        if not result.repository_metadata:
            return "unknown"
        commits = result.repository_metadata.total_commits or 0
        if commits > 500:
            return "mature — long commit history."
        if commits > 50:
            return "evolving — active development."
        return "early-stage — limited history."

    def _debt_summary(self, result: AnalysisResult) -> str:
        areas: list[str] = []
        if result.import_analysis and result.import_analysis.circular_imports:
            areas.append("circular dependencies")
        if result.file_inventory and result.file_inventory.duplicate_files > 0:
            areas.append("duplicate code")
        if result.complexity_report and result.complexity_report.average_complexity > 10:
            areas.append("high complexity")
        if result.documentation_report and result.documentation_report.docstring_coverage < 0.3:
            areas.append("low documentation")
        if not areas:
            return "Low technical debt; the codebase is in good shape."
        return "Technical debt concentrated in: " + ", ".join(areas) + "."

    def _velocity(self, result: AnalysisResult) -> str:
        if not result.git_analysis:
            return "unknown"
        commits = result.git_analysis.total_commits
        if commits > 200:
            return "high — frequent commits indicate active development."
        if commits > 20:
            return "moderate — steady development pace."
        return "low — infrequent commits."

    def _summary(self, result: AnalysisResult) -> str:
        parts: list[str] = []
        if result.repository_metadata:
            parts.append(f"{result.repository_metadata.owner}/{result.repository_metadata.name}")
        if result.language_distribution and result.language_distribution.primary_language:
            parts.append(f"primarily {result.language_distribution.primary_language}")
        if result.metrics_report:
            parts.append(f"{result.metrics_report.total_sloc} SLOC")
        if result.test_analysis:
            parts.append(f"{result.test_analysis.total_test_files} test files")
        return "Repository: " + ", ".join(parts) + "."

    def _strengths(self, result: AnalysisResult) -> list[str]:
        strengths: list[str] = []
        if result.documentation_report and result.documentation_report.readme_score > 0.5:
            strengths.append("Good documentation.")
        if result.test_analysis and result.test_analysis.total_test_files > 0:
            strengths.append("Test suite present.")
        if result.complexity_report and result.complexity_report.average_complexity < 5:
            strengths.append("Low average complexity.")
        if result.import_analysis and not result.import_analysis.circular_imports:
            strengths.append("No circular imports.")
        return strengths

    def _weaknesses(self, result: AnalysisResult) -> list[str]:
        weaknesses: list[str] = []
        if result.complexity_report and result.complexity_report.average_complexity > 10:
            weaknesses.append("High complexity in core functions.")
        if result.documentation_report and result.documentation_report.docstring_coverage < 0.3:
            weaknesses.append("Low docstring coverage.")
        if result.file_inventory and result.file_inventory.duplicate_files > 0:
            weaknesses.append("Duplicate code detected.")
        if result.import_analysis and result.import_analysis.circular_imports:
            weaknesses.append("Circular dependencies present.")
        if result.dependency_analysis and result.dependency_analysis.unused_dependencies:
            weaknesses.append("Unused dependencies.")
        return weaknesses


__all__ = ["ProjectReviewEngine"]
