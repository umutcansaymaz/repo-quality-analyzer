"""Dependency analyzer.

Parses dependency manifests from 8 ecosystems and produces a
:class:`DependencyAnalysis`:

- ``requirements.txt`` (Python)
- ``pyproject.toml`` (Python)
- ``package.json`` (Node.js)
- ``Cargo.toml`` (Rust)
- ``go.mod`` (Go)
- ``composer.json`` (PHP)
- ``pom.xml`` (Java Maven)
- ``build.gradle`` (Java Gradle)

For each dependency it records the name, version and ecosystem. It also
detects unused and duplicate dependencies and builds a flat dependency
graph (parent → children).
"""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.analyzers.dependency.manifests import (
    cargo,
    composer,
    gradle,
    nodejs,
    pom,
    python,
)
from repo_analyzer.analyzers.dependency.manifests import (
    go as go_manifest,
)
from repo_analyzer.core.domain.analysis_outputs import DependencyAnalysis
from repo_analyzer.core.domain.repository import Repository


class DependencyAnalyzer(BaseAnalyzer):
    """Analyze project dependencies across multiple ecosystems."""

    _analyzer_name = "dependency"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 1

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run dependency analysis and return a :class:`DependencyAnalysis`."""
        deps: list[dict[str, Any]] = []
        graph: dict[str, list[str]] = defaultdict(list)
        ecosystems: set[str] = set()

        for path in self._find_manifests(workspace):
            ecosystem, parsed = self._parse_manifest(path)
            if not parsed:
                continue
            ecosystems.add(ecosystem)
            manifest_name = path.name
            for dep in parsed:
                deps.append(dep)
                graph[manifest_name].append(dep["name"])

        unused = self._detect_unused(deps, workspace)
        duplicates = self._detect_duplicates(deps)
        analysis = DependencyAnalysis(
            dependencies=deps,
            dependency_graph=dict(graph),
            unused_dependencies=unused,
            duplicate_dependencies=duplicates,
            ecosystems=sorted(ecosystems),
            total_dependencies=len(deps),
        )
        return {"dependency_analysis": analysis.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _find_manifests(self, workspace: Path):  # type: ignore[no-untyped-def]
        """Yield known manifest files anywhere in the workspace."""
        names = {
            "requirements.txt",
            "pyproject.toml",
            "package.json",
            "Cargo.toml",
            "go.mod",
            "composer.json",
            "pom.xml",
            "build.gradle",
            "build.gradle.kts",
        }
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                if name in names:
                    yield Path(root) / name

    def _parse_manifest(self, path: Path) -> tuple[str, list[dict[str, Any]]]:
        """Dispatch to the right parser based on the file name."""
        name = path.name
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return "", []
        if name == "requirements.txt":
            return "pypi", python.parse_requirements(content)
        if name == "pyproject.toml":
            return "pypi", python.parse_pyproject(content)
        if name == "package.json":
            return "npm", nodejs.parse_package_json(content)
        if name == "Cargo.toml":
            return "cargo", cargo.parse_cargo_toml(content)
        if name == "go.mod":
            return "go", go_manifest.parse_go_mod(content)
        if name == "composer.json":
            return "composer", composer.parse_composer_json(content)
        if name == "pom.xml":
            return "maven", pom.parse_pom_xml(content)
        if name in {"build.gradle", "build.gradle.kts"}:
            return "gradle", gradle.parse_build_gradle(content)
        return "", []

    def _detect_unused(self, deps: list[dict[str, Any]], workspace: Path) -> list[str]:
        """Heuristic: a dependency is unused if its name never appears in source."""
        used: set[str] = set()
        names = {d["name"] for d in deps}
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for fname in files:
                if fname.endswith(
                    (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".kt")
                ):
                    try:
                        content = (Path(root) / fname).read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    for name in names:
                        if name in content:
                            used.add(name)
        return sorted(names - used)

    @staticmethod
    def _detect_duplicates(deps: list[dict[str, Any]]) -> list[str]:
        """Find dependencies that appear more than once (same name + ecosystem)."""
        seen: dict[str, int] = defaultdict(int)
        for dep in deps:
            key = f"{dep.get('ecosystem', '')}:{dep['name']}"
            seen[key] += 1
        return [k for k, count in seen.items() if count > 1]


__all__ = ["DependencyAnalyzer"]
