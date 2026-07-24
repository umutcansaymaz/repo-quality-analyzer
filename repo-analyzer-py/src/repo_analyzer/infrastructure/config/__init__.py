"""Configuration system for repo-analyzer.

Merges configuration from four sources, in increasing priority:

1. Built-in defaults (defined in :mod:`repo_analyzer.infrastructure.config.defaults`)
2. ``config.yaml`` file (default ``~/.config/repo-analyzer/config.yaml``)
3. Environment variables prefixed with ``GRA_``
4. CLI arguments

Implements the design described in ADR-005 of the SDD.
"""

from __future__ import annotations

from repo_analyzer.infrastructure.config.defaults import (
    DEFAULT_CONFIG_YAML,
    get_default_cache_dir,
    get_default_config_dir,
    get_default_config_path,
)
from repo_analyzer.infrastructure.config.settings import (
    AISettings,
    CacheSettings,
    Config,
    LoggingSettings,
    PluginSettings,
    ReportSettings,
    ScoringConfig,
    ScoringWeights,
    VCSSettings,
    load_config,
)

__all__ = [
    "DEFAULT_CONFIG_YAML",
    "AISettings",
    "CacheSettings",
    "Config",
    "LoggingSettings",
    "PluginSettings",
    "ReportSettings",
    "ScoringConfig",
    "ScoringWeights",
    "VCSSettings",
    "get_default_cache_dir",
    "get_default_config_dir",
    "get_default_config_path",
    "load_config",
]
