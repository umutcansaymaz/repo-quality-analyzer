"""Analyzer port (abstract interface for analysis plugins).

Every analyzer — built-in or third-party plugin — implements this port. The
orchestrator discovers analyzers through the plugin manager and runs them
in the pipeline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.repository import Repository


class AnalyzerPort(ABC):
    """Abstract interface for an analysis engine (plugin).

    Lifecycle:
        1. :meth:`metadata` — static descriptor.
        2. :meth:`initialize` — one-time setup.
        3. :meth:`can_run` — gate check for the current context.
        4. :meth:`run` — perform the analysis.
        5. :meth:`dispose` — release resources.
    """

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Return static metadata (name, version, languages, phase...)."""

    @abstractmethod
    def initialize(self, config: dict[str, Any]) -> None:
        """Initialize the analyzer with the resolved configuration.

        Args:
            config: Analyzer-specific configuration dict.
        """

    @abstractmethod
    def can_run(self, repository: Repository, workspace: Path) -> bool:
        """Return ``True`` if this analyzer applies to the given repository.

        Args:
            repository: The repository being analyzed.
            workspace: The cloned working tree.
        """

    @abstractmethod
    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run the analysis and return a raw findings payload.

        Args:
            repository: The repository being analyzed.
            workspace: The cloned working tree.

        Returns:
            A dict of raw findings (structure is analyzer-specific). The
            orchestrator normalizes them into domain models.
        """

    @abstractmethod
    def dispose(self) -> None:
        """Release resources held by the analyzer."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The analyzer's unique name."""

    @property
    @abstractmethod
    def version(self) -> str:
        """The analyzer's semantic version."""

    @property
    def languages(self) -> Sequence[str]:
        """Languages this analyzer supports (``("*",)`` for all)."""
        return ("*",)

    @property
    def phase(self) -> int:
        """Pipeline phase (0-5) in which this analyzer runs."""
        return 2


__all__ = ["AnalyzerPort"]
