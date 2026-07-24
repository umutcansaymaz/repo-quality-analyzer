"""Engineering Knowledge Graph Builder.

Transforms an :class:`EvidenceCollection` (plus the structured
:class:`AnalysisResult` outputs) into an :class:`EngineeringGraph`.

Design:
    - **Read-only**: The builder never modifies the input data.
    - **No I/O**: No repository re-parsing; all data comes from the
      in-memory evidence collection and analysis result.
    - **Deduplicating**: Nodes are deduplicated by a natural ``key`` —
      the same file/class/function never produces two nodes.
    - **Edge-rich**: Imports, dependencies, belongs-to, affects, reports
      relationships are all derived from the existing data.

Usage::

    from repo_analyzer.core.evidence import GraphBuilder

    graph = GraphBuilder.build(collection, result)
    for node in graph.evidence_for_file("src/app.py"):
        print(node.label, node.node_type)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.evidence.graph_models import (
    EdgeType,
    EngineeringGraph,
    GraphEdge,
    GraphIndex,
    GraphNode,
    NodeType,
)
from repo_analyzer.core.evidence.models import (
    Evidence,
    EvidenceCollection,
    EvidenceType,
)


class GraphBuilder:
    """Build an :class:`EngineeringGraph` from evidence + analysis outputs.

    The builder is stateless and thread-safe. The :meth:`build` method is
    the single entry point.
    """

    @classmethod
    def build(
        cls,
        collection: EvidenceCollection,
        result: AnalysisResult,
    ) -> EngineeringGraph:
        """Transform ``collection`` + ``result`` into an :class:`EngineeringGraph`.

        Args:
            collection: The :class:`EvidenceCollection` from the evidence phase.
            result: The source :class:`AnalysisResult` (for import/dependency
                graphs, symbols, file inventory).

        Returns:
            An :class:`EngineeringGraph` with nodes, edges and indexes.
        """
        builder = cls()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        # Registry of nodes by natural key for deduplication.
        key_registry: dict[str, GraphNode] = {}

        # 1. Structural nodes (repository, files, modules, classes, functions).
        builder._build_repository_node(result, nodes, key_registry)
        builder._build_file_nodes(collection, result, nodes, key_registry)
        builder._build_symbol_nodes(collection, result, nodes, key_registry)
        builder._build_module_nodes(collection, result, nodes, key_registry)
        builder._build_dependency_nodes(collection, result, nodes, key_registry)

        # 2. Evidence / finding nodes.
        builder._build_evidence_nodes(collection, nodes, key_registry)

        # 3. Edges from structural data.
        builder._build_belongs_to_edges(result, nodes, key_registry, edges)
        builder._build_import_edges(result, nodes, key_registry, edges)
        builder._build_dependency_edges(result, nodes, key_registry, edges)
        builder._build_inheritance_edges(result, nodes, key_registry, edges)

        # 4. Edges from evidence (AFFECTS, REPORTS, DERIVED_FROM, RELATED_TO).
        builder._build_evidence_edges(collection, nodes, key_registry, edges)

        # 5. Build indexes.
        index = builder._build_index(nodes, edges)

        # 6. Statistics.
        stats = builder._build_statistics(nodes, edges)

        return EngineeringGraph(nodes=nodes, edges=edges, index=index, statistics=stats)

    # ------------------------------------------------------------------
    # Node builders
    # ------------------------------------------------------------------

    def _build_repository_node(
        self,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create a REPOSITORY node."""
        repo = result.repository
        key = f"repo:{repo.host}/{repo.owner}/{repo.name}"
        node = GraphNode(
            node_type=NodeType.REPOSITORY,
            label=f"{repo.owner}/{repo.name}",
            key=key,
            metadata={"host": repo.host, "url": repo.url},
        )
        nodes.append(node)
        key_registry[key] = node

    def _build_file_nodes(
        self,
        collection: EvidenceCollection,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create FILE nodes for every file referenced in evidence or inventory."""
        file_paths: set[str] = set()
        # From evidence.
        for ev in collection.evidence:
            if ev.file_path:
                file_paths.add(ev.file_path)
        # From file inventory.
        if result.file_inventory:
            for f in result.file_inventory.files:
                file_paths.add(f)
        for fp in sorted(file_paths):
            key = f"file:{fp}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.FILE,
                label=fp,
                key=key,
                file_path=fp,
            )
            nodes.append(node)
            key_registry[key] = node

    def _build_symbol_nodes(
        self,
        collection: EvidenceCollection,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create FUNCTION, CLASS, METHOD nodes from AST symbols."""
        if not result.symbols:
            return
        for func in result.symbols.functions:
            file_path = func.get("file", "")
            name = func.get("name", "")
            if not name:
                continue
            key = f"func:{file_path}:{name}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.FUNCTION,
                label=name,
                key=key,
                file_path=file_path or None,
                line=func.get("line"),
                function_name=name,
            )
            nodes.append(node)
            key_registry[key] = node
        for cls in result.symbols.classes:
            file_path = cls.get("file", "")
            name = cls.get("name", "")
            if not name:
                continue
            key = f"class:{file_path}:{name}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.CLASS,
                label=name,
                key=key,
                file_path=file_path or None,
                line=cls.get("line"),
                class_name=name,
            )
            nodes.append(node)
            key_registry[key] = node
        for method in result.symbols.methods:
            file_path = method.get("file", "")
            name = method.get("name", "")
            if not name:
                continue
            key = f"method:{file_path}:{name}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.METHOD,
                label=name,
                key=key,
                file_path=file_path or None,
                line=method.get("line"),
                function_name=name,
            )
            nodes.append(node)
            key_registry[key] = node

    def _build_module_nodes(
        self,
        collection: EvidenceCollection,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create MODULE nodes from import graph keys."""
        module_names: set[str] = set()
        if result.import_analysis:
            for src in result.import_analysis.import_graph:
                module_names.add(src)
            for dsts in result.import_analysis.import_graph.values():
                module_names.update(dsts)
        for mod in sorted(module_names):
            key = f"module:{mod}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.MODULE,
                label=mod,
                key=key,
                module=mod,
            )
            nodes.append(node)
            key_registry[key] = node

    def _build_dependency_nodes(
        self,
        collection: EvidenceCollection,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create DEPENDENCY nodes from dependency analysis."""
        if not result.dependency_analysis:
            return
        for dep in result.dependency_analysis.dependencies:
            name = dep.get("name", "")
            if not name:
                continue
            ecosystem = dep.get("ecosystem", "")
            key = f"dep:{ecosystem}:{name}"
            if key in key_registry:
                continue
            node = GraphNode(
                node_type=NodeType.DEPENDENCY,
                label=name,
                key=key,
                metadata={
                    "version": dep.get("version", ""),
                    "ecosystem": ecosystem,
                    "direct": dep.get("direct", True),
                },
            )
            nodes.append(node)
            key_registry[key] = node

    def _build_evidence_nodes(
        self,
        collection: EvidenceCollection,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
    ) -> None:
        """Create EVIDENCE / finding nodes from the evidence collection."""
        for ev in collection.evidence:
            key = f"evidence:{ev.id}"
            if key in key_registry:
                continue
            node_type = self._evidence_to_node_type(ev)
            node = GraphNode(
                node_type=node_type,
                label=ev.message,
                key=key,
                file_path=ev.file_path,
                line=ev.line,
                module=ev.module,
                class_name=ev.class_name,
                function_name=ev.function_name,
                severity=ev.severity.value,
                evidence_id=ev.id,
                metadata={
                    "analyzer": ev.analyzer,
                    "finding_type": ev.finding_type.value,
                    "category": ev.category,
                    "confidence": ev.confidence,
                    "tags": ev.tags,
                },
            )
            nodes.append(node)
            key_registry[key] = node

    # ------------------------------------------------------------------
    # Edge builders
    # ------------------------------------------------------------------

    def _build_belongs_to_edges(
        self,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Create BELONGS_TO edges: file → module, class → file, function → file."""
        # File → Repository.
        repo_node = key_registry.get(
            f"repo:{result.repository.host}/{result.repository.owner}/{result.repository.name}"
        )
        if repo_node:
            for node in nodes:
                if node.node_type == NodeType.FILE:
                    edges.append(
                        GraphEdge(
                            source_id=node.id,
                            target_id=repo_node.id,
                            edge_type=EdgeType.BELONGS_TO,
                        )
                    )
        # Function/Class/Method → File.
        for node in nodes:
            if node.node_type in (NodeType.FUNCTION, NodeType.CLASS, NodeType.METHOD):
                if node.file_path:
                    file_node = key_registry.get(f"file:{node.file_path}")
                    if file_node:
                        edges.append(
                            GraphEdge(
                                source_id=node.id,
                                target_id=file_node.id,
                                edge_type=EdgeType.BELONGS_TO,
                            )
                        )
        # File → Module (derive module from path).
        for node in nodes:
            if node.node_type == NodeType.FILE and node.file_path:
                module_name = self._derive_module_from_path(node.file_path)
                if module_name:
                    mod_node = key_registry.get(f"module:{module_name}")
                    if mod_node:
                        edges.append(
                            GraphEdge(
                                source_id=node.id,
                                target_id=mod_node.id,
                                edge_type=EdgeType.BELONGS_TO,
                            )
                        )

    def _build_import_edges(
        self,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Create IMPORTS edges from the import graph."""
        if not result.import_analysis:
            return
        for src, dsts in result.import_analysis.import_graph.items():
            src_node = key_registry.get(f"module:{src}")
            if not src_node:
                continue
            for dst in dsts:
                dst_node = key_registry.get(f"module:{dst}")
                if dst_node and src_node.id != dst_node.id:
                    edges.append(
                        GraphEdge(
                            source_id=src_node.id,
                            target_id=dst_node.id,
                            edge_type=EdgeType.IMPORTS,
                        )
                    )

    def _build_dependency_edges(
        self,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Create DEPENDS_ON edges from the dependency graph."""
        if not result.dependency_analysis:
            return
        for src, dsts in result.dependency_analysis.dependency_graph.items():
            src_node = key_registry.get(f"file:{src}") or key_registry.get(f"module:{src}")
            if not src_node:
                continue
            for dst in dsts:
                # Try to find the dependency node.
                for ek in ("pypi", "npm", "cargo", "go", "composer", "maven", "gradle"):
                    dst_node = key_registry.get(f"dep:{ek}:{dst}")
                    if dst_node:
                        break
                else:
                    dst_node = None
                if dst_node:
                    edges.append(
                        GraphEdge(
                            source_id=src_node.id,
                            target_id=dst_node.id,
                            edge_type=EdgeType.DEPENDS_ON,
                        )
                    )

    def _build_inheritance_edges(
        self,
        result: AnalysisResult,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Create DERIVED_FROM edges from inheritance data."""
        if not result.symbols:
            return
        for inh in result.symbols.inheritances:
            file_path = inh.get("file", "")
            cls_name = inh.get("class", "")
            parent = inh.get("parent", "")
            if not cls_name or not parent:
                continue
            cls_node = key_registry.get(f"class:{file_path}:{cls_name}")
            parent_node = key_registry.get(f"class:{file_path}:{parent}") or key_registry.get(
                f"class::{parent}"
            )
            if cls_node and parent_node:
                edges.append(
                    GraphEdge(
                        source_id=cls_node.id,
                        target_id=parent_node.id,
                        edge_type=EdgeType.DERIVED_FROM,
                    )
                )

    def _build_evidence_edges(
        self,
        collection: EvidenceCollection,
        nodes: list[GraphNode],
        key_registry: dict[str, GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Create AFFECTS / REPORTS / RELATED_TO edges from evidence.

        Each evidence node is linked to:
            - The file it belongs to (AFFECTS).
            - The function/class/symbol it references (AFFECTS / REPORTS).
            - Other evidence it's related to (RELATED_TO).
        """
        # Build a lookup: evidence_id → graph_node.
        ev_to_node: dict[UUID, GraphNode] = {}
        for node in nodes:
            if node.evidence_id is not None:
                ev_to_node[node.evidence_id] = node
        for ev in collection.evidence:
            ev_node = ev_to_node.get(ev.id)
            if ev_node is None:
                continue
            # AFFECTS: evidence → file.
            if ev.file_path:
                file_node = key_registry.get(f"file:{ev.file_path}")
                if file_node and ev_node.id != file_node.id:
                    edges.append(
                        GraphEdge(
                            source_id=ev_node.id,
                            target_id=file_node.id,
                            edge_type=EdgeType.AFFECTS,
                        )
                    )
            # AFFECTS: evidence → function.
            if ev.function_name and ev.file_path:
                func_node = key_registry.get(f"func:{ev.file_path}:{ev.function_name}")
                if func_node and ev_node.id != func_node.id:
                    edges.append(
                        GraphEdge(
                            source_id=ev_node.id,
                            target_id=func_node.id,
                            edge_type=EdgeType.AFFECTS,
                        )
                    )
            # AFFECTS: evidence → class.
            if ev.class_name and ev.file_path:
                cls_node = key_registry.get(f"class:{ev.file_path}:{ev.class_name}")
                if cls_node and ev_node.id != cls_node.id:
                    edges.append(
                        GraphEdge(
                            source_id=ev_node.id,
                            target_id=cls_node.id,
                            edge_type=EdgeType.AFFECTS,
                        )
                    )
            # AFFECTS: evidence → module.
            if ev.module:
                mod_node = key_registry.get(f"module:{ev.module}")
                if mod_node and ev_node.id != mod_node.id:
                    edges.append(
                        GraphEdge(
                            source_id=ev_node.id,
                            target_id=mod_node.id,
                            edge_type=EdgeType.AFFECTS,
                        )
                    )
        # RELATED_TO: evidence relationships.
        for rel in collection.relationships:
            src_node = ev_to_node.get(rel.source_id)
            tgt_node = ev_to_node.get(rel.target_id)
            if src_node and tgt_node:
                edges.append(
                    GraphEdge(
                        source_id=src_node.id,
                        target_id=tgt_node.id,
                        edge_type=EdgeType.RELATED_TO,
                        detail=rel.relationship_type.value,
                    )
                )

    # ------------------------------------------------------------------
    # Index + statistics
    # ------------------------------------------------------------------

    def _build_index(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> GraphIndex:
        """Build the lookup indexes from nodes and edges."""
        by_node_id: dict[UUID, GraphNode] = {}
        by_file: dict[str, list[UUID]] = {}
        by_function: dict[str, list[UUID]] = {}
        by_class: dict[str, list[UUID]] = {}
        by_evidence: dict[UUID, UUID] = {}
        by_analyzer: dict[str, list[UUID]] = {}
        by_type: dict[str, list[UUID]] = {}
        by_key: dict[str, UUID] = {}
        outgoing: dict[UUID, list[GraphEdge]] = {}
        incoming: dict[UUID, list[GraphEdge]] = {}
        for node in nodes:
            by_node_id[node.id] = node
            by_key[node.key] = node.id
            by_type.setdefault(node.node_type.value, []).append(node.id)
            if node.file_path:
                by_file.setdefault(node.file_path, []).append(node.id)
            if node.function_name:
                by_function.setdefault(node.function_name, []).append(node.id)
            if node.class_name:
                by_class.setdefault(node.class_name, []).append(node.id)
            if node.evidence_id is not None:
                by_evidence[node.evidence_id] = node.id
            analyzer = node.metadata.get("analyzer", "")
            if analyzer:
                by_analyzer.setdefault(analyzer, []).append(node.id)
        for edge in edges:
            outgoing.setdefault(edge.source_id, []).append(edge)
            incoming.setdefault(edge.target_id, []).append(edge)
        return GraphIndex(
            by_node_id=by_node_id,
            by_file=by_file,
            by_function=by_function,
            by_class=by_class,
            by_evidence=by_evidence,
            by_analyzer=by_analyzer,
            by_type=by_type,
            by_key=by_key,
            outgoing=outgoing,
            incoming=incoming,
        )

    def _build_statistics(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> dict[str, Any]:
        """Build summary statistics."""
        node_type_counts: dict[str, int] = {}
        for node in nodes:
            node_type_counts[node.node_type.value] = (
                node_type_counts.get(node.node_type.value, 0) + 1
            )
        edge_type_counts: dict[str, int] = {}
        for edge in edges:
            edge_type_counts[edge.edge_type.value] = (
                edge_type_counts.get(edge.edge_type.value, 0) + 1
            )
        return {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_type_counts": node_type_counts,
            "edge_type_counts": edge_type_counts,
            "unique_files": len({n.file_path for n in nodes if n.file_path}),
            "unique_functions": len({n.function_name for n in nodes if n.function_name}),
            "unique_classes": len({n.class_name for n in nodes if n.class_name}),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _evidence_to_node_type(ev: Evidence) -> NodeType:
        """Map an :class:`EvidenceType` to a :class:`NodeType`."""
        mapping = {
            EvidenceType.SECURITY: NodeType.SECURITY_FINDING,
            EvidenceType.CODE_QUALITY: NodeType.EVIDENCE,
            EvidenceType.ARCHITECTURE: NodeType.ARCHITECTURE_FINDING,
            EvidenceType.COMPLEXITY: NodeType.METRIC_FINDING,
            EvidenceType.IMPORT: NodeType.EVIDENCE,
            EvidenceType.DEPENDENCY: NodeType.EVIDENCE,
            EvidenceType.GIT: NodeType.EVIDENCE,
            EvidenceType.DOCUMENTATION: NodeType.EVIDENCE,
            EvidenceType.TEST: NodeType.EVIDENCE,
            EvidenceType.METRIC: NodeType.METRIC_FINDING,
            EvidenceType.SYMBOL: NodeType.SYMBOL,
            EvidenceType.RISK: NodeType.EVIDENCE,
            EvidenceType.TECHNICAL_DEBT: NodeType.EVIDENCE,
            EvidenceType.REFACTOR: NodeType.EVIDENCE,
            EvidenceType.FILE_SYSTEM: NodeType.EVIDENCE,
            EvidenceType.REPOSITORY: NodeType.REPOSITORY,
        }
        return mapping.get(ev.finding_type, NodeType.EVIDENCE)

    @staticmethod
    def _derive_module_from_path(file_path: str) -> str | None:
        """Derive a module name from a file path.

        ``src/repo_analyzer/core/orchestrator.py`` → ``repo_analyzer.core.orchestrator``
        """
        # Strip common source roots.
        cleaned = file_path
        for prefix in ("src/", "lib/", "app/"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
                break
        # Remove extension.
        if "." in cleaned:
            cleaned = cleaned.rsplit(".", 1)[0]
        # Convert path separators to dots.
        module = cleaned.replace("/", ".").replace("\\", ".")
        return module if module else None


__all__ = ["GraphBuilder"]
