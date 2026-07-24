"""GitHub repository provider with real git-clone support.

Implements :class:`RepositoryProvider` for GitHub-hosted repositories using
the ``git`` binary. Supports HTTPS (public + token), SSH and SSH-agent
authentication. Clones are performed with shallow + partial-clone
optimizations and are cached by the :class:`CloneService`.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Sequence
from pathlib import Path

from repo_analyzer.core.domain.repository import AccessMode, Credential, Repository
from repo_analyzer.core.ports.repository_port import RepositoryProvider
from repo_analyzer.infrastructure.errors import (
    AuthenticationException,
    RepositoryCloneException,
    RepositoryNotFoundException,
    RepositoryTimeoutException,
)
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class GitHubRepositoryProvider(RepositoryProvider):
    """A :class:`RepositoryProvider` for ``github.com`` repositories.

    Supports HTTPS (with optional token), SSH and SSH-agent access. Uses the
    ``git`` binary for cloning and metadata queries.
    """

    supported_hosts: frozenset[str] = frozenset({"github.com", "www.github.com"})

    def __init__(
        self,
        *,
        clone_depth: int = 1,
        partial_clone: bool = True,
        timeout: int = 120,
    ) -> None:
        self._clone_depth = clone_depth
        self._partial_clone = partial_clone
        self._timeout = timeout

    def can_handle(self, repository: Repository) -> bool:
        """Return ``True`` if the repository's host is GitHub."""
        return repository.host.lower() in self.supported_hosts

    def resolve(self, repository: Repository) -> Repository:
        """Resolve the current commit SHA via ``git ls-remote``."""
        _logger.debug("Resolving repository %s/%s", repository.owner, repository.name)
        if not self.can_handle(repository):
            raise RepositoryNotFoundException(
                f"Not a GitHub repository: {repository.url}",
                repository=repository.url,
            )
        clone_url = self._build_clone_url(repository)
        commit_sha = self._ls_remote_head(clone_url, repository)
        return repository.model_copy(
            update={
                "clone_url": clone_url,
                "default_branch": "main",
                "commit_sha": commit_sha,
            }
        )

    def clone(self, repository: Repository, destination: Path) -> Path:
        """Clone the repository into ``destination`` (must not exist).

        Builds the appropriate clone URL based on the access mode, runs
        ``git clone`` with shallow/partial optimizations and returns the
        working-tree path.

        Raises:
            RepositoryCloneException: If the clone fails for a transient reason.
            AuthenticationException: If credentials are missing/invalid.
            RepositoryNotFoundException: If the repository does not exist.
            RepositoryTimeoutException: If the clone exceeds the timeout.
        """
        if destination.exists():
            raise RepositoryCloneException(
                f"Destination already exists: {destination}",
                repository=repository.url,
                context={"destination": str(destination)},
            )
        clone_url = self._build_clone_url(repository)
        cmd = self._build_clone_command(clone_url, destination)
        _logger.info("Cloning %s into %s", repository.url, destination)
        try:
            self._run_git(cmd, repository.url)
        except RepositoryTimeoutException:
            raise
        except AuthenticationException:
            raise
        except RepositoryCloneException as exc:
            # Distinguish 404 from auth errors via stderr inspection.
            if "not found" in (exc.context.get("stderr", "") or "").lower():
                raise RepositoryNotFoundException(
                    f"Repository not found: {repository.url}",
                    repository=repository.url,
                ) from exc
            raise
        return destination

    def list_branches(self, repository: Repository) -> Sequence[str]:
        """Return the list of branch names via ``git ls-remote``."""
        clone_url = self._build_clone_url(repository)
        return self._ls_remote(clone_url, repository, ref_prefix="refs/heads/")

    def list_tags(self, repository: Repository) -> Sequence[str]:
        """Return the list of tag names via ``git ls-remote``."""
        clone_url = self._build_clone_url(repository)
        return self._ls_remote(clone_url, repository, ref_prefix="refs/tags/")

    # ----- internal helpers ---------------------------------------------------

    @staticmethod
    def _build_clone_url(repository: Repository) -> str:
        if repository.access == AccessMode.SSH:
            return f"git@{repository.host}:{repository.owner}/{repository.name}.git"
        if repository.access in {AccessMode.PRIVATE, AccessMode.TOKEN} and repository.credential:
            token = GitHubRepositoryProvider._resolve_token(repository.credential)
            if token:
                return f"https://x-access-token:{token}@{repository.host}/{repository.owner}/{repository.name}.git"
        return f"https://{repository.host}/{repository.owner}/{repository.name}.git"

    @staticmethod
    def _resolve_token(credential: Credential) -> str | None:
        """Resolve a token from the credential reference (env only at this stage)."""
        if credential.source == "env":
            return os.environ.get(credential.identifier)
        if credential.source == "keyring":
            try:
                import keyring

                value = keyring.get_password("repo-analyzer", credential.identifier)
                return str(value) if value else None
            except Exception:
                return None
        return None

    def _build_clone_command(self, clone_url: str, destination: Path) -> list[str]:
        cmd: list[str] = ["git", "clone", "--no-progress"]
        if self._clone_depth and self._clone_depth > 0:
            cmd.extend(["--depth", str(self._clone_depth)])
        if self._partial_clone:
            cmd.append("--filter=blob:none")
        cmd.extend([clone_url, str(destination)])
        return cmd

    def _run_git(self, cmd: list[str], repo_url: str) -> str:
        """Run a git command and return stdout, mapping errors to exceptions."""
        _logger.debug("Running: %s", " ".join(_redact_cmd(cmd)))
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RepositoryTimeoutException(
                f"Git command timed out after {self._timeout}s",
                repository=repo_url,
                context={"command": _redact_cmd(cmd)},
            ) from exc
        except FileNotFoundError as exc:
            raise RepositoryCloneException(
                "git binary not found on PATH",
                repository=repo_url,
            ) from exc
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            lowered = stderr.lower()
            if (
                "could not read username" in lowered
                or "authentication failed" in lowered
                or "permission denied" in lowered
            ):
                raise AuthenticationException(
                    f"Authentication failed for {repo_url}",
                    host=repo_url,
                    context={"stderr": stderr},
                )
            if "not found" in lowered or "does not exist" in lowered:
                raise RepositoryNotFoundException(
                    f"Repository not found: {repo_url}",
                    repository=repo_url,
                    context={"stderr": stderr},
                )
            raise RepositoryCloneException(
                f"git clone failed (exit {proc.returncode})",
                repository=repo_url,
                context={"stderr": stderr, "returncode": proc.returncode},
            )
        return proc.stdout

    def _ls_remote_head(self, clone_url: str, repository: Repository) -> str:
        """Resolve the HEAD commit SHA via ``git ls-remote``."""
        try:
            proc = subprocess.run(
                ["git", "ls-remote", clone_url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return "HEAD"
        if proc.returncode != 0 or not proc.stdout:
            return "HEAD"
        return proc.stdout.split()[0]

    def _ls_remote(
        self,
        clone_url: str,
        repository: Repository,
        *,
        ref_prefix: str,
    ) -> Sequence[str]:
        try:
            proc = subprocess.run(
                ["git", "ls-remote", "--heads", "--tags", clone_url],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []
        if proc.returncode != 0:
            return []
        names: list[str] = []
        for line in proc.stdout.splitlines():
            parts = line.split("\t", 1)
            if len(parts) != 2:
                continue
            ref = parts[1]
            if ref.startswith(ref_prefix):
                names.append(ref[len(ref_prefix) :])
        return names


def _redact_cmd(cmd: list[str]) -> list[str]:
    """Return a copy of ``cmd`` with any embedded tokens redacted."""
    redacted: list[str] = []
    for arg in cmd:
        if "x-access-token:" in arg:
            redacted.append("[REDACTED_URL]")
        else:
            redacted.append(arg)
    return redacted


__all__ = ["GitHubRepositoryProvider"]
