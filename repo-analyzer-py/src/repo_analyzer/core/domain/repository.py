"""Repository domain model."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AccessMode(str, Enum):
    """How the repository is accessed."""

    PUBLIC = "public"
    PRIVATE = "private"
    SSH = "ssh"
    TOKEN = "token"


class Credential(BaseModel):
    """A reference to a credential (never the credential value itself).

    The actual secret is retrieved at runtime from a credential store
    (keyring, env var, etc.). Storing only a reference here keeps the model
    safe to serialize and log.
    """

    model_config = ConfigDict(extra="forbid")

    source: str = Field(description="Credential source: 'env', 'keyring', 'ssh-agent', 'file'.")
    identifier: str = Field(
        description="Identifier within the source (e.g. env var name or keyring service)."
    )
    username: str | None = None

    def __repr__(self) -> str:
        return f"Credential(source={self.source!r}, identifier={self.identifier!r})"


class RepositoryRef(BaseModel):
    """A lightweight reference to a repository (URL + ref)."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(description="Repository URL (HTTPS or SSH).")
    host: str = Field(description="VCS host, e.g. 'github.com'.")
    owner: str = Field(description="Repository owner (user or org).")
    name: str = Field(description="Repository name.")
    ref: str = Field(default="HEAD", description="Branch, tag or commit.")
    access: AccessMode = AccessMode.PUBLIC
    credential: Credential | None = None

    @field_validator("url")
    @classmethod
    def _non_empty_url(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Repository URL must not be empty")
        return value.strip()

    @model_validator(mode="after")
    def _require_credential_for_private(self) -> RepositoryRef:
        if self.access in {AccessMode.PRIVATE, AccessMode.TOKEN} and self.credential is None:
            raise ValueError(f"A credential is required for access mode {self.access!r}")
        return self


class Repository(RepositoryRef):
    """A repository with resolved commit information."""

    model_config = ConfigDict(extra="forbid")

    commit_sha: str | None = Field(default=None, description="Resolved commit SHA.")
    default_branch: str | None = None
    description: str | None = None
    stars: int | None = None
    forks: int | None = None
    clone_url: str | None = None

    def to_ref(self) -> RepositoryRef:
        """Return a :class:`RepositoryRef` view of this repository."""
        return RepositoryRef(
            url=self.url,
            host=self.host,
            owner=self.owner,
            name=self.name,
            ref=self.ref,
            access=self.access,
            credential=self.credential,
        )


def parse_repository_url(url: str, access: AccessMode = AccessMode.PUBLIC) -> Repository:
    """Parse a GitHub-style URL into a :class:`Repository`.

    Supports ``https://github.com/owner/repo[.git]`` and
    ``git@github.com:owner/repo[.git]`` forms.

    Args:
        url: The repository URL.
        access: Access mode to assign.

    Returns:
        A populated :class:`Repository`.

    Raises:
        ValueError: If the URL cannot be parsed.
    """
    cleaned = url.strip()
    if not cleaned:
        raise ValueError("Empty repository URL")
    host: str
    owner: str
    name: str
    if cleaned.startswith("git@") or cleaned.startswith("ssh://"):
        # ssh: git@github.com:owner/repo.git  or  ssh://git@github.com/owner/repo.git
        body = cleaned
        if body.startswith("ssh://"):
            body = body[len("ssh://") :]
        if "@" in body:
            body = body.split("@", 1)[1]
        if ":" in body and body.index(":") < body.index("/"):
            host, remainder = body.split(":", 1)
        else:
            host, remainder = body.split("/", 1)
        parts = remainder.rstrip("/").split("/")
    else:
        from urllib.parse import urlparse

        parsed = urlparse(cleaned)
        host = parsed.netloc
        path = parsed.path.lstrip("/")
        parts = path.rstrip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse owner/repo from URL: {url!r}")
    owner = parts[0]
    name = parts[1]
    if name.endswith(".git"):
        name = name[: -len(".git")]
    return Repository(
        url=cleaned,
        host=host,
        owner=owner,
        name=name,
        ref="HEAD",
        access=access,
    )


__all__ = [
    "AccessMode",
    "Credential",
    "Repository",
    "RepositoryRef",
    "parse_repository_url",
]
