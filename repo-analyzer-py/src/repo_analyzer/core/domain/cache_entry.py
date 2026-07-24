"""Cache-entry domain model."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CacheEntryType(str, Enum):
    """Type of cached artifact."""

    CLONE = "clone"
    ANALYSIS = "analysis"
    AI_REVIEW = "ai_review"


class CacheKey(BaseModel):
    """A deterministic cache key for a repository / artifact."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    repository_url: str
    commit_sha: str | None = None
    entry_type: CacheEntryType = CacheEntryType.ANALYSIS
    analyzer_version: str = "0.1.0"
    config_hash: str = ""

    def to_hash(self) -> str:
        """Compute the deterministic hash representation of this key."""
        import hashlib

        material = "|".join(
            [
                self.repository_url.strip().rstrip("/"),
                self.commit_sha or "HEAD",
                self.entry_type.value,
                self.analyzer_version,
                self.config_hash,
            ]
        )
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def __str__(self) -> str:
        return self.to_hash()

    def __hash__(self) -> int:
        return hash(self.to_hash())


class CacheEntry(BaseModel):
    """An entry stored in the cache."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    key: str = Field(description="Hash of the :class:`CacheKey`.")
    repository_url: str
    commit_sha: str | None = None
    entry_type: CacheEntryType = CacheEntryType.ANALYSIS
    workspace_path: str | None = None
    result_json: str | None = Field(
        default=None, description="Serialized result for analysis entries."
    )
    size_bytes: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    expires_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC) + timedelta(days=7))
    last_accessed_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    access_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("key")
    @classmethod
    def _non_empty_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Cache key must not be empty")
        return value.strip()

    @property
    def is_expired(self) -> bool:
        """``True`` if :attr:`expires_at` is in the past."""
        return datetime.now(tz=UTC) > self.expires_at

    @property
    def workspace(self) -> Path | None:
        """The workspace path as a :class:`~pathlib.Path`, if set."""
        return Path(self.workspace_path) if self.workspace_path else None

    def touch(self) -> None:
        """Update :attr:`last_accessed_at` and bump :attr:`access_count`."""
        self.last_accessed_at = datetime.now(tz=UTC)
        self.access_count += 1


__all__ = ["CacheEntry", "CacheEntryType", "CacheKey"]
