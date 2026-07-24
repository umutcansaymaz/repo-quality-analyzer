"""Engineering Knowledge Graph domain models.

The Knowledge Graph layer provides an **in-memory graph representation** of
the engineering relationships within a repository. It is built from the
:class:`EvidenceCollection` and the structured :class:`AnalysisResult`
outputs — no repository re-parsing, no AST re-generation.

Design principles:
    - **Immutable**: All models use ``frozen=True`` (Pydantic equivalent of
      ``@dataclass(frozen=True)``).
    - **Lightweight**: Pure Python dicts + UUIDs; no external graph database.
    - **Indexed**: O(1) lookup by node id, file path, symbol, evidence id,
      analyzer name.
    - **Queryable**: Rich API for traversing relationships — "all evidence
      for this file", "all dependencies of this class", etc.

Integration:
    - :class:`EngineeringGraph` is attached to :class:`AnalysisResult`
      via the optional ``knowledge_graph`` field (backward compatible —
      defaults to ``None``).
    - :class:`GraphBuilder` reads an :class:`EvidenceCollection` plus the
      :class:`AnalysisResult` and produces an :class:`EngineeringGraph`.
    - No evidence builder, analyzer, or review engine is modified.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class NodeType(str, Enum):
    """The kind of entity represented by a graph node.

    Each value corresponds to a structural or semantic element in the
    repository's engineering model.
    """

    REPOSITORY = "repository"
    PACKAGE = "package"
    MODULE = "module"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    SYMBOL = "symbol"
    DEPENDENCY = "dependency"
    SECURITY_FINDING = "security_finding"
    ARCHITECTURE_FINDING = "architecture_finding"
    METRIC_FINDING = "metric_finding"
    EVIDENCE = "evidence"


class EdgeType(str, Enum):
    """The kind of relationship represented by a directed graph edge.

    Edges are directed: ``source → target``. The direction follows
    natural dependency flow — e.g. ``File A IMPORTS Module B`` means
    ``A`` depends on ``B``.
    """

    IMPORTS = "imports"
    CALLS = "calls"
    DEPENDS_ON = "depends_on"
    BELONGS_TO = "belongs_to"
    REFERENCES = "references"
    USES = "uses"
    AFFECTS = "affects"
    REPORTS = "reports"
    DERIVED_FROM = "derived_from"
    RELATED_TO = "related_to"


class GraphNode(BaseModel):
    """A single node in the engineering knowledge graph.

    Each node represents a structural element (file, class, function) or
    a finding (evidence, security issue, metric). The ``label`` is the
    human-readable identifier; ``key`` is the unique natural key used for
    deduplication.

    Immutability:
        Configured with ``frozen=True`` so nodes cannot be mutated after
        creation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    node_type: NodeType
    label: str = Field(description="Human-readable identifier (file path, class name, …).")
    key: str = Field(description="Unique natural key for deduplication.")
    file_path: str | None = None
    line: int | None = None
    module: str | None = None
    class_name: str | None = None
    function_name: str | None = None
    severity: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_id: UUID | None = Field(
        default=None,
        description="Link to the Evidence object when node_type is EVIDENCE or a finding type.",
    )


class GraphEdge(BaseModel):
    """A directed edge between two graph nodes.

    Edges represent engineering relationships: imports, calls, belongs-to,
    affects, reports, etc.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    edge_type: EdgeType
    detail: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphIndex(BaseModel):
    """Pre-built lookup indexes for O(1) / O(log n) graph queries.

    All indexes map a natural key (file path, function name, etc.) to
    a list of node UUIDs. This avoids linear scans during common queries.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    #: Node ID → GraphNode.
    by_node_id: dict[UUID, GraphNode] = Field(default_factory=dict)

    #: File path → list of node IDs.
    by_file: dict[str, list[UUID]] = Field(default_factory=dict)

    #: Function name → list of node IDs.
    by_function: dict[str, list[UUID]] = Field(default_factory=dict)

    #: Class name → list of node IDs.
    by_class: dict[str, list[UUID]] = Field(default_factory=dict)

    #: Evidence ID → node ID.
    by_evidence: dict[UUID, UUID] = Field(default_factory=dict)

    #: Analyzer name → list of node IDs.
    by_analyzer: dict[str, list[UUID]] = Field(default_factory=dict)

    #: Node type → list of node IDs.
    by_type: dict[str, list[UUID]] = Field(default_factory=dict)

    #: Natural key → node ID (deduplication).
    by_key: dict[str, UUID] = Field(default_factory=dict)

    #: Adjacency list: source node ID → list of outgoing edges.
    outgoing: dict[UUID, list[GraphEdge]] = Field(default_factory=dict)

    #: Reverse adjacency: target node ID → list of incoming edges.
    incoming: dict[UUID, list[GraphEdge]] = Field(default_factory=dict)


class EngineeringGraph(BaseModel):
    """An immutable engineering knowledge graph.

    The graph is built by :class:`GraphBuilder` from an
    :class:`EvidenceCollection` and the structured outputs of
    :class:`AnalysisResult`.

    Structure:
        - ``nodes``: list of all :class:`GraphNode` objects.
        - ``edges``: list of all :class:`GraphEdge` objects.
        - ``index``: pre-built :class:`GraphIndex` for fast queries.

    Querying:
        The graph provides a rich API for traversing relationships — see
        :meth:`evidence_for_file`, :meth:`dependencies_of`, :meth:`security_findings_in`,
        :meth:`metrics_for_module`, :meth:`symbol_of_evidence`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    index: GraphIndex = Field(default_factory=GraphIndex)
    statistics: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_nodes(self) -> int:
        """Total number of nodes in the graph."""
        return len(self.nodes)

    @property
    def total_edges(self) -> int:
        """Total number of edges in the graph."""
        return len(self.edges)

    # ------------------------------------------------------------------
    # Node queries
    # ------------------------------------------------------------------

    def get_node(self, node_id: UUID) -> GraphNode | None:
        """Look up a node by ID — O(1)."""
        return self.index.by_node_id.get(node_id)

    def nodes_for_file(self, file_path: str) -> list[GraphNode]:
        """Return all nodes associated with a file — O(1) + O(k)."""
        ids = self.index.by_file.get(file_path, [])
        return [self.index.by_node_id[nid] for nid in ids if nid in self.index.by_node_id]

    def nodes_for_function(self, function_name: str) -> list[GraphNode]:
        """Return all nodes for a function — O(1) + O(k)."""
        ids = self.index.by_function.get(function_name, [])
        return [self.index.by_node_id[nid] for nid in ids if nid in self.index.by_node_id]

    def nodes_for_class(self, class_name: str) -> list[GraphNode]:
        """Return all nodes for a class — O(1) + O(k)."""
        ids = self.index.by_class.get(class_name, [])
        return [self.index.by_node_id[nid] for nid in ids if nid in self.index.by_node_id]

    def node_for_evidence(self, evidence_id: UUID) -> GraphNode | None:
        """Return the graph node linked to an evidence item — O(1)."""
        node_id = self.index.by_evidence.get(evidence_id)
        if node_id is None:
            return None
        return self.index.by_node_id.get(node_id)

    def nodes_by_type(self, node_type: NodeType) -> list[GraphNode]:
        """Return all nodes of a given type — O(1) + O(k)."""
        ids = self.index.by_type.get(node_type.value, [])
        return [self.index.by_node_id[nid] for nid in ids if nid in self.index.by_node_id]

    def nodes_by_analyzer(self, analyzer: str) -> list[GraphNode]:
        """Return all nodes produced by a given analyzer — O(1) + O(k)."""
        ids = self.index.by_analyzer.get(analyzer, [])
        return [self.index.by_node_id[nid] for nid in ids if nid in self.index.by_node_id]

    # ------------------------------------------------------------------
    # Edge queries
    # ------------------------------------------------------------------

    def outgoing_edges(self, node_id: UUID) -> list[GraphEdge]:
        """Return all edges leaving ``node_id`` — O(1) + O(k)."""
        return self.index.outgoing.get(node_id, [])

    def incoming_edges(self, node_id: UUID) -> list[GraphEdge]:
        """Return all edges entering ``node_id`` — O(1) + O(k)."""
        return self.index.incoming.get(node_id, [])

    def neighbors(self, node_id: UUID, edge_type: EdgeType | None = None) -> list[GraphNode]:
        """Return all neighbor nodes reachable from ``node_id``.

        Args:
            node_id: The starting node.
            edge_type: Optional filter — only follow edges of this type.

        Returns:
            A list of :class:`GraphNode` objects.
        """
        result: list[GraphNode] = []
        for edge in self.outgoing_edges(node_id):
            if edge_type is not None and edge.edge_type != edge_type:
                continue
            node = self.get_node(edge.target_id)
            if node is not None:
                result.append(node)
        return result

    def reverse_neighbors(
        self, node_id: UUID, edge_type: EdgeType | None = None
    ) -> list[GraphNode]:
        """Return all nodes that have an edge pointing to ``node_id``."""
        result: list[GraphNode] = []
        for edge in self.incoming_edges(node_id):
            if edge_type is not None and edge.edge_type != edge_type:
                continue
            node = self.get_node(edge.source_id)
            if node is not None:
                result.append(node)
        return result

    # ------------------------------------------------------------------
    # High-level engineering queries
    # ------------------------------------------------------------------

    def evidence_for_file(self, file_path: str) -> list[GraphNode]:
        """Return all EVIDENCE-type nodes associated with a file.

        This answers: "What evidence was found in this file?"
        """
        file_nodes = self.nodes_for_file(file_path)
        file_node_ids = {n.id for n in file_nodes}
        evidence_nodes: list[GraphNode] = []
        for node in file_nodes:
            if node.node_type == NodeType.EVIDENCE:
                evidence_nodes.append(node)
        # Also check evidence nodes that REPORTS or AFFECTS this file.
        for fn_id in file_node_ids:
            for edge in self.incoming_edges(fn_id):
                if edge.edge_type in (EdgeType.REPORTS, EdgeType.AFFECTS):
                    src = self.get_node(edge.source_id)
                    if src is not None and src not in evidence_nodes:
                        evidence_nodes.append(src)
        return evidence_nodes

    def dependencies_of(self, node_id: UUID) -> list[GraphNode]:
        """Return all dependencies of a node (DEPENDS_ON + IMPORTS edges).

        This answers: "What does this class/file/module depend on?"
        """
        result: list[GraphNode] = []
        for edge in self.outgoing_edges(node_id):
            if edge.edge_type in (EdgeType.DEPENDS_ON, EdgeType.IMPORTS):
                node = self.get_node(edge.target_id)
                if node is not None:
                    result.append(node)
        return result

    def security_findings_in(self, node_id: UUID) -> list[GraphNode]:
        """Return all security-finding nodes that AFFECT or REPORTS on a node.

        This answers: "What security findings are in this function/file?"
        """
        result: list[GraphNode] = []
        for edge in self.incoming_edges(node_id):
            if edge.edge_type in (EdgeType.AFFECTS, EdgeType.REPORTS):
                src = self.get_node(edge.source_id)
                if src is not None and src.node_type in (
                    NodeType.SECURITY_FINDING,
                    NodeType.EVIDENCE,
                ):
                    result.append(src)
        return result

    def metrics_for_node(self, node_id: UUID) -> list[GraphNode]:
        """Return all metric-finding nodes that REPORTS on a node.

        This answers: "What metrics are associated with this file/module?"
        """
        result: list[GraphNode] = []
        for edge in self.incoming_edges(node_id):
            if edge.edge_type == EdgeType.REPORTS:
                src = self.get_node(edge.source_id)
                if src is not None and src.node_type == NodeType.METRIC_FINDING:
                    result.append(src)
        return result

    def symbol_of_evidence(self, evidence_id: UUID) -> GraphNode | None:
        """Return the symbol/function/class node an evidence item belongs to.

        This answers: "Which symbol does this evidence point to?"
        """
        ev_node = self.node_for_evidence(evidence_id)
        if ev_node is None:
            return None
        # Follow AFFECTS / REPORTS edges from the evidence node.
        for edge in self.outgoing_edges(ev_node.id):
            if edge.edge_type in (EdgeType.AFFECTS, EdgeType.REPORTS, EdgeType.DERIVED_FROM):
                target = self.get_node(edge.target_id)
                if target is not None and target.node_type in (
                    NodeType.FUNCTION,
                    NodeType.CLASS,
                    NodeType.METHOD,
                    NodeType.SYMBOL,
                    NodeType.FILE,
                    NodeType.MODULE,
                ):
                    return target
        return None

    def files_of_module(self, module_name: str) -> list[GraphNode]:
        """Return all FILE nodes that BELONGS_TO a module.

        This answers: "Which files are in this module?"
        """
        module_nodes = [n for n in self.nodes_by_type(NodeType.MODULE) if n.label == module_name]
        result: list[GraphNode] = []
        for mod_node in module_nodes:
            for edge in self.incoming_edges(mod_node.id):
                if edge.edge_type == EdgeType.BELONGS_TO:
                    src = self.get_node(edge.source_id)
                    if src is not None and src.node_type == NodeType.FILE:
                        result.append(src)
        return result

    # ------------------------------------------------------------------
    # Graph traversal (BFS, limited depth)
    # ------------------------------------------------------------------

    def traverse(
        self,
        start_id: UUID,
        max_depth: int = 3,
        edge_types: set[EdgeType] | None = None,
    ) -> list[GraphNode]:
        """Breadth-first traversal from ``start_id`` up to ``max_depth``.

        Args:
            start_id: The starting node.
            max_depth: Maximum traversal depth.
            edge_types: Optional set of edge types to follow. If ``None``,
                all edge types are followed.

        Returns:
            A list of reachable :class:`GraphNode` objects (excluding the
            start node).
        """
        visited: set[UUID] = {start_id}
        result: list[GraphNode] = []
        current_level: list[UUID] = [start_id]
        for _depth in range(max_depth):
            next_level: list[UUID] = []
            for nid in current_level:
                for edge in self.outgoing_edges(nid):
                    if edge_types is not None and edge.edge_type not in edge_types:
                        continue
                    if edge.target_id not in visited:
                        visited.add(edge.target_id)
                        node = self.get_node(edge.target_id)
                        if node is not None:
                            result.append(node)
                        next_level.append(edge.target_id)
            current_level = next_level
            if not current_level:
                break
        return result


__all__ = [
    "EdgeType",
    "EngineeringGraph",
    "GraphEdge",
    "GraphIndex",
    "GraphNode",
    "NodeType",
]
