"""Extended health-score engine.

Computes 10 sub-scores (security, architecture, maintainability, performance,
documentation, testing, developer experience, scalability, code quality,
overall) and a letter grade (A+ to F).
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import ExtendedHealthScore


class HealthScoreReviewEngine:
    """Compute the extended :class:`ExtendedHealthScore`."""

    def compute(self, result: AnalysisResult) -> ExtendedHealthScore:
        """Compute all sub-scores from the :class:`AnalysisResult`."""
        security = self._security_score(result)
        architecture = self._architecture_score(result)
        maintainability = self._maintainability_score(result)
        performance = self._performance_score(result)
        documentation = self._documentation_score(result)
        testing = self._testing_score(result)
        dx = self._dx_score(result)
        scalability = self._scalability_score(result)
        quality = self._quality_score(result)
        overall = self._overall(
            security, architecture, maintainability, documentation, testing, quality
        )
        score = ExtendedHealthScore(
            overall=overall,
            security=security,
            architecture=architecture,
            maintainability=maintainability,
            performance=performance,
            documentation=documentation,
            testing=testing,
            developer_experience=dx,
            scalability=scalability,
            code_quality=quality,
        )
        score.compute_grade()
        return score

    def _security_score(self, result: AnalysisResult) -> float:
        if not result.security_findings:
            return 100.0
        penalties = {"critical": 30, "high": 15, "medium": 7, "low": 3, "info": 0}
        score = 100.0
        for f in result.security_findings:
            score -= penalties.get(f.severity.value, 0)
        return max(0.0, score)

    def _architecture_score(self, result: AnalysisResult) -> float:
        score = 100.0
        if result.import_analysis and result.import_analysis.circular_imports:
            score -= min(30, len(result.import_analysis.circular_imports) * 5)
        if result.architecture:
            if result.architecture.coupling > 0.7:
                score -= 15
            if result.architecture.cohesion < 0.3:
                score -= 15
        if result.dependency_analysis and result.dependency_analysis.unused_dependencies:
            score -= min(10, len(result.dependency_analysis.unused_dependencies) * 2)
        return max(0.0, score)

    def _maintainability_score(self, result: AnalysisResult) -> float:
        if not result.complexity_report:
            return 70.0
        avg_cc = result.complexity_report.average_complexity
        if avg_cc < 5:
            return 95.0
        if avg_cc < 10:
            return 80.0
        if avg_cc < 15:
            return 60.0
        return 40.0

    def _performance_score(self, result: AnalysisResult) -> float:
        # Heuristic: large files and high complexity hint at perf risk.
        if not result.metrics_report:
            return 70.0
        big_files = sum(1 for f in result.metrics_report.per_file if f.sloc > 500)
        if big_files == 0:
            return 90.0
        if big_files < 5:
            return 75.0
        return 55.0

    def _documentation_score(self, result: AnalysisResult) -> float:
        if not result.documentation_report:
            return 50.0
        score = result.documentation_report.readme_score * 60
        score += result.documentation_report.docstring_coverage * 40
        return round(min(100.0, score * 100), 2)

    def _testing_score(self, result: AnalysisResult) -> float:
        if not result.test_analysis:
            return 30.0
        if result.test_analysis.total_test_files == 0:
            return 20.0
        coverage = result.test_analysis.estimated_coverage
        if coverage is not None:
            return coverage
        # Heuristic from test file count.
        if result.test_analysis.total_test_files > 20:
            return 75.0
        if result.test_analysis.total_test_files > 5:
            return 60.0
        return 45.0

    def _dx_score(self, result: AnalysisResult) -> float:
        score = 50.0
        if result.documentation_report and result.documentation_report.has_installation:
            score += 15
        if result.documentation_report and result.documentation_report.has_contribution_guide:
            score += 15
        if result.test_analysis and result.test_analysis.total_test_files > 0:
            score += 10
        if result.test_analysis and result.test_analysis.has_fixtures:
            score += 10
        return min(100.0, score)

    def _scalability_score(self, result: AnalysisResult) -> float:
        if not result.architecture:
            return 60.0
        score = 100.0
        if result.architecture.coupling > 0.7:
            score -= 20
        if result.architecture.cohesion < 0.3:
            score -= 15
        if result.import_analysis and result.import_analysis.circular_imports:
            score -= 20
        return max(0.0, score)

    def _quality_score(self, result: AnalysisResult) -> float:
        if not result.complexity_report:
            return 70.0
        avg_cc = result.complexity_report.average_complexity
        score = 100.0 - (avg_cc * 5)
        if result.file_inventory and result.file_inventory.duplicate_files > 0:
            score -= min(20, result.file_inventory.duplicate_files * 2)
        return max(0.0, score)

    @staticmethod
    def _overall(*scores: float) -> float:
        weights = [0.20, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05, 0.05]
        return round(sum(s * w for s, w in zip(scores, weights, strict=False)), 2)


__all__ = ["HealthScoreReviewEngine"]
