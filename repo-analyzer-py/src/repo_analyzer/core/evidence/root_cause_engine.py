"""Root Cause Detection Engine.

Analyzes the :class:`EngineeringGraph` to discover architectural root
causes — patterns where multiple individual findings (evidence) share a
common underlying problem.

Algorithm overview:
    The engine runs a series of **detection rules**, each of which examines
    the graph for a specific architectural anti-pattern (God Class, Tight
    Coupling, Circular Dependency, etc.). Each rule:

    1. Queries the graph for evidence clusters (groups of evidence that
       affect the same file/class/module).
    2. Checks whether the cluster matches the rule's pattern (e.g. ≥3
       symptom types present).
    3. If matched, creates a :class:`RootCause` linking all supporting
       evidence with a confidence score.
    4. Optionally suppresses evidence that is explained by generated-code
       detection (false positive reduction).

    Rules are independent and idempotent — running them in any order
    produces the same result. Each rule produces zero or more root causes.

Confidence scoring:
    Confidence is computed from four factors:
        - **Evidence count** (0-0.3): more evidence → higher confidence.
        - **Analyzer diversity** (0-0.3): evidence from multiple analyzers → higher.
        - **Graph strength** (0-0.2): strong graph connections (AFFECTS, BELONGS_TO) → higher.
        - **Contradiction penalty** (0-0.2): contradictory evidence (e.g. generated code) lowers confidence.

    Final confidence = sum of factors, clamped to [0, 1].

Usage::

    from repo_analyzer.core.evidence import RootCauseDetectionEngine

    collection = RootCauseDetectionEngine.detect(graph, evidence_collection)
    for rc in collection.root_causes:
        print(rc.category, rc.confidence, rc.evidence_count)
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from repo_analyzer.core.evidence.graph_models import (
    EngineeringGraph,
    NodeType,
)
from repo_analyzer.core.evidence.models import (
    Evidence,
    EvidenceCollection,
    EvidenceType,
)
from repo_analyzer.core.evidence.root_cause_models import (
    RootCause,
    RootCauseCategory,
    RootCauseCollection,
    RootCauseEvidence,
    RootCauseRelationship,
    RootCauseRelationshipType,
    RootCauseSeverity,
)
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Minimum number of distinct symptom categories needed to declare a root cause.
_MIN_SYMPTOMS = 2

#: Minimum confidence score for a root cause to be included.
_MIN_CONFIDENCE = 0.15

#: Evidence categories that indicate generated code (false positive suppression).
_GENERATED_CODE_TAGS = frozenset({"generated", "auto-generated", "minified", "vendor"})


def _severity_to_root_cause_severity(severity: str) -> RootCauseSeverity:
    """Map a Severity string to a :class:`RootCauseSeverity`."""
    mapping = {
        "critical": RootCauseSeverity.CRITICAL,
        "high": RootCauseSeverity.HIGH,
        "medium": RootCauseSeverity.MEDIUM,
        "low": RootCauseSeverity.LOW,
        "info": RootCauseSeverity.INFO,
    }
    return mapping.get(severity.lower(), RootCauseSeverity.MEDIUM)


class _DetectionContext:
    """Helper: groups evidence by the structural element they affect.

    This is the core clustering mechanism — evidence items that AFFECT the
    same file/class/module are grouped together, then rules check whether
    the group matches a root-cause pattern.
    """

    def __init__(self, graph: EngineeringGraph, collection: EvidenceCollection) -> None:
        self.graph = graph
        self.collection = collection
        self._evidence_by_id: dict[UUID, Evidence] = {ev.id: ev for ev in collection.evidence}
        # Build clusters: (file_path, class_name, function_name) → list of evidence.
        self._file_clusters: dict[str, list[Evidence]] = defaultdict(list)
        self._class_clusters: dict[str, list[Evidence]] = defaultdict(list)
        self._module_clusters: dict[str, list[Evidence]] = defaultdict(list)
        self._build_clusters()

    def _build_clusters(self) -> None:
        """Group evidence by the file/class/module they affect."""
        for ev in self.collection.evidence:
            if self._is_generated_code(ev):
                continue
            if ev.file_path:
                self._file_clusters[ev.file_path].append(ev)
            if ev.class_name and ev.file_path:
                key = f"{ev.file_path}::{ev.class_name}"
                self._class_clusters[key].append(ev)
            if ev.module:
                self._module_clusters[ev.module].append(ev)

    @staticmethod
    def _is_generated_code(ev: Evidence) -> bool:
        """Check if evidence is from generated code (false positive suppression)."""
        for tag in ev.tags:
            if tag.lower() in _GENERATED_CODE_TAGS:
                return True
        return False

    def evidence_for_file(self, file_path: str) -> list[Evidence]:
        """Return all non-generated evidence for a file."""
        return self._file_clusters.get(file_path, [])

    def evidence_for_class(self, file_path: str, class_name: str) -> list[Evidence]:
        """Return all non-generated evidence for a class."""
        return self._class_clusters.get(f"{file_path}::{class_name}", [])

    def evidence_for_module(self, module: str) -> list[Evidence]:
        """Return all non-generated evidence for a module."""
        return self._module_clusters.get(module, [])

    def symptom_types(self, evidence_list: list[Evidence]) -> set[str]:
        """Return the set of distinct symptom categories in a cluster."""
        return {ev.category for ev in evidence_list}

    def analyzer_diversity(self, evidence_list: list[Evidence]) -> set[str]:
        """Return the set of distinct analyzers that produced evidence."""
        return {ev.analyzer for ev in evidence_list}

    def graph_strength(self, evidence_list: list[Evidence]) -> int:
        """Count graph edges (AFFECTS/BELONGS_TO) linking evidence to structure."""
        count = 0
        for ev in evidence_list:
            node = self.graph.node_for_evidence(ev.id)
            if node is None:
                continue
            count += len(self.graph.outgoing_edges(node.id))
            count += len(self.graph.incoming_edges(node.id))
        return count


class RootCauseDetectionEngine:
    """Detect architectural root causes from the engineering graph.

    The engine is stateless and thread-safe. The :meth:`detect` method is
    the single entry point.
    """

    @classmethod
    def detect(
        cls,
        graph: EngineeringGraph,
        collection: EvidenceCollection,
    ) -> RootCauseCollection:
        """Analyze ``graph`` and ``collection`` to produce root causes.

        Args:
            graph: The :class:`EngineeringGraph` from the graph phase.
            collection: The :class:`EvidenceCollection` from the evidence phase.

        Returns:
            A :class:`RootCauseCollection` with detected root causes and
            inter-root-cause relationships.
        """
        engine = cls()
        ctx = _DetectionContext(graph, collection)
        root_causes: list[RootCause] = []

        # Run all detection rules.
        root_causes.extend(engine._detect_god_class(ctx))
        root_causes.extend(engine._detect_god_service(ctx))
        root_causes.extend(engine._detect_circular_dependency(ctx, graph))
        root_causes.extend(engine._detect_tight_coupling(ctx, graph))
        root_causes.extend(engine._detect_low_cohesion(ctx, graph))
        root_causes.extend(engine._detect_large_module(ctx))
        root_causes.extend(engine._detect_oversized_service(ctx))
        root_causes.extend(engine._detect_shotgun_surgery(ctx))
        root_causes.extend(engine._detect_dependency_explosion(ctx, graph))
        root_causes.extend(engine._detect_anemic_domain_model(ctx))
        root_causes.extend(engine._detect_duplicated_responsibility(ctx))
        root_causes.extend(engine._detect_srp_violation(ctx))

        # Deduplicate root causes (same category + same central node).
        root_causes = engine._deduplicate(root_causes)

        # Build inter-root-cause relationships.
        relationships = engine._build_relationships(root_causes)

        # Build indexes.
        by_category: dict[str, list[UUID]] = defaultdict(list)
        by_severity: dict[str, list[UUID]] = defaultdict(list)
        by_file: dict[str, list[UUID]] = defaultdict(list)
        by_evidence: dict[str, list[UUID]] = defaultdict(list)
        for rc in root_causes:
            by_category[rc.category.value].append(rc.id)
            by_severity[rc.severity.value].append(rc.id)
            for f in rc.affected_files:
                by_file[f].append(rc.id)
            for eid in rc.evidence_ids:
                by_evidence[str(eid)].append(rc.id)

        stats = engine._build_statistics(root_causes, relationships)

        return RootCauseCollection(
            root_causes=root_causes,
            relationships=relationships,
            by_category=dict(by_category),
            by_severity=dict(by_severity),
            by_file=dict(by_file),
            by_evidence=dict(by_evidence),
            statistics=stats,
        )

    # ------------------------------------------------------------------
    # Detection rules — each returns a list of RootCause (possibly empty)
    # ------------------------------------------------------------------

    def _detect_god_class(self, ctx: _DetectionContext) -> list[RootCause]:
        """God Class: a class with many responsibilities (high complexity +
        many methods + large size + code smells).

        Pattern: ≥3 of {high_complexity, long_method, large_class,
        code_smell, low_testability} in the same class.
        """
        root_causes: list[RootCause] = []
        god_class_symptoms = {
            "cyclomatic_complexity",
            "long_method",
            "large_class",
            "god_class",
            "high_complexity",
            "large_file",
        }
        for cluster_key, evidence_list in ctx._class_clusters.items():
            file_path, class_name = cluster_key.split("::", 1)
            symptoms = ctx.symptom_types(evidence_list) & god_class_symptoms
            if len(symptoms) < _MIN_SYMPTOMS:
                continue
            confidence = self._compute_confidence(ctx, evidence_list)
            if confidence < _MIN_CONFIDENCE:
                continue
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.GOD_CLASS,
                    title=f"God Class: {class_name}",
                    severity=RootCauseSeverity.HIGH,
                    confidence=confidence,
                    description=(
                        f"Class '{class_name}' in '{file_path}' accumulates multiple "
                        f"responsibilities: {', '.join(sorted(symptoms))}."
                    ),
                    technical_rationale=(
                        f"Detected {len(symptoms)} distinct symptom types from "
                        f"{len(ctx.analyzer_diversity(evidence_list))} analyzer(s) "
                        f"across {len(evidence_list)} evidence item(s)."
                    ),
                    root_cause_origin=(
                        "Organic growth without refactoring — the class has "
                        "accumulated responsibilities over time."
                    ),
                    affected_modules=[],
                    affected_classes=[class_name],
                    affected_files=[file_path],
                    evidence_links=self._build_evidence_links(
                        evidence_list, "supports God Class pattern"
                    ),
                    central_node_ids=self._central_nodes(ctx, evidence_list),
                )
            )
        return root_causes

    def _detect_god_service(self, ctx: _DetectionContext) -> list[RootCause]:
        """God Service: a service module with too many functions and high complexity.

        Pattern: file with many functions (>10) + high complexity + code smells.
        """
        root_causes: list[RootCause] = []
        for file_path, evidence_list in ctx._file_clusters.items():
            symptoms = ctx.symptom_types(evidence_list)
            has_many_functions = any(
                ev.metrics.get("function_count", 0) > 10
                for ev in evidence_list
                if ev.finding_type == EvidenceType.METRIC
            )
            has_complexity = "cyclomatic_complexity" in symptoms
            has_smells = bool(symptoms & {"long_method", "god_class", "high_complexity"})
            if has_many_functions and (has_complexity or has_smells):
                confidence = self._compute_confidence(ctx, evidence_list)
                if confidence < _MIN_CONFIDENCE:
                    continue
                root_causes.append(
                    RootCause(
                        category=RootCauseCategory.GOD_SERVICE,
                        title=f"God Service: {file_path}",
                        severity=RootCauseSeverity.HIGH,
                        confidence=confidence,
                        description=(
                            f"File '{file_path}' acts as a god service with too many "
                            f"functions and high complexity."
                        ),
                        technical_rationale=(
                            f"File has >10 functions, complexity evidence, and "
                            f"{len(evidence_list)} total evidence items."
                        ),
                        root_cause_origin=(
                            "Service layer grew without splitting into focused services."
                        ),
                        affected_files=[file_path],
                        evidence_links=self._build_evidence_links(
                            evidence_list, "supports God Service pattern"
                        ),
                        central_node_ids=self._central_nodes(ctx, evidence_list),
                    )
                )
        return root_causes

    def _detect_circular_dependency(
        self, ctx: _DetectionContext, graph: EngineeringGraph
    ) -> list[RootCause]:
        """Circular Dependency: import cycles detected in the graph.

        Pattern: ARCHITECTURE evidence with category 'cyclic_dependency' or
        'circular_import', plus IMPORTS edges forming a cycle.
        """
        root_causes: list[RootCause] = []
        cycle_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category in ("cyclic_dependency", "circular_import")
            and not ctx._is_generated_code(ev)
        ]
        if not cycle_evidence:
            return root_causes
        # Group by module set.
        for ev in cycle_evidence:
            modules = [ref.value for ref in ev.references if ref.kind.value == "module"]
            if not modules:
                modules = [ev.module] if ev.module else []
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.CIRCULAR_DEPENDENCY,
                    title=f"Circular Dependency: {' → '.join(modules[:5])}",
                    severity=RootCauseSeverity.HIGH,
                    confidence=confidence,
                    description=(
                        f"Circular dependency detected between modules: {', '.join(modules[:10])}."
                    ),
                    technical_rationale=(
                        "Import graph contains a cycle, preventing clean layering."
                    ),
                    root_cause_origin=(
                        "Modules were added without checking import direction, "
                        "creating bidirectional dependencies."
                    ),
                    affected_modules=modules,
                    affected_files=[ev.file_path] if ev.file_path else [],
                    evidence_links=self._build_evidence_links([ev], "directly detects the cycle"),
                    central_node_ids=self._central_nodes(ctx, [ev]),
                )
            )
        return root_causes

    def _detect_tight_coupling(
        self, ctx: _DetectionContext, graph: EngineeringGraph
    ) -> list[RootCause]:
        """Tight Coupling: a module/file with many outgoing DEPENDS_ON or
        IMPORTS edges.

        Pattern: file with >5 outgoing dependency edges + evidence of coupling.
        """
        root_causes: list[RootCause] = []
        coupling_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category in ("high_coupling", "tight_coupling") and not ctx._is_generated_code(ev)
        ]
        for ev in coupling_evidence:
            modules = [ev.module] if ev.module else []
            files = [ev.file_path] if ev.file_path else []
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.TIGHT_COUPLING,
                    title=f"Tight Coupling: {ev.file_path or ev.module or 'repository'}",
                    severity=RootCauseSeverity.MEDIUM,
                    confidence=confidence,
                    description=(
                        f"High coupling detected in {ev.file_path or ev.module}: "
                        f"the element depends on too many others."
                    ),
                    technical_rationale=(
                        "Graph analysis shows excessive outgoing dependency edges."
                    ),
                    root_cause_origin=(
                        "Direct dependencies were used instead of abstractions, "
                        "creating tight binding between modules."
                    ),
                    affected_modules=modules,
                    affected_files=files,
                    evidence_links=self._build_evidence_links([ev], "measures coupling"),
                    central_node_ids=self._central_nodes(ctx, [ev]),
                )
            )
        return root_causes

    def _detect_low_cohesion(
        self, ctx: _DetectionContext, graph: EngineeringGraph
    ) -> list[RootCause]:
        """Low Cohesion: module with unrelated responsibilities.

        Pattern: ARCHITECTURE evidence with category 'low_cohesion'.
        """
        root_causes: list[RootCause] = []
        cohesion_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category == "low_cohesion" and not ctx._is_generated_code(ev)
        ]
        for ev in cohesion_evidence:
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.LOW_COHESION,
                    title=f"Low Cohesion: {ev.module or ev.file_path or 'repository'}",
                    severity=RootCauseSeverity.MEDIUM,
                    confidence=confidence,
                    description=(
                        f"Low cohesion in {ev.module or ev.file_path}: the module "
                        f"mixes unrelated responsibilities."
                    ),
                    technical_rationale="Cohesion metric is below the threshold.",
                    root_cause_origin=("Module was used as a dumping ground for unrelated code."),
                    affected_modules=[ev.module] if ev.module else [],
                    affected_files=[ev.file_path] if ev.file_path else [],
                    evidence_links=self._build_evidence_links([ev], "measures cohesion"),
                    central_node_ids=self._central_nodes(ctx, [ev]),
                )
            )
        return root_causes

    def _detect_large_module(self, ctx: _DetectionContext) -> list[RootCause]:
        """Large Module: file with >500 SLOC and evidence of maintainability issues.

        Pattern: METRIC evidence with category 'large_file' + complexity or
        documentation issues.
        """
        root_causes: list[RootCause] = []
        for file_path, evidence_list in ctx._file_clusters.items():
            has_large = any(ev.category == "large_file" for ev in evidence_list)
            has_issues = bool(
                ctx.symptom_types(evidence_list)
                & {"cyclomatic_complexity", "low_docstring_coverage", "long_method"}
            )
            if has_large and has_issues:
                confidence = self._compute_confidence(ctx, evidence_list)
                if confidence < _MIN_CONFIDENCE:
                    continue
                root_causes.append(
                    RootCause(
                        category=RootCauseCategory.LARGE_MODULE,
                        title=f"Large Module: {file_path}",
                        severity=RootCauseSeverity.MEDIUM,
                        confidence=confidence,
                        description=(
                            f"File '{file_path}' is too large and has maintainability issues."
                        ),
                        technical_rationale=(
                            "File exceeds 500 SLOC and has complexity/documentation evidence."
                        ),
                        root_cause_origin="Code was added to the file without splitting.",
                    )
                )
                root_causes[-1] = root_causes[-1].model_copy(
                    update={
                        "evidence_links": self._build_evidence_links(
                            evidence_list, "supports Large Module pattern"
                        ),
                        "affected_files": [file_path],
                        "central_node_ids": self._central_nodes(ctx, evidence_list),
                    }
                )
        return root_causes

    def _detect_oversized_service(self, ctx: _DetectionContext) -> list[RootCause]:
        """Oversized Service: combination of high complexity + large class +
        duplicate logic + long methods + low testability in same file/class.

        Pattern: ≥3 of {complexity, large_file, duplicate, long_method, no_tests, low_coverage}
        in the same file.
        """
        root_causes: list[RootCause] = []
        oversized_symptoms = {
            "cyclomatic_complexity",
            "large_file",
            "duplicate_file",
            "long_method",
            "no_tests",
            "low_coverage",
        }
        for file_path, evidence_list in ctx._file_clusters.items():
            symptoms = ctx.symptom_types(evidence_list) & oversized_symptoms
            if len(symptoms) < 3:
                continue
            confidence = self._compute_confidence(ctx, evidence_list)
            if confidence < _MIN_CONFIDENCE:
                continue
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.OVERSIZED_SERVICE,
                    title=f"Oversized Service: {file_path}",
                    severity=RootCauseSeverity.HIGH,
                    confidence=confidence,
                    description=(
                        f"File '{file_path}' shows {len(symptoms)} symptoms of an "
                        f"oversized service: {', '.join(sorted(symptoms))}."
                    ),
                    technical_rationale=(
                        f"Multiple analyzers ({len(ctx.analyzer_diversity(evidence_list))}) "
                        f"report {len(evidence_list)} evidence items in this file."
                    ),
                    root_cause_origin=(
                        "The service accumulated responsibilities without being split."
                    ),
                    affected_files=[file_path],
                    evidence_links=self._build_evidence_links(
                        evidence_list, "supports Oversized Service pattern"
                    ),
                    central_node_ids=self._central_nodes(ctx, evidence_list),
                )
            )
        return root_causes

    def _detect_shotgun_surgery(self, ctx: _DetectionContext) -> list[RootCause]:
        """Shotgun Surgery: same finding type spread across many files.

        Pattern: a single category (e.g. 'unused_import') appearing in ≥5
        different files.
        """
        root_causes: list[RootCause] = []
        category_files: dict[str, set[str]] = defaultdict(set)
        category_evidence: dict[str, list[Evidence]] = defaultdict(list)
        for ev in ctx.collection.evidence:
            if ctx._is_generated_code(ev) or not ev.file_path:
                continue
            category_files[ev.category].add(ev.file_path)
            category_evidence[ev.category].append(ev)
        for cat, files in category_files.items():
            if len(files) < 5:
                continue
            ev_list = category_evidence[cat]
            confidence = self._compute_confidence(ctx, ev_list)
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.SHOTGUN_SURGERY,
                    title=f"Shotgun Surgery: {cat} across {len(files)} files",
                    severity=RootCauseSeverity.MEDIUM,
                    confidence=confidence,
                    description=(
                        f"Finding '{cat}' appears in {len(files)} different files, "
                        f"suggesting a systemic issue rather than a local one."
                    ),
                    technical_rationale=(
                        f"{len(ev_list)} evidence items from "
                        f"{len(ctx.analyzer_diversity(ev_list))} analyzer(s)."
                    ),
                    root_cause_origin=(
                        "A pattern was copy-pasted or a convention was not enforced "
                        "across the codebase."
                    ),
                    affected_files=sorted(files)[:20],
                    evidence_links=self._build_evidence_links(
                        ev_list[:20], "part of the systemic pattern"
                    ),
                )
            )
        return root_causes

    def _detect_dependency_explosion(
        self, ctx: _DetectionContext, graph: EngineeringGraph
    ) -> list[RootCause]:
        """Dependency Explosion: a file/module with >10 outgoing DEPENDS_ON edges.

        Pattern: DEPENDENCY evidence + high outgoing edge count in graph.
        """
        root_causes: list[RootCause] = []
        dep_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.finding_type == EvidenceType.DEPENDENCY and not ctx._is_generated_code(ev)
        ]
        # Count dependencies per file from graph.
        for node in graph.nodes_by_type(NodeType.FILE):
            deps = graph.dependencies_of(node.id)
            if len(deps) > 10:
                related_ev = [ev for ev in dep_evidence if ev.file_path == node.file_path]
                if not related_ev:
                    continue
                confidence = self._compute_confidence(ctx, related_ev)
                root_causes.append(
                    RootCause(
                        category=RootCauseCategory.DEPENDENCY_EXPLOSION,
                        title=f"Dependency Explosion: {node.label}",
                        severity=RootCauseSeverity.MEDIUM,
                        confidence=confidence,
                        description=(
                            f"File '{node.label}' depends on {len(deps)} external "
                            f"packages, creating a large supply-chain surface."
                        ),
                        technical_rationale=(
                            "Graph shows >10 outgoing DEPENDS_ON edges from this file."
                        ),
                        root_cause_origin=(
                            "Dependencies were added without consolidation or "
                            "wrapping behind interfaces."
                        ),
                        affected_files=[node.label] if node.file_path else [],
                        evidence_links=self._build_evidence_links(
                            related_ev, "measures dependency count"
                        ),
                    )
                )
        return root_causes

    def _detect_anemic_domain_model(self, ctx: _DetectionContext) -> list[RootCause]:
        """Anemic Domain Model: classes with many fields but no behavior.

        Pattern: CODE_QUALITY evidence with category 'anemic_model'.
        """
        root_causes: list[RootCause] = []
        anemic_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category == "anemic_model" and not ctx._is_generated_code(ev)
        ]
        for ev in anemic_evidence:
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.ANEMIC_DOMAIN_MODEL,
                    title=f"Anemic Domain Model: {ev.class_name or ev.file_path or 'unknown'}",
                    severity=RootCauseSeverity.LOW,
                    confidence=confidence,
                    description=(
                        f"Class '{ev.class_name or '?'}' appears to be an anemic domain model "
                        f"(data without behavior)."
                    ),
                    technical_rationale="AST analysis shows no methods on the class.",
                    root_cause_origin=(
                        "Domain logic was moved to services, breaking encapsulation."
                    ),
                    affected_classes=[ev.class_name] if ev.class_name else [],
                    affected_files=[ev.file_path] if ev.file_path else [],
                    evidence_links=self._build_evidence_links([ev], "detects missing methods"),
                )
            )
        return root_causes

    def _detect_duplicated_responsibility(self, ctx: _DetectionContext) -> list[RootCause]:
        """Duplicated Responsibility: duplicate code across files.

        Pattern: FILE_SYSTEM evidence with category 'duplicate_file'.
        """
        root_causes: list[RootCause] = []
        dup_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category == "duplicate_file" and not ctx._is_generated_code(ev)
        ]
        for ev in dup_evidence:
            files = [ref.value for ref in ev.references if ref.kind.value == "file"]
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.DUPLICATED_RESPONSIBILITY,
                    title=f"Duplicated Responsibility: {len(files)} files",
                    severity=RootCauseSeverity.MEDIUM,
                    confidence=confidence,
                    description=(
                        f"{len(files)} files share identical content, suggesting "
                        f"duplicated responsibility."
                    ),
                    technical_rationale="SHA-256 hash matching detected identical files.",
                    root_cause_origin=(
                        "Code was copy-pasted instead of being extracted into a shared utility."
                    ),
                    affected_files=files[:20],
                    evidence_links=self._build_evidence_links([ev], "detects identical content"),
                )
            )
        return root_causes

    def _detect_srp_violation(self, ctx: _DetectionContext) -> list[RootCause]:
        """SRP Violation: a class with >20 methods (Single Responsibility Principle).

        Pattern: CODE_QUALITY evidence with category 'god_class' or class with
        many methods from AST symbols.
        """
        root_causes: list[RootCause] = []
        srp_evidence = [
            ev
            for ev in ctx.collection.evidence
            if ev.category == "god_class" and not ctx._is_generated_code(ev)
        ]
        for ev in srp_evidence:
            confidence = self._compute_confidence(ctx, [ev])
            root_causes.append(
                RootCause(
                    category=RootCauseCategory.SRP_VIOLATION,
                    title=f"SRP Violation: {ev.class_name or ev.file_path or 'unknown'}",
                    severity=RootCauseSeverity.MEDIUM,
                    confidence=confidence,
                    description=(
                        f"Class '{ev.class_name or '?'}' has too many methods, "
                        f"violating the Single Responsibility Principle."
                    ),
                    technical_rationale="Method count exceeds the SRP threshold (>20).",
                    root_cause_origin=(
                        "Responsibilities were added to the class without extracting new classes."
                    ),
                    affected_classes=[ev.class_name] if ev.class_name else [],
                    affected_files=[ev.file_path] if ev.file_path else [],
                    evidence_links=self._build_evidence_links([ev], "measures method count"),
                )
            )
        return root_causes

    # ------------------------------------------------------------------
    # Confidence scoring
    # ------------------------------------------------------------------

    def _compute_confidence(self, ctx: _DetectionContext, evidence_list: list[Evidence]) -> float:
        """Compute a confidence score (0-1) for a root cause.

        Factors:
            - Evidence count: 0-0.3 (more evidence → higher).
            - Analyzer diversity: 0-0.3 (more analyzers → higher).
            - Graph strength: 0-0.2 (more graph edges → higher).
            - Contradiction penalty: 0-0.2 (generated code → lower).
        """
        if not evidence_list:
            return 0.0
        # Evidence count factor (capped at 5 evidence items for max score).
        count_score = min(len(evidence_list) / 5.0, 1.0) * 0.3
        # Analyzer diversity factor.
        analyzers = ctx.analyzer_diversity(evidence_list)
        diversity_score = min(len(analyzers) / 3.0, 1.0) * 0.3
        # Graph strength factor.
        edge_count = ctx.graph_strength(evidence_list)
        graph_score = min(edge_count / 10.0, 1.0) * 0.2
        # Contradiction penalty: check for generated-code evidence.
        generated_count = sum(1 for ev in evidence_list if ctx._is_generated_code(ev))
        contradiction_penalty = (generated_count / max(len(evidence_list), 1)) * 0.2
        total = count_score + diversity_score + graph_score - contradiction_penalty
        return max(0.0, min(1.0, round(total, 3)))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_evidence_links(
        evidence_list: list[Evidence], reason: str
    ) -> list[RootCauseEvidence]:
        """Build :class:`RootCauseEvidence` links from evidence."""
        return [
            RootCauseEvidence(
                evidence_id=ev.id,
                contribution=min(1.0, 0.5 + ev.confidence * 0.5),
                reason=f"{reason}: {ev.message}",
            )
            for ev in evidence_list
        ]

    @staticmethod
    def _central_nodes(ctx: _DetectionContext, evidence_list: list[Evidence]) -> list[UUID]:
        """Return the graph node IDs that are central to this root cause."""
        node_ids: list[UUID] = []
        for ev in evidence_list:
            node = ctx.graph.node_for_evidence(ev.id)
            if node is not None:
                node_ids.append(node.id)
        return list(dict.fromkeys(node_ids))  # dedupe preserving order

    @staticmethod
    def _deduplicate(root_causes: list[RootCause]) -> list[RootCause]:
        """Remove duplicate root causes (same category + overlapping files).

        When two root causes have the same category and share ≥1 affected
        file, the one with the higher confidence is kept.
        """
        if not root_causes:
            return []
        # Group by category.
        by_cat: dict[str, list[RootCause]] = defaultdict(list)
        for rc in root_causes:
            by_cat[rc.category.value].append(rc)
        result: list[RootCause] = []
        for _cat, group in by_cat.items():
            # Sort by confidence (desc).
            sorted_group = sorted(group, key=lambda rc: rc.confidence, reverse=True)
            kept: list[RootCause] = []
            for rc in sorted_group:
                is_dup = False
                for kept_rc in kept:
                    # Check file overlap.
                    overlap = set(rc.affected_files) & set(kept_rc.affected_files)
                    if overlap:
                        is_dup = True
                        break
                if not is_dup:
                    kept.append(rc)
            result.extend(kept)
        return result

    @staticmethod
    def _build_relationships(
        root_causes: list[RootCause],
    ) -> list[RootCauseRelationship]:
        """Build inter-root-cause relationships.

        Rules:
            - God Class → CAUSES → Tight Coupling (if both exist for same file).
            - God Class → CAUSES → Low Cohesion.
            - Oversized Service → LEADS_TO → Tight Coupling.
            - Circular Dependency → AGGRAVATES → Tight Coupling.
            - God Class → CO_OCCURS_WITH → SRP Violation.
        """
        relationships: list[RootCauseRelationship] = []
        # Index root causes by category and file.
        by_cat: dict[str, list[RootCause]] = defaultdict(list)
        for rc in root_causes:
            by_cat[rc.category.value].append(rc)
        # Rule: God Class → causes → Tight Coupling (same file).
        for gc in by_cat.get("god_class", []):
            for tc in by_cat.get("tight_coupling", []):
                if set(gc.affected_files) & set(tc.affected_files):
                    relationships.append(
                        RootCauseRelationship(
                            source_root_cause_id=gc.id,
                            target_root_cause_id=tc.id,
                            relationship_type=RootCauseRelationshipType.CAUSES,
                            detail="God Class causes tight coupling through excessive dependencies.",
                        )
                    )
        # Rule: God Class → causes → Low Cohesion.
        for gc in by_cat.get("god_class", []):
            for lc in by_cat.get("low_cohesion", []):
                if set(gc.affected_files) & set(lc.affected_files):
                    relationships.append(
                        RootCauseRelationship(
                            source_root_cause_id=gc.id,
                            target_root_cause_id=lc.id,
                            relationship_type=RootCauseRelationshipType.CAUSES,
                            detail="God Class causes low cohesion by mixing responsibilities.",
                        )
                    )
        # Rule: Oversized Service → leads_to → Tight Coupling.
        for os in by_cat.get("oversized_service", []):
            for tc in by_cat.get("tight_coupling", []):
                if set(os.affected_files) & set(tc.affected_files):
                    relationships.append(
                        RootCauseRelationship(
                            source_root_cause_id=os.id,
                            target_root_cause_id=tc.id,
                            relationship_type=RootCauseRelationshipType.LEADS_TO,
                            detail="Oversized service leads to tight coupling.",
                        )
                    )
        # Rule: Circular Dependency → aggravates → Tight Coupling.
        for cd in by_cat.get("circular_dependency", []):
            for tc in by_cat.get("tight_coupling", []):
                relationships.append(
                    RootCauseRelationship(
                        source_root_cause_id=cd.id,
                        target_root_cause_id=tc.id,
                        relationship_type=RootCauseRelationshipType.AGGRAVATES,
                        detail="Circular dependency aggravates tight coupling.",
                    )
                )
        # Rule: God Class → co_occurs_with → SRP Violation.
        for gc in by_cat.get("god_class", []):
            for srp in by_cat.get("srp_violation", []):
                if set(gc.affected_files) & set(srp.affected_files):
                    relationships.append(
                        RootCauseRelationship(
                            source_root_cause_id=gc.id,
                            target_root_cause_id=srp.id,
                            relationship_type=RootCauseRelationshipType.CO_OCCURS_WITH,
                            detail="God Class and SRP violation co-occur in the same file.",
                        )
                    )
        return relationships

    @staticmethod
    def _build_statistics(
        root_causes: list[RootCause],
        relationships: list[RootCauseRelationship],
    ) -> dict[str, Any]:
        """Build summary statistics."""
        cat_counts: dict[str, int] = defaultdict(int)
        sev_counts: dict[str, int] = defaultdict(int)
        for rc in root_causes:
            cat_counts[rc.category.value] += 1
            sev_counts[rc.severity.value] += 1
        avg_confidence = sum(rc.confidence for rc in root_causes) / max(len(root_causes), 1)
        return {
            "total_root_causes": len(root_causes),
            "total_relationships": len(relationships),
            "by_category_counts": dict(cat_counts),
            "by_severity_counts": dict(sev_counts),
            "average_confidence": round(avg_confidence, 3),
            "total_evidence_linked": sum(rc.evidence_count for rc in root_causes),
        }


__all__ = ["RootCauseDetectionEngine"]
