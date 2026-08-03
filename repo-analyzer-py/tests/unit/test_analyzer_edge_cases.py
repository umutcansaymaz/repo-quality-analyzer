"""Edge-case tests for the analysis engines."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from repo_analyzer.analyzers.ast.analyzer import ASTAnalyzer
from repo_analyzer.analyzers.ast.tree_sitter_loader import TreeSitterLoader
from repo_analyzer.analyzers.filesystem.analyzer import FilesystemAnalyzer
from repo_analyzer.analyzers.imports.analyzer import ImportAnalyzer
from repo_analyzer.analyzers.metrics.analyzer import MetricEngine
from repo_analyzer.analyzers.test_coverage.analyzer import TestAnalyzer
from repo_analyzer.core.domain.repository import parse_repository_url


@pytest.fixture()
def repo() -> Any:
    return parse_repository_url("https://github.com/test/edge-repo")


class TestFilesystemEdgeCases:
    def test_empty_directory(self, repo: Any, tmp_path: Path) -> None:
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["total_files"] == 0

    def test_symlink_handling(self, repo: Any, tmp_path: Path) -> None:
        target = tmp_path / "target.txt"
        target.write_text("x")
        link = tmp_path / "link.txt"
        os.symlink(target, link)
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["symlinks"] >= 1

    def test_duplicate_detection(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("identical content")
        (tmp_path / "b.txt").write_text("identical content")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["duplicate_files"] >= 2

    def test_binary_detection(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "data.bin").write_bytes(b"\x00\x01\x02\x03\x00")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["binary_files"] >= 1

    def test_generated_file_detection(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "module.pyc").write_bytes(b"x")
        (tmp_path / "package-lock.json").write_text("{}")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["file_inventory"]["generated_files"] >= 2

    def test_gitignore_respected(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / ".gitignore").write_text("*.log\n")
        (tmp_path / "app.log").write_text("log")
        (tmp_path / "app.py").write_text("print('hi')")
        analyzer = FilesystemAnalyzer()
        result = analyzer.run(repo, tmp_path)
        files = result["file_inventory"]["files"]
        assert "app.log" not in files
        assert "app.py" in files


class TestASTEdgeCases:
    def test_handles_syntax_error(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "broken.py").write_text("def broken(:\n    pass\n")
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, tmp_path)
        # Should not crash; symbols may be empty.
        assert "symbols" in result

    def test_handles_empty_file(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("")
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["symbols"]["functions"] == []

    def test_javascript_parsing(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app.js").write_text(
            "function add(a, b) { return a + b; }\n"
            "class Foo { bar() { return 1; } }\n"
            "import x from 'lib';\n"
            "export default add;\n"
        )
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, tmp_path)
        symbols = result["symbols"]
        assert len(symbols["functions"]) >= 1

    def test_typescript_parsing(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app.ts").write_text("function greet(name: string): string { return name; }\n")
        analyzer = ASTAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert len(result["symbols"]["functions"]) >= 1


class TestTreeSitterLoader:
    def test_language_for_file_python(self) -> None:
        loader = TreeSitterLoader()
        assert loader.language_for_file(Path("test.py")) == "python"

    def test_language_for_file_unknown(self) -> None:
        loader = TreeSitterLoader()
        assert loader.language_for_file(Path("test.xyz")) is None

    def test_parse_returns_none_for_unknown(self) -> None:
        loader = TreeSitterLoader()
        assert loader.parse("nonexistent", "content") is None

    def test_parse_python(self) -> None:
        loader = TreeSitterLoader()
        tree = loader.parse("python", "def f():\n    pass\n")
        assert tree is not None

    def test_available_languages(self) -> None:
        loader = TreeSitterLoader()
        langs = loader.available_languages()
        assert "python" in langs


class TestImportAnalyzerEdgeCases:
    def test_handles_invalid_python(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "bad.py").write_text("def broken(:\n")
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert "import_analysis" in result

    def test_detects_js_imports(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app.js").write_text("import react from 'react';\nconst fs = require('fs');\n")
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, tmp_path)
        graph = result["import_analysis"]["import_graph"]
        assert "app.js" in graph

    def test_empty_workspace(self, repo: Any, tmp_path: Path) -> None:
        analyzer = ImportAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["import_analysis"]["import_graph"] == {}


class TestMetricEngineEdgeCases:
    def test_empty_file(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "empty.py").write_text("")
        analyzer = MetricEngine()
        result = analyzer.run(repo, tmp_path)
        assert result["metrics_report"]["total_loc"] == 0

    def test_comment_only_file(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "comments.py").write_text("# just a comment\n# another\n")
        analyzer = MetricEngine()
        result = analyzer.run(repo, tmp_path)
        report = result["metrics_report"]
        assert report["total_comment_lines"] == 2

    def test_non_python_file_skipped(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "data.txt").write_text("not python")
        analyzer = MetricEngine()
        result = analyzer.run(repo, tmp_path)
        assert result["metrics_report"]["total_loc"] == 0


class TestTestAnalyzerEdgeCases:
    def test_no_tests(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app.py").write_text("print('hi')")
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["test_analysis"]["total_test_files"] == 0

    def test_go_test_file(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app_test.go").write_text(
            'package main\nimport "testing"\nfunc TestX(t *testing.T) {}\n'
        )
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["test_analysis"]["total_test_files"] >= 1
        assert "go-testing" in result["test_analysis"]["frameworks"]

    def test_jest_test_file(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "app.test.js").write_text("test('adds', () => { expect(1+1).toBe(2); });\n")
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["test_analysis"]["total_test_files"] >= 1

    def test_coverage_from_xml(self, repo: Any, tmp_path: Path) -> None:
        (tmp_path / "coverage.xml").write_text(
            '<?xml version="1.0" ?>\n<coverage line-rate="0.85"></coverage>\n'
        )
        analyzer = TestAnalyzer()
        result = analyzer.run(repo, tmp_path)
        assert result["test_analysis"]["estimated_coverage"] == 85.0
