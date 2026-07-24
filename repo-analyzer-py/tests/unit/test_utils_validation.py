"""Tests for ``repo_analyzer.utils.validation``."""

from __future__ import annotations

from repo_analyzer.utils.validation import is_valid_git_url, is_valid_semver, is_valid_url


class TestIsValidUrl:
    """Tests for :func:`is_valid_url`."""

    def test_valid_https(self) -> None:
        assert is_valid_url("https://github.com/a/b") is True

    def test_valid_http(self) -> None:
        assert is_valid_url("http://example.com") is True

    def test_invalid_scheme(self) -> None:
        assert is_valid_url("ftp://example.com") is False

    def test_missing_scheme(self) -> None:
        assert is_valid_url("example.com/path") is False

    def test_empty(self) -> None:
        assert is_valid_url("") is False

    def test_none_like(self) -> None:
        assert is_valid_url("not a url at all") is False


class TestIsValidGitUrl:
    """Tests for :func:`is_valid_git_url`."""

    def test_https_github(self) -> None:
        assert is_valid_git_url("https://github.com/owner/repo") is True

    def test_https_github_with_git(self) -> None:
        assert is_valid_git_url("https://github.com/owner/repo.git") is True

    def test_ssh_form(self) -> None:
        assert is_valid_git_url("git@github.com:owner/repo.git") is True

    def test_ssh_protocol(self) -> None:
        assert is_valid_git_url("ssh://git@github.com/owner/repo.git") is True

    def test_empty(self) -> None:
        assert is_valid_git_url("") is False

    def test_plain_text(self) -> None:
        assert is_valid_git_url("just text") is False


class TestIsValidSemver:
    """Tests for :func:`is_valid_semver`."""

    def test_simple(self) -> None:
        assert is_valid_semver("1.2.3") is True

    def test_with_prerelease(self) -> None:
        assert is_valid_semver("1.0.0-alpha.1") is True

    def test_with_build(self) -> None:
        assert is_valid_semver("1.0.0+build.123") is True

    def test_full(self) -> None:
        assert is_valid_semver("1.0.0-alpha+build") is True

    def test_zero_version(self) -> None:
        assert is_valid_semver("0.0.0") is True

    def test_two_components(self) -> None:
        assert is_valid_semver("1.2") is False

    def test_leading_zeros(self) -> None:
        assert is_valid_semver("01.2.3") is False

    def test_empty(self) -> None:
        assert is_valid_semver("") is False

    def test_v_prefix(self) -> None:
        assert is_valid_semver("v1.2.3") is False
