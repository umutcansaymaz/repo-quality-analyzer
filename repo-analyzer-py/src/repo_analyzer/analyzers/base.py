"""Base classes for built-in analyzers.

Every analyzer — built-in or third-party plugin — implements
:class:`repo_analyzer.core.ports.analyzer_port.AnalyzerPort`. This module
provides :class:`BaseAnalyzer`, a concrete base class that handles the
boilerplate (metadata, initialize, dispose) so that individual analyzers
only need to implement :meth:`run`.
"""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.analyzer_port import AnalyzerPort


class BaseAnalyzer(AnalyzerPort):
    """Base class for all built-in analyzers.

    Subclasses set :attr:`_analyzer_name`, :attr:`_analyzer_version`,
    :attr:`_analyzer_phase` and :attr:`_supported_languages`, and implement
    :meth:`run`.
    """

    _analyzer_name: str = "base"
    _analyzer_version: str = "0.1.0"
    _analyzer_phase: int = 2
    _supported_languages: Sequence[str] = ("*",)

    def __init__(self) -> None:
        self._initialized: bool = False
        self._config: dict[str, Any] = {}

    @property
    def name(self) -> str:
        return self._analyzer_name

    @property
    def version(self) -> str:
        return self._analyzer_version

    @property
    def phase(self) -> int:
        return self._analyzer_phase

    @property
    def languages(self) -> Sequence[str]:
        return self._supported_languages

    def metadata(self) -> dict[str, Any]:
        return {
            "name": self._analyzer_name,
            "version": self._analyzer_version,
            "phase": self._analyzer_phase,
            "languages": list(self._supported_languages),
        }

    def initialize(self, config: dict[str, Any]) -> None:
        self._config = config or {}
        self._initialized = True

    def can_run(self, repository: Repository, workspace: Path) -> bool:
        return workspace.exists() and workspace.is_dir()

    @abstractmethod
    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run the analysis and return a raw findings payload."""

    def dispose(self) -> None:
        self._initialized = False


__all__ = ["BaseAnalyzer"]
