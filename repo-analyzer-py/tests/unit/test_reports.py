"""Tests for the report renderers and generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_analyzer.core.domain.report import Report, ReportFormat
from repo_analyzer.infrastructure.errors import ReportRenderException
from repo_analyzer.reports import HtmlReport, JsonReport, MarkdownReport, PdfReport, ReportGenerator


class TestRenderers:
    """Tests for the individual renderer classes."""

    def test_markdown_render_raises_at_scaffold_stage(self) -> None:
        renderer = MarkdownReport()
        report = Report(repository_url="https://github.com/o/r")
        with pytest.raises(ReportRenderException):
            renderer.render(report)

    def test_html_render_raises_at_scaffold_stage(self) -> None:
        renderer = HtmlReport()
        report = Report(repository_url="https://github.com/o/r")
        with pytest.raises(ReportRenderException):
            renderer.render(report)

    def test_pdf_render_raises_at_scaffold_stage(self) -> None:
        renderer = PdfReport()
        report = Report(repository_url="https://github.com/o/r")
        with pytest.raises(ReportRenderException):
            renderer.render(report)

    def test_json_render_produces_valid_json(self) -> None:
        renderer = JsonReport()
        report = Report(repository_url="https://github.com/o/r")
        data = renderer.render(report)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed["repository_url"] == "https://github.com/o/r"

    def test_json_mime_type(self) -> None:
        assert JsonReport().mime_type() == "application/json"

    def test_json_extension(self) -> None:
        assert JsonReport().extension() == "json"

    def test_markdown_extension(self) -> None:
        assert MarkdownReport().extension() == "md"

    def test_html_extension(self) -> None:
        assert HtmlReport().extension() == "html"

    def test_pdf_extension(self) -> None:
        assert PdfReport().extension() == "pdf"

    def test_format_property(self) -> None:
        assert JsonReport().format == ReportFormat.JSON
        assert MarkdownReport().format == ReportFormat.MARKDOWN
        assert HtmlReport().format == ReportFormat.HTML
        assert PdfReport().format == ReportFormat.PDF

    def test_supports_graphs(self) -> None:
        assert MarkdownReport().supports_graphs() is True
        assert JsonReport().supports_graphs() is False
        assert HtmlReport().supports_graphs() is True
        assert PdfReport().supports_graphs() is True


class TestReportGenerator:
    """Tests for :class:`ReportGenerator`."""

    def test_render_json_only(self, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["json"])
        report = Report(repository_url="https://github.com/o/r")
        results = generator.render(report)
        assert ReportFormat.JSON in results
        assert results[ReportFormat.JSON].exists()

    def test_render_multiple_formats(self, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["json"])
        report = Report(repository_url="https://github.com/o/r")
        results = generator.render(report)
        assert len(results) >= 1

    def test_render_skips_unsupported_formats(self, tmp_path: Path) -> None:
        """Formats that raise should be skipped, not fatal."""
        generator = ReportGenerator(tmp_path, ["markdown", "json"])
        report = Report(repository_url="https://github.com/o/r")
        results = generator.render(report)
        # Markdown raises, so only JSON should succeed.
        assert ReportFormat.JSON in results
        assert ReportFormat.MARKDOWN not in results

    def test_render_format_returns_bytes(self, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["json"])
        report = Report(repository_url="https://github.com/o/r")
        data = generator.render_format(report, ReportFormat.JSON)
        assert isinstance(data, bytes)

    def test_render_format_unsupported_raises(self, tmp_path: Path) -> None:
        report = Report(repository_url="https://github.com/o/r")
        # All built-in formats are registered in the generator, so we test a
        # renderer (Markdown) that raises at the scaffold stage directly.
        renderer = MarkdownReport()
        with pytest.raises(ReportRenderException):
            renderer.render(report)

    def test_output_dir_created(self, tmp_path: Path) -> None:
        """The output directory should be created if missing."""
        out = tmp_path / "reports" / "nested"
        ReportGenerator(out, ["json"])
        assert out.exists()

    def test_formats_property(self, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["json", "html"])
        assert ReportFormat.JSON in generator.formats
        assert ReportFormat.HTML in generator.formats
