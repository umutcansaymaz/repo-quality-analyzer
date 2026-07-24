"""Shared report / finding primitives."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Severity(str, Enum):
    """Severity of a finding."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @classmethod
    def from_score(cls, score: int) -> Severity:
        """Map a 0-100 numeric score to a :class:`Severity`.

        Higher score → higher severity.
        """
        if score >= 90:
            return cls.CRITICAL
        if score >= 70:
            return cls.HIGH
        if score >= 40:
            return cls.MEDIUM
        if score >= 10:
            return cls.LOW
        return cls.INFO


class ReportFormat(str, Enum):
    """Supported report output formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"


class Location(BaseModel):
    """A location within a source file."""

    model_config = ConfigDict(extra="forbid")

    file: str = Field(description="Path relative to the repository root.")
    line: int | None = Field(default=None, ge=0)
    column: int | None = Field(default=None, ge=0)
    end_line: int | None = Field(default=None, ge=0)
    end_column: int | None = Field(default=None, ge=0)

    def __str__(self) -> str:
        parts = [self.file]
        if self.line is not None:
            parts.append(f":{self.line}")
            if self.column is not None:
                parts.append(f":{self.column}")
        return "".join(parts)


class Finding(BaseModel):
    """Base finding model shared by security, quality and architecture."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    rule_id: str = Field(description="Stable rule identifier, e.g. 'bandit.B101'.")
    severity: Severity
    message: str
    location: Location | None = None
    category: str = "general"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    code_snippet: str | None = None
    fix_suggestion: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("message")
    @classmethod
    def _non_empty_message(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Finding message must not be empty")
        return value


class ReportMeta(BaseModel):
    """Metadata attached to a generated report."""

    model_config = ConfigDict(extra="forbid")

    version: str = "0.1.0"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    tool: str = "repo-analyzer"
    config_snapshot: dict[str, Any] = Field(default_factory=dict)


class Report(BaseModel):
    """A complete analysis report."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    repository_url: str
    commit_sha: str | None = None
    meta: ReportMeta = Field(default_factory=ReportMeta)
    findings: list[Finding] = Field(default_factory=list)
    health_score: Any | None = None  # Avoid circular import; set by aggregator.
    ai_review: Any | None = None

    @property
    def findings_by_severity(self) -> dict[Severity, list[Finding]]:
        """Group findings by severity."""
        grouped: dict[Severity, list[Finding]] = {sev: [] for sev in Severity}
        for finding in self.findings:
            grouped[finding.severity].append(finding)
        return grouped


__all__ = [
    "Finding",
    "Location",
    "Report",
    "ReportFormat",
    "ReportMeta",
    "Severity",
]
