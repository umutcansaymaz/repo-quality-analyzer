"""Shared pytest fixtures for the repo-analyzer test suite."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from repo_analyzer.infrastructure.config import Config, load_config


@pytest.fixture()
def temp_cache_dir(tmp_path: Path) -> Path:
    """A temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return cache


@pytest.fixture()
def isolated_config(tmp_path: Path) -> Config:
    """A :class:`Config` whose cache + log paths live under ``tmp_path``."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    log_file = tmp_path / "logs" / "ra.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    return load_config(
        overrides={
            "cache": {"dir": str(cache_dir), "enabled": True},
            "logging": {"file": str(log_file)},
        }
    )


@pytest.fixture()
def env_cache_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    """Redirect the default cache dir to ``tmp_path`` via env var."""
    cache_dir = tmp_path / "env-cache"
    cache_dir.mkdir()
    monkeypatch.setenv("GRA_CACHE_DIR", str(cache_dir))
    yield cache_dir


@pytest.fixture()
def sample_repository_url() -> str:
    """A sample public GitHub URL."""
    return "https://github.com/octocat/Hello-World"


@pytest.fixture()
def sample_workspace() -> Path:
    """The path to the bundled sample-repo fixture (with .git history)."""
    return Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture()
def sample_repo(sample_workspace: Path):  # type: ignore[no-untyped-def]
    """A parsed :class:`Repository` for the sample fixture."""
    from repo_analyzer.core.domain.repository import parse_repository_url

    return parse_repository_url("https://github.com/test/sample-repo")
