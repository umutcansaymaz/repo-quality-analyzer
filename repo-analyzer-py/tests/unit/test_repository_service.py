"""Tests for the repository service (VCS provider + factory)."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyzer.adapters.vcs import (
    DefaultRepositoryProviderFactory,
    GitHubRepositoryProvider,
)
from repo_analyzer.core.domain.repository import (
    AccessMode,
    parse_repository_url,
)
from repo_analyzer.infrastructure.errors import RepositoryException, RepositoryNotFoundException


class TestGitHubRepositoryProvider:
    """Tests for :class:`GitHubRepositoryProvider`."""

    def test_can_handle_github(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        assert provider.can_handle(repo) is True

    def test_cannot_handle_other_host(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://gitlab.com/o/r")
        assert provider.can_handle(repo) is False

    def test_resolve_populates_clone_url(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        resolved = provider.resolve(repo)
        assert resolved.clone_url == "https://github.com/o/r.git"
        assert resolved.default_branch == "main"

    def test_resolve_ssh_clone_url(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("git@github.com:o/r.git")
        repo = repo.model_copy(update={"access": AccessMode.SSH})
        resolved = provider.resolve(repo)
        assert resolved.clone_url == "git@github.com:o/r.git"

    def test_resolve_non_github_raises(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://gitlab.com/o/r")
        with pytest.raises(RepositoryNotFoundException):
            provider.resolve(repo)

    def test_clone_not_implemented(self, tmp_path: Path) -> None:
        """Clone should raise at the infrastructure stage."""
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        with pytest.raises(RepositoryException):
            provider.clone(repo, tmp_path / "dest")

    def test_list_branches_returns_empty(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        assert list(provider.list_branches(repo)) == []

    def test_list_tags_returns_empty(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        assert list(provider.list_tags(repo)) == []


class TestDefaultRepositoryProviderFactory:
    """Tests for :class:`DefaultRepositoryProviderFactory`."""

    def test_get_github_provider(self) -> None:
        factory = DefaultRepositoryProviderFactory()
        repo = parse_repository_url("https://github.com/o/r")
        provider = factory.get(repo)
        assert isinstance(provider, GitHubRepositoryProvider)

    def test_get_unknown_host_raises(self) -> None:
        factory = DefaultRepositoryProviderFactory()
        repo = parse_repository_url("https://bitbucket.org/o/r")
        with pytest.raises(RepositoryException):
            factory.get(repo)

    def test_register_custom_provider(self) -> None:
        class FakeProvider(GitHubRepositoryProvider):
            supported_hosts = frozenset({"fake.host"})

            def can_handle(self, repository):  # type: ignore[no-untyped-def]
                return repository.host == "fake.host"

        factory = DefaultRepositoryProviderFactory()
        factory.register(FakeProvider())
        repo = parse_repository_url("https://fake.host/o/r")
        provider = factory.get(repo)
        assert isinstance(provider, FakeProvider)

    def test_register_idempotent(self) -> None:
        """Registering the same instance twice should not duplicate."""
        factory = DefaultRepositoryProviderFactory()
        provider = GitHubRepositoryProvider()
        factory.register(provider)
        # No error on second registration.
        factory.register(provider)
