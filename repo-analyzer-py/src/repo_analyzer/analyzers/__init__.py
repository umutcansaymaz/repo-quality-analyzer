"""Built-in analysis engines.

Each analyzer implements :class:`repo_analyzer.core.ports.analyzer_port.AnalyzerPort`
via :class:`repo_analyzer.analyzers.base.BaseAnalyzer`. The orchestrator runs
them in phase order (0-4) with intra-phase parallelism.
"""

from __future__ import annotations

from repo_analyzer.analyzers.architecture.analyzer import GraphEngine
from repo_analyzer.analyzers.ast.analyzer import ASTAnalyzer
from repo_analyzer.analyzers.base import BaseAnalyzer
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

__all__ = [
    "BaseAnalyzer",
    "FilesystemAnalyzer",
    "LanguageDetector",
    "ASTAnalyzer",
    "ImportAnalyzer",
    "DependencyAnalyzer",
    "MetricEngine",
    "ComplexityAnalyzer",
    "GitAnalyzer",
    "DocumentationAnalyzer",
    "TestAnalyzer",
    "GraphEngine",
    "RepositoryDetector",
]
