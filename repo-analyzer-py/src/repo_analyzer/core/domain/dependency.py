"""Dependency domain model."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Version(BaseModel):
    """A semantic version with optional pre-release and build metadata.

    Stored as the raw string to preserve the exact form, with ``major``,
    ``minor`` and ``patch`` parsed out for comparison.
    """

    model_config = ConfigDict(extra="forbid")

    raw: str
    major: int = 0
    minor: int = 0
    patch: int = 0
    prerelease: str | None = None
    build: str | None = None

    @field_validator("raw")
    @classmethod
    def _non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Version must not be empty")
        return value.strip()

    def __str__(self) -> str:
        return self.raw

    @classmethod
    def parse(cls, raw: str) -> Version:
        """Parse a version string into a :class:`Version`."""
        match = re.match(
            r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
            r"(?:-(?P<pre>[0-9A-Za-z.-]+))?(?:\+(?P<build>[0-9A-Za-z.-]+))?$",
            raw.strip(),
        )
        if not match:
            return cls(raw=raw)
        return cls(
            raw=raw.strip(),
            major=int(match.group("major")),
            minor=int(match.group("minor")),
            patch=int(match.group("patch")),
            prerelease=match.group("pre"),
            build=match.group("build"),
        )


class License(BaseModel):
    """A software license."""

    model_config = ConfigDict(extra="forbid")

    spdx_id: str = Field(description="SPDX identifier, e.g. 'MIT', 'Apache-2.0'.")
    name: str | None = None
    url: str | None = None

    def __str__(self) -> str:
        return self.spdx_id


class Dependency(BaseModel):
    """A (direct or transitive) dependency of the analyzed repository."""

    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    name: str
    version: Version
    ecosystem: str = Field(description="Package ecosystem: 'pypi', 'npm', 'cargo'...")
    license: License | None = None
    direct: bool = True
    dependencies: list[Dependency] = Field(default_factory=list)
    resolved_url: str | None = None
    vulnerabilities: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_vulnerable(self) -> bool:
        """``True`` if the dependency has any known vulnerabilities."""
        return bool(self.vulnerabilities)


__all__ = ["Dependency", "License", "Version"]
