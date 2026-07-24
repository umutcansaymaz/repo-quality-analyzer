"""Technical-debt engine.

Categorizes debt into Architecture, Code, Documentation, Testing and Security
debt, each item carrying estimated hours, developer count and priority.
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import (
    RiskLevel,
    TechnicalDebt,
    TechnicalDebtItem,
)


class TechnicalDebtEngine:
    """Produce a :class:`TechnicalDebt` analysis."""

    def analyze(self, result: AnalysisResult) -> TechnicalDebt:
        """Build the technical-debt analysis."""
        architecture = self._architecture_debt(result)
        code = self._code_debt(result)
        documentation = self._documentation_debt(result)
        testing = self._testing_debt(result)
        security = self._security_debt(result)
        total = sum(
            i.estimated_hours for i in architecture + code + documentation + testing + security
        )
        return TechnicalDebt(
            architecture_debt=architecture,
            code_debt=code,
            documentation_debt=documentation,
            testing_debt=testing,
            security_debt=security,
            total_estimated_hours=round(total, 1),
            summary=self._summary(architecture, code, documentation, testing, security, total),
        )

    def _architecture_debt(self, result: AnalysisResult) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        if result.import_analysis:
            for cycle in result.import_analysis.circular_imports[:5]:
                items.append(
                    TechnicalDebtItem(
                        category="architecture",
                        title="Circular dependency",
                        description=f"Cycle: {' -> '.join(cycle)}",
                        estimated_hours=8.0,
                        estimated_developers=1,
                        priority=RiskLevel.HIGH,
                        affected_areas=cycle,
                    )
                )
        if result.architecture and result.architecture.coupling > 0.7:
            items.append(
                TechnicalDebtItem(
                    category="architecture",
                    title="High coupling",
                    description=f"Coupling score {result.architecture.coupling:.2f}.",
                    estimated_hours=16.0,
                    estimated_developers=2,
                    priority=RiskLevel.MEDIUM,
                )
            )
        return items

    def _code_debt(self, result: AnalysisResult) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        if result.complexity_report:
            for func in result.complexity_report.top_complex_functions[:10]:
                cc = func.get("complexity", 0)
                if cc > 10:
                    items.append(
                        TechnicalDebtItem(
                            category="code",
                            title=f"Complex function: {func.get('name', '')}",
                            description=f"Cyclomatic complexity {cc}.",
                            estimated_hours=4.0,
                            estimated_developers=1,
                            priority=RiskLevel.HIGH if cc > 15 else RiskLevel.MEDIUM,
                            affected_areas=[func.get("file", "")],
                        )
                    )
        if result.file_inventory:
            for _hash, paths in result.file_inventory.duplicate_groups[:5]:
                items.append(
                    TechnicalDebtItem(
                        category="code",
                        title="Duplicate code",
                        description=f"{len(paths)} files share identical content.",
                        estimated_hours=6.0,
                        estimated_developers=1,
                        priority=RiskLevel.MEDIUM,
                        affected_areas=paths,
                    )
                )
        return items

    def _documentation_debt(self, result: AnalysisResult) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        if result.documentation_report:
            if not result.documentation_report.has_installation:
                items.append(
                    TechnicalDebtItem(
                        category="documentation",
                        title="Missing installation guide",
                        description="README lacks installation instructions.",
                        estimated_hours=1.0,
                        estimated_developers=1,
                        priority=RiskLevel.LOW,
                    )
                )
            if result.documentation_report.docstring_coverage < 0.3:
                items.append(
                    TechnicalDebtItem(
                        category="documentation",
                        title="Low docstring coverage",
                        description=f"Coverage is {result.documentation_report.docstring_coverage:.0%}.",
                        estimated_hours=8.0,
                        estimated_developers=1,
                        priority=RiskLevel.MEDIUM,
                    )
                )
        return items

    def _testing_debt(self, result: AnalysisResult) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        if result.test_analysis:
            if result.test_analysis.total_test_files == 0:
                items.append(
                    TechnicalDebtItem(
                        category="testing",
                        title="No tests",
                        description="The repository has no test files.",
                        estimated_hours=24.0,
                        estimated_developers=2,
                        priority=RiskLevel.HIGH,
                    )
                )
            elif (
                result.test_analysis.estimated_coverage is not None
                and result.test_analysis.estimated_coverage < 50
            ):
                items.append(
                    TechnicalDebtItem(
                        category="testing",
                        title="Low test coverage",
                        description=f"Estimated coverage {result.test_analysis.estimated_coverage:.0f}%.",
                        estimated_hours=16.0,
                        estimated_developers=2,
                        priority=RiskLevel.MEDIUM,
                    )
                )
        return items

    def _security_debt(self, result: AnalysisResult) -> list[TechnicalDebtItem]:
        items: list[TechnicalDebtItem] = []
        critical = sum(1 for f in result.security_findings if f.severity.value == "critical")
        high = sum(1 for f in result.security_findings if f.severity.value == "high")
        if critical > 0:
            items.append(
                TechnicalDebtItem(
                    category="security",
                    title=f"{critical} critical security finding(s)",
                    description="Critical findings require immediate remediation.",
                    estimated_hours=critical * 4.0,
                    estimated_developers=1,
                    priority=RiskLevel.CRITICAL,
                )
            )
        if high > 0:
            items.append(
                TechnicalDebtItem(
                    category="security",
                    title=f"{high} high-severity security finding(s)",
                    description="High-severity findings should be fixed before the next release.",
                    estimated_hours=high * 2.0,
                    estimated_developers=1,
                    priority=RiskLevel.HIGH,
                )
            )
        return items

    @staticmethod
    def _summary(
        architecture: list[TechnicalDebtItem],
        code: list[TechnicalDebtItem],
        documentation: list[TechnicalDebtItem],
        testing: list[TechnicalDebtItem],
        security: list[TechnicalDebtItem],
        total: float,
    ) -> str:
        return (
            f"Technical debt totals ~{total:.0f} hours across "
            f"{len(architecture)} architecture, {len(code)} code, "
            f"{len(documentation)} documentation, {len(testing)} testing "
            f"and {len(security)} security item(s)."
        )


__all__ = ["TechnicalDebtEngine"]
