"""Built-in configuration defaults and well-known paths."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Application-wide constants
APP_NAME = "repo-analyzer"
APP_DISPLAY_NAME = "Repo Analyzer"
ENV_PREFIX = "GRA_"

# Default configuration as a YAML string. Used both as documentation and as
# the seed for ``repo-analyzer config init``.
DEFAULT_CONFIG_YAML = """\
# repo-analyzer configuration
# This file is merged with defaults, environment variables and CLI flags.

log_level: INFO
verbose: false
debug: false

vcs:
  clone_depth: 1
  partial_clone: true
  timeout_sec: 120

cache:
  enabled: true
  dir: "~/.cache/repo-analyzer"
  ttl_days: 7
  max_size_gb: 2

reports:
  output_dir: "./reports"
  formats:
    - markdown
    - json

logging:
  file: "~/.cache/repo-analyzer/repo-analyzer.log"
  level: DEBUG
  rotate_max_bytes: 10485760
  rotate_backup_count: 5

plugins:
  dirs:
    - "~/.config/repo-analyzer/plugins"
  trusted: []
  isolated_default: false

scoring:
  weights:
    security: 0.40
    quality: 0.25
    architecture: 0.20
    test: 0.15

ai:
  enabled: false
  provider: "zai"
  model: "glm-4.6"
  max_tokens: 4096
  temperature: 0.2
"""


def get_default_config_dir() -> Path:
    """Return the platform-appropriate default config directory.

    Respects ``XDG_CONFIG_HOME`` on POSIX systems and ``APPDATA`` on Windows.

    Returns:
        A :class:`~pathlib.Path` to the config directory (not guaranteed to
        exist).
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".config" / APP_NAME


def get_default_config_path() -> Path:
    """Return the default config file path (``config.yaml`` in the config dir)."""
    return get_default_config_dir() / "config.yaml"


def get_default_cache_dir() -> Path:
    """Return the platform-appropriate default cache directory."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        return Path(base) / APP_NAME / "cache"
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg) / APP_NAME
    return Path.home() / ".cache" / APP_NAME


__all__ = [
    "APP_DISPLAY_NAME",
    "APP_NAME",
    "DEFAULT_CONFIG_YAML",
    "ENV_PREFIX",
    "get_default_cache_dir",
    "get_default_config_dir",
    "get_default_config_path",
]
