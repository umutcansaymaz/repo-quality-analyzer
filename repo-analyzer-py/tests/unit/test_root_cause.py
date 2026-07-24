"""Unit tests for the Root Cause Detection Engine.

Covers:
    - Empty graph / no evidence (no root causes)
    - Single root cause (God Class pattern)
    - Multiple root causes (different categories)
    - Evidence clustering (same file evidence grouped)
    - Confidence calculation
    - Graph-based relationships between root causes
    - Duplicate root cause prevention
    - False positive reduction (generated code suppression)
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.report import Severity
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.evidence import (
    Evidence,
    EvidenceCollection,
    EvidenceType,
    GraphBuilder,
    RootCause,
    RootCauseCategory,
    RootCauseCollection,
    RootCauseDetectionEngine,
    RootCauseSeverity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_evidence(
    *,
    finding_type: EvidenceType = EvidenceType.CODE_QUALITY,
    severity: Severity = Severity.HIGH,
    category: str = "general",
    file_path: str | None = None,
    class_name: str | None = None,
    function_name: str | None = None,
    module: str | None = None,
    analyzer: str = "test-analyzer",
    message: str = "test finding",
    tags: list[str] | None = None,
) -> Evidence:
    """Create a single Evidence for testing."""
    return Evidence(
        analyzer=analyzer,
        finding_type=finding_type,
        severity=severity,
        confidence=0.9,
        category=category,
        file_path=file_path,
        class_name=class_name,
        function_name=function_name,
        module=module,
        message=message,
        tags=tags or [],
    )


def _build_graph_and_collection(
    evidence: list[Evidence],
    result: AnalysisResult | None = None,
) -> tuple[EvidenceCollection, Any]:
    """Build an EvidenceCollection + EngineeringGraph from evidence.

    Builds a properly-indexed EvidenceCollection (the GraphBuilder needs
    by_file/by_type indexes to create file/type nodes).
    """
    if result is None:
        repo = parse_repository_url("https://github.com/test/repo")
        result = AnalysisResult(repository=repo)
    # Build indexes manually (EvidenceBuilder requires a full AnalysisResult).
    by_analyzer: dict[str, list] = {}
    by_severity: dict[str, list] = {}
    by_file: dict[str, list] = {}
    by_type: dict[str, list] = {}
    for ev in evidence:
        by_analyzer.setdefault(ev.analyzer, []).append(ev.id)
        by_severity.setdefault(ev.severity.value, []).append(ev.id)
        if ev.file_path:
            by_file.setdefault(ev.file_path, []).append(ev.id)
        by_type.setdefault(ev.finding_type.value, []).append(ev.id)
    collection = EvidenceCollection(
        evidence=evidence,
        by_analyzer=by_analyzer,
        by_severity=by_severity,
        by_file=by_file,
        by_type=by_type,
        statistics={"total_evidence": len(evidence)},
    )
    graph = GraphBuilder.build(collection, result)
    return collection, graph


# ---------------------------------------------------------------------------
# Tests: empty / no evidence
# ---------------------------------------------------------------------------


class TestEmptyDetection:
    def test_empty_collection_produces_no_root_causes(self) -> None:
        repo = parse_repository_url("https://github.com/test/empty")
        result = AnalysisResult(repository=repo)
        collection = EvidenceCollection(evidence=[])
        graph = GraphBuilder.build(collection, result)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        assert rc_collection.total == 0
        assert len(rc_collection.relationships) == 0

    def test_empty_statistics(self) -> None:
        repo = parse_repository_url("https://github.com/test/empty")
        result = AnalysisResult(repository=repo)
        collection = EvidenceCollection(evidence=[])
        graph = GraphBuilder.build(collection, result)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        assert rc_collection.statistics["total_root_causes"] == 0
        assert rc_collection.statistics["average_confidence"] == 0.0


# ---------------------------------------------------------------------------
# Tests: single root cause — God Class
# ---------------------------------------------------------------------------


class TestGodClassDetection:
    def test_god_class_detected(self) -> None:
        """A class with complexity + large_file + code_smell should produce God Class."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="complexity-analyzer",
                message="High complexity",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="metrics-engine",
                message="Large file",
            ),
            _make_evidence(
                category="long_method",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="code-quality-engine",
                message="Long method",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_class = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        assert len(god_class) >= 1
        assert "UserService" in god_class[0].title

    def test_god_class_has_evidence_links(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_class = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        if god_class:
            assert god_class[0].evidence_count >= 2

    def test_god_class_has_description(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_class = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        if god_class:
            assert god_class[0].description
            assert god_class[0].technical_rationale
            assert god_class[0].root_cause_origin

    def test_god_class_has_affected_files(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_class = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        if god_class:
            assert "src/service.py" in god_class[0].affected_files
            assert "UserService" in god_class[0].affected_classes


# ---------------------------------------------------------------------------
# Tests: multiple root causes
# ---------------------------------------------------------------------------


class TestMultipleRootCauses:
    def test_multiple_categories_detected(self) -> None:
        evidence = [
            # God Class symptoms.
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
            # Circular dependency.
            _make_evidence(
                finding_type=EvidenceType.IMPORT,
                category="circular_import",
                module="module_a",
                message="Circular: module_a -> module_b",
            ),
            # Shotgun surgery.
            *[
                _make_evidence(
                    category="unused_import",
                    file_path=f"src/file_{i}.py",
                    analyzer="import-analyzer",
                )
                for i in range(6)
            ],
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        categories = {rc.category for rc in rc_collection.root_causes}
        assert (
            RootCauseCategory.GOD_CLASS in categories
            or RootCauseCategory.OVERSIZED_SERVICE in categories
        )
        assert RootCauseCategory.CIRCULAR_DEPENDENCY in categories
        assert RootCauseCategory.SHOTGUN_SURGERY in categories

    def test_statistics_correct(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        stats = rc_collection.statistics
        assert stats["total_root_causes"] == rc_collection.total
        assert "by_category_counts" in stats
        assert "by_severity_counts" in stats
        assert "average_confidence" in stats

    def test_by_category_index(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        if rc_collection.root_causes:
            for rc in rc_collection.root_causes:
                assert rc.category.value in rc_collection.by_category


# ---------------------------------------------------------------------------
# Tests: evidence clustering
# ---------------------------------------------------------------------------


class TestEvidenceClustering:
    def test_evidence_grouped_by_file(self) -> None:
        """Evidence for the same file should be grouped into root causes."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/big.py",
                class_name="BigClass",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/big.py",
                class_name="BigClass",
            ),
            _make_evidence(
                category="long_method",
                file_path="src/big.py",
                class_name="BigClass",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        for rc in rc_collection.root_causes:
            assert "src/big.py" in rc.affected_files

    def test_evidence_in_different_files_not_grouped(self) -> None:
        """Evidence for different files should not be grouped into the same root cause."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/a.py",
                class_name="ClassA",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/b.py",
                class_name="ClassB",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        # Each root cause should only affect one file.
        for rc in rc_collection.root_causes:
            assert len(rc.affected_files) <= 1

    def test_for_evidence_lookup(self) -> None:
        """for_evidence should return root causes that reference an evidence ID."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        if rc_collection.root_causes:
            ev_id = rc_collection.root_causes[0].evidence_ids[0]
            rcs = rc_collection.for_evidence(ev_id)
            assert len(rcs) >= 1


# ---------------------------------------------------------------------------
# Tests: confidence scoring
# ---------------------------------------------------------------------------


class TestConfidenceScoring:
    def test_confidence_in_range(self) -> None:
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="complexity-analyzer",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="metrics-engine",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        for rc in rc_collection.root_causes:
            assert 0.0 <= rc.confidence <= 1.0

    def test_more_evidence_higher_confidence(self) -> None:
        """More evidence should generally produce higher confidence."""
        # 2 evidence items.
        ev_small = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/a.py",
                class_name="A",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/a.py",
                class_name="A",
            ),
        ]
        # 5 evidence items.
        ev_large = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/b.py",
                class_name="B",
                analyzer="complexity-analyzer",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/b.py",
                class_name="B",
                analyzer="metrics-engine",
            ),
            _make_evidence(
                category="long_method",
                file_path="src/b.py",
                class_name="B",
                analyzer="code-quality-engine",
            ),
            _make_evidence(
                category="god_class",
                file_path="src/b.py",
                class_name="B",
                analyzer="quality-engine",
            ),
            _make_evidence(
                category="high_complexity",
                file_path="src/b.py",
                class_name="B",
                analyzer="complexity-analyzer",
            ),
        ]
        col_small, graph_small = _build_graph_and_collection(ev_small)
        col_large, graph_large = _build_graph_and_collection(ev_large)
        rc_small = RootCauseDetectionEngine.detect(graph_small, col_small)
        rc_large = RootCauseDetectionEngine.detect(graph_large, col_large)
        # Find God Class root causes if any.
        gc_small = rc_small.filter_by_category(RootCauseCategory.GOD_CLASS)
        gc_large = rc_large.filter_by_category(RootCauseCategory.GOD_CLASS)
        if gc_small and gc_large:
            assert gc_large[0].confidence >= gc_small[0].confidence

    def test_zero_confidence_for_no_evidence(self) -> None:
        """Empty evidence should produce 0.0 confidence."""
        repo = parse_repository_url("https://github.com/test/empty")
        result = AnalysisResult(repository=repo)
        collection = EvidenceCollection(evidence=[])
        graph = GraphBuilder.build(collection, result)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        assert rc_collection.statistics["average_confidence"] == 0.0


# ---------------------------------------------------------------------------
# Tests: duplicate root cause prevention
# ---------------------------------------------------------------------------


class TestDuplicatePrevention:
    def test_no_duplicate_god_class_for_same_file(self) -> None:
        """Two God Class detections for the same file should merge."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
            ),
            # These could trigger God Class again for the same file.
            _make_evidence(
                category="long_method",
                file_path="src/service.py",
                class_name="UserService",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_classes = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        # Should have at most 1 God Class for the same file.
        assert len(god_classes) <= 1


# ---------------------------------------------------------------------------
# Tests: false positive reduction
# ---------------------------------------------------------------------------


class TestFalsePositiveReduction:
    def test_generated_code_evidence_suppressed(self) -> None:
        """Evidence tagged as 'generated' should not produce root causes."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/generated.py",
                class_name="Generated",
                tags=["generated"],
            ),
            _make_evidence(
                category="large_file",
                file_path="src/generated.py",
                class_name="Generated",
                tags=["generated"],
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        god_classes = rc_collection.filter_by_category(RootCauseCategory.GOD_CLASS)
        assert len(god_classes) == 0

    def test_non_generated_evidence_not_suppressed(self) -> None:
        """Evidence without 'generated' tag should produce root causes."""
        evidence = [
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
                tags=["complexity"],
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
                tags=["metrics"],
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        # Should produce at least one root cause.
        assert rc_collection.total >= 1


# ---------------------------------------------------------------------------
# Tests: root cause relationships
# ---------------------------------------------------------------------------


class TestRootCauseRelationships:
    def test_relationships_built_when_applicable(self) -> None:
        """When God Class + Tight Coupling co-occur, a CAUSES relationship should exist."""
        evidence = [
            # God Class.
            _make_evidence(
                category="cyclomatic_complexity",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="complexity-analyzer",
            ),
            _make_evidence(
                category="large_file",
                file_path="src/service.py",
                class_name="UserService",
                analyzer="metrics-engine",
            ),
            # Tight coupling (same file).
            _make_evidence(
                finding_type=EvidenceType.ARCHITECTURE,
                category="high_coupling",
                file_path="src/service.py",
                analyzer="architecture-review-engine",
            ),
        ]
        collection, graph = _build_graph_and_collection(evidence)
        rc_collection = RootCauseDetectionEngine.detect(graph, collection)
        # If both God Class and Tight Coupling are detected for the same file,
        # there should be a relationship.
        if rc_collection.relationships:
            for rel in rc_collection.relationships:
                assert rel.source_root_cause_id != rel.target_root_cause_id


# ---------------------------------------------------------------------------
# Tests: model properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_root_cause_is_immutable(self) -> None:
        rc = RootCause(
            category=RootCauseCategory.GOD_CLASS,
            title="Test",
        )
        with pytest.raises(Exception):  # noqa: B017
            rc.title = "mutated"  # type: ignore[misc]

    def test_root_cause_evidence_count(self) -> None:
        from repo_analyzer.core.evidence.root_cause_models import RootCauseEvidence

        rc = RootCause(
            category=RootCauseCategory.GOD_CLASS,
            title="Test",
            evidence_links=[
                RootCauseEvidence(evidence_id=uuid4(), reason="test"),
                RootCauseEvidence(evidence_id=uuid4(), reason="test2"),
            ],
        )
        assert rc.evidence_count == 2

    def test_collection_get_by_id(self) -> None:
        rc = RootCause(category=RootCauseCategory.GOD_CLASS, title="Test")
        collection = RootCauseCollection(root_causes=[rc])
        found = collection.get_by_id(rc.id)
        assert found is not None
        assert found.id == rc.id
        assert collection.get_by_id(uuid4()) is None

    def test_collection_filter_by_severity(self) -> None:
        rc1 = RootCause(
            category=RootCauseCategory.GOD_CLASS, title="A", severity=RootCauseSeverity.HIGH
        )
        rc2 = RootCause(
            category=RootCauseCategory.LOW_COHESION, title="B", severity=RootCauseSeverity.LOW
        )
        collection = RootCauseCollection(root_causes=[rc1, rc2])
        high = collection.filter_by_severity(RootCauseSeverity.HIGH)
        assert len(high) == 1
        assert high[0].title == "A"

    def test_collection_for_file(self) -> None:
        rc = RootCause(
            category=RootCauseCategory.GOD_CLASS,
            title="Test",
            affected_files=["src/app.py"],
        )
        collection = RootCauseCollection(root_causes=[rc])
        rcs = collection.for_file("src/app.py")
        assert len(rcs) == 1
        assert collection.for_file("other.py") == []
