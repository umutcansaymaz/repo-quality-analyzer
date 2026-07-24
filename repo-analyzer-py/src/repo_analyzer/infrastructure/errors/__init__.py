"""Exception hierarchy for repo-analyzer.

All application errors derive from :class:`RepoAnalyzerError`. The hierarchy
follows the categories defined in the SDD (ADR-011):

- Fatal errors (cannot continue) → :class:`FatalError`
- Recoverable errors (skip and continue) → :class:`RecoverableError`
- Transient errors (retryable) → :class:`TransientError`

Each exception carries a stable ``code``, a human readable ``message`` and a
structured ``context`` dict for diagnostics.
"""

from __future__ import annotations

from repo_analyzer.infrastructure.errors.ai import (
    AIContextLengthException,
    AIException,
    AIRateLimitException,
    AIResponseParsingException,
)
from repo_analyzer.infrastructure.errors.analyzer import (
    AnalysisException,
    BaseAnalyzerException,
    PluginError,
)
from repo_analyzer.infrastructure.errors.base import (
    FatalError,
    RecoverableError,
    RepoAnalyzerError,
    TransientError,
)
from repo_analyzer.infrastructure.errors.cache import (
    CacheCorruptedException,
    CacheException,
    CacheExpiredException,
)
from repo_analyzer.infrastructure.errors.config import (
    ConfigFileNotFoundException,
    ConfigurationError,
    ConfigurationException,
    ConfigValidationException,
)
from repo_analyzer.infrastructure.errors.network import (
    ConnectionTimeoutException,
    NetworkException,
    RateLimitException,
)
from repo_analyzer.infrastructure.errors.report import (
    ReportException,
    ReportRenderException,
    ReportTemplateNotFoundException,
)
from repo_analyzer.infrastructure.errors.repository import (
    AuthenticationException,
    RepositoryCloneException,
    RepositoryException,
    RepositoryNotFoundException,
    RepositoryTimeoutException,
)
from repo_analyzer.infrastructure.errors.security import (
    CredentialNotFoundException,
    PluginTrustException,
    SecurityException,
)

__all__ = [
    "RepoAnalyzerError",
    "FatalError",
    "RecoverableError",
    "TransientError",
    "BaseAnalyzerException",
    "AnalysisException",
    "PluginError",
    "RepositoryException",
    "RepositoryCloneException",
    "RepositoryNotFoundException",
    "RepositoryTimeoutException",
    "AuthenticationException",
    "CacheException",
    "CacheCorruptedException",
    "CacheExpiredException",
    "ConfigurationException",
    "ConfigurationError",
    "ConfigFileNotFoundException",
    "ConfigValidationException",
    "NetworkException",
    "RateLimitException",
    "ConnectionTimeoutException",
    "SecurityException",
    "CredentialNotFoundException",
    "PluginTrustException",
    "AIException",
    "AIRateLimitException",
    "AIContextLengthException",
    "AIResponseParsingException",
    "ReportException",
    "ReportTemplateNotFoundException",
    "ReportRenderException",
]
