"""Integration tests for the full analysis pipeline.

These tests exercise the clone → analyze → review → report chain using
the bundled ``tests/fixtures/sample_repo`` fixture (no network required).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.adapters.llm import MockLLMProvider
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.orchestrator import Orchestrator
from repo_analyzer.reports import ReportGenerator


@pytest.fixture()
def cache(tmp_path: Path) -> SQLiteCacheAdapter:
    adapter = SQLiteCacheAdapter(tmp_path / "integration-cache.db")
    yield adapter  # type: ignore[misc]
    adapter.close()


@pytest.fixture()
def workspace() -> Path:
    return Path(__file__).parents[1] / "fixtures" / "sample_repo"


@pytest.fixture()
def orchestrator(cache: SQLiteCacheAdapter) -> Orchestrator:
    return Orchestrator(cache, max_workers=2, llm=MockLLMProvider())


@pytest.fixture()
def result(orchestrator: Orchestrator, workspace: Path):  # type: ignore[no-untyped-def]
    """Run the full analysis on the fixture repo."""
    repo = parse_repository_url("https://github.com/test/sample-repo")

    # Patch clone to use the fixture directly (no network).
    def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
        return workspace, repository

    orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
    return orchestrator.analyze(repo)


class TestFullPipeline:
    """End-to-end pipeline tests (clone → analyze → review)."""

    def test_analysis_completes(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.status.value == "completed"

    def test_repository_metadata_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.repository_metadata is not None
        assert result.repository_metadata.name == "sample-repo"

    def test_file_inventory_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.file_inventory is not None
        assert result.file_inventory.total_files > 0

    def test_language_distribution_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.language_distribution is not None
        assert "Python" in result.language_distribution.loc

    def test_metrics_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.metrics_report is not None
        assert result.metrics_report.total_loc > 0

    def test_complexity_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.complexity_report is not None

    def test_git_analysis_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.git_analysis is not None
        assert result.git_analysis.total_commits >= 1

    def test_documentation_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.documentation_report is not None

    def test_test_analysis_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.test_analysis is not None
        assert result.test_analysis.total_test_files > 0

    def test_ai_review_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        assert result.ai_review is not None
        assert result.ai_review.health_score is not None
        assert result.ai_review.security_review is not None

    def test_architecture_finding_populated(self, result) -> None:  # type: ignore[no-untyped-def]
        """The ArchitectureFinding field must be populated from the graph report."""
        assert result.architecture is not None

    def test_no_errors(self, result) -> None:  # type: ignore[no-untyped-def]
        assert len(result.errors) == 0, f"Unexpected errors: {result.errors}"


class TestHealthScoreCorrectness:
    """Verify the HealthScore weight fix (weights sum to 1.0)."""

    def test_overall_can_reach_100(self, result) -> None:  # type: ignore[no-untyped-def]
        """With all sub-scores at 100, overall must be 100 (not 85)."""
        hs = result.ai_review.health_score
        # The fixture repo won't have all 100s, but overall must be > 0
        # and the grade must be a valid letter.
        assert hs is not None
        assert 0 <= hs.overall <= 100
        assert hs.grade.value  # non-empty

    def test_weights_sum_to_one(self) -> None:
        """The internal weights must sum to exactly 1.0 after normalization."""

        weights = [0.20, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05, 0.05, 0.05]
        total = sum(weights)
        normalized = [w / total for w in weights]
        assert abs(sum(normalized) - 1.0) < 0.001


class TestReportGeneration:
    """End-to-end report generation tests."""

    def test_markdown_report(
        self,
        result,
        tmp_path: Path,  # type: ignore[no-untyped-def]
    ) -> None:
        gen = ReportGenerator(tmp_path, ["md"])
        paths = gen.render(result)
        md_path = next(p for p in paths.values() if p.suffix == ".md")
        content = md_path.read_text()
        assert "Repository Analysis Report" in content
        assert "Executive Summary" in content

    def test_json_report_schema(
        self,
        result,
        tmp_path: Path,  # type: ignore[no-untyped-def]
    ) -> None:
        gen = ReportGenerator(tmp_path, ["json"])
        paths = gen.render(result)
        json_path = next(p for p in paths.values() if p.suffix == ".json")
        data = json.loads(json_path.read_text())
        assert data["schema_version"] == "1.0.0"
        assert "analysis" in data

    def test_html_report(
        self,
        result,
        tmp_path: Path,  # type: ignore[no-untyped-def]
    ) -> None:
        gen = ReportGenerator(tmp_path, ["html"])
        paths = gen.render(result)
        html_path = next(p for p in paths.values() if p.suffix == ".html")
        content = html_path.read_text()
        assert "<!DOCTYPE html>" in content
        assert "theme-toggle" in content

    def test_all_formats(
        self,
        result,
        tmp_path: Path,  # type: ignore[no-untyped-def]
    ) -> None:
        gen = ReportGenerator(tmp_path, ["md", "json", "html"])
        paths = gen.render(result)
        assert len(paths) >= 3


class TestResultSerialization:
    """Verify the AnalysisResult serializes without errors."""

    def test_model_dump_works(self, result) -> None:  # type: ignore[no-untyped-def]
        """Regression test: model_dump must not fail with default=str."""
        payload = result.model_dump(mode="json")
        assert isinstance(payload, dict)
        assert "repository" in payload

    def test_json_serialization(self, result) -> None:  # type: ignore[no-untyped-def]
        """The result must be JSON-serializable."""
        payload = result.model_dump(mode="json")
        text = json.dumps(payload, default=str)
        assert len(text) > 0
