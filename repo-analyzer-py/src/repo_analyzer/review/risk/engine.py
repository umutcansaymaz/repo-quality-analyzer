"""Risk engine.

Ranks every risk (from security, quality, architecture findings) into
Critical / High / Medium / Low buckets, each with probability, impact,
fix cost and recommended timeline.
"""

from __future__ import annotations

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.review_outputs import RiskItem, RiskLevel, RiskSummary


class RiskEngine:
    """Aggregate all findings into a :class:`RiskSummary`."""

    def summarize(self, result: AnalysisResult) -> RiskSummary:
        """Build the risk summary."""
        items: list[RiskItem] = []
        # Security findings → risks.
        for sf in result.security_findings:
            items.append(
                RiskItem(
                    title=sf.message,
                    level=self._sev_to_risk(sf.severity.value),
                    probability="high" if sf.severity.value in {"critical", "high"} else "medium",
                    impact="high" if sf.severity.value in {"critical", "high"} else "medium",
                    fix_cost="low" if sf.severity.value == "low" else "medium",
                    recommended_timeline="immediate"
                    if sf.severity.value == "critical"
                    else "1 week",
                    description=sf.message,
                    affected_files=[sf.location.file] if sf.location else [],
                )
            )
        # Complexity hotspots → risks.
        if result.complexity_report:
            for func in result.complexity_report.top_complex_functions[:10]:
                cc = func.get("complexity", 0)
                if cc > 10:
                    items.append(
                        RiskItem(
                            title=f"High complexity: {func.get('name', '')}",
                            level=RiskLevel.HIGH if cc > 15 else RiskLevel.MEDIUM,
                            probability="medium",
                            impact="medium",
                            fix_cost="high",
                            recommended_timeline="2-4 weeks",
                            description=f"Cyclomatic complexity {cc}.",
                            affected_files=[func.get("file", "")],
                        )
                    )
        # Circular imports → risks.
        if result.import_analysis:
            for cycle in result.import_analysis.circular_imports[:5]:
                items.append(
                    RiskItem(
                        title="Circular dependency",
                        level=RiskLevel.HIGH,
                        probability="high",
                        impact="high",
                        fix_cost="medium",
                        recommended_timeline="2 weeks",
                        description=f"Cycle: {' -> '.join(cycle)}",
                        affected_files=cycle,
                    )
                )
        # Sort into buckets.
        return RiskSummary(
            critical=[i for i in items if i.level == RiskLevel.CRITICAL],
            high=[i for i in items if i.level == RiskLevel.HIGH],
            medium=[i for i in items if i.level == RiskLevel.MEDIUM],
            low=[i for i in items if i.level == RiskLevel.LOW],
            overall_risk_level=self._overall_level(items),
        )

    @staticmethod
    def _sev_to_risk(severity: str) -> RiskLevel:
        return {
            "critical": RiskLevel.CRITICAL,
            "high": RiskLevel.HIGH,
            "medium": RiskLevel.MEDIUM,
            "low": RiskLevel.LOW,
            "info": RiskLevel.INFO,
        }.get(severity, RiskLevel.MEDIUM)

    @staticmethod
    def _overall_level(items: list[RiskItem]) -> RiskLevel:
        if any(i.level == RiskLevel.CRITICAL for i in items):
            return RiskLevel.CRITICAL
        if any(i.level == RiskLevel.HIGH for i in items):
            return RiskLevel.HIGH
        if any(i.level == RiskLevel.MEDIUM for i in items):
            return RiskLevel.MEDIUM
        if items:
            return RiskLevel.LOW
        return RiskLevel.INFO


__all__ = ["RiskEngine"]
