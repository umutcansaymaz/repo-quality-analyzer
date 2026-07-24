"""Code-quality issue domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.report import Finding, Location, Severity


class IssueType(str, Enum):
    """Types of code-quality issues."""

    COMPLEXITY = "complexity"
    DUPLICATION = "duplication"
    DEAD_CODE = "dead_code"
    CODE_SMELL = "code_smell"
    ANTI_PATTERN = "anti_pattern"
    NAMING = "naming"
    DOCUMENTATION = "documentation"
    STYLE = "style"
    OTHER = "other"


class Issue(BaseModel):
    """A code-quality issue (non-security).

    Issues are produced by quality analyzers such as complexity, duplication
    and documentation analyzers.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    type: IssueType
    severity: Severity
    location: Location | None = None
    message: str
    code_snippet: str | None = None
    suggestion: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_finding(self, rule_id: str | None = None) -> Finding:
        """Convert this issue to a generic :class:`Finding`."""
        return Finding(
            id=self.id,
            rule_id=rule_id or f"issue.{self.type.value}",
            severity=self.severity,
            message=self.message,
            location=self.location,
            category=self.type.value,
            code_snippet=self.code_snippet,
            fix_suggestion=self.suggestion,
            metadata=self.metadata,
        )


__all__ = ["Issue", "IssueType"]
