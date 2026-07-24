"""Plugin discovery.

Locates analyzer plugins from two sources:

1. **Python entry points** under the ``repo_analyzer.plugins`` group. This
   is the recommended distribution mechanism: ``pip install``-ed packages
   advertise their plugins in ``pyproject.toml`` and they are picked up
   automatically.
2. **Plugin directories** configured in ``plugins.dirs``. Each ``.py`` file
   in these directories is imported and scanned for classes implementing
   :class:`AnalyzerPort`.

No concrete plugin is required at this stage — discovery simply returns an
empty list when nothing is found.
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.infrastructure.errors import PluginError
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: The entry-point group used by third-party analyzer plugins.
ENTRY_POINT_GROUP = "repo_analyzer.plugins"


class PluginDiscovery:
    """Discovers analyzer plugins from entry points and plugin directories."""

    def __init__(self, plugin_dirs: Sequence[str | Path] | None = None) -> None:
        """Initialize discovery.

        Args:
            plugin_dirs: Optional list of directories to scan for ``.py``
                plugin files. ``~`` and environment variables are expanded.
        """
        self._dirs: list[Path] = []
        if plugin_dirs:
            for raw in plugin_dirs:
                path = Path(str(raw)).expanduser()
                self._dirs.append(path)

    def discover(self) -> list[AnalyzerPort]:
        """Discover and instantiate analyzer plugins.

        Returns:
            A list of :class:`AnalyzerPort` instances. Each discovered plugin
            class is instantiated with no arguments.
        """
        instances: list[AnalyzerPort] = []
        instances.extend(self._discover_entry_points())
        instances.extend(self._discover_directories())
        return instances

    # ----- entry points ---------------------------------------------------------
    def _discover_entry_points(self) -> list[AnalyzerPort]:
        """Discover plugins registered as Python entry points."""
        results: list[AnalyzerPort] = []
        try:
            eps = self._iter_entry_points(ENTRY_POINT_GROUP)
        except Exception as exc:  # pragma: no cover - environment-dependent
            _logger.debug("Entry-point discovery unavailable: %s", exc)
            return results
        for ep in eps:
            try:
                obj = ep.load()
                instance = self._instantiate(obj)
                if instance is not None:
                    results.append(instance)
                    _logger.debug(
                        "Discovered plugin %s from entry point %s",
                        instance.name,
                        ep.name,
                    )
            except Exception as exc:
                _logger.warning("Failed to load entry point %s: %s", ep.name, exc)
        return results

    @staticmethod
    def _iter_entry_points(group: str) -> list[Any]:
        """Return entry points for ``group`` across Python versions.

        Uses :mod:`importlib.metadata` and tolerates environments where the
        metadata backend differs.
        """
        try:
            from importlib.metadata import entry_points

            eps = entry_points()
            # Python 3.12+ returns a SelectableGroups-like object.
            if hasattr(eps, "select"):
                return list(eps.select(group=group))
            # Older API: dict-like. This branch is unreachable on 3.12+ but
            # kept for backwards compatibility.
            getter = getattr(eps, "get", None)
            if getter is not None:
                return list(getter(group, []))
            return []
        except Exception:  # pragma: no cover - defensive
            return []

    # ----- directory scanning ---------------------------------------------------
    def _discover_directories(self) -> list[AnalyzerPort]:
        """Discover plugins by scanning configured directories for ``.py`` files."""
        results: list[AnalyzerPort] = []
        for directory in self._dirs:
            if not directory.exists() or not directory.is_dir():
                _logger.debug("Plugin directory does not exist: %s", directory)
                continue
            for py_file in sorted(directory.rglob("*.py")):
                if py_file.name.startswith("_"):
                    continue
                results.extend(self._load_from_file(py_file))
        return results

    def _load_from_file(self, path: Path) -> list[AnalyzerPort]:
        """Import a Python file and return any analyzer classes found."""
        module_name = f"repo_analyzer_plugin_{path.stem}_{abs(hash(str(path)))}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return []
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as exc:
            _logger.warning("Failed to import plugin file %s: %s", path, exc)
            return []
        results: list[AnalyzerPort] = []
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if obj is AnalyzerPort:
                continue
            if not issubclass(obj, AnalyzerPort):
                continue
            instance = self._instantiate(obj)
            if instance is not None:
                results.append(instance)
        return results

    @staticmethod
    def _instantiate(obj: Any) -> AnalyzerPort | None:
        """Instantiate an analyzer class with no arguments.

        Returns ``None`` if ``obj`` is not a concrete class implementing
        :class:`AnalyzerPort`.
        """
        if not inspect.isclass(obj):
            return None
        if not issubclass(obj, AnalyzerPort):
            return None
        if inspect.isabstract(obj):
            return None
        try:
            instance = obj()
        except Exception as exc:
            raise PluginError(
                f"Failed to instantiate plugin {obj.__name__}: {exc}",
                analyzer_id=obj.__name__,
            ) from exc
        return instance


__all__ = ["ENTRY_POINT_GROUP", "PluginDiscovery"]
