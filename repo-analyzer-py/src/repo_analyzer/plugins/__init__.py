"""Plugin subsystem: discovery, registry and lifecycle management.

The plugin system lets new analyzers be added at runtime without modifying
the core. Built-in analyzers are registered automatically; third-party
plugins are discovered via Python entry points or by scanning configured
plugin directories.

This is scaffolding only: no concrete plugin is shipped at this stage.
"""

from __future__ import annotations

from repo_analyzer.core.ports.analyzer_port import AnalyzerPort
from repo_analyzer.plugins.discovery import PluginDiscovery
from repo_analyzer.plugins.manager import PluginManager
from repo_analyzer.plugins.registry import PluginRegistry

__all__ = [
    "AnalyzerPort",
    "PluginDiscovery",
    "PluginManager",
    "PluginRegistry",
]
