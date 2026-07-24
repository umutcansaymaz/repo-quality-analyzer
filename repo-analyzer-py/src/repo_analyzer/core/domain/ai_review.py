"""AI-review domain model."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Priority(str, Enum):
    """Priority of an AI recommendation."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ModelInfo(BaseModel):
    """Information about the LLM that produced a review."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str
    api_version: str | None = None


class Recommendation(BaseModel):
    """A single AI-generated recommendation."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    effort: str = Field(default="medium", description="Estimated effort: low/medium/high.")
    related_finding_ids: list[UUID] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("effort")
    @classmethod
    def _validate_effort(cls, value: str) -> str:
        lowered = value.lower()
        if lowered not in {"low", "medium", "high"}:
            raise ValueError(f"Effort must be low/medium/high, got {value!r}")
        return lowered


class AIReview(BaseModel):
    """An AI-generated review of a repository analysis."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    summary: str = ""
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    confidence: int = Field(default=0, ge=0, le=100)
    model: ModelInfo | None = None
    generated_at: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("summary")
    @classmethod
    def _strip_summary(cls, value: str) -> str:
        return value.strip()


__all__ = ["AIReview", "ModelInfo", "Priority", "Recommendation"]
