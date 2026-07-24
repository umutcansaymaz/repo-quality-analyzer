"""Plugin manager: orchestrates discovery + registry + lifecycle.

The :class:`PluginManager` is the single entry point through which the
orchestrator obtains the list of available analyzers. It owns a
:class:`PluginRegistry` and a :class:`PluginDiscovery` and wires them
together.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.infrastructure.logging import get_logger
from repo_analyzer.plugins.discovery import PluginDiscovery
from repo_analyzer.plugins.registry import PluginRegistry

_logger = get_logger(__name__)


class PluginManager:
    """High-level facade for the plugin subsystem.

    Responsibilities:

    - Discover plugins (entry points + directories).
    - Register them in the :class:`PluginRegistry`.
    - Initialize each plugin with its configuration.
    - Dispose all plugins on shutdown.
    """

    def __init__(
        self,
        registry: PluginRegistry | None = None,
        discovery: PluginDiscovery | None = None,
    ) -> None:
        self._registry = registry or PluginRegistry()
        self._discovery = discovery or PluginDiscovery()
        self._initialized: bool = False

    # ----- properties -----------------------------------------------------------
    @property
    def registry(self) -> PluginRegistry:
        """The underlying :class:`PluginRegistry`."""
        return self._registry

    @property
    def discovery(self) -> PluginDiscovery:
        """The underlying :class:`PluginDiscovery`."""
        return self._discovery

    @property
    def initialized(self) -> bool:
        """``True`` once :meth:`load_all` has been called."""
        return self._initialized

    # ----- lifecycle ------------------------------------------------------------
    def load_all(self, plugin_dirs: Sequence[str | Path] | None = None) -> int:
        """Discover and register all available plugins.

        Args:
            plugin_dirs: Optional override for the directories to scan. When
                ``None``, the discovery's configured directories are used.

        Returns:
            The number of plugins newly registered.
        """
        if plugin_dirs is not None:
            self._discovery = PluginDiscovery(plugin_dirs)
        _logger.info("Discovering plugins...")
        plugins = self._discovery.discover()
        count = 0
        for plugin in plugins:
            try:
                self._registry.register(plugin)
                count += 1
            except Exception as exc:
                _logger.warning("Failed to register plugin %s: %s", type(plugin).__name__, exc)
        self._initialized = True
        _logger.info("Loaded %d plugin(s)", count)
        return count

    def initialize_all(self, config: dict[str, Any]) -> None:
        """Initialize every registered plugin with ``config``.

        Args:
            config: Plugin configuration dict.
        """
        for plugin in self._registry.all():
            try:
                plugin.initialize(config)
                _logger.debug("Initialized plugin %s", plugin.name)
            except Exception as exc:
                _logger.warning("Failed to initialize plugin %s: %s", plugin.name, exc)

    def dispose_all(self) -> None:
        """Dispose every registered plugin and clear the registry."""
        removed = self._registry.clear()
        self._initialized = False
        _logger.info("Disposed %d plugin(s)", removed)

    # ----- access ---------------------------------------------------------------
    def get(self, name: str) -> AnalyzerPort:
        """Return a plugin by name."""
        return self._registry.get(name)

    def all(self) -> Sequence[AnalyzerPort]:
        """Return all registered plugins."""
        return self._registry.all()

    def names(self) -> Sequence[str]:
        """Return the names of all registered plugins."""
        return self._registry.names()

    def __len__(self) -> int:
        return len(self._registry)

    def __contains__(self, name: object) -> bool:
        return name in self._registry


__all__ = ["PluginManager"]
