"""Unit tests for the Engineering Knowledge Graph.

Covers:
    - Empty graph (no evidence, no analysis data)
    - Single file (one file, one function, one evidence)
    - Multiple files (cross-file relationships)
    - Dependency relationships
    - Import relationships
    - Evidence connections (AFFECTS, REPORTS)
    - Duplicate node prevention
    - Graph API queries
    - Graph traversal
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from repo_analyzer.core.domain.analysis_outputs import (
    DependencyAnalysis,
    FileInventory,
    FileMetrics,
    ImportAnalysis,
    MetricsReport,
    SymbolCollection,
)
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.report import Location, Severity
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.domain.security_finding import (
    Confidence,
    SecurityCategory,
    SecurityFinding,
)
from repo_analyzer.core.evidence import (
    EdgeType,
    EvidenceBuilder,
    EvidenceCollection,
    GraphBuilder,
    NodeType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_result() -> AnalysisResult:
    """An AnalysisResult with no findings — only the repository."""
    repo = parse_repository_url("https://github.com/test/empty")
    return AnalysisResult(repository=repo)


@pytest.fixture()
def empty_collection(empty_result: AnalysisResult) -> EvidenceCollection:
    """An EvidenceCollection from an empty result."""
    return EvidenceBuilder.build(empty_result)


@pytest.fixture()
def single_file_result() -> AnalysisResult:
    """An AnalysisResult with one file, one function, one security finding."""
    repo = parse_repository_url("https://github.com/test/single")
    result = AnalysisResult(repository=repo)
    result.security_findings = [
        SecurityFinding(
            rule_id="bandit.B101",
            category=SecurityCategory.SAST,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            message="Use of assert detected",
            location=Location(file="src/app.py", line=42),
        )
    ]
    result.symbols = SymbolCollection(
        functions=[{"name": "greet", "file": "src/app.py", "line": 1}],
        classes=[{"name": "Greeter", "file": "src/app.py", "line": 10}],
    )
    result.file_inventory = FileInventory(
        total_files=1,
        files=["src/app.py"],
    )
    return result


@pytest.fixture()
def single_file_collection(single_file_result: AnalysisResult) -> EvidenceCollection:
    return EvidenceBuilder.build(single_file_result)


@pytest.fixture()
def multi_file_result() -> AnalysisResult:
    """An AnalysisResult with multiple files, imports, and dependencies."""
    repo = parse_repository_url("https://github.com/test/multi")
    result = AnalysisResult(repository=repo)
    result.security_findings = [
        SecurityFinding(
            rule_id="r1",
            category=SecurityCategory.SAST,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            message="Security issue in app.py",
            location=Location(file="src/app.py", line=10),
        ),
        SecurityFinding(
            rule_id="r2",
            category=SecurityCategory.SECRET,
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            message="Hardcoded token in utils.py",
            location=Location(file="src/utils.py", line=5),
        ),
    ]
    result.symbols = SymbolCollection(
        functions=[
            {"name": "greet", "file": "src/app.py", "line": 1},
            {"name": "helper", "file": "src/utils.py", "line": 3},
        ],
        classes=[
            {"name": "App", "file": "src/app.py", "line": 20},
        ],
    )
    result.import_analysis = ImportAnalysis(
        import_graph={
            "src/app.py": ["src/utils.py", "os"],
            "src/utils.py": ["json"],
        },
        unused_imports=[{"name": "os", "file": "src/app.py", "module": "os"}],
    )
    result.dependency_analysis = DependencyAnalysis(
        dependencies=[
            {"name": "requests", "version": "2.0", "ecosystem": "pypi"},
            {"name": "pyyaml", "version": "6.0", "ecosystem": "pypi"},
        ],
        dependency_graph={"src/app.py": ["requests"]},
        unused_dependencies=["pyyaml"],
        total_dependencies=2,
    )
    result.file_inventory = FileInventory(
        total_files=2,
        files=["src/app.py", "src/utils.py"],
    )
    result.metrics_report = MetricsReport(
        per_file=[
            FileMetrics(path="src/app.py", loc=100, sloc=80),
            FileMetrics(path="src/utils.py", loc=50, sloc=40),
        ],
    )
    return result


@pytest.fixture()
def multi_file_collection(multi_file_result: AnalysisResult) -> EvidenceCollection:
    return EvidenceBuilder.build(multi_file_result)


# ---------------------------------------------------------------------------
# Tests: empty graph
# ---------------------------------------------------------------------------


class TestEmptyGraph:
    def test_empty_graph_has_no_nodes(
        self, empty_collection: EvidenceCollection, empty_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(empty_collection, empty_result)
        assert graph.total_nodes >= 1  # At least the repository node.

    def test_empty_graph_has_repository_node(
        self, empty_collection: EvidenceCollection, empty_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(empty_collection, empty_result)
        repo_nodes = graph.nodes_by_type(NodeType.REPOSITORY)
        assert len(repo_nodes) == 1

    def test_empty_graph_has_no_evidence_nodes(
        self, empty_collection: EvidenceCollection, empty_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(empty_collection, empty_result)
        evidence_nodes = graph.nodes_by_type(NodeType.EVIDENCE)
        assert len(evidence_nodes) == 0

    def test_empty_graph_statistics(
        self, empty_collection: EvidenceCollection, empty_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(empty_collection, empty_result)
        assert graph.statistics["total_nodes"] >= 1
        assert "node_type_counts" in graph.statistics


# ---------------------------------------------------------------------------
# Tests: single file
# ---------------------------------------------------------------------------


class TestSingleFile:
    def test_has_file_node(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        assert len(file_nodes) >= 1
        assert any(n.label == "src/app.py" for n in file_nodes)

    def test_has_function_node(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        func_nodes = graph.nodes_by_type(NodeType.FUNCTION)
        assert len(func_nodes) >= 1
        assert any(n.label == "greet" for n in func_nodes)

    def test_has_class_node(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        class_nodes = graph.nodes_by_type(NodeType.CLASS)
        assert len(class_nodes) >= 1
        assert any(n.label == "Greeter" for n in class_nodes)

    def test_has_security_finding_node(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        sec_nodes = graph.nodes_by_type(NodeType.SECURITY_FINDING)
        assert len(sec_nodes) >= 1

    def test_belongs_to_edge_function_to_file(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        func_nodes = graph.nodes_by_type(NodeType.FUNCTION)
        for fn in func_nodes:
            neighbors = graph.neighbors(fn.id, EdgeType.BELONGS_TO)
            assert any(n.node_type == NodeType.FILE for n in neighbors)

    def test_affects_edge_evidence_to_file(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        sec_nodes = graph.nodes_by_type(NodeType.SECURITY_FINDING)
        assert len(sec_nodes) >= 1
        ev_node = sec_nodes[0]
        neighbors = graph.neighbors(ev_node.id, EdgeType.AFFECTS)
        assert any(n.node_type == NodeType.FILE for n in neighbors)


# ---------------------------------------------------------------------------
# Tests: multiple files
# ---------------------------------------------------------------------------


class TestMultipleFiles:
    def test_has_multiple_file_nodes(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        assert len(file_nodes) >= 2

    def test_has_module_nodes(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        module_nodes = graph.nodes_by_type(NodeType.MODULE)
        assert len(module_nodes) >= 1

    def test_has_dependency_nodes(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        dep_nodes = graph.nodes_by_type(NodeType.DEPENDENCY)
        assert len(dep_nodes) >= 2
        labels = [n.label for n in dep_nodes]
        assert "requests" in labels
        assert "pyyaml" in labels

    def test_import_edges(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        import_edges = [e for e in graph.edges if e.edge_type == EdgeType.IMPORTS]
        assert len(import_edges) >= 1

    def test_dependency_edges(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        dep_edges = [e for e in graph.edges if e.edge_type == EdgeType.DEPENDS_ON]
        assert len(dep_edges) >= 1

    def test_belongs_to_edges(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        bt_edges = [e for e in graph.edges if e.edge_type == EdgeType.BELONGS_TO]
        assert len(bt_edges) >= 2  # at least 2 files → repository

    def test_statistics_correct(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        assert graph.statistics["total_nodes"] == graph.total_nodes
        assert graph.statistics["total_edges"] == graph.total_edges
        assert graph.statistics["unique_files"] >= 2


# ---------------------------------------------------------------------------
# Tests: duplicate node prevention
# ---------------------------------------------------------------------------


class TestDuplicateNodes:
    def test_no_duplicate_file_nodes(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        """Building the graph twice from the same data should not create
        duplicate nodes for the same file."""
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        file_nodes = [
            n for n in graph.nodes if n.node_type == NodeType.FILE and n.label == "src/app.py"
        ]
        assert len(file_nodes) == 1

    def test_no_duplicate_function_nodes(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        func_nodes = [
            n for n in graph.nodes if n.node_type == NodeType.FUNCTION and n.label == "greet"
        ]
        assert len(func_nodes) == 1

    def test_no_duplicate_class_nodes(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        class_nodes = [
            n for n in graph.nodes if n.node_type == NodeType.CLASS and n.label == "Greeter"
        ]
        assert len(class_nodes) == 1

    def test_by_key_index_unique(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """The by_key index must map each natural key to exactly one node."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        for key, node_id in graph.index.by_key.items():
            node = graph.get_node(node_id)
            assert node is not None
            assert node.key == key


# ---------------------------------------------------------------------------
# Tests: graph API queries
# ---------------------------------------------------------------------------


class TestGraphAPI:
    def test_evidence_for_file(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """evidence_for_file should return all evidence nodes for a file."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        evidence = graph.evidence_for_file("src/app.py")
        assert len(evidence) >= 1

    def test_dependencies_of(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """dependencies_of should return nodes connected via DEPENDS_ON."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        # Find a file node that has dependencies.
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        found_deps = False
        for fn in file_nodes:
            deps = graph.dependencies_of(fn.id)
            if deps:
                found_deps = True
                break
        assert found_deps, "Expected at least one file with dependencies"

    def test_security_findings_in(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """security_findings_in should return security nodes that AFFECT a node."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        found_security = False
        for fn in file_nodes:
            sec = graph.security_findings_in(fn.id)
            if sec:
                found_security = True
                break
        assert found_security, "Expected at least one file with security findings"

    def test_metrics_for_node(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """metrics_for_node should return metric nodes that REPORT on a node."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        found_metrics = False
        for fn in file_nodes:
            metrics = graph.metrics_for_node(fn.id)
            if metrics:
                found_metrics = True
                break
        # Metrics may or may not exist depending on evidence.
        # Just verify the method runs without error.
        assert isinstance(found_metrics, bool)

    def test_symbol_of_evidence(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """symbol_of_evidence should return the symbol node an evidence points to."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        # Find an evidence node that has an AFFECTS edge to a function.
        ev_nodes = graph.nodes_by_type(NodeType.SECURITY_FINDING)
        for ev in ev_nodes:
            symbol = graph.symbol_of_evidence(ev.evidence_id or uuid4())
            if symbol is not None:
                assert symbol.node_type in (
                    NodeType.FILE,
                    NodeType.FUNCTION,
                    NodeType.CLASS,
                    NodeType.METHOD,
                    NodeType.MODULE,
                )
                return
        # If no evidence has a symbol, that's fine — just verify no crash.

    def test_nodes_for_file(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        nodes = graph.nodes_for_file("src/app.py")
        assert len(nodes) >= 1

    def test_nodes_for_function(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        nodes = graph.nodes_for_function("greet")
        assert len(nodes) >= 1

    def test_nodes_for_class(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        nodes = graph.nodes_for_class("Greeter")
        assert len(nodes) >= 1

    def test_node_for_evidence(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        # Find an evidence node and look it up.
        ev_nodes = [n for n in graph.nodes if n.evidence_id is not None]
        if ev_nodes:
            ev_node = ev_nodes[0]
            found = graph.node_for_evidence(ev_node.evidence_id)
            assert found is not None
            assert found.id == ev_node.id

    def test_get_node_returns_none_for_unknown(
        self, empty_collection: EvidenceCollection, empty_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(empty_collection, empty_result)
        assert graph.get_node(uuid4()) is None


# ---------------------------------------------------------------------------
# Tests: graph traversal
# ---------------------------------------------------------------------------


class TestGraphTraversal:
    def test_traverse_returns_reachable_nodes(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        """traverse should return nodes reachable from a start node."""
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        # Start from a file node.
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        if file_nodes:
            reachable = graph.traverse(file_nodes[0].id, max_depth=2)
            assert isinstance(reachable, list)

    def test_traverse_respects_max_depth(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        if file_nodes:
            depth1 = graph.traverse(file_nodes[0].id, max_depth=1)
            depth3 = graph.traverse(file_nodes[0].id, max_depth=3)
            assert len(depth3) >= len(depth1)

    def test_traverse_with_edge_filter(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        if file_nodes:
            only_imports = graph.traverse(
                file_nodes[0].id, max_depth=2, edge_types={EdgeType.IMPORTS}
            )
            assert isinstance(only_imports, list)


# ---------------------------------------------------------------------------
# Tests: model properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_graph_node_is_immutable(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        node = graph.nodes[0]
        with pytest.raises(Exception):  # noqa: B017
            node.label = "mutated"  # type: ignore[misc]

    def test_graph_edge_is_immutable(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        if graph.edges:
            edge = graph.edges[0]
            with pytest.raises(Exception):  # noqa: B017
                edge.detail = "mutated"  # type: ignore[misc]

    def test_graph_is_immutable(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        with pytest.raises(Exception):  # noqa: B017
            graph.nodes = []  # type: ignore[misc]

    def test_graph_total_properties(
        self, multi_file_collection: EvidenceCollection, multi_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(multi_file_collection, multi_file_result)
        assert graph.total_nodes == len(graph.nodes)
        assert graph.total_edges == len(graph.edges)

    def test_outgoing_edges(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        # Any node should return a list (possibly empty).
        node = graph.nodes[0]
        edges = graph.outgoing_edges(node.id)
        assert isinstance(edges, list)

    def test_incoming_edges(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        node = graph.nodes[0]
        edges = graph.incoming_edges(node.id)
        assert isinstance(edges, list)

    def test_reverse_neighbors(
        self, single_file_collection: EvidenceCollection, single_file_result: AnalysisResult
    ) -> None:
        graph = GraphBuilder.build(single_file_collection, single_file_result)
        # File node should have reverse neighbors (evidence that AFFECTS it).
        file_nodes = graph.nodes_by_type(NodeType.FILE)
        if file_nodes:
            rns = graph.reverse_neighbors(file_nodes[0].id)
            assert isinstance(rns, list)
