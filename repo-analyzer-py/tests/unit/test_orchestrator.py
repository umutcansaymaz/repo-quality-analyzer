"""Tests for the :class:`Orchestrator` and :class:`CloneService`.

These tests use the bundled ``tests/fixtures/sample_repo`` working tree so
no network access is required. The clone service is tested with a mocked
provider to avoid real git operations.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.adapters.vcs.clone_service import CloneService
from repo_analyzer.adapters.vcs.factory import DefaultRepositoryProviderFactory
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.orchestrator import Orchestrator


@pytest.fixture()
def cache(tmp_path: Path) -> SQLiteCacheAdapter:
    adapter = SQLiteCacheAdapter(tmp_path / "cache.db")
    yield adapter  # type: ignore[misc]
    adapter.close()


class TestOrchestrator:
    """Tests for :class:`Orchestrator` running against the sample fixture."""

    def test_analyze_local_repo(self, cache: SQLiteCacheAdapter, sample_workspace: Path) -> None:
        """The orchestrator should run all analyzers on a local workspace."""
        # We simulate a "clone" by copying the fixture into the cache dir.
        repo = parse_repository_url("https://github.com/test/sample-repo")

        # Patch the clone service to return the fixture path directly.
        orchestrator = Orchestrator(cache, max_workers=2)
        # Monkeypatch the clone method to skip real git and use the fixture.
        original_clone = orchestrator._clone_service.clone  # type: ignore[attr-defined]

        def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
            return sample_workspace, repository

        orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
        try:
            result = orchestrator.analyze(repo)
        finally:
            orchestrator._clone_service.clone = original_clone  # type: ignore[method-assign]

        assert result.status.value == "completed"
        assert result.repository_metadata is not None
        assert result.file_inventory is not None
        assert result.language_distribution is not None
        assert result.symbols is not None
        assert result.metrics_report is not None
        assert result.documentation_report is not None

    def test_analyze_populates_analysis_result(
        self, cache: SQLiteCacheAdapter, sample_workspace: Path
    ) -> None:
        """The result should contain structured outputs from each analyzer."""
        repo = parse_repository_url("https://github.com/test/sample-repo")
        orchestrator = Orchestrator(cache, max_workers=2)

        def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
            return sample_workspace, repository

        orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
        result = orchestrator.analyze(repo)

        assert result.metrics_report is not None
        assert result.metrics_report.total_loc > 0
        assert result.metrics_report.total_functions > 0
        assert result.file_inventory is not None
        assert result.file_inventory.total_files > 0
        assert result.test_analysis is not None
        assert result.test_analysis.total_test_files > 0

    def test_analyze_records_errors_for_failed_analyzers(
        self, cache: SQLiteCacheAdapter, sample_workspace: Path
    ) -> None:
        """A failing analyzer should be recorded in ``errors``, not abort."""
        repo = parse_repository_url("https://github.com/test/sample-repo")
        orchestrator = Orchestrator(cache, max_workers=2)

        def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
            return sample_workspace, repository

        orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]

        # Make one analyzer fail.
        bad_analyzer = MagicMock()
        bad_analyzer.name = "bad"
        bad_analyzer.version = "0.0.0"
        bad_analyzer.phase = 0
        bad_analyzer.metadata.return_value = {"name": "bad"}
        bad_analyzer.initialize.return_value = None
        bad_analyzer.can_run.return_value = True
        bad_analyzer.run.side_effect = RuntimeError("boom")
        bad_analyzer.dispose.return_value = None
        orchestrator._analyzers = [bad_analyzer]  # type: ignore[attr-defined]

        result = orchestrator.analyze(repo)
        # The run should still complete (the error is non-fatal).
        assert result.status.value == "completed"
        assert len(result.errors) >= 1


class TestCloneService:
    """Tests for :class:`CloneService` with a mocked provider."""

    def test_clone_uses_cache_on_second_call(
        self, cache: SQLiteCacheAdapter, tmp_path: Path
    ) -> None:
        """A second clone of the same repo should hit the cache."""

        # Build a mock provider that "clones" by creating a file in dest.
        def fake_clone(repository, destination):  # type: ignore[no-untyped-def]
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "README.md").write_text("# fake")
            return destination

        mock_provider = MagicMock()
        mock_provider.can_handle.return_value = True
        resolved = parse_repository_url("https://github.com/test/repo").model_copy(
            update={"commit_sha": "abc123"}
        )
        mock_provider.resolve.return_value = resolved
        mock_provider.clone.side_effect = fake_clone

        factory = DefaultRepositoryProviderFactory()
        factory._providers = [mock_provider]  # type: ignore[attr-defined]

        service = CloneService(cache, factory=factory, max_retries=1)
        repo = parse_repository_url("https://github.com/test/repo")

        # First call: clone (miss).
        path1, _ = service.clone(repo, use_cache=True)
        assert path1.exists()
        assert mock_provider.clone.call_count == 1

        # Second call: cache hit (provider.clone not called again).
        path2, _ = service.clone(repo, use_cache=True)
        assert path2.exists()
        assert mock_provider.clone.call_count == 1  # unchanged


class TestAnalysisResultIntegration:
    """Verify the AnalysisResult aggregate holds all analyzer outputs."""

    def test_result_serializes_to_json(
        self, cache: SQLiteCacheAdapter, sample_workspace: Path
    ) -> None:
        """The full AnalysisResult should serialize to JSON without errors."""
        repo = parse_repository_url("https://github.com/test/sample-repo")
        orchestrator = Orchestrator(cache, max_workers=2)

        def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
            return sample_workspace, repository

        orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
        result = orchestrator.analyze(repo)

        payload = result.model_dump(mode="json")
        assert "repository" in payload
        assert "repository_metadata" in payload
        assert "file_inventory" in payload
        assert "language_distribution" in payload
        assert "metrics_report" in payload
        assert "status" in payload
        assert payload["status"] == "completed"

    def test_result_has_commit_sha(self, cache: SQLiteCacheAdapter, sample_workspace: Path) -> None:
        """The result should carry the resolved commit SHA."""
        repo = parse_repository_url("https://github.com/test/sample-repo")
        repo = repo.model_copy(update={"commit_sha": "deadbeef"})
        orchestrator = Orchestrator(cache, max_workers=2)

        def fake_clone(repository, *, cancel_event=None, progress=None, use_cache=True):  # type: ignore[no-untyped-def]
            return sample_workspace, repository

        orchestrator._clone_service.clone = fake_clone  # type: ignore[method-assign]
        result = orchestrator.analyze(repo)
        assert result.commit_sha == "deadbeef"
