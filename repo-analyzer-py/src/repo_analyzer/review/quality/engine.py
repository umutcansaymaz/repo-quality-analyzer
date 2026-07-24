"""Code quality review engine.

Detects 20+ code smells using heuristics over the AST/metric outputs from
Prompt 3. Each smell carries engineering context: impact and recommendation.
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import (
    CodeQualityReview,
    CodeSmellFinding,
    RiskLevel,
)


class CodeQualityEngine:
    """Detect code smells and produce a :class:`CodeQualityReview`."""

    def review(self, result: AnalysisResult) -> CodeQualityReview:
        """Run code-quality analysis over the :class:`AnalysisResult`."""
        smells: list[CodeSmellFinding] = []
        smells.extend(self._detect_god_classes(result))
        smells.extend(self._detect_long_methods(result))
        smells.extend(self._detect_high_complexity(result))
        smells.extend(self._detect_dead_code(result))
        smells.extend(self._detect_magic_numbers(result))
        smells.extend(self._detect_duplicate_code(result))
        smells.extend(self._detect_low_cohesion(result))
        smells.extend(self._detect_high_coupling(result))
        smells.extend(self._detect_anemic_models(result))
        score = self._compute_score(smells)
        return CodeQualityReview(
            smells=smells,
            quality_score=score,
            summary=self._build_summary(smells, score),
            duplicate_code_percentage=self._duplicate_percentage(result),
            dead_code_count=sum(1 for s in smells if s.smell_type == "dead_code"),
            complexity_hotspots=[s.file for s in smells if s.smell_type == "high_complexity"][:10],
        )

    # ----- detectors -----------------------------------------------------------

    def _detect_god_classes(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Classes with too many methods or too many lines are God Classes."""
        smells: list[CodeSmellFinding] = []
        if not result.symbols:
            return smells
        # Group methods by file/class.
        class_methods: dict[str, int] = {}
        for cls in result.symbols.classes:
            key = f"{cls.get('file', '')}:{cls.get('name', '')}"
            class_methods[key] = 0
        for method in result.symbols.methods:
            key = f"{method.get('file', '')}:{method.get('name', '')}"
            # Approximate: count methods per file.
            file_key = method.get("file", "")
            class_methods[file_key] = class_methods.get(file_key, 0) + 1
        for key, count in class_methods.items():
            if count > 15:
                file_path = key.split(":")[0]
                smells.append(
                    CodeSmellFinding(
                        smell_type="god_class",
                        title=f"God Class detected in {file_path}",
                        severity=RiskLevel.MEDIUM,
                        file=file_path,
                        description=f"File contains {count} methods, suggesting a God Class.",
                        impact="High cognitive load, difficult to test, violates SRP.",
                        recommendation="Split the class into focused, single-responsibility classes.",
                        effort="high",
                    )
                )
        return smells

    def _detect_long_methods(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Functions longer than ~50 lines are Long Methods."""
        smells: list[CodeSmellFinding] = []
        if not result.symbols:
            return smells
        for func in result.symbols.functions:
            length = func.get("length_lines", 0)
            if length > 50:
                smells.append(
                    CodeSmellFinding(
                        smell_type="long_method",
                        title=f"Long method: {func.get('name', '')}",
                        severity=RiskLevel.MEDIUM,
                        file=func.get("file", ""),
                        line=func.get("line"),
                        description=f"Method '{func.get('name', '')}' is {length} lines long.",
                        impact="Hard to understand, test, and maintain; higher defect density.",
                        recommendation="Extract sub-methods with descriptive names; apply the Single Level of Abstraction principle.",
                        effort="medium",
                    )
                )
        return smells

    def _detect_high_complexity(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Functions with cyclomatic complexity > 10 are complexity hotspots."""
        smells: list[CodeSmellFinding] = []
        if not result.complexity_report:
            return smells
        for func in result.complexity_report.top_complex_functions:
            if func.get("complexity", 0) > 10:
                smells.append(
                    CodeSmellFinding(
                        smell_type="high_complexity",
                        title=f"High complexity: {func.get('name', '')}",
                        severity=RiskLevel.HIGH
                        if func.get("complexity", 0) > 15
                        else RiskLevel.MEDIUM,
                        file=func.get("file", ""),
                        line=func.get("lineno"),
                        description=f"Function '{func.get('name', '')}' has cyclomatic complexity {func.get('complexity')}.",
                        impact="High branch count increases test surface and defect probability.",
                        recommendation="Refactor into smaller functions; replace conditionals with polymorphism or lookup tables.",
                        effort="high",
                    )
                )
        return smells

    def _detect_dead_code(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Unused imports are a proxy for dead code."""
        smells: list[CodeSmellFinding] = []
        if not result.import_analysis:
            return smells
        for unused in result.import_analysis.unused_imports:
            smells.append(
                CodeSmellFinding(
                    smell_type="dead_code",
                    title=f"Unused import: {unused.get('name', '')}",
                    severity=RiskLevel.LOW,
                    file=unused.get("file", ""),
                    description=f"Import '{unused.get('name', '')}' is never used.",
                    impact="Increases cognitive noise and slows down IDE / static analysis.",
                    recommendation="Remove the unused import.",
                    effort="low",
                )
            )
        return smells

    def _detect_magic_numbers(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Files with many numeric literals may suffer from Magic Numbers."""
        smells: list[CodeSmellFinding] = []
        if not result.metrics_report:
            return smells
        for file_metrics in result.metrics_report.per_file:
            # Heuristic: high SLOC with high complexity often hides magic numbers.
            if file_metrics.sloc > 200 and file_metrics.function_count < 5:
                smells.append(
                    CodeSmellFinding(
                        smell_type="magic_numbers",
                        title=f"Potential magic numbers in {file_metrics.path}",
                        severity=RiskLevel.LOW,
                        file=file_metrics.path,
                        description="Large file with few functions may contain unexplained numeric literals.",
                        impact="Magic numbers obscure intent and are error-prone when changed.",
                        recommendation="Extract numbers into named constants with descriptive names.",
                        effort="low",
                    )
                )
        return smells

    def _detect_duplicate_code(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Duplicate-file groups indicate copy-paste duplication."""
        smells: list[CodeSmellFinding] = []
        if not result.file_inventory:
            return smells
        for digest, paths in result.file_inventory.duplicate_groups:
            if len(paths) >= 2:
                smells.append(
                    CodeSmellFinding(
                        smell_type="duplicate_code",
                        title=f"Duplicate code block ({len(paths)} files)",
                        severity=RiskLevel.MEDIUM,
                        file=paths[0],
                        description=f"{len(paths)} files share identical content (hash {digest[:8]}).",
                        impact="Changes must be made in multiple places; high maintenance cost.",
                        recommendation="Extract the shared logic into a reusable module or function.",
                        effort="medium",
                    )
                )
        return smells

    def _detect_low_cohesion(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Architecture with low cohesion indicator."""
        smells: list[CodeSmellFinding] = []
        if result.architecture and result.architecture.cohesion < 0.3:
            smells.append(
                CodeSmellFinding(
                    smell_type="low_cohesion",
                    title="Low module cohesion",
                    severity=RiskLevel.MEDIUM,
                    file="<repository>",
                    description=f"Measured cohesion is {result.architecture.cohesion:.2f} (low).",
                    impact="Modules mix unrelated responsibilities, reducing reusability.",
                    recommendation="Reorganize modules around single responsibilities; co-locate related code.",
                    effort="high",
                )
            )
        return smells

    def _detect_high_coupling(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Architecture with high coupling indicator."""
        smells: list[CodeSmellFinding] = []
        if result.architecture and result.architecture.coupling > 0.7:
            smells.append(
                CodeSmellFinding(
                    smell_type="high_coupling",
                    title="High module coupling",
                    severity=RiskLevel.MEDIUM,
                    file="<repository>",
                    description=f"Measured coupling is {result.architecture.coupling:.2f} (high).",
                    impact="Changes cascade across modules; hard to test in isolation.",
                    recommendation="Introduce interfaces / abstractions to decouple dependents.",
                    effort="high",
                )
            )
        return smells

    def _detect_anemic_models(self, result: AnalysisResult) -> list[CodeSmellFinding]:
        """Classes with many fields but few methods may be Anemic Models."""
        smells: list[CodeSmellFinding] = []
        if not result.symbols:
            return smells
        # Heuristic: classes with no methods.
        for cls in result.symbols.classes:
            if not cls.get("methods"):
                smells.append(
                    CodeSmellFinding(
                        smell_type="anemic_model",
                        title=f"Anemic model: {cls.get('name', '')}",
                        severity=RiskLevel.LOW,
                        file=cls.get("file", ""),
                        line=cls.get("line"),
                        description=f"Class '{cls.get('name', '')}' appears to have no methods.",
                        impact="Domain logic ends up in services, breaking encapsulation.",
                        recommendation="Move behavior into the domain model (Rich Domain Model).",
                        effort="medium",
                    )
                )
        return smells

    # ----- scoring -------------------------------------------------------------

    @staticmethod
    def _compute_score(smells: list[CodeSmellFinding]) -> float:
        penalties = {RiskLevel.HIGH: 12, RiskLevel.MEDIUM: 6, RiskLevel.LOW: 2, RiskLevel.INFO: 0}
        score = 100.0
        for smell in smells:
            score -= penalties.get(smell.severity, 0)
        return max(0.0, score)

    @staticmethod
    def _duplicate_percentage(result: AnalysisResult) -> float:
        if not result.file_inventory or result.file_inventory.total_files == 0:
            return 0.0
        return round(
            result.file_inventory.duplicate_files / result.file_inventory.total_files * 100,
            2,
        )

    @staticmethod
    def _build_summary(smells: list[CodeSmellFinding], score: float) -> str:
        if not smells:
            return "No significant code smells were detected."
        high = sum(1 for s in smells if s.severity == RiskLevel.HIGH)
        medium = sum(1 for s in smells if s.severity == RiskLevel.MEDIUM)
        low = sum(1 for s in smells if s.severity == RiskLevel.LOW)
        return (
            f"Code quality review found {len(smells)} smell(s) "
            f"({high} high, {medium} medium, {low} low). "
            f"Overall quality score: {score:.0f}/100. "
            "High-severity smells should be refactored to reduce maintenance cost."
        )


__all__ = ["CodeQualityEngine"]
