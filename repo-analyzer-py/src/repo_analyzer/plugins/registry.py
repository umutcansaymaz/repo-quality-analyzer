"""Plugin registry: in-memory store of discovered analyzers.

The registry holds analyzer *instances* keyed by their unique name. It is
populated by the :class:`PluginManager` during discovery.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Sequence
from typing import Any

from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.infrastructure.errors import PluginError
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)


class PluginRegistry:
    """Thread-safe registry of analyzer instances.

    The registry is the single source of truth for which analyzers are
    available to the orchestrator. Plugins are keyed by their
    :attr:`~AnalyzerPort.name`.
    """

    def __init__(self) -> None:
        self._plugins: dict[str, AnalyzerPort] = {}
        self._metadata: dict[str, dict[str, Any]] = {}
        self._lock = threading.RLock()

    def register(self, plugin: AnalyzerPort, metadata: dict[str, Any] | None = None) -> None:
        """Register an analyzer instance.

        Args:
            plugin: The analyzer to register.
            metadata: Optional metadata (source, version, signature status).

        Raises:
            PluginError: If a plugin with the same name is already registered.
        """
        with self._lock:
            name = plugin.name
            if name in self._plugins:
                raise PluginError(
                    f"Plugin {name!r} is already registered",
                    analyzer_id=name,
                )
            self._plugins[name] = plugin
            self._metadata[name] = metadata or {}
            _logger.debug("Registered plugin %s (v%s)", name, plugin.version)

    def unregister(self, name: str) -> bool:
        """Remove a plugin by name.

        Args:
            name: The plugin name.

        Returns:
            ``True`` if a plugin was removed.
        """
        with self._lock:
            plugin = self._plugins.pop(name, None)
            self._metadata.pop(name, None)
            if plugin is not None:
                try:
                    plugin.dispose()
                except Exception:  # pragma: no cover - defensive
                    _logger.warning("Error disposing plugin %s", name)
                return True
            return False

    def get(self, name: str) -> AnalyzerPort:
        """Return the plugin registered under ``name``.

        Raises:
            PluginError: If no such plugin is registered.
        """
        with self._lock:
            plugin = self._plugins.get(name)
            if plugin is None:
                raise PluginError(f"Plugin {name!r} is not registered", analyzer_id=name)
            return plugin

    def metadata(self, name: str) -> dict[str, Any]:
        """Return the metadata dict for a plugin."""
        with self._lock:
            if name not in self._metadata:
                raise PluginError(f"Plugin {name!r} is not registered", analyzer_id=name)
            return dict(self._metadata[name])

    def all(self) -> Sequence[AnalyzerPort]:
        """Return all registered plugins as a list."""
        with self._lock:
            return list(self._plugins.values())

    def names(self) -> Sequence[str]:
        """Return the names of all registered plugins."""
        with self._lock:
            return list(self._plugins.keys())

    def clear(self) -> int:
        """Dispose and remove all plugins.

        Returns:
            The number of plugins removed.
        """
        with self._lock:
            count = len(self._plugins)
            for plugin in list(self._plugins.values()):
                try:
                    plugin.dispose()
                except Exception:  # pragma: no cover - defensive
                    _logger.warning("Error disposing plugin")
            self._plugins.clear()
            self._metadata.clear()
            return count

    def __contains__(self, name: object) -> bool:
        with self._lock:
            return name in self._plugins

    def __len__(self) -> int:
        with self._lock:
            return len(self._plugins)

    def __iter__(self) -> Iterator[AnalyzerPort]:
        with self._lock:
            return iter(list(self._plugins.values()))


__all__ = ["PluginRegistry"]
