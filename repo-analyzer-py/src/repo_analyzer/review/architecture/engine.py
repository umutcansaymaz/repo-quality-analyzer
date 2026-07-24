"""Architecture review engine.

Evaluates the repository's architecture using the analysis outputs from
Prompt 3. Produces structured observations covering layer separation,
dependency direction, SOLID, DRY, KISS, YAGNI, DI, abstraction level and
technical-debt areas.
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import (
    ArchitectureObservation,
    ArchitectureReview,
    RiskLevel,
)


class ArchitectureReviewEngine:
    """Produce an :class:`ArchitectureReview` from analysis outputs."""

    def review(self, result: AnalysisResult) -> ArchitectureReview:
        """Run the architecture review."""
        observations: list[ArchitectureObservation] = []
        observations.extend(self._assess_layer_separation(result))
        observations.extend(self._assess_dependency_direction(result))
        observations.extend(self._assess_modularity(result))
        observations.extend(self._assess_solid(result))
        observations.extend(self._assess_dry(result))
        observations.extend(self._assess_kiss(result))
        observations.extend(self._assess_yagni(result))
        observations.extend(self._assess_di(result))
        observations.extend(self._assess_abstraction(result))
        observations.extend(self._assess_composition_vs_inheritance(result))
        score = self._compute_score(observations)
        return ArchitectureReview(
            observations=observations,
            architecture_score=score,
            summary=self._build_summary(observations, score),
            layer_separation=self._layer_label(result),
            dependency_direction=self._dependency_label(result),
            modularity=self._modularity_label(result),
            solid_assessment=self._solid_assessment(result),
            dry_assessment=self._dry_assessment(result),
            kiss_assessment=self._kiss_assessment(result),
            yagni_assessment=self._yagni_assessment(result),
            composition_vs_inheritance=self._composition_label(result),
            di_assessment=self._di_assessment(result),
            abstraction_level=self._abstraction_label(result),
            technical_debt_areas=self._debt_areas(result),
        )

    # ----- assessments ---------------------------------------------------------

    def _assess_layer_separation(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Check whether layers (cli / core / adapters) are separated."""
        obs: list[ArchitectureObservation] = []
        if not result.import_analysis:
            return obs
        # If cli imports core directly (bypassing ports), layering is weak.
        for src, dsts in result.import_analysis.import_graph.items():
            if "cli" in src:
                for dst in dsts:
                    if "adapters" in dst and "core" not in dst:
                        obs.append(
                            ArchitectureObservation(
                                topic="layer_separation",
                                assessment=f"CLI layer ({src}) directly imports adapter ({dst}).",
                                impact="The driving layer depends on a concrete adapter rather than a port, "
                                "tightening coupling and reducing testability.",
                                recommendation="Depend on the abstract port (interface) and inject the adapter.",
                                severity=RiskLevel.MEDIUM,
                            )
                        )
        return obs

    def _assess_dependency_direction(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Check whether dependencies point inward (Hexagonal rule)."""
        obs: list[ArchitectureObservation] = []
        if not result.import_analysis:
            return obs
        for cycle in result.import_analysis.circular_imports:
            obs.append(
                ArchitectureObservation(
                    topic="dependency_direction",
                    assessment=f"Circular import detected: {' -> '.join(cycle)}",
                    impact="Circular dependencies prevent clean layering and make modules impossible to "
                    "test or reuse in isolation.",
                    recommendation="Break the cycle by extracting shared logic into a lower-level module.",
                    severity=RiskLevel.HIGH,
                )
            )
        return obs

    def _assess_modularity(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess modularity via coupling / cohesion."""
        obs: list[ArchitectureObservation] = []
        if result.architecture:
            if result.architecture.coupling > 0.7:
                obs.append(
                    ArchitectureObservation(
                        topic="modularity",
                        assessment=f"High coupling ({result.architecture.coupling:.2f}).",
                        impact="Tightly coupled modules change together, amplifying the blast radius of edits.",
                        recommendation="Introduce interfaces and events to decouple the most-connected modules.",
                        severity=RiskLevel.MEDIUM,
                    )
                )
            if result.architecture.cohesion < 0.3:
                obs.append(
                    ArchitectureObservation(
                        topic="modularity",
                        assessment=f"Low cohesion ({result.architecture.cohesion:.2f}).",
                        impact="Low-cohesion modules mix responsibilities, reducing reusability.",
                        recommendation="Split modules along responsibility boundaries.",
                        severity=RiskLevel.MEDIUM,
                    )
                )
        return obs

    def _assess_solid(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess SOLID principles heuristically."""
        obs: list[ArchitectureObservation] = []
        if result.symbols:
            for cls in result.symbols.classes:
                if len(cls.get("methods", [])) > 20:
                    obs.append(
                        ArchitectureObservation(
                            topic="solid_srp",
                            assessment=f"Class '{cls.get('name', '')}' has >20 methods.",
                            impact="Violates the Single Responsibility Principle; the class has multiple reasons to change.",
                            recommendation="Split into smaller, focused classes.",
                            severity=RiskLevel.MEDIUM,
                        )
                    )
        return obs

    def _assess_dry(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess DRY via duplicate-code groups."""
        obs: list[ArchitectureObservation] = []
        if result.file_inventory:
            for _hash, paths in result.file_inventory.duplicate_groups:
                if len(paths) >= 3:
                    obs.append(
                        ArchitectureObservation(
                            topic="dry",
                            assessment=f"{len(paths)} files share identical content.",
                            impact="Violates DRY; changes must be replicated, risking drift.",
                            recommendation="Extract the shared code into a reusable utility module.",
                            severity=RiskLevel.MEDIUM,
                        )
                    )
        return obs

    def _assess_kiss(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess KISS via complexity."""
        obs: list[ArchitectureObservation] = []
        if result.complexity_report:
            high = [
                f
                for f in result.complexity_report.top_complex_functions
                if f.get("complexity", 0) > 15
            ]
            if high:
                obs.append(
                    ArchitectureObservation(
                        topic="kiss",
                        assessment=f"{len(high)} function(s) exceed complexity 15.",
                        impact="Over-engineered control flow violates KISS and raises defect probability.",
                        recommendation="Simplify by extracting helper functions and removing dead branches.",
                        severity=RiskLevel.MEDIUM,
                    )
                )
        return obs

    def _assess_yagni(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess YAGNI via unused dependencies / dead code."""
        obs: list[ArchitectureObservation] = []
        if result.dependency_analysis and result.dependency_analysis.unused_dependencies:
            obs.append(
                ArchitectureObservation(
                    topic="yagni",
                    assessment=f"{len(result.dependency_analysis.unused_dependencies)} unused dependency(ies).",
                    impact="Unused dependencies violate YAGNI and increase supply-chain attack surface.",
                    recommendation="Remove unused dependencies from manifests.",
                    severity=RiskLevel.LOW,
                )
            )
        return obs

    def _assess_di(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess dependency-injection usage (heuristic)."""
        obs: list[ArchitectureObservation] = []
        if result.symbols:
            # Look for classes whose __init__ takes no arguments (no injection).
            no_di = [c for c in result.symbols.classes if not c.get("methods")]
            if len(no_di) > 5:
                obs.append(
                    ArchitectureObservation(
                        topic="di",
                        assessment=f"{len(no_di)} classes show no constructor injection.",
                        impact="Without DI, classes construct their own dependencies, making unit testing hard.",
                        recommendation="Accept dependencies via constructors; use a DI container.",
                        severity=RiskLevel.LOW,
                    )
                )
        return obs

    def _assess_abstraction(self, result: AnalysisResult) -> list[ArchitectureObservation]:
        """Assess abstraction level via interface count."""
        obs: list[ArchitectureObservation] = []
        if result.symbols:
            interface_count = len(result.symbols.interfaces)
            class_count = len(result.symbols.classes)
            if class_count > 10 and interface_count == 0:
                obs.append(
                    ArchitectureObservation(
                        topic="abstraction",
                        assessment="Many classes but no interfaces detected.",
                        impact="Lack of abstraction prevents polymorphism and testing with fakes.",
                        recommendation="Introduce interfaces for the most-used collaborator classes.",
                        severity=RiskLevel.LOW,
                    )
                )
        return obs

    def _assess_composition_vs_inheritance(
        self, result: AnalysisResult
    ) -> list[ArchitectureObservation]:
        """Assess inheritance depth."""
        obs: list[ArchitectureObservation] = []
        if result.symbols:
            if len(result.symbols.inheritances) > len(result.symbols.classes) * 0.5:
                obs.append(
                    ArchitectureObservation(
                        topic="composition_vs_inheritance",
                        assessment="High inheritance-to-class ratio detected.",
                        impact="Deep inheritance hierarchies are fragile and hard to extend.",
                        recommendation="Prefer composition over inheritance; extract strategies into separate objects.",
                        severity=RiskLevel.LOW,
                    )
                )
        return obs

    # ----- labels --------------------------------------------------------------

    def _layer_label(self, result: AnalysisResult) -> str:
        if not result.import_analysis:
            return "unknown"
        cli_imports = sum(1 for s in result.import_analysis.import_graph if "cli" in s)
        if cli_imports == 0:
            return "good"
        return "weak"

    def _dependency_label(self, result: AnalysisResult) -> str:
        if not result.import_analysis:
            return "unknown"
        if result.import_analysis.circular_imports:
            return "circular"
        return "inward"

    def _modularity_label(self, result: AnalysisResult) -> str:
        if not result.architecture:
            return "unknown"
        if result.architecture.coupling > 0.7:
            return "tightly-coupled"
        if result.architecture.cohesion < 0.3:
            return "low-cohesion"
        return "modular"

    def _solid_assessment(self, result: AnalysisResult) -> dict[str, str]:
        srp = "unknown"
        if result.symbols:
            big_classes = [c for c in result.symbols.classes if len(c.get("methods", [])) > 20]
            srp = "violated" if big_classes else "ok"
        return {
            "SRP": srp,
            "OCP": "unknown",
            "LSP": "unknown",
            "ISP": "unknown",
            "DIP": "weak"
            if result.import_analysis and result.import_analysis.import_graph
            else "unknown",
        }

    def _dry_assessment(self, result: AnalysisResult) -> str:
        if not result.file_inventory:
            return "unknown"
        return "violated" if result.file_inventory.duplicate_files > 0 else "ok"

    def _kiss_assessment(self, result: AnalysisResult) -> str:
        if not result.complexity_report:
            return "unknown"
        high = [
            f for f in result.complexity_report.top_complex_functions if f.get("complexity", 0) > 15
        ]
        return "violated" if high else "ok"

    def _yagni_assessment(self, result: AnalysisResult) -> str:
        if not result.dependency_analysis:
            return "unknown"
        return "violated" if result.dependency_analysis.unused_dependencies else "ok"

    def _composition_label(self, result: AnalysisResult) -> str:
        if not result.symbols:
            return "unknown"
        ratio = len(result.symbols.inheritances) / max(len(result.symbols.classes), 1)
        return "inheritance-heavy" if ratio > 0.5 else "balanced"

    def _di_assessment(self, result: AnalysisResult) -> str:
        if not result.symbols:
            return "unknown"
        return "partial" if len(result.symbols.classes) > 5 else "unknown"

    def _abstraction_label(self, result: AnalysisResult) -> str:
        if not result.symbols:
            return "unknown"
        if result.symbols.classes and not result.symbols.interfaces:
            return "low"
        return "adequate"

    def _debt_areas(self, result: AnalysisResult) -> list[str]:
        areas: list[str] = []
        if result.import_analysis and result.import_analysis.circular_imports:
            areas.append("circular-dependencies")
        if result.file_inventory and result.file_inventory.duplicate_files > 0:
            areas.append("duplicate-code")
        if result.complexity_report and result.complexity_report.average_complexity > 10:
            areas.append("high-complexity")
        if result.dependency_analysis and result.dependency_analysis.unused_dependencies:
            areas.append("unused-dependencies")
        if result.documentation_report and result.documentation_report.docstring_coverage < 0.3:
            areas.append("low-documentation")
        return areas

    # ----- scoring / summary ---------------------------------------------------

    @staticmethod
    def _compute_score(observations: list[ArchitectureObservation]) -> float:
        penalties = {RiskLevel.HIGH: 15, RiskLevel.MEDIUM: 7, RiskLevel.LOW: 3, RiskLevel.INFO: 0}
        score = 100.0
        for obs in observations:
            score -= penalties.get(obs.severity, 0)
        return max(0.0, score)

    @staticmethod
    def _build_summary(observations: list[ArchitectureObservation], score: float) -> str:
        if not observations:
            return "No architectural issues were detected; the structure follows clean separation."
        high = sum(1 for o in observations if o.severity == RiskLevel.HIGH)
        med = sum(1 for o in observations if o.severity == RiskLevel.MEDIUM)
        return (
            f"Architecture review found {len(observations)} observation(s) "
            f"({high} high, {med} medium). Score: {score:.0f}/100. "
            "Addressing circular dependencies and layer violations will yield the largest improvement."
        )


__all__ = ["ArchitectureReviewEngine"]
