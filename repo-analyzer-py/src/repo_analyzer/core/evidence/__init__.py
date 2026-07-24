"""Evidence Engine package.

Provides a unified representation of all findings produced by the analysis
pipeline. See :mod:`repo_analyzer.core.evidence.models` for the domain
models and :mod:`repo_analyzer.core.evidence.builder` for the builder.
"""

from __future__ import annotations

from repo_analyzer.core.evidence.builder import EvidenceBuilder
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
    "Evidence",
    "EvidenceBuilder",
    "EvidenceCollection",
    "EvidenceReference",
    "EvidenceRelationship",
    "EvidenceType",
    "ReferenceKind",
    "RelationshipType",
]
