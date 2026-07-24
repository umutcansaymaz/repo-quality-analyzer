"""Evidence Builder service.

Transforms an :class:`AnalysisResult` into an :class:`EvidenceCollection`
by extracting findings from every analyzer and review-engine output field.

Design:
    - **Read-only**: The builder never modifies the ``AnalysisResult``.
    - **No I/O**: No repository re-scanning; all data comes from the
      in-memory result.
    - **Plugin-compatible**: No hardcoded analyzer names — the builder
      reads whatever data is present in the result fields.
    - **Normalizing**: Duplicate evidence (same file + symbol + type +
      category) is merged, with a ``DUPLICATE`` relationship recorded.

Usage::

    from repo_analyzer.core.evidence import EvidenceBuilder

    collection = EvidenceBuilder.build(result)
    for ev in collection.evidence:
        print(ev.analyzer, ev.finding_type, ev.message)
"""

from __future__ import annotations

from uuid import UUID

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.report import Severity
from repo_analyzer.core.evidence.models import (
    Evidence,
    EvidenceCollection,
    EvidenceReference,
    EvidenceRelationship,
    EvidenceType,
    ReferenceKind,
    RelationshipType,
)

#: Severity ranking for deduplication (higher = more severe).
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.CRITICAL: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.INFO: 1,
}


def _risk_level_to_severity(risk_level: str) -> Severity:
    """Map a ``RiskLevel`` string to a :class:`Severity`."""
    mapping = {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }
    return mapping.get(risk_level.lower(), Severity.INFO)


class EvidenceBuilder:
    """Build an :class:`EvidenceCollection` from an :class:`AnalysisResult`.

    The builder is stateless and thread-safe. The :meth:`build` method is
    the single entry point.
    """

    @classmethod
    def build(cls, result: AnalysisResult) -> EvidenceCollection:
        """Transform ``result`` into an :class:`EvidenceCollection`.

        Args:
            result: A populated :class:`AnalysisResult` (may be partially
                populated — missing fields produce no evidence).

        Returns:
            An :class:`EvidenceCollection` with normalized evidence and
            relationships.
        """
        builder = cls()
        evidence: list[Evidence] = []
        evidence.extend(builder._extract_security_findings(result))
        evidence.extend(builder._extract_security_review(result))
        evidence.extend(builder._extract_code_quality(result))
        evidence.extend(builder._extract_architecture_smells(result))
        evidence.extend(builder._extract_architecture_observations(result))
        evidence.extend(builder._extract_complexity(result))
        evidence.extend(builder._extract_imports(result))
        evidence.extend(builder._extract_dependencies(result))
        evidence.extend(builder._extract_git(result))
        evidence.extend(builder._extract_documentation(result))
        evidence.extend(builder._extract_tests(result))
        evidence.extend(builder._extract_metrics(result))
        evidence.extend(builder._extract_symbols(result))
        evidence.extend(builder._extract_file_system(result))
        evidence.extend(builder._extract_risks(result))
        evidence.extend(builder._extract_technical_debt(result))
        evidence.extend(builder._extract_refactors(result))
        evidence.extend(builder._extract_repository_metadata(result))
        # Normalize and build relationships.
        evidence, relationships = builder._normalize(evidence)
        collection = builder._build_collection(evidence, relationships)
        return collection

    # ------------------------------------------------------------------
    # Extractors — one per data source in AnalysisResult
    # ------------------------------------------------------------------

    def _extract_security_findings(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.security_findings``."""
        evidence: list[Evidence] = []
        for sf in result.security_findings:
            refs: list[EvidenceReference] = []
            if sf.location:
                refs.append(
                    EvidenceReference(
                        kind=ReferenceKind.FILE,
                        value=sf.location.file,
                        line=sf.location.line,
                    )
                )
            if sf.cwe:
                refs.append(EvidenceReference(kind=ReferenceKind.CWE, value=sf.cwe))
            if sf.cvss is not None:
                refs.append(EvidenceReference(kind=ReferenceKind.CVSS, value=str(sf.cvss)))
            evidence.append(
                Evidence(
                    analyzer="security-engine",
                    finding_type=EvidenceType.SECURITY,
                    severity=sf.severity,
                    confidence=self._confidence_from_enum(sf.confidence.value),
                    category=sf.category.value,
                    file_path=sf.location.file if sf.location else None,
                    line=sf.location.line if sf.location else None,
                    message=sf.message,
                    explanation=sf.description or sf.fix_suggestion,
                    tags=[sf.rule_id],
                    references=refs,
                    source_id=sf.id,
                    metrics={"cvss": sf.cvss} if sf.cvss else {},
                )
            )
        return evidence

    def _extract_security_review(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``ai_review.security_review.findings``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.security_review:
            return evidence
        for f in review.security_review.findings:
            evidence.append(
                Evidence(
                    analyzer=f.tool or "security-review",
                    finding_type=EvidenceType.SECURITY,
                    severity=_risk_level_to_severity(f.severity.value),
                    confidence=f.confidence,
                    category=f.category,
                    file_path=f.file,
                    line=f.line,
                    message=f.title,
                    explanation=f"{f.why_risky} {f.real_world_risk} Solution: {f.solution}",
                    tags=[f.category, f.tool],
                    references=[
                        EvidenceReference(kind=ReferenceKind.FILE, value=f.file, line=f.line),
                        *[
                            EvidenceReference(kind=ReferenceKind.RULE, value=ref)
                            for ref in f.references
                        ],
                    ],
                    source_id=f.id,
                    metrics={"cvss_estimate": f.cvss_estimate},
                )
            )
        return evidence

    def _extract_code_quality(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``ai_review.code_quality_review.smells``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.code_quality_review:
            return evidence
        for smell in review.code_quality_review.smells:
            evidence.append(
                Evidence(
                    analyzer="code-quality-engine",
                    finding_type=EvidenceType.CODE_QUALITY,
                    severity=_risk_level_to_severity(smell.severity.value),
                    confidence=0.8,
                    category=smell.smell_type,
                    file_path=smell.file,
                    line=smell.line,
                    message=smell.title,
                    explanation=(
                        f"{smell.description} Impact: {smell.impact}. "
                        f"Recommendation: {smell.recommendation}"
                    ),
                    tags=[smell.smell_type, smell.effort],
                    references=[
                        EvidenceReference(
                            kind=ReferenceKind.FILE, value=smell.file, line=smell.line
                        )
                    ]
                    if smell.file
                    else [],
                    source_id=smell.id,
                )
            )
        return evidence

    def _extract_architecture_smells(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.architecture.smells``."""
        evidence: list[Evidence] = []
        if not result.architecture:
            return evidence
        for smell in result.architecture.smells:
            evidence.append(
                Evidence(
                    analyzer="graph-engine",
                    finding_type=EvidenceType.ARCHITECTURE,
                    severity=smell.severity,
                    confidence=0.9,
                    category=smell.type.value,
                    file_path=smell.location.file if smell.location else None,
                    line=smell.location.line if smell.location else None,
                    message=smell.message,
                    explanation=None,
                    tags=[smell.type.value],
                    references=[
                        EvidenceReference(kind=ReferenceKind.MODULE, value=m)
                        for m in smell.affected_modules
                    ],
                    source_id=smell.id,
                )
            )
        # Also extract cycles.
        for cycle in result.architecture.cycles:
            evidence.append(
                Evidence(
                    analyzer="graph-engine",
                    finding_type=EvidenceType.ARCHITECTURE,
                    severity=Severity.HIGH,
                    confidence=1.0,
                    category="cyclic_dependency",
                    message=f"Circular dependency: {cycle}",
                    tags=["cyclic_dependency"],
                    references=[
                        EvidenceReference(kind=ReferenceKind.MODULE, value=node)
                        for node in cycle.nodes
                    ],
                )
            )
        return evidence

    def _extract_architecture_observations(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``ai_review.architecture_review.observations``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.architecture_review:
            return evidence
        for obs in review.architecture_review.observations:
            evidence.append(
                Evidence(
                    analyzer="architecture-review-engine",
                    finding_type=EvidenceType.ARCHITECTURE,
                    severity=_risk_level_to_severity(obs.severity.value),
                    confidence=0.7,
                    category=obs.topic,
                    message=obs.assessment,
                    explanation=f"Impact: {obs.impact}. Recommendation: {obs.recommendation}",
                    tags=[obs.topic],
                    source_id=obs.id,
                )
            )
        return evidence

    def _extract_complexity(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.complexity_report``."""
        evidence: list[Evidence] = []
        if not result.complexity_report:
            return evidence
        for func in result.complexity_report.top_complex_functions:
            cc = func.get("complexity", 0)
            severity = Severity.HIGH if cc > 15 else Severity.MEDIUM if cc > 10 else Severity.LOW
            evidence.append(
                Evidence(
                    analyzer="complexity-analyzer",
                    finding_type=EvidenceType.COMPLEXITY,
                    severity=severity,
                    confidence=1.0,
                    category="cyclomatic_complexity",
                    file_path=func.get("file"),
                    line=func.get("lineno"),
                    function_name=func.get("name"),
                    symbol=func.get("name"),
                    message=f"High complexity: {func.get('name', '?')} (CC={cc})",
                    explanation=f"Cyclomatic complexity is {cc}, rank {func.get('rank', '?')}.",
                    tags=["complexity", func.get("rank", "")],
                    references=[
                        EvidenceReference(
                            kind=ReferenceKind.FUNCTION,
                            value=str(func.get("name", "")),
                        )
                    ],
                    metrics={"complexity": cc, "rank": func.get("rank")},
                )
            )
        return evidence

    def _extract_imports(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.import_analysis``."""
        evidence: list[Evidence] = []
        if not result.import_analysis:
            return evidence
        for unused in result.import_analysis.unused_imports:
            evidence.append(
                Evidence(
                    analyzer="import-analyzer",
                    finding_type=EvidenceType.IMPORT,
                    severity=Severity.LOW,
                    confidence=0.9,
                    category="unused_import",
                    file_path=unused.get("file"),
                    message=f"Unused import: {unused.get('name', '?')}",
                    explanation=f"Module '{unused.get('module', '?')}' is imported but never used.",
                    tags=["unused_import", "dead_code"],
                    source_id=None,
                )
            )
        for dup in result.import_analysis.duplicate_imports:
            evidence.append(
                Evidence(
                    analyzer="import-analyzer",
                    finding_type=EvidenceType.IMPORT,
                    severity=Severity.LOW,
                    confidence=0.9,
                    category="duplicate_import",
                    file_path=dup.get("file"),
                    message=f"Duplicate import: {dup.get('module', '?')}",
                    tags=["duplicate_import"],
                )
            )
        for cycle in result.import_analysis.circular_imports:
            evidence.append(
                Evidence(
                    analyzer="import-analyzer",
                    finding_type=EvidenceType.IMPORT,
                    severity=Severity.HIGH,
                    confidence=1.0,
                    category="circular_import",
                    message=f"Circular import: {' -> '.join(cycle)}",
                    tags=["circular_import"],
                    references=[
                        EvidenceReference(kind=ReferenceKind.MODULE, value=m) for m in cycle
                    ],
                )
            )
        return evidence

    def _extract_dependencies(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.dependency_analysis``."""
        evidence: list[Evidence] = []
        if not result.dependency_analysis:
            return evidence
        for dep in result.dependency_analysis.unused_dependencies:
            evidence.append(
                Evidence(
                    analyzer="dependency-analyzer",
                    finding_type=EvidenceType.DEPENDENCY,
                    severity=Severity.LOW,
                    confidence=0.8,
                    category="unused_dependency",
                    message=f"Unused dependency: {dep}",
                    explanation=f"'{dep}' is declared but not referenced in source.",
                    tags=["unused_dependency", "yagni"],
                )
            )
        for dep in result.dependency_analysis.duplicate_dependencies:
            evidence.append(
                Evidence(
                    analyzer="dependency-analyzer",
                    finding_type=EvidenceType.DEPENDENCY,
                    severity=Severity.LOW,
                    confidence=0.8,
                    category="duplicate_dependency",
                    message=f"Duplicate dependency: {dep}",
                    tags=["duplicate_dependency"],
                )
            )
        return evidence

    def _extract_git(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.git_analysis``."""
        evidence: list[Evidence] = []
        if not result.git_analysis:
            return evidence
        for file_path, churn in result.git_analysis.most_changed_files[:10]:
            if churn > 10:
                evidence.append(
                    Evidence(
                        analyzer="git-history-analyzer",
                        finding_type=EvidenceType.GIT,
                        severity=Severity.MEDIUM if churn > 20 else Severity.LOW,
                        confidence=1.0,
                        category="high_churn",
                        file_path=file_path,
                        message=f"High churn: {file_path} ({churn} changes)",
                        explanation=f"File changed {churn} times — likely a maintenance hotspot.",
                        tags=["churn", "hotspot"],
                        metrics={"churn_count": churn},
                    )
                )
        return evidence

    def _extract_documentation(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.documentation_report``."""
        evidence: list[Evidence] = []
        if not result.documentation_report:
            return evidence
        doc = result.documentation_report
        if not doc.has_installation:
            evidence.append(
                Evidence(
                    analyzer="documentation-analyzer",
                    finding_type=EvidenceType.DOCUMENTATION,
                    severity=Severity.LOW,
                    confidence=1.0,
                    category="missing_installation",
                    message="Missing installation guide",
                    tags=["documentation"],
                )
            )
        if doc.docstring_coverage < 0.3:
            evidence.append(
                Evidence(
                    analyzer="documentation-analyzer",
                    finding_type=EvidenceType.DOCUMENTATION,
                    severity=Severity.MEDIUM,
                    confidence=1.0,
                    category="low_docstring_coverage",
                    message=f"Low docstring coverage: {doc.docstring_coverage:.0%}",
                    tags=["documentation", "docstring"],
                    metrics={"docstring_coverage": doc.docstring_coverage},
                )
            )
        return evidence

    def _extract_tests(self, result: AnalysisResult) -> list[Evidence]:
        """Extract evidence from ``result.test_analysis``."""
        evidence: list[Evidence] = []
        if not result.test_analysis:
            return evidence
        tests = result.test_analysis
        if tests.total_test_files == 0:
            evidence.append(
                Evidence(
                    analyzer="test-coverage-analyzer",
                    finding_type=EvidenceType.TEST,
                    severity=Severity.HIGH,
                    confidence=1.0,
                    category="no_tests",
                    message="No test files detected",
                    explanation="The repository has no test files — testing debt is high.",
                    tags=["testing", "no_tests"],
                )
            )
        elif tests.estimated_coverage is not None and tests.estimated_coverage < 50:
            evidence.append(
                Evidence(
                    analyzer="test-coverage-analyzer",
                    finding_type=EvidenceType.TEST,
                    severity=Severity.MEDIUM,
                    confidence=0.9,
                    category="low_coverage",
                    message=f"Low test coverage: {tests.estimated_coverage:.0f}%",
                    tags=["testing", "low_coverage"],
                    metrics={"estimated_coverage": tests.estimated_coverage},
                )
            )
        return evidence

    def _extract_metrics(self, result: AnalysisResult) -> list[Evidence]:
        """Extract per-file metric evidence from ``result.metrics_report``."""
        evidence: list[Evidence] = []
        if not result.metrics_report:
            return evidence
        for fm in result.metrics_report.per_file:
            if fm.sloc > 500:
                evidence.append(
                    Evidence(
                        analyzer="metrics-engine",
                        finding_type=EvidenceType.METRIC,
                        severity=Severity.MEDIUM if fm.sloc > 1000 else Severity.LOW,
                        confidence=1.0,
                        category="large_file",
                        file_path=fm.path,
                        message=f"Large file: {fm.path} ({fm.sloc} SLOC)",
                        tags=["large_file"],
                        metrics={
                            "sloc": fm.sloc,
                            "loc": fm.loc,
                            "function_count": fm.function_count,
                            "class_count": fm.class_count,
                        },
                    )
                )
        return evidence

    def _extract_symbols(self, result: AnalysisResult) -> list[Evidence]:
        """Extract AST symbol evidence from ``result.symbols``."""
        evidence: list[Evidence] = []
        if not result.symbols:
            return evidence
        for func in result.symbols.functions:
            evidence.append(
                Evidence(
                    analyzer="ast-analyzer",
                    finding_type=EvidenceType.SYMBOL,
                    severity=Severity.INFO,
                    confidence=1.0,
                    category="function",
                    file_path=func.get("file"),
                    line=func.get("line"),
                    function_name=func.get("name"),
                    symbol=func.get("name"),
                    message=f"Function: {func.get('name', '?')}",
                    tags=["function"],
                    metrics={"length_lines": func.get("length_lines", 0)},
                )
            )
        for cls in result.symbols.classes:
            evidence.append(
                Evidence(
                    analyzer="ast-analyzer",
                    finding_type=EvidenceType.SYMBOL,
                    severity=Severity.INFO,
                    confidence=1.0,
                    category="class",
                    file_path=cls.get("file"),
                    line=cls.get("line"),
                    class_name=cls.get("name"),
                    symbol=cls.get("name"),
                    message=f"Class: {cls.get('name', '?')}",
                    tags=["class"],
                )
            )
        return evidence

    def _extract_file_system(self, result: AnalysisResult) -> list[Evidence]:
        """Extract file-system evidence (duplicates, large files)."""
        evidence: list[Evidence] = []
        if not result.file_inventory:
            return evidence
        for _hash, paths in result.file_inventory.duplicate_groups:
            if len(paths) >= 2:
                evidence.append(
                    Evidence(
                        analyzer="filesystem-analyzer",
                        finding_type=EvidenceType.FILE_SYSTEM,
                        severity=Severity.MEDIUM,
                        confidence=1.0,
                        category="duplicate_file",
                        file_path=paths[0],
                        message=f"Duplicate code: {len(paths)} files identical",
                        tags=["duplicate_code", "dry"],
                        references=[
                            EvidenceReference(kind=ReferenceKind.FILE, value=p) for p in paths
                        ],
                    )
                )
        return evidence

    def _extract_risks(self, result: AnalysisResult) -> list[Evidence]:
        """Extract risk evidence from ``ai_review.risk_summary``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.risk_summary:
            return evidence
        rs = review.risk_summary
        for risk in [*rs.critical, *rs.high, *rs.medium, *rs.low]:
            evidence.append(
                Evidence(
                    analyzer="risk-engine",
                    finding_type=EvidenceType.RISK,
                    severity=_risk_level_to_severity(risk.level.value),
                    confidence=0.8,
                    category="risk",
                    message=risk.title,
                    explanation=risk.description,
                    tags=["risk", risk.level.value, risk.probability, risk.impact],
                    source_id=risk.id,
                    metrics={
                        "probability": risk.probability,
                        "impact": risk.impact,
                        "fix_cost": risk.fix_cost,
                    },
                )
            )
        return evidence

    def _extract_technical_debt(self, result: AnalysisResult) -> list[Evidence]:
        """Extract technical-debt evidence from ``ai_review.technical_debt``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.technical_debt:
            return evidence
        td = review.technical_debt
        for category, items in [
            ("architecture", td.architecture_debt),
            ("code", td.code_debt),
            ("documentation", td.documentation_debt),
            ("testing", td.testing_debt),
            ("security", td.security_debt),
        ]:
            for item in items:
                evidence.append(
                    Evidence(
                        analyzer="technical-debt-engine",
                        finding_type=EvidenceType.TECHNICAL_DEBT,
                        severity=_risk_level_to_severity(item.priority.value),
                        confidence=0.8,
                        category=f"{category}_debt",
                        message=item.title,
                        explanation=item.description,
                        tags=["technical_debt", category],
                        source_id=item.id,
                        metrics={
                            "estimated_hours": item.estimated_hours,
                            "estimated_developers": item.estimated_developers,
                        },
                    )
                )
        return evidence

    def _extract_refactors(self, result: AnalysisResult) -> list[Evidence]:
        """Extract refactor evidence from ``ai_review.refactor_plan``."""
        evidence: list[Evidence] = []
        review = result.ai_review
        if not review or not review.refactor_plan:
            return evidence
        rp = review.refactor_plan
        for category, items in [
            ("quick_win", rp.quick_wins),
            ("high_impact", rp.high_impact),
            ("long_term", rp.long_term),
            ("breaking_change", rp.breaking_changes),
            ("architecture_improvement", rp.architecture_improvements),
        ]:
            for item in items:
                evidence.append(
                    Evidence(
                        analyzer="refactor-engine",
                        finding_type=EvidenceType.REFACTOR,
                        severity=Severity.INFO,
                        confidence=0.7,
                        category=category,
                        message=item.title,
                        explanation=item.description,
                        tags=["refactor", category, item.impact, item.effort],
                        source_id=item.id,
                        references=[
                            EvidenceReference(kind=ReferenceKind.FILE, value=f)
                            for f in item.affected_files
                        ],
                    )
                )
        return evidence

    def _extract_repository_metadata(self, result: AnalysisResult) -> list[Evidence]:
        """Extract a single repository-level evidence item."""
        if not result.repository_metadata:
            return []
        meta = result.repository_metadata
        return [
            Evidence(
                analyzer="repository-detector",
                finding_type=EvidenceType.REPOSITORY,
                severity=Severity.INFO,
                confidence=1.0,
                category="repository_info",
                message=f"Repository: {meta.owner}/{meta.name}",
                explanation=meta.description,
                tags=["repository"],
                metrics={
                    "total_commits": meta.total_commits,
                    "total_branches": meta.total_branches,
                    "contributors": len(meta.contributors),
                    "size_bytes": meta.size_bytes,
                    "license": meta.license,
                },
            )
        ]

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------

    def _normalize(
        self, evidence: list[Evidence]
    ) -> tuple[list[Evidence], list[EvidenceRelationship]]:
        """Deduplicate evidence and build relationships.

        Two evidence items are duplicates if they share the same
        ``(file_path, symbol, finding_type, category)`` key. When
        duplicates are found, the one with the higher severity (or higher
        confidence as tie-breaker) is kept. A ``DUPLICATE`` relationship
        is recorded linking the kept item to each discarded one.

        No data is lost: the discarded items' ``source_id`` values are
        recorded in the kept item's ``related_evidence_ids`` list.
        """
        if not evidence:
            return [], []
        groups: dict[tuple[str | None, str | None, str, str], list[Evidence]] = {}
        for ev in evidence:
            key = ev.dedup_key()
            groups.setdefault(key, []).append(ev)
        normalized: list[Evidence] = []
        relationships: list[EvidenceRelationship] = []
        for group in groups.values():
            if len(group) == 1:
                normalized.append(group[0])
                continue
            # Sort by severity (desc), then confidence (desc).
            sorted_group = sorted(
                group,
                key=lambda e: (_SEVERITY_RANK.get(e.severity, 0), e.confidence),
                reverse=True,
            )
            keeper = sorted_group[0]
            duplicates = sorted_group[1:]
            # Collect source_ids of discarded duplicates.
            related_ids = list(keeper.related_evidence_ids)
            for dup in duplicates:
                related_ids.append(dup.id)
                relationships.append(
                    EvidenceRelationship(
                        source_id=keeper.id,
                        target_id=dup.id,
                        relationship_type=RelationshipType.DUPLICATE,
                        detail=f"Duplicate of {keeper.message}",
                    )
                )
            # Create a new Evidence with updated related_evidence_ids
            # (frozen model → model_copy).
            keeper = keeper.model_copy(update={"related_evidence_ids": related_ids})
            normalized.append(keeper)
        return normalized, relationships

    # ------------------------------------------------------------------
    # Collection assembly
    # ------------------------------------------------------------------

    def _build_collection(
        self,
        evidence: list[Evidence],
        relationships: list[EvidenceRelationship],
    ) -> EvidenceCollection:
        """Assemble the final :class:`EvidenceCollection` with indexes."""
        by_analyzer: dict[str, list[UUID]] = {}
        by_severity: dict[str, list[UUID]] = {}
        by_file: dict[str, list[UUID]] = {}
        by_type: dict[str, list[UUID]] = {}
        for ev in evidence:
            by_analyzer.setdefault(ev.analyzer, []).append(ev.id)
            by_severity.setdefault(ev.severity.value, []).append(ev.id)
            if ev.file_path:
                by_file.setdefault(ev.file_path, []).append(ev.id)
            by_type.setdefault(ev.finding_type.value, []).append(ev.id)
        statistics = {
            "total_evidence": len(evidence),
            "total_relationships": len(relationships),
            "by_analyzer_counts": {k: len(v) for k, v in by_analyzer.items()},
            "by_severity_counts": {k: len(v) for k, v in by_severity.items()},
            "by_type_counts": {k: len(v) for k, v in by_type.items()},
            "unique_files": len(by_file),
        }
        return EvidenceCollection(
            evidence=evidence,
            relationships=relationships,
            by_analyzer=by_analyzer,
            by_severity=by_severity,
            by_file=by_file,
            by_type=by_type,
            statistics=statistics,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _confidence_from_enum(confidence_str: str) -> float:
        """Map a confidence label ('high'/'medium'/'low') to a float."""
        return {"high": 0.9, "medium": 0.6, "low": 0.3}.get(confidence_str.lower(), 0.5)


__all__ = ["EvidenceBuilder"]
