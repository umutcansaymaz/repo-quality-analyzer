"""Ports (abstract interfaces) defining the Hexagonal secondary ports.

Each port is an abstract base class that adapters implement. The core
orchestrator depends only on these ports, never on concrete adapters.
"""

from __future__ import annotations

from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.core.ports.cache_port import CachePort
from repo_analyzer.core.ports.llm_port import LLMPort
from repo_analyzer.core.ports.output_port import OutputPort
from repo_analyzer.core.ports.repository_port import (
    RepositoryProvider,
    RepositoryProviderFactory,
)

__all__ = [
    "AnalyzerPort",
    "CachePort",
    "LLMPort",
    "OutputPort",
    "RepositoryProvider",
    "RepositoryProviderFactory",
]
