"""Default repository-provider factory.

Registers the built-in providers (GitHub) and selects the right one based on
the repository host. New providers (GitLab, Bitbucket...) can be registered
without modifying the orchestrator.
"""

from __future__ import annotations

from repo_analyzer.adapters.vcs.github_provider import GitHubRepositoryProvider
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.repository_port import (
    RepositoryProvider,
    RepositoryProviderFactory,
)
from repo_analyzer.infrastructure.errors import RepositoryException
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class DefaultRepositoryProviderFactory(RepositoryProviderFactory):
    """A registry-based factory for :class:`RepositoryProvider` instances.

    Providers are tried in registration order; the first that returns
    ``True`` from :meth:`RepositoryProvider.can_handle` is selected.
    """

    def __init__(
        self,
        *,
        clone_depth: int = 1,
        partial_clone: bool = True,
        timeout: int = 120,
    ) -> None:
        self._providers: list[RepositoryProvider] = []
        self._clone_depth = clone_depth
        self._partial_clone = partial_clone
        self._timeout = timeout
        self.register(
            GitHubRepositoryProvider(
                clone_depth=clone_depth,
                partial_clone=partial_clone,
                timeout=timeout,
            )
        )

    def register(self, provider: RepositoryProvider) -> None:
        """Register a provider."""
        if provider in self._providers:
            return
        _logger.debug("Registering repository provider %s", type(provider).__name__)
        self._providers.append(provider)

    def get(self, repository: Repository) -> RepositoryProvider:
        """Return the first provider capable of handling ``repository``.

        Raises:
            RepositoryException: If no provider can handle the repository.
        """
        for provider in self._providers:
            if provider.can_handle(repository):
                return provider
        raise RepositoryException(
            f"No repository provider registered for host {repository.host!r}",
            repository=repository.url,
            context={"host": repository.host},
        )


__all__ = ["DefaultRepositoryProviderFactory"]
