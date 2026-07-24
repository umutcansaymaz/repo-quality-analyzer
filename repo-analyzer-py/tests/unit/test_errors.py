"""Tests for the exception hierarchy."""

from __future__ import annotations

from repo_analyzer.infrastructure.errors import (
    AIException,
    AnalysisException,
    AuthenticationException,
    BaseAnalyzerException,
    CacheException,
    ConfigurationException,
    FatalError,
    NetworkException,
    PluginError,
    RecoverableError,
    RepoAnalyzerError,
    ReportException,
    RepositoryException,
    RepositoryNotFoundException,
    SecurityException,
    TransientError,
)


def test_root_exception_is_exception() -> None:
    """The root error should subclass Exception."""
    assert issubclass(RepoAnalyzerError, Exception)


def test_error_carries_code_and_message() -> None:
    """An error should expose ``code`` and ``message``."""
    err = RepositoryException("boom", repository="a/b")
    assert err.code == "GRA_REPO_001"
    assert err.message == "boom"
    assert err.context["repository"] == "a/b"


def test_error_to_dict() -> None:
    """``to_dict`` should serialize the error."""
    err = CacheException("x", cache_key="k")
    d = err.to_dict()
    assert d["code"] == "GRA_CACHE_001"
    assert d["message"] == "x"
    assert d["context"]["cache_key"] == "k"
    assert d["type"] == "CacheException"


def test_error_repr() -> None:
    """``repr`` should include the code."""
    err = ConfigurationException("bad")
    assert "ConfigurationException" in repr(err)
    assert err.code in repr(err)


def test_error_chaining() -> None:
    """The ``cause`` should be set as ``__cause__``."""
    original = ValueError("orig")
    err = NetworkException("wrapped", cause=original)
    assert err.__cause__ is original


def test_fatal_vs_recoverable() -> None:
    """Fatal and Recoverable should be distinct categories."""
    assert issubclass(AuthenticationException, FatalError)
    assert issubclass(RepositoryException, RecoverableError)
    assert not issubclass(AuthenticationException, RecoverableError)


def test_transient_is_retryable() -> None:
    """Transient errors should be retryable."""
    err = NetworkException("timeout")
    assert isinstance(err, TransientError)
    assert err.retryable is True


def test_base_analyzer_exception_carries_analyzer_id() -> None:
    """The analyzer id should be stored in context."""
    err = AnalysisException("fail", analyzer_id="security")
    assert err.analyzer_id == "security"
    assert err.context["analyzer_id"] == "security"


def test_plugin_error_carries_analyzer_id() -> None:
    err = PluginError("bad plugin", analyzer_id="x")
    assert err.analyzer_id == "x"


def test_authentication_exception_stores_host() -> None:
    err = AuthenticationException("nope", host="github.com")
    assert err.host == "github.com"
    assert err.context["host"] == "github.com"


def test_repository_not_found_inherits_repository_exception() -> None:
    assert issubclass(RepositoryNotFoundException, RepositoryException)


def test_all_exceptions_are_repo_analyzer_errors() -> None:
    """Every domain exception should derive from the root error."""
    for cls in [
        AnalysisException,
        BaseAnalyzerException,
        PluginError,
        RepositoryException,
        RepositoryNotFoundException,
        AuthenticationException,
        CacheException,
        ConfigurationException,
        NetworkException,
        SecurityException,
        AIException,
        ReportException,
    ]:
        assert issubclass(cls, RepoAnalyzerError)


def test_error_default_message() -> None:
    """When no message is given, the default should be used."""
    err = CacheException()
    assert err.message == CacheException.default_message


def test_error_custom_code() -> None:
    """A custom code should override the class default."""
    err = CacheException("x", code="GRA_CUSTOM_999")
    assert err.code == "GRA_CUSTOM_999"
