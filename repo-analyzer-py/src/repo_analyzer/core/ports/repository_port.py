"""Repository provider port (abstract VCS interface).

A :class:`RepositoryProvider` knows how to resolve, clone and inspect a
repository for a given VCS host (GitHub, GitLab, Bitbucket...). The
:class:`RepositoryProviderFactory` selects the right provider based on the
repository URL so that new providers can be added without touching the
orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path

from repo_analyzer.core.domain.repository import Repository


class RepositoryProvider(ABC):
    """Abstract interface for a VCS host provider."""

    #: The host names this provider handles (e.g. ``{"github.com"}``).
    supported_hosts: frozenset[str] = frozenset()

    @abstractmethod
    def can_handle(self, repository: Repository) -> bool:
        """Return ``True`` if this provider can handle ``repository``."""

    @abstractmethod
    def resolve(self, repository: Repository) -> Repository:
        """Resolve metadata (commit SHA, default branch...).

        Args:
            repository: The repository to resolve (``ref`` may be a branch).

        Returns:
            A new :class:`Repository` with ``commit_sha`` filled in.
        """

    @abstractmethod
    def clone(self, repository: Repository, destination: Path) -> Path:
        """Clone the repository into ``destination``.

        Args:
            repository: The repository to clone.
            destination: Target directory (must not exist).

        Returns:
            The path to the cloned working tree.

        Note:
            At this infrastructure stage no actual clone is performed; the
            method is part of the contract that concrete adapters fulfill.
        """

    @abstractmethod
    def list_branches(self, repository: Repository) -> Sequence[str]:
        """Return the list of branch names."""

    @abstractmethod
    def list_tags(self, repository: Repository) -> Sequence[str]:
        """Return the list of tag names."""


class RepositoryProviderFactory(ABC):
    """Abstract factory that selects a :class:`RepositoryProvider` by host."""

    @abstractmethod
    def register(self, provider: RepositoryProvider) -> None:
        """Register a provider."""

    @abstractmethod
    def get(self, repository: Repository) -> RepositoryProvider:
        """Return a provider capable of handling ``repository``.

        Raises:
            RepositoryException: If no registered provider can handle it.
        """


__all__ = ["RepositoryProvider", "RepositoryProviderFactory"]
