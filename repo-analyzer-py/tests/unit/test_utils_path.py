"""Tests for ``repo_analyzer.utils.path``."""

from __future__ import annotations

from pathlib import Path

from repo_analyzer.utils.path import (
    expand_user_path,
    normalize_path,
    repo_cache_dir,
    temp_directory,
)


def test_expand_user_path_resolves_tilde(tmp_path: Path) -> None:
    """Tilde should expand to the home directory."""
    result = expand_user_path("~/test")
    assert str(result).startswith(str(Path.home()))


def test_expand_user_path_resolves_env_vars(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Environment variables should be expanded."""
    monkeypatch.setenv("TEST_VAR", str(Path("/tmp")))
    result = expand_user_path("$TEST_VAR/sub")
    assert result == Path("/tmp/sub")


def test_expand_user_path_returns_absolute() -> None:
    """Relative paths should resolve to absolute."""
    result = expand_user_path("relative/path")
    assert result.is_absolute()


def test_normalize_path_collapses_dots(tmp_path: Path) -> None:
    """``.`` and ``..`` should be collapsed."""
    base = str(tmp_path)
    result = normalize_path(f"{base}/./sub/../file")
    assert result == Path(base) / "file"


def test_normalize_path_expands_tilde() -> None:
    """Tilde expansion should occur."""
    result = normalize_path("~/dir")
    assert str(result).startswith(str(Path.home()))


def test_repo_cache_dir_is_stable() -> None:
    """The same URL should always map to the same cache dir."""
    d1 = repo_cache_dir("/tmp/cache", "https://github.com/a/b")
    d2 = repo_cache_dir("/tmp/cache", "https://github.com/a/b")
    assert d1 == d2


def test_repo_cache_dir_differs_for_different_urls() -> None:
    """Different URLs should map to different dirs."""
    d1 = repo_cache_dir("/tmp/cache", "https://github.com/a/b")
    d2 = repo_cache_dir("/tmp/cache", "https://github.com/a/c")
    assert d1 != d2


def test_repo_cache_dir_strips_trailing_slash() -> None:
    """A trailing slash should not affect the hash."""
    d1 = repo_cache_dir("/tmp/cache", "https://github.com/a/b")
    d2 = repo_cache_dir("/tmp/cache", "https://github.com/a/b/")
    assert d1 == d2


def test_temp_directory_creates_and_removes() -> None:
    """The temp dir should exist inside the block and be removed after."""
    created: Path | None = None
    with temp_directory() as tmp:
        assert tmp.exists()
        assert tmp.is_dir()
        created = tmp
    assert created is not None
    assert not created.exists()


def test_temp_directory_prefix() -> None:
    """The temp dir name should carry the prefix."""
    with temp_directory(prefix="custom-prefix-") as tmp:
        assert tmp.name.startswith("custom-prefix-")
