"""Documentation analyzer.

Inspects the repository's documentation:

- README presence and quality (installation, usage, API, contribution).
- LICENSE file.
- CHANGELOG file.
- CONTRIBUTING file.
- Wiki link in README.
- Docstring coverage (Python).
"""

from __future__ import annotations

import ast
import os
import re
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import DocumentationReport
from repo_analyzer.core.domain.repository import Repository


class DocumentationAnalyzer(BaseAnalyzer):
    """Analyze repository documentation quality."""

    _analyzer_name = "documentation"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 4

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run documentation analysis and return a :class:`DocumentationReport`."""
        readme_path = self._find_readme(workspace)
        readme_content = ""
        if readme_path:
            try:
                readme_content = readme_path.read_text(encoding="utf-8", errors="ignore").lower()
            except OSError:
                pass
        has_installation = bool(re.search(r"install", readme_content))
        has_usage = bool(re.search(r"usage|example|getting started|quickstart", readme_content))
        has_api = bool(re.search(r"\bapi\b|endpoint|reference", readme_content))
        has_contribution = self._has_file(workspace, {"contributing.md", ".github/contributing.md"})
        has_license = self._has_file(workspace, {"license", "license.md", "license.txt"})
        has_changelog = self._has_file(workspace, {"changelog.md", "changes.md", "history.md"})
        has_wiki = bool(re.search(r"wiki|docs\.github\.com", readme_content))
        score = (
            sum(
                [
                    has_installation,
                    has_usage,
                    has_api,
                    has_contribution,
                    has_license,
                    has_changelog,
                    has_wiki,
                    bool(readme_path),
                ]
            )
            / 8.0
        )
        docstring_coverage = self._docstring_coverage(workspace)
        report = DocumentationReport(
            has_installation=has_installation,
            has_usage_example=has_usage,
            has_api_docs=has_api,
            has_contribution_guide=has_contribution,
            has_license=has_license,
            has_changelog=has_changelog,
            has_wiki_link=has_wiki,
            readme_score=round(score, 2),
            docstring_coverage=docstring_coverage,
        )
        return {"documentation_report": report.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    @staticmethod
    def _find_readme(workspace: Path) -> Path | None:
        for name in ("README.md", "README.rst", "README.txt", "README", "readme.md"):
            candidate = workspace / name
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _has_file(workspace: Path, names: set[str]) -> bool:
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                if name.lower() in names:
                    return True
        return False

    def _docstring_coverage(self, workspace: Path) -> float:
        """Compute Python docstring coverage (documented / total definitions)."""
        total = 0
        documented = 0
        for path in self._iter_python_files(workspace):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    total += 1
                    if ast.get_docstring(node):
                        documented += 1
        if total == 0:
            return 0.0
        return round(documented / total, 4)

    def _iter_python_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                if name.endswith(".py"):
                    yield Path(root) / name


__all__ = ["DocumentationAnalyzer"]
