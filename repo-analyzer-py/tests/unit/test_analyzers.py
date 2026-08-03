"""Tests for the built-in analysis engines.

These tests use the bundled ``tests/fixtures/sample_repo`` working tree so
that no network access is required. Each analyzer is exercised against the
fixture and its structured output is validated.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyzer.analyzers.architecture.analyzer import GraphEngine
from repo_analyzer.analyzers.ast.analyzer import ASTAnalyzer
from repo_analyzer.analyzers.complexity.analyzer import ComplexityAnalyzer
from repo_analyzer.analyzers.dependency.analyzer import DependencyAnalyzer
from repo_analyzer.analyzers.documentation.analyzer import DocumentationAnalyzer
from repo_analyzer.analyzers.filesystem.analyzer import FilesystemAnalyzer
from repo_analyzer.analyzers.git_history.analyzer import GitAnalyzer
from repo_analyzer.analyzers.imports.analyzer import ImportAnalyzer
from repo_analyzer.analyzers.language.analyzer import LanguageDetector
from repo_analyzer.analyzers.metrics.analyzer import MetricEngine
from repo_analyzer.analyzers.repository_detector.analyzer import RepositoryDetector
from repo_analyzer.analyzers.test_coverage.analyzer import TestAnalyzer
from repo_analyzer.core.domain.repository import parse_repository_url


@pytest.fixture()
def repo(sample_workspace: Path):  # type: ignore[no-untyped-def]
    return parse_repository_url("https://github.com/test/sample-repo")


# ---------------------------------------------------------------------------
# FilesystemAnalyzer
# ---------------------------------------------------------------------------


class TestFilesystemAnalyzer:
    def test_scans_files(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        inv = result["file_inventory"]
        assert inv["total_files"] > 0
        assert inv["total_directories"] >= 0
        assert inv["total_bytes"] > 0

    def test_detects_extension_distribution(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        exts = result["file_inventory"]["extension_distribution"]
        assert "py" in exts
        assert "md" in exts

    def test_detects_empty_files(self, repo, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        (tmp_path / "empty.txt").write_text("")
        (tmp_path / "full.txt").write_text("content")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["empty_files"] >= 1

    def test_detects_hidden_files(self, repo, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        (tmp_path / ".hidden").write_text("x")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["hidden_files"] >= 1

    def test_can_run(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = FilesystemAnalyzer()
        assert analyzer.can_run(repo, sample_workspace) is True

    def test_metadata(self) -> None:
        analyzer = FilesystemAnalyzer()
        meta = analyzer.metadata()
        assert meta["name"] == "filesystem"
        assert meta["phase"] == 0


# ---------------------------------------------------------------------------
# LanguageDetector
# ---------------------------------------------------------------------------


class TestLanguageDetector:
    def test_detects_python(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = LanguageDetector()
        result = analyzer.run(repo, sample_workspace)
        dist = result["language_distribution"]
        assert "Python" in dist["loc"]
        assert dist["loc"]["Python"] > 0

    def test_detects_markdown(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = LanguageDetector()
        result = analyzer.run(repo, sample_workspace)
        dist = result["language_distribution"]
        assert "Markdown" in dist["loc"]

    def test_primary_language(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = LanguageDetector()
        result = analyzer.run(repo, sample_workspace)
        dist = result["language_distribution"]
        # Python should dominate.
        assert dist["loc"]["Python"] == max(dist["loc"].values())

    def test_shebang_detection(self, repo, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        script = tmp_path / "script"
        script.write_text("#!/usr/bin/env python3\nprint('hi')\n")
        analyzer = LanguageDetector()
        result = analyzer.run(repo, tmp_path)
        dist = result["language_distribution"]
        assert "Python" in dist["loc"]


# ---------------------------------------------------------------------------
# ASTAnalyzer
# ---------------------------------------------------------------------------


class TestASTAnalyzer:
    def test_extracts_functions(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        symbols = result["symbols"]
        names = [f["name"] for f in symbols["functions"]]
        assert "greet" in names
        assert "complex_function" in names

    def test_extracts_classes(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        symbols = result["symbols"]
        names = [c["name"] for c in symbols["classes"]]
        assert "Animal" in names
        assert "Dog" in names

    def test_extracts_inheritance(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        symbols = result["symbols"]
        parents = [i["parent"] for i in symbols["inheritances"]]
        assert "Animal" in parents

    def test_extracts_imports(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        symbols = result["symbols"]
        assert len(symbols["imports"]) > 0


# ---------------------------------------------------------------------------
# ImportAnalyzer
# ---------------------------------------------------------------------------


class TestImportAnalyzer:
    def test_builds_import_graph(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        graph = result["import_analysis"]["import_graph"]
        assert len(graph) > 0

    def test_detects_unused_imports(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        unused = result["import_analysis"]["unused_imports"]
        # The fixture intentionally imports an unused module.
        names = [u["name"] for u in unused]
        assert "unused_module" in names

    def test_classifies_external_internal(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["import_analysis"]
        assert len(analysis["external_dependencies"]) > 0
        assert len(analysis["internal_dependencies"]) >= 0


# ---------------------------------------------------------------------------
# DependencyAnalyzer
# ---------------------------------------------------------------------------


class TestDependencyAnalyzer:
    def test_parses_requirements(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DependencyAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        deps = result["dependency_analysis"]["dependencies"]
        names = [d["name"] for d in deps]
        assert "requests" in names
        assert "pyyaml" in names

    def test_parses_pyproject(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DependencyAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        ecosystems = result["dependency_analysis"]["ecosystems"]
        assert "pypi" in ecosystems

    def test_parses_package_json(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DependencyAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        deps = result["dependency_analysis"]["dependencies"]
        names = [d["name"] for d in deps]
        assert "lodash" in names
        assert "npm" in result["dependency_analysis"]["ecosystems"]

    def test_total_dependencies(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DependencyAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        assert result["dependency_analysis"]["total_dependencies"] > 0


# ---------------------------------------------------------------------------
# MetricEngine
# ---------------------------------------------------------------------------


class TestMetricEngine:
    def test_computes_loc(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = MetricEngine()
        result = analyzer.run(repo, sample_workspace)
        report = result["metrics_report"]
        assert report["total_loc"] > 0
        assert report["total_sloc"] > 0

    def test_counts_functions_classes(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = MetricEngine()
        result = analyzer.run(repo, sample_workspace)
        report = result["metrics_report"]
        assert report["total_functions"] > 0
        assert report["total_classes"] > 0

    def test_comment_ratio(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = MetricEngine()
        result = analyzer.run(repo, sample_workspace)
        report = result["metrics_report"]
        assert 0 <= report["overall_comment_ratio"] <= 1

    def test_per_file_metrics(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = MetricEngine()
        result = analyzer.run(repo, sample_workspace)
        report = result["metrics_report"]
        assert len(report["per_file"]) > 0


# ---------------------------------------------------------------------------
# ComplexityAnalyzer
# ---------------------------------------------------------------------------


class TestComplexityAnalyzer:
    def test_finds_complex_functions(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ComplexityAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        funcs = result["complexity_report"]["top_complex_functions"]
        names = [f["name"] for f in funcs]
        assert "complex_function" in names

    def test_complex_function_high_complexity(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ComplexityAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        funcs = result["complexity_report"]["top_complex_functions"]
        complex_fn = next(f for f in funcs if f["name"] == "complex_function")
        assert complex_fn["complexity"] > 1

    def test_maintainability_index(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = ComplexityAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        mi = result["complexity_report"]["maintainability_index"]
        assert len(mi) > 0


# ---------------------------------------------------------------------------
# GitAnalyzer
# ---------------------------------------------------------------------------


class TestGitAnalyzer:
    def test_can_run(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GitAnalyzer()
        assert analyzer.can_run(repo, sample_workspace) is True

    def test_cannot_run_without_git(self, repo, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GitAnalyzer()
        assert analyzer.can_run(repo, tmp_path) is False

    def test_finds_commits(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GitAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["git_analysis"]
        assert analysis["total_commits"] >= 1

    def test_finds_contributors(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GitAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["git_analysis"]
        assert analysis["total_authors"] >= 1


# ---------------------------------------------------------------------------
# DocumentationAnalyzer
# ---------------------------------------------------------------------------


class TestDocumentationAnalyzer:
    def test_has_installation(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert report["has_installation"] is True

    def test_has_usage(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert report["has_usage_example"] is True

    def test_has_license(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert report["has_license"] is True

    def test_has_changelog(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert report["has_changelog"] is True

    def test_docstring_coverage(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert report["docstring_coverage"] > 0

    def test_readme_score(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = DocumentationAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        report = result["documentation_report"]
        assert 0 < report["readme_score"] <= 1


# ---------------------------------------------------------------------------
# TestAnalyzer
# ---------------------------------------------------------------------------


class TestTestAnalyzerAnalysis:
    def test_detects_pytest(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["test_analysis"]
        assert "pytest" in analysis["frameworks"]

    def test_finds_test_files(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["test_analysis"]
        assert analysis["total_test_files"] >= 1

    def test_finds_test_functions(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["test_analysis"]
        assert analysis["total_test_functions"] >= 1

    def test_has_unit_tests(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, sample_workspace)
        analysis = result["test_analysis"]
        assert analysis["has_unit_tests"] is True


# ---------------------------------------------------------------------------
# GraphEngine
# ---------------------------------------------------------------------------


class TestGraphEngine:
    def test_builds_import_graph(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GraphEngine()
        result = analyzer.run(repo, sample_workspace)
        graph = result["graph_report"]["import_graph"]
        assert graph["nodes"] > 0

    def test_builds_directory_graph(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GraphEngine()
        result = analyzer.run(repo, sample_workspace)
        graph = result["graph_report"]["directory_graph"]
        assert graph["nodes"] > 0

    def test_builds_module_graph(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = GraphEngine()
        result = analyzer.run(repo, sample_workspace)
        graph = result["graph_report"]["module_graph"]
        assert graph["nodes"] >= 0


# ---------------------------------------------------------------------------
# RepositoryDetector
# ---------------------------------------------------------------------------


class TestRepositoryDetector:
    def test_detects_name_owner(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["name"] == "sample-repo"
        assert meta["owner"] == "test"

    def test_detects_license(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["license"] == "MIT"

    def test_detects_default_branch(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["default_branch"] in {"main", "master"}

    def test_detects_total_commits(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["total_commits"] is not None
        assert meta["total_commits"] >= 1

    def test_detects_readme(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["readme_path"] is not None

    def test_detects_size(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert meta["size_bytes"] is not None
        assert meta["size_bytes"] > 0

    def test_detects_contributors(self, repo, sample_workspace: Path) -> None:  # type: ignore[no-untyped-def]
        analyzer = RepositoryDetector()
        result = analyzer.run(repo, sample_workspace)
        meta = result["repository_metadata"]
        assert len(meta["contributors"]) >= 1
