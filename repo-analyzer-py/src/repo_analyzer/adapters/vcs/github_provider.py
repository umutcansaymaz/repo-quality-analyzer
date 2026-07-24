"""GitHub repository provider.

Implements :class:`RepositoryProvider` for GitHub-hosted repositories. The
class is structurally complete: method signatures, docstrings and contracts
are final. The actual git-clone / API calls are intentionally not wired up
at this infrastructure stage (see SDD roadmap: clone is added in MVP).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from repo_analyzer.core.domain.repository import AccessMode, Repository
from repo_analyzer.core.ports.repository_port import RepositoryProvider
from repo_analyzer.infrastructure.errors import (
    RepositoryException,
    RepositoryNotFoundException,
)
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class GitHubRepositoryProvider(RepositoryProvider):
    """A :class:`RepositoryProvider` for ``github.com`` repositories.

    Supports both HTTPS (with optional token) and SSH access modes. A future
    ``GitLabRepositoryProvider`` can be added by subclassing and overriding
    :attr:`supported_hosts` and the host-specific URL parsing.
    """

    supported_hosts: frozenset[str] = frozenset({"github.com", "www.github.com"})

    def can_handle(self, repository: Repository) -> bool:
        """Return ``True`` if the repository's host is GitHub."""
        host = repository.host.lower()
        return host in self.supported_hosts

    def resolve(self, repository: Repository) -> Repository:
        """Resolve repository metadata (commit SHA, default branch).

        At the infrastructure stage this performs only lightweight URL
        validation and returns the repository with ``commit_sha`` left as
        ``None``. Concrete resolution (via GitHub API or ``git ls-remote``)
        is implemented in the MVP phase.
        """
        _logger.debug("Resolving repository %s/%s", repository.owner, repository.name)
        if not self.can_handle(repository):
            raise RepositoryNotFoundException(
                f"Not a GitHub repository: {repository.url}",
                repository=repository.url,
            )
        # Return a copy with clone_url populated.
        return repository.model_copy(
            update={
                "clone_url": self._build_clone_url(repository),
                "default_branch": "main",
            }
        )

    def clone(self, repository: Repository, destination: Path) -> Path:
        """Clone the repository into ``destination``.

        Not implemented at the infrastructure stage — raises
        :class:`RepositoryException` to signal that clone support is added in
        a later phase.
        """
        _logger.info(
            "Clone requested for %s into %s (not implemented at this stage)",
            repository.url,
            destination,
        )
        raise RepositoryException(
            "Clone is not implemented at the infrastructure stage.",
            repository=repository.url,
            context={"destination": str(destination)},
        )

    def list_branches(self, repository: Repository) -> Sequence[str]:
        """Return the list of branches.

        Not implemented at the infrastructure stage — returns an empty list.
        """
        _logger.debug("list_branches called for %s (stub)", repository.url)
        return []

    def list_tags(self, repository: Repository) -> Sequence[str]:
        """Return the list of tags.

        Not implemented at the infrastructure stage — returns an empty list.
        """
        _logger.debug("list_tags called for %s (stub)", repository.url)
        return []

    @staticmethod
    def _build_clone_url(repository: Repository) -> str:
        """Build the clone URL appropriate for the repository's access mode.

        Args:
            repository: The repository.

        Returns:
            A clone URL (HTTPS with optional token, or SSH).
        """
        if repository.access == AccessMode.SSH:
            return f"git@{repository.host}:{repository.owner}/{repository.name}.git"
        # HTTPS (with token embedded in credential store at runtime).
        return f"https://{repository.host}/{repository.owner}/{repository.name}.git"


__all__ = ["GitHubRepositoryProvider"]
