"""Analyzer-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import RecoverableError


class BaseAnalyzerException(RecoverableError):
    """Base class for all analyzer failures.

    Carries the ``analyzer_id`` so the orchestrator knows which analyzer
    failed and can skip it while continuing with the rest.
    """

    code = "GRA_ANA_000"
    default_message = "An analyzer failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        analyzer_id: str = "unknown",
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        ctx["analyzer_id"] = analyzer_id
        super().__init__(message, context=ctx, **kwargs)
        self.analyzer_id = analyzer_id


class AnalysisException(BaseAnalyzerException):
    """Generic failure while running an analysis."""

    code = "GRA_ANA_001"
    default_message = "Analysis failed."


class PluginError(RecoverableError):
    """A plugin operation failed (registration, discovery, instantiation...).

    Recoverable: the affected plugin is skipped while the rest continue.
    """

    code = "GRA_ANA_002"
    default_message = "Plugin operation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        analyzer_id: str = "unknown",
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        ctx["analyzer_id"] = analyzer_id
        super().__init__(message, context=ctx, **kwargs)
        self.analyzer_id = analyzer_id


__all__ = ["AnalysisException", "BaseAnalyzerException", "PluginError"]
