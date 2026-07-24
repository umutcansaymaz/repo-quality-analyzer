"""Report-related exceptions."""

from __future__ import annotations

from typing import Any

from repo_analyzer.infrastructure.errors.base import RecoverableError


class ReportException(RecoverableError):
    """A report generation / rendering operation failed.

    Recoverable: other formats can still be produced.
    """

    code = "GRA_RPT_001"
    default_message = "Report generation failed."

    def __init__(
        self,
        message: str | None = None,
        *,
        format: str | None = None,
        context: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        ctx = dict(context) if context else {}
        if format:
            ctx["format"] = format
        super().__init__(message, context=ctx, **kwargs)
        self.format = format


class ReportTemplateNotFoundException(ReportException):
    """A report template was not found."""

    code = "GRA_RPT_002"
    default_message = "Report template not found."


class ReportRenderException(ReportException):
    """Rendering a report to its target format failed."""

    code = "GRA_RPT_003"
    default_message = "Failed to render report."


__all__ = [
    "ReportException",
    "ReportRenderException",
    "ReportTemplateNotFoundException",
]
