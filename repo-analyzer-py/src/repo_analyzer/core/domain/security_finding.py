"""Security finding domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from repo_analyzer.core.domain.report import Finding, Location, Severity


class SecurityCategory(str, Enum):
    """Categories of security findings."""

    SAST = "sast"
    SECRET = "secret"
    DEPENDENCY = "dependency"
    INJECTION = "injection"
    AUTH = "auth"
    CRYPTO = "crypto"
    CONFIG = "config"
    PERMISSION = "permission"
    OTHER = "other"


class Confidence(str, Enum):
    """Confidence level of a security finding."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    def to_float(self) -> float:
        """Return a numeric confidence in [0, 1]."""
        return {"high": 0.9, "medium": 0.6, "low": 0.3}[self.value]


class SecurityFinding(BaseModel):
    """A security-related finding (SAST, secret, dependency vulnerability...).

    Carries enough information to produce a remediation ticket.
    """

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    rule_id: str = Field(description="Rule identifier, e.g. 'bandit.B101'.")
    category: SecurityCategory = SecurityCategory.SAST
    severity: Severity
    confidence: Confidence = Confidence.MEDIUM
    message: str
    location: Location | None = None
    cwe: str | None = Field(default=None, description="CWE identifier, e.g. 'CWE-79'.")
    cvss: float | None = Field(default=None, ge=0.0, le=10.0)
    description: str | None = None
    fix_suggestion: str | None = None
    references: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_finding(self) -> Finding:
        """Convert this security finding to a generic :class:`Finding`."""
        return Finding(
            id=self.id,
            rule_id=self.rule_id,
            severity=self.severity,
            message=self.message,
            location=self.location,
            category=self.category.value,
            confidence=self.confidence.to_float(),
            code_snippet=self.description,
            fix_suggestion=self.fix_suggestion,
            metadata=self.metadata,
        )


__all__ = ["SecurityFinding", "SecurityCategory", "Confidence"]
