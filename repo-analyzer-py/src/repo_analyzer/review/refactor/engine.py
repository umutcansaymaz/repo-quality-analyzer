"""Refactor engine.

Produces a :class:`RefactorPlan` organized into Quick Wins, High Impact,
Long-Term, Breaking Changes and Architecture Improvements. Also emits a list
of :class:`QuickWin` items with effort-in-minutes.
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import QuickWin, RefactorItem, RefactorPlan


class RefactorEngine:
    """Produce a :class:`RefactorPlan` and quick wins."""

    def plan(self, result: AnalysisResult) -> tuple[RefactorPlan, list[QuickWin]]:
        """Build the refactor plan and quick wins."""
        quick_wins: list[QuickWin] = []
        high_impact: list[RefactorItem] = []
        long_term: list[RefactorItem] = []
        breaking: list[RefactorItem] = []
        arch: list[RefactorItem] = []

        # Quick wins: unused imports, missing docs.
        if result.import_analysis:
            for unused in result.import_analysis.unused_imports[:20]:
                quick_wins.append(
                    QuickWin(
                        title=f"Remove unused import: {unused.get('name', '')}",
                        description=f"File {unused.get('file', '')} imports {unused.get('name', '')} but never uses it.",
                        effort_minutes=2,
                        impact="low",
                    )
                )
        if result.dependency_analysis:
            for dep in result.dependency_analysis.unused_dependencies[:10]:
                quick_wins.append(
                    QuickWin(
                        title=f"Remove unused dependency: {dep}",
                        description=f"'{dep}' is declared but not referenced in source.",
                        effort_minutes=5,
                        impact="low",
                    )
                )

        # High impact: complex functions, circular deps.
        if result.complexity_report:
            for func in result.complexity_report.top_complex_functions[:5]:
                cc = func.get("complexity", 0)
                if cc > 10:
                    high_impact.append(
                        RefactorItem(
                            title=f"Refactor complex function: {func.get('name', '')}",
                            description=f"Cyclomatic complexity {cc} in {func.get('file', '')}.",
                            impact="high",
                            effort="medium",
                            affected_files=[func.get("file", "")],
                        )
                    )
        if result.import_analysis:
            for cycle in result.import_analysis.circular_imports[:3]:
                high_impact.append(
                    RefactorItem(
                        title="Break circular dependency",
                        description=f"Cycle: {' -> '.join(cycle)}",
                        impact="high",
                        effort="medium",
                        affected_files=cycle,
                    )
                )

        # Long term: coupling / cohesion.
        if result.architecture:
            if result.architecture.coupling > 0.7:
                long_term.append(
                    RefactorItem(
                        title="Reduce module coupling",
                        description=f"Coupling is {result.architecture.coupling:.2f}.",
                        impact="medium",
                        effort="high",
                    )
                )
            if result.architecture.cohesion < 0.3:
                long_term.append(
                    RefactorItem(
                        title="Improve module cohesion",
                        description=f"Cohesion is {result.architecture.cohesion:.2f}.",
                        impact="medium",
                        effort="high",
                    )
                )

        # Breaking changes: module reorganization.
        if result.file_inventory and result.file_inventory.duplicate_files > 5:
            breaking.append(
                RefactorItem(
                    title="Extract shared library from duplicate code",
                    description="Multiple files share identical content; extract into a library.",
                    impact="high",
                    effort="high",
                    breaking=True,
                )
            )

        # Architecture improvements: introduce interfaces / DI.
        if result.symbols and not result.symbols.interfaces and len(result.symbols.classes) > 10:
            arch.append(
                RefactorItem(
                    title="Introduce interfaces for key collaborators",
                    description="No interfaces detected; add abstractions for testability.",
                    impact="medium",
                    effort="medium",
                )
            )
        if result.documentation_report and result.documentation_report.docstring_coverage < 0.3:
            arch.append(
                RefactorItem(
                    title="Establish documentation standard",
                    description="Docstring coverage is low; add a docstring linting CI step.",
                    impact="low",
                    effort="low",
                )
            )

        plan = RefactorPlan(
            quick_wins=high_impact[:3],  # high-impact items double as quick wins here
            high_impact=high_impact,
            long_term=long_term,
            breaking_changes=breaking,
            architecture_improvements=arch,
        )
        return plan, quick_wins


__all__ = ["RefactorEngine"]
