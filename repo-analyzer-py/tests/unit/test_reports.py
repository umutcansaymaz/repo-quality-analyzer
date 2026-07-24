"""Tests for the report renderers and generator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.reports import (
    SCHEMA_VERSION,
    HtmlRenderer,
    JsonRenderer,
    MarkdownRenderer,
    PdfRenderer,
    ReportGenerator,
)


@pytest.fixture()
def sample_result() -> AnalysisResult:
    """A minimal AnalysisResult for renderer tests."""
    repo = parse_repository_url("https://github.com/test/sample")
    return AnalysisResult(repository=repo)


@pytest.fixture()
def populated_result(sample_workspace: Path) -> AnalysisResult:
    """A populated AnalysisResult built from the sample fixture."""
    from repo_analyzer.adapters.cache import SQLiteCacheAdapter
    from repo_analyzer.adapters.llm import MockLLMProvider
    from repo_analyzer.core.orchestrator import Orchestrator

    repo = parse_repository_url("https://github.com/test/sample-repo")
    cache = SQLiteCacheAdapter(sample_workspace / ".test-cache.db")
    orchestrator = Orchestrator(cache, llm=MockLLMProvider())

    # Patch clone to use the fixture directly.
    def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
        return sample_workspace, repository

    orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
    try:
        result = orchestrator.analyze(repo)
    finally:
        cache.close()
    return result


class TestMarkdownRenderer:
    def test_render_produces_markdown(self, sample_result: AnalysisResult) -> None:
        renderer = MarkdownRenderer()
        data = renderer.render(sample_result)
        text = data.decode("utf-8")
        assert "# Repository Analysis Report" in text
        assert "## 1. Executive Summary" in text

    def test_render_has_all_sections(self, populated_result: AnalysisResult) -> None:
        renderer = MarkdownRenderer()
        text = renderer.render(populated_result).decode("utf-8")
        for section in [
            "## 1. Executive Summary",
            "## 2. Repository Overview",
            "## 3. Repository Statistics",
            "## 4. File System Analysis",
            "## 5. Language Analysis",
            "## 6. Complexity Analysis",
            "## 7. Dependency Analysis",
            "## 8. Git Analysis",
            "## 9. Security Findings",
            "## 10. Architecture Review",
            "## 11. Technical Debt",
            "## 12. Risk Assessment",
            "## 13. AI Review",
            "## 14. Quick Wins",
            "## 15. Refactor Roadmap",
            "## 16. Overall Health",
            "## 17. Appendix",
        ]:
            assert section in text, f"Missing section: {section}"

    def test_extension(self) -> None:
        assert MarkdownRenderer().extension() == "md"

    def test_mime_type(self) -> None:
        assert MarkdownRenderer().mime_type() == "text/markdown"


class TestJsonRenderer:
    def test_render_produces_valid_json(self, sample_result: AnalysisResult) -> None:
        renderer = JsonRenderer()
        data = renderer.render(sample_result)
        payload = json.loads(data.decode("utf-8"))
        assert payload["schema_version"] == SCHEMA_VERSION
        assert "analysis" in payload
        assert "generated_at" in payload

    def test_schema_version(self) -> None:
        assert SCHEMA_VERSION == "1.0.0"

    def test_extension(self) -> None:
        assert JsonRenderer().extension() == "json"


class TestHtmlRenderer:
    def test_render_produces_html(self, sample_result: AnalysisResult) -> None:
        renderer = HtmlRenderer()
        data = renderer.render(sample_result)
        text = data.decode("utf-8")
        assert "<!DOCTYPE html>" in text
        assert "<html" in text

    def test_has_theme_toggle(self, sample_result: AnalysisResult) -> None:
        renderer = HtmlRenderer()
        text = renderer.render(sample_result).decode("utf-8")
        assert "theme-toggle" in text
        assert "data-theme" in text

    def test_has_search(self, sample_result: AnalysisResult) -> None:
        renderer = HtmlRenderer()
        text = renderer.render(sample_result).decode("utf-8")
        assert "search-box" in text

    def test_has_css(self, sample_result: AnalysisResult) -> None:
        renderer = HtmlRenderer()
        text = renderer.render(sample_result).decode("utf-8")
        assert "<style>" in text
        assert "--bg" in text  # CSS variable

    def test_has_dark_mode(self, sample_result: AnalysisResult) -> None:
        renderer = HtmlRenderer()
        text = renderer.render(sample_result).decode("utf-8")
        assert "dark" in text

    def test_extension(self) -> None:
        assert HtmlRenderer().extension() == "html"


class TestPdfRenderer:
    def test_render_produces_pdf(self, sample_result: AnalysisResult) -> None:
        renderer = PdfRenderer()
        data = renderer.render(sample_result)
        # PDF files start with %PDF.
        assert data[:4] == b"%PDF"

    def test_has_cover_page(self, sample_result: AnalysisResult) -> None:
        renderer = PdfRenderer()
        text = renderer._cover_page(sample_result)
        assert "Repository Analysis Report" in text

    def test_has_toc(self) -> None:
        renderer = PdfRenderer()
        text = renderer._table_of_contents()
        assert "Table of Contents" in text
        assert "Repository Overview" in text

    def test_extension(self) -> None:
        assert PdfRenderer().extension() == "pdf"


class TestReportGenerator:
    def test_render_all_formats(self, populated_result: AnalysisResult, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["md", "json", "html"])
        paths = generator.render(populated_result)
        assert len(paths) >= 2  # at least 2 should succeed
        for path in paths.values():
            assert path.exists()

    def test_render_markdown(self, populated_result: AnalysisResult, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["md"])
        paths = generator.render(populated_result)
        assert any(p.suffix == ".md" for p in paths.values())

    def test_render_json(self, populated_result: AnalysisResult, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["json"])
        paths = generator.render(populated_result)
        json_path = next(p for p in paths.values() if p.suffix == ".json")
        data = json.loads(json_path.read_text())
        assert data["schema_version"] == SCHEMA_VERSION

    def test_render_html(self, populated_result: AnalysisResult, tmp_path: Path) -> None:
        generator = ReportGenerator(tmp_path, ["html"])
        paths = generator.render(populated_result)
        html_path = next(p for p in paths.values() if p.suffix == ".html")
        assert "<!DOCTYPE html>" in html_path.read_text()

    def test_render_format_returns_bytes(
        self, populated_result: AnalysisResult, tmp_path: Path
    ) -> None:
        from repo_analyzer.core.domain.report import ReportFormat

        generator = ReportGenerator(tmp_path, ["json"])
        data = generator.render_format(populated_result, ReportFormat.JSON)
        assert isinstance(data, bytes)

    def test_output_dir_created(self, tmp_path: Path) -> None:
        out = tmp_path / "reports" / "nested"
        ReportGenerator(out, ["json"])
        assert out.exists()

    def test_format_alias_md(self, populated_result: AnalysisResult, tmp_path: Path) -> None:
        """The 'md' alias should map to 'markdown'."""
        generator = ReportGenerator(tmp_path, ["md"])
        assert len(generator.formats) == 1
        from repo_analyzer.core.domain.report import ReportFormat

        assert generator.formats[0] == ReportFormat.MARKDOWN
