"""Output port (abstract interface for report renderers)."""

from __future__ import annotations

from abc import ABC, abstractmethod

from repo_analyzer.core.domain.report import Report, ReportFormat


class OutputPort(ABC):
    """Abstract interface for a report renderer.

    Each supported output format (Markdown, JSON, HTML, PDF) is a separate
    adapter implementing this port. New formats can be added without
    touching the report generator (ADR-007).
    """

    @abstractmethod
    def render(self, report: Report) -> bytes:
        """Render ``report`` into the target format.

        Args:
            report: The report to render.

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
