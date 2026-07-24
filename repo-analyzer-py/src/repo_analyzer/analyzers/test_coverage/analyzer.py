"""Test analyzer.

Detects test frameworks and estimates test-suite characteristics:

- Frameworks in use (pytest, unittest, jest, vitest, ...).
- Total test files and test functions.
- Estimated coverage (from coverage artifacts if present).
- Presence of integration tests, unit tests, fixtures and mocks.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import TestAnalysis
from repo_analyzer.core.domain.repository import Repository

_FRAMEWORK_PATTERNS: dict[str, re.Pattern[str]] = {
    "pytest": re.compile(r"\bimport pytest\b|\bfrom pytest\b"),
    "unittest": re.compile(r"\bimport unittest\b|\bfrom unittest\b"),
    "jest": re.compile(r"jest\.(fn|mock|spyOn|test|describe|it|expect)"),
    "vitest": re.compile(r"\bfrom ['\"]vitest['\"]\b|\bvitest\b"),
    "mocha": re.compile(r"\bdescribe\s*\(|\bit\s*\("),
    "rspec": re.compile(r"\bRSpec\.describe\b|\bdescribe\s+\w+\s+do\b"),
    "go-testing": re.compile(r'\btesting\.T\b|"testing"'),
}


class TestAnalyzer(BaseAnalyzer):
    """Analyze the test suite of a repository."""

    # Tell pytest not to collect this class as a test case.
    __test__ = False

    _analyzer_name = "test-coverage"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 4

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run test analysis and return a :class:`TestAnalysis`."""
        frameworks: set[str] = set()
        test_files: list[str] = []
        total_functions = 0
        has_fixtures = False
        has_mocks = False
        has_integration = False
        has_unit = False

        for path in self._iter_files(workspace):
            name = path.name.lower()
            is_test = self._is_test_file(name)
            if not is_test:
                continue
            rel = str(path.relative_to(workspace))
            test_files.append(rel)
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for fw, pattern in _FRAMEWORK_PATTERNS.items():
                if pattern.search(content):
                    frameworks.add(fw)
            total_functions += len(re.findall(r"\bdef test_\w+|\bit\(\s*['\"]", content))
            if re.search(r"@pytest\.fixture|fixture\(", content):
                has_fixtures = True
            if re.search(r"mock|Mock|patch\(", content):
                has_mocks = True
            if "integration" in rel.lower() or "e2e" in rel.lower():
                has_integration = True
            else:
                has_unit = True

        coverage = self._estimate_coverage(workspace)
        analysis = TestAnalysis(
            frameworks=sorted(frameworks),
            total_test_files=len(test_files),
            total_test_functions=total_functions,
            estimated_coverage=coverage,
            has_integration_tests=has_integration,
            has_unit_tests=has_unit,
            has_fixtures=has_fixtures,
            has_mocks=has_mocks,
            test_files=test_files,
        )
        return {"test_analysis": analysis.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                yield Path(root) / name

    @staticmethod
    def _is_test_file(name: str) -> bool:
        if name.startswith("test_") and name.endswith((".py",)):
            return True
        if name.endswith(("_test.py", ".test.js", ".test.ts", ".spec.js", ".spec.ts")):
            return True
        if name == "test.js" or name == "test.ts":
            return True
        if name.endswith(("_test.go",)):
            return True
        return False

    @staticmethod
    def _estimate_coverage(workspace: Path) -> float | None:
        """Try to read coverage from artifacts; return ``None`` if unavailable."""
        # Python coverage.xml
        coverage_xml = workspace / "coverage.xml"
        if coverage_xml.exists():
            try:
                import xml.etree.ElementTree as ET

                tree = ET.parse(coverage_xml)  # noqa: S314
                root = tree.getroot()
                line_rate = root.attrib.get("line-rate")
                if line_rate:
                    return round(float(line_rate) * 100, 2)
            except Exception:  # pragma: no cover - defensive
                pass
        # JS coverage/coverage-final.json
        coverage_json = workspace / "coverage" / "coverage-final.json"
        if coverage_json.exists():
            try:
                import json

                data = json.loads(coverage_json.read_text(encoding="utf-8"))
                totals: list[float] = []
                for _file, info in data.items():
                    s = info.get("s", {})
                    if s:
                        covered = sum(1 for v in s.values() if v > 0)
                        totals.append(covered / len(s))
                if totals:
                    return round(sum(totals) / len(totals) * 100, 2)
            except Exception:  # pragma: no cover - defensive
                pass
        return None


__all__ = ["TestAnalyzer"]
