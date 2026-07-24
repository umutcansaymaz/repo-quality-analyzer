"""Tests for :class:`CloneService` and :class:`GitHubRepositoryProvider` helpers.

These tests cover the non-network code paths: URL building, command
construction, redaction and retry logic.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.adapters.vcs.clone_service import CloneService
from repo_analyzer.adapters.vcs.factory import DefaultRepositoryProviderFactory
from repo_analyzer.adapters.vcs.github_provider import (
    GitHubRepositoryProvider,
    _redact_cmd,
)
from repo_analyzer.core.domain.repository import (
    AccessMode,
    Credential,
    parse_repository_url,
)
from repo_analyzer.infrastructure.errors import (
    AuthenticationException,
    RepositoryCloneException,
    RepositoryNotFoundException,
)


@pytest.fixture()
def cache(tmp_path: Path) -> SQLiteCacheAdapter:
    adapter = SQLiteCacheAdapter(tmp_path / "cache.db")
    yield adapter  # type: ignore[misc]
    adapter.close()


class TestGitHubProviderHelpers:
    """Tests for the helper methods that do not require network."""

    def test_build_clone_url_public(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        url = provider._build_clone_url(repo)
        assert url == "https://github.com/o/r.git"

    def test_build_clone_url_ssh(self) -> None:
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("git@github.com:o/r.git")
        repo = repo.model_copy(update={"access": AccessMode.SSH})
        url = provider._build_clone_url(repo)
        assert url == "git@github.com:o/r.git"

    def test_build_clone_url_with_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GRA_TOKEN", "ghp_secret")
        provider = GitHubRepositoryProvider()
        repo = parse_repository_url("https://github.com/o/r")
        repo = repo.model_copy(
            update={
                "access": AccessMode.TOKEN,
                "credential": Credential(source="env", identifier="GRA_TOKEN"),
            }
        )
        url = provider._build_clone_url(repo)
        assert "ghp_secret" in url
        assert "x-access-token" in url

    def test_build_clone_command(self, tmp_path: Path) -> None:
        provider = GitHubRepositoryProvider(clone_depth=5, partial_clone=True)
        cmd = provider._build_clone_command("https://example.com/repo.git", tmp_path / "dest")
        assert "git" in cmd
        assert "clone" in cmd
        assert "--depth" in cmd
        assert "5" in cmd
        assert "--filter=blob:none" in cmd

    def test_build_clone_command_no_partial(self, tmp_path: Path) -> None:
        provider = GitHubRepositoryProvider(clone_depth=1, partial_clone=False)
        cmd = provider._build_clone_command("url", tmp_path / "dest")
        assert "--filter=blob:none" not in cmd

    def test_resolve_token_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MY_TOKEN", "abc123")
        cred = Credential(source="env", identifier="MY_TOKEN")
        assert GitHubRepositoryProvider._resolve_token(cred) == "abc123"

    def test_resolve_token_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("MISSING_TOKEN", raising=False)
        cred = Credential(source="env", identifier="MISSING_TOKEN")
        assert GitHubRepositoryProvider._resolve_token(cred) is None

    def test_resolve_token_keyring_unavailable(self) -> None:
        cred = Credential(source="keyring", identifier="svc")
        # keyring may not be installed; should return None gracefully.
        result = GitHubRepositoryProvider._resolve_token(cred)
        assert result is None or isinstance(result, str)

    def test_resolve_token_unknown_source(self) -> None:
        cred = Credential(source="unknown", identifier="x")
        assert GitHubRepositoryProvider._resolve_token(cred) is None

    def test_run_git_raises_on_missing_binary(self) -> None:
        provider = GitHubRepositoryProvider()
        with patch("subprocess.run", side_effect=FileNotFoundError("no git")):
            with pytest.raises(RepositoryCloneException):
                provider._run_git(["git", "clone", "url", "dest"], "url")

    def test_run_git_raises_on_timeout(self) -> None:
        provider = GitHubRepositoryProvider(timeout=1)
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=1),
        ):
            from repo_analyzer.infrastructure.errors import RepositoryTimeoutException

            with pytest.raises(RepositoryTimeoutException):
                provider._run_git(["git", "clone", "url", "dest"], "url")

    def test_run_git_maps_auth_error(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="fatal: could not read Username for 'https://github.com'",
        )
        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(AuthenticationException):
                provider._run_git(["git", "clone", "url", "dest"], "url")

    def test_run_git_maps_not_found(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="fatal: repository not found"
        )
        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(RepositoryNotFoundException):
                provider._run_git(["git", "clone", "url", "dest"], "url")

    def test_run_git_maps_generic_error(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="some other error"
        )
        with patch("subprocess.run", return_value=mock_proc):
            with pytest.raises(RepositoryCloneException):
                provider._run_git(["git", "clone", "url", "dest"], "url")

    def test_run_git_success(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
        with patch("subprocess.run", return_value=mock_proc):
            result = provider._run_git(["git", "clone", "url", "dest"], "url")
            assert result == "ok"

    def test_ls_remote_head_returns_sha(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="abc1234567890\tHEAD", stderr=""
        )
        with patch("subprocess.run", return_value=mock_proc):
            sha = provider._ls_remote_head("url", parse_repository_url("https://github.com/o/r"))
            assert sha == "abc1234567890"

    def test_ls_remote_head_failure_returns_HEAD(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("subprocess.run", return_value=mock_proc):
            sha = provider._ls_remote_head("url", parse_repository_url("https://github.com/o/r"))
            assert sha == "HEAD"

    def test_ls_remote_branches(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="sha\trefs/heads/main\nsha\trefs/heads/dev\nsha\trefs/tags/v1\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=mock_proc):
            branches = provider.list_branches(parse_repository_url("https://github.com/o/r"))
            assert "main" in branches
            assert "dev" in branches

    def test_ls_remote_tags(self) -> None:
        provider = GitHubRepositoryProvider()
        mock_proc = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="sha\trefs/tags/v1.0\nsha\trefs/tags/v2.0\n",
            stderr="",
        )
        with patch("subprocess.run", return_value=mock_proc):
            tags = provider.list_tags(parse_repository_url("https://github.com/o/r"))
            assert "v1.0" in tags
            assert "v2.0" in tags


class TestRedactCmd:
    """Tests for the ``_redact_cmd`` helper."""

    def test_redacts_token_url(self) -> None:
        cmd = ["git", "clone", "https://x-access-token:secret@github.com/o/r.git", "dest"]
        redacted = _redact_cmd(cmd)
        assert "[REDACTED_URL]" in redacted
        assert "secret" not in redacted

    def test_passes_through_normal_cmd(self) -> None:
        cmd = ["git", "clone", "https://github.com/o/r.git", "dest"]
        redacted = _redact_cmd(cmd)
        assert redacted == cmd


class TestCloneServiceRetry:
    """Tests for the retry logic in :class:`CloneService`."""

    def test_retry_on_timeout(self, cache: SQLiteCacheAdapter, tmp_path: Path) -> None:
        """The clone service should retry on timeout."""
        from repo_analyzer.infrastructure.errors import (
            RepositoryTimeoutException,
        )

        repo = parse_repository_url("https://github.com/test/repo").model_copy(
            update={"commit_sha": "abc"}
        )
        provider = GitHubRepositoryProvider()
        # Mock resolve to succeed, then clone to timeout twice then succeed.
        call_count = {"n": 0}

        def fake_clone(repository, destination):  # type: ignore[no-untyped-def]
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise RepositoryTimeoutException("timeout", repository=repository.url)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "file.txt").write_text("ok")
            return destination

        with (
            patch.object(provider, "resolve", return_value=repo),
            patch.object(provider, "clone", side_effect=fake_clone),
        ):
            factory = DefaultRepositoryProviderFactory()
            factory._providers = [provider]  # type: ignore[attr-defined]
            service = CloneService(cache, factory=factory, max_retries=3, backoff_base=0.01)
            # Bypass cache to force the retry path.
            path, _ = service.clone(repo, use_cache=False)
            assert path.exists()
            assert call_count["n"] == 3

    def test_retry_exhausted_raises(self, cache: SQLiteCacheAdapter, tmp_path: Path) -> None:
        """When retries are exhausted the last exception should propagate."""
        from repo_analyzer.infrastructure.errors import RepositoryCloneException

        repo = parse_repository_url("https://github.com/test/repo").model_copy(
            update={"commit_sha": "abc"}
        )
        provider = GitHubRepositoryProvider()

        def always_fail(repository, destination):  # type: ignore[no-untyped-def]
            raise RepositoryCloneException("nope", repository=repository.url)

        with (
            patch.object(provider, "resolve", return_value=repo),
            patch.object(provider, "clone", side_effect=always_fail),
        ):
            factory = DefaultRepositoryProviderFactory()
            factory._providers = [provider]  # type: ignore[attr-defined]
            service = CloneService(cache, factory=factory, max_retries=2, backoff_base=0.01)
            with pytest.raises(RepositoryCloneException):
                service.clone(repo, use_cache=False)

    def test_cleanup_workspace_removes_dir(self, cache: SQLiteCacheAdapter, tmp_path: Path) -> None:
        service = CloneService(cache)
        d = tmp_path / "to-clean"
        d.mkdir()
        (d / "file.txt").write_text("x")
        service.cleanup_workspace(d)
        assert not d.exists()

    def test_cleanup_workspace_missing_is_noop(
        self, cache: SQLiteCacheAdapter, tmp_path: Path
    ) -> None:
        service = CloneService(cache)
        service.cleanup_workspace(tmp_path / "nonexistent")  # should not raise

    def test_dir_size(self, cache: SQLiteCacheAdapter, tmp_path: Path) -> None:
        d = tmp_path / "measure"
        d.mkdir()
        (d / "a.txt").write_text("x" * 100)
        (d / "b.txt").write_text("y" * 50)
        size = CloneService._dir_size(d)
        assert size == 150
