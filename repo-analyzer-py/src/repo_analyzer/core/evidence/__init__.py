"""Evidence Engine + Engineering Knowledge Graph package.

Provides:
    - **Evidence models** (:mod:`.models`): unified finding representation.
    - **Evidence builder** (:mod:`.builder`): AnalysisResult → EvidenceCollection.
    - **Graph models** (:mod:`.graph_models`): in-memory engineering graph.
    - **Graph builder** (:mod:`.graph_builder`): EvidenceCollection → EngineeringGraph.
"""

from __future__ import annotations

from repo_analyzer.core.evidence.builder import EvidenceBuilder
from repo_analyzer.core.evidence.graph_builder import GraphBuilder
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
    EvidenceReference,
    EvidenceRelationship,
    EvidenceType,
    ReferenceKind,
    RelationshipType,
)

__all__ = [
    # Evidence models
    "Evidence",
    "EvidenceBuilder",
    "EvidenceCollection",
    "EvidenceReference",
    "EvidenceRelationship",
    "EvidenceType",
    "ReferenceKind",
    "RelationshipType",
    # Graph models
    "EdgeType",
    "EngineeringGraph",
    "GraphBuilder",
    "GraphEdge",
    "GraphIndex",
    "GraphNode",
    "NodeType",
]
