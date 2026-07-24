"""Output port (abstract interface for report renderers).

The ``render`` method accepts any reportable object (currently
:class:`AnalysisResult`). Keeping the parameter typed as ``Any`` allows new
report shapes to be added without breaking the port contract.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from repo_analyzer.core.domain.report import ReportFormat


class OutputPort(ABC):
    """Abstract interface for a report renderer.

    Each supported output format (Markdown, JSON, HTML, PDF) is a separate
    adapter implementing this port. New formats can be added without
    touching the report generator (ADR-007).
    """

    @abstractmethod
    def render(self, report: Any) -> bytes:
        """Render ``report`` into the target format.

        Args:
            report: The reportable object (typically an
                :class:`AnalysisResult`).

        Returns:
            The rendered content as bytes.
        """

    @abstractmethod
    def supports_graphs(self) -> bool:
        """Return ``True`` if the format supports embedded graphs."""

    @abstractmethod
    def mime_type(self) -> str:
        """Return the MIME type of the rendered output."""

    @abstractmethod
    def extension(self) -> str:
        """Return the file extension (without the dot)."""

    @property
    @abstractmethod
    def format(self) -> ReportFormat:
        """The :class:`ReportFormat` this renderer produces."""


__all__ = ["OutputPort"]
