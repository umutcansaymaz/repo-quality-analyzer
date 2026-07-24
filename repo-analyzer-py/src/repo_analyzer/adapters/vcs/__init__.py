"""VCS adapters implementing :class:`RepositoryProvider`."""

from __future__ import annotations

from repo_analyzer.adapters.vcs.factory import DefaultRepositoryProviderFactory
from repo_analyzer.adapters.vcs.github_provider import GitHubRepositoryProvider
from repo_analyzer.core.ports.repository_port import (
    RepositoryProvider,
    RepositoryProviderFactory,
)

__all__ = [
    "DefaultRepositoryProviderFactory",
    "GitHubRepositoryProvider",
    "RepositoryProvider",
    "RepositoryProviderFactory",
]
