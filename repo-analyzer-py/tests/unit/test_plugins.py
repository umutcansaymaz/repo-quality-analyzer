"""Tests for the plugin subsystem (registry, discovery, manager)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.infrastructure.errors import PluginError
from repo_analyzer.plugins import PluginDiscovery, PluginManager, PluginRegistry


class DummyAnalyzer(AnalyzerPort):
    """A concrete analyzer used in tests."""

    def __init__(self, name: str = "dummy", version: str = "0.1.0") -> None:
        self._name = name
        self._version = version
        self.disposed = False
        self.initialized = False

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def metadata(self) -> dict[str, Any]:
        return {"name": self._name, "version": self._version}

    def initialize(self, config: dict[str, Any]) -> None:
        self.initialized = True

    def can_run(self, repository: Repository, workspace: Path) -> bool:
        return True

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        return {"findings": []}

    def dispose(self) -> None:
        self.disposed = True


class TestPluginRegistry:
    """Tests for :class:`PluginRegistry`."""

    def test_register_and_get(self) -> None:
        registry = PluginRegistry()
        plugin = DummyAnalyzer()
        registry.register(plugin)
        assert registry.get("dummy") is plugin

    def test_register_duplicate_raises(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer())
        with pytest.raises(PluginError):
            registry.register(DummyAnalyzer())

    def test_get_missing_raises(self) -> None:
        registry = PluginRegistry()
        with pytest.raises(PluginError):
            registry.get("nope")

    def test_unregister_existing(self) -> None:
        registry = PluginRegistry()
        plugin = DummyAnalyzer()
        registry.register(plugin)
        assert registry.unregister("dummy") is True
        assert "dummy" not in registry

    def test_unregister_missing_returns_false(self) -> None:
        registry = PluginRegistry()
        assert registry.unregister("nope") is False

    def test_unregister_disposes(self) -> None:
        registry = PluginRegistry()
        plugin = DummyAnalyzer()
        registry.register(plugin)
        registry.unregister("dummy")
        assert plugin.disposed is True

    def test_all_returns_list(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer("a"))
        registry.register(DummyAnalyzer("b"))
        all_plugins = registry.all()
        assert len(all_plugins) == 2

    def test_names(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer("x"))
        assert "x" in registry.names()

    def test_clear_disposes_and_returns_count(self) -> None:
        registry = PluginRegistry()
        p1 = DummyAnalyzer("a")
        p2 = DummyAnalyzer("b")
        registry.register(p1)
        registry.register(p2)
        count = registry.clear()
        assert count == 2
        assert p1.disposed is True
        assert p2.disposed is True

    def test_contains(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer("x"))
        assert "x" in registry
        assert "y" not in registry

    def test_len(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer("a"))
        registry.register(DummyAnalyzer("b"))
        assert len(registry) == 2

    def test_metadata(self) -> None:
        registry = PluginRegistry()
        registry.register(DummyAnalyzer(), metadata={"source": "test"})
        meta = registry.metadata("dummy")
        assert meta["source"] == "test"


class TestPluginDiscovery:
    """Tests for :class:`PluginDiscovery`."""

    def test_discover_from_directory(self, tmp_path: Path) -> None:
        """A .py file with a concrete analyzer should be discovered."""
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text(
            "from repo_analyzer.core.ports.analyzer_port import AnalyzerPort\n"
            "from repo_analyzer.core.domain.repository import Repository\n"
            "from pathlib import Path\n"
            "from typing import Any\n"
            "class FoundAnalyzer(AnalyzerPort):\n"
            "    @property\n"
            "    def name(self) -> str: return 'found'\n"
            "    @property\n"
            "    def version(self) -> str: return '1.0.0'\n"
            "    def metadata(self) -> dict[str, Any]: return {}\n"
            "    def initialize(self, config: dict[str, Any]) -> None: pass\n"
            "    def can_run(self, repository: Repository, workspace: Path) -> bool: return True\n"
            "    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]: return {}\n"
            "    def dispose(self) -> None: pass\n"
        )
        discovery = PluginDiscovery([tmp_path])
        plugins = discovery.discover()
        names = [p.name for p in plugins]
        assert "found" in names

    def test_discover_missing_directory_returns_empty(self, tmp_path: Path) -> None:
        """A non-existent directory should yield no plugins."""
        discovery = PluginDiscovery([tmp_path / "does-not-exist"])
        assert discovery.discover() == []

    def test_discover_skips_underscore_files(self, tmp_path: Path) -> None:
        """Files starting with ``_`` should be skipped."""
        (tmp_path / "_private.py").write_text("# not a plugin\n")
        discovery = PluginDiscovery([tmp_path])
        assert discovery.discover() == []

    def test_discover_handles_broken_file(self, tmp_path: Path) -> None:
        """A file with a syntax error should be skipped gracefully."""
        (tmp_path / "broken.py").write_text("def broken(:\n")
        discovery = PluginDiscovery([tmp_path])
        assert discovery.discover() == []


class TestPluginManager:
    """Tests for :class:`PluginManager`."""

    def test_load_all_with_no_plugins(self) -> None:
        manager = PluginManager()
        count = manager.load_all([])
        assert count == 0

    def test_load_all_from_directory(self, tmp_path: Path) -> None:
        plugin_file = tmp_path / "p.py"
        plugin_file.write_text(
            "from repo_analyzer.core.ports.analyzer_port import AnalyzerPort\n"
            "from repo_analyzer.core.domain.repository import Repository\n"
            "from pathlib import Path\n"
            "from typing import Any\n"
            "class M(AnalyzerPort):\n"
            "    @property\n"
            "    def name(self) -> str: return 'm'\n"
            "    @property\n"
            "    def version(self) -> str: return '0.1.0'\n"
            "    def metadata(self) -> dict[str, Any]: return {}\n"
            "    def initialize(self, config: dict[str, Any]) -> None: pass\n"
            "    def can_run(self, repository: Repository, workspace: Path) -> bool: return True\n"
            "    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]: return {}\n"
            "    def dispose(self) -> None: pass\n"
        )
        manager = PluginManager()
        count = manager.load_all([tmp_path])
        assert count == 1
        assert "m" in manager

    def test_initialize_all(self) -> None:
        manager = PluginManager()
        plugin = DummyAnalyzer()
        manager.registry.register(plugin)
        manager.initialize_all({})
        assert plugin.initialized is True

    def test_dispose_all_clears_registry(self) -> None:
        manager = PluginManager()
        plugin = DummyAnalyzer()
        manager.registry.register(plugin)
        manager.dispose_all()
        assert len(manager) == 0
        assert plugin.disposed is True

    def test_get_by_name(self) -> None:
        manager = PluginManager()
        plugin = DummyAnalyzer("xyz")
        manager.registry.register(plugin)
        assert manager.get("xyz") is plugin

    def test_all_returns_plugins(self) -> None:
        manager = PluginManager()
        manager.registry.register(DummyAnalyzer("a"))
        manager.registry.register(DummyAnalyzer("b"))
        assert len(manager.all()) == 2

    def test_names(self) -> None:
        manager = PluginManager()
        manager.registry.register(DummyAnalyzer("a"))
        assert "a" in manager.names()

    def test_len(self) -> None:
        manager = PluginManager()
        manager.registry.register(DummyAnalyzer("a"))
        assert len(manager) == 1
