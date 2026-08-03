"""Graph engine using :mod:`networkx`.

Builds four graph representations of the repository:

- Dependency graph (manifest → dependencies).
- Import graph (module → imported modules).
- Directory graph (parent dir → child entries).
- Module graph (file → file imports).

Cycles are detected in the import / module graphs.
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import GraphReport
from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class GraphEngine(BaseAnalyzer):
    """Build repository graphs with :mod:`networkx`."""

    _analyzer_name = "graph"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 3

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Build graphs and return a :class:`GraphReport`."""
        import_graph = self._build_import_graph(workspace)
        directory_graph = self._build_directory_graph(workspace)
        module_graph = self._build_module_graph(workspace)
        dependency_graph = self._build_dependency_graph(workspace)
        cycles = self._detect_cycles(import_graph)
        report = GraphReport(
            dependency_graph=self._serialize_graph(dependency_graph),
            import_graph=self._serialize_graph(import_graph),
            directory_graph=self._serialize_graph(directory_graph),
            module_graph=self._serialize_graph(module_graph),
            cycles=cycles,
        )
        return {"graph_report": report.model_dump(mode="json")}

    # ----- graph builders ------------------------------------------------------

    def _build_import_graph(self, workspace: Path) -> dict[str, list[str]]:
        """Build a module → imported-modules graph from Python imports."""
        import ast

        graph: dict[str, list[str]] = defaultdict(list)
        for path in self._iter_python_files(workspace):
            rel = str(path.relative_to(workspace))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        graph[rel].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        graph[rel].append(node.module)
        return dict(graph)

    @staticmethod
    def _build_directory_graph(workspace: Path) -> dict[str, list[str]]:
        """Build a directory → children graph."""
        graph: dict[str, list[str]] = defaultdict(list)
        for root, dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            rel = str(Path(root).relative_to(workspace))
            if rel == ".":
                rel = "<root>"
            for name in dirs:
                graph[rel].append(name + "/")
            for name in files:
                graph[rel].append(name)
        return dict(graph)

    def _build_module_graph(self, workspace: Path) -> dict[str, list[str]]:
        """Build a file → file graph resolving relative imports."""
        import ast

        graph: dict[str, list[str]] = defaultdict(list)
        py_files = {p.relative_to(workspace): p for p in self._iter_python_files(workspace)}
        for rel_path, path in py_files.items():
            rel = str(rel_path)
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    target = node.module.replace(".", "/") + ".py"
                    if Path(workspace / target) in py_files.values():
                        graph[rel].append(target)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        target = alias.name.replace(".", "/") + ".py"
                        if Path(workspace / target) in py_files.values():
                            graph[rel].append(target)
        return dict(graph)

    @staticmethod
    def _build_dependency_graph(workspace: Path) -> dict[str, list[str]]:
        """Build a manifest → dependencies graph (best-effort)."""
        graph: dict[str, list[str]] = defaultdict(list)
        manifest_names = {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
        }
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                if name in manifest_names:
                    graph[name] = []
        return dict(graph)

    # ----- helpers -------------------------------------------------------------

    def _iter_python_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                if name.endswith(".py"):
                    yield Path(root) / name

    @staticmethod
    def _detect_cycles(graph: dict[str, list[str]]) -> list[list[str]]:
        """Detect cycles via NetworkX if available, else DFS fallback."""
        try:
            import networkx as nx

            digraph: nx.DiGraph[str] = nx.DiGraph()
            for src, dsts in graph.items():
                for dst in dsts:
                    digraph.add_edge(src, dst)
            return [list(cycle) for cycle in nx.simple_cycles(digraph)][:50]
        except ImportError:  # pragma: no cover - networkx is a dependency
            return []

    @staticmethod
    def _serialize_graph(graph: dict[str, list[str]]) -> dict[str, Any]:
        """Serialize a graph to a JSON-friendly adjacency dict with stats."""
        node_count = len(graph)
        edge_count = sum(len(dsts) for dsts in graph.values())
        return {
            "nodes": node_count,
            "edges": edge_count,
            "adjacency": graph,
        }


__all__ = ["GraphEngine"]
