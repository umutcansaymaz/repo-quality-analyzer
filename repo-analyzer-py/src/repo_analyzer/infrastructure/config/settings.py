"""Pydantic Settings models for repo-analyzer configuration.

Configuration is loaded with the following priority (lowest to highest):

1. Field defaults defined in this module.
2. Values from a YAML config file (``config.yaml``).
3. Environment variables prefixed with ``GRA_`` (nested fields use ``_``).
4. Programmatic overrides (e.g. CLI flags) passed to :func:`load_config`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from repo_analyzer.infrastructure.config.defaults import (
    DEFAULT_CONFIG_YAML,
    ENV_PREFIX,
    get_default_cache_dir,
    get_default_config_path,
)
from repo_analyzer.utils.path import expand_user_path

# Valid log levels (case-insensitive).
_VALID_LOG_LEVELS = {"TRACE", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_VALID_REPORT_FORMATS = {"markdown", "json", "html", "pdf"}


class VCSSettings(BaseModel):
    """Version-control-system (clone / fetch) settings."""

    model_config = ConfigDict(extra="forbid")

    clone_depth: int = Field(default=1, ge=1, description="Depth for shallow clones.")
    partial_clone: bool = Field(
        default=True, description="Use ``--filter=blob:none`` when supported."
    )
    timeout_sec: int = Field(default=120, ge=1, description="Clone / fetch timeout.")


class CacheSettings(BaseModel):
    """Cache subsystem settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    dir: str = Field(default_factory=lambda: str(get_default_cache_dir()))
    ttl_days: int = Field(default=7, ge=0)
    max_size_gb: float = Field(default=2.0, gt=0)

    @field_validator("dir")
    @classmethod
    def _expand_dir(cls, value: str) -> str:
        return str(expand_user_path(value))


class ReportSettings(BaseModel):
    """Report output settings."""

    model_config = ConfigDict(extra="forbid")

    output_dir: str = "./reports"
    formats: list[str] = Field(default_factory=lambda: ["markdown", "json"])

    @field_validator("formats")
    @classmethod
    def _validate_formats(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one report format must be configured")
        normalized: list[str] = []
        for fmt in value:
            lowered = fmt.lower()
            if lowered not in _VALID_REPORT_FORMATS:
                raise ValueError(
                    f"Unsupported report format {fmt!r}. Valid: {sorted(_VALID_REPORT_FORMATS)}"
                )
            normalized.append(lowered)
        return normalized

    @field_validator("output_dir")
    @classmethod
    def _expand_output(cls, value: str) -> str:
        return str(expand_user_path(value))


class LoggingSettings(BaseModel):
    """File logging settings."""

    model_config = ConfigDict(extra="forbid")

    file: str = Field(default_factory=lambda: str(get_default_cache_dir() / "repo-analyzer.log"))
    level: str = "DEBUG"
    rotate_max_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    rotate_backup_count: int = Field(default=5, ge=1)

    @field_validator("level")
    @classmethod
    def _validate_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level {value!r}. Valid: {sorted(_VALID_LOG_LEVELS)}")
        return upper

    @field_validator("file")
    @classmethod
    def _expand_file(cls, value: str) -> str:
        return str(expand_user_path(value))


class PluginSettings(BaseModel):
    """Plugin subsystem settings."""

    model_config = ConfigDict(extra="forbid")

    dirs: list[str] = Field(default_factory=lambda: ["~/.config/repo-analyzer/plugins"])
    trusted: list[str] = Field(default_factory=list)
    isolated_default: bool = False

    @field_validator("dirs")
    @classmethod
    def _expand_dirs(cls, value: list[str]) -> list[str]:
        return [str(expand_user_path(d)) for d in value]


class ScoringWeights(BaseModel):
    """Health-score weighting (must sum to ~1.0)."""

    model_config = ConfigDict(extra="forbid")

    security: float = Field(default=0.40, ge=0.0, le=1.0)
    quality: float = Field(default=0.25, ge=0.0, le=1.0)
    architecture: float = Field(default=0.20, ge=0.0, le=1.0)
    test: float = Field(default=0.15, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _check_sum(self) -> ScoringWeights:
        total = self.security + self.quality + self.architecture + self.test
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"Scoring weights must sum to 1.0, got {total:.4f}")
        return self


class AISettings(BaseModel):
    """AI review engine settings."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    provider: str = "zai"
    model: str = "glm-4.6"
    max_tokens: int = Field(default=4096, ge=1)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


class ScoringConfig(BaseModel):
    """Wrapper for scoring configuration (matches the ``scoring:`` YAML section)."""

    model_config = ConfigDict(extra="forbid")

    weights: ScoringWeights = Field(default_factory=ScoringWeights)


class Config(BaseSettings):
    """Top-level configuration model for repo-analyzer.

    Field defaults reflect the built-in defaults. They can be overridden by
    a YAML config file, environment variables (``GRA_<FIELD>``) and finally
    programmatic overrides passed to :func:`load_config`.
    """

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_nested_delimiter="_",
        extra="ignore",
        case_sensitive=False,
    )

    log_level: str = "INFO"
    verbose: bool = False
    debug: bool = False

    vcs: VCSSettings = Field(default_factory=VCSSettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    reports: ReportSettings = Field(default_factory=ReportSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    plugins: PluginSettings = Field(default_factory=PluginSettings)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    ai: AISettings = Field(default_factory=AISettings)

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        upper = value.upper()
        if upper not in _VALID_LOG_LEVELS:
            raise ValueError(f"Invalid log level {value!r}. Valid: {sorted(_VALID_LOG_LEVELS)}")
        return upper

    @model_validator(mode="after")
    def _sync_debug(self) -> Config:
        """If debug mode is enabled, force DEBUG log level."""
        if self.debug and self.log_level not in {"DEBUG", "TRACE"}:
            self.log_level = "DEBUG"
        return self


def _load_yaml(path: Path | None) -> dict[str, Any]:
    """Load a YAML config file into a dict, or return an empty dict.

    If ``path`` is ``None`` the default config path is tried; if it does not
    exist an empty dict is returned (silent default).
    """
    candidate = path if path is not None else get_default_config_path()
    if not candidate.exists():
        if path is not None:
            from repo_analyzer.infrastructure.errors import ConfigFileNotFoundException

            raise ConfigFileNotFoundException(
                f"Config file not found: {candidate}", context={"path": str(candidate)}
            )
        return {}
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        from repo_analyzer.infrastructure.errors import ConfigValidationException

        raise ConfigValidationException(
            f"Failed to parse YAML config: {exc}",
            context={"path": str(candidate)},
        ) from exc
    if not isinstance(data, dict):
        from repo_analyzer.infrastructure.errors import ConfigValidationException

        raise ConfigValidationException(
            "Config file must contain a YAML mapping at the top level",
            context={"path": str(candidate)},
        )
    return data


def load_config(
    config_path: str | Path | None = None,
    *,
    overrides: dict[str, Any] | None = None,
    env: dict[str, str] | None = None,
) -> Config:
    """Load and validate the configuration.

    Args:
        config_path: Optional explicit path to a ``config.yaml`` file. If
            ``None`` the default location is used (silently skipped if absent).
        overrides: Optional dict of programmatic overrides (highest priority).
            Keys match the :class:`Config` field names; nested values use the
            same structure as the YAML (e.g. ``{"cache": {"enabled": False}}``).
        env: Optional environment mapping (defaults to ``os.environ``). Useful
            for testing.

    Returns:
        A validated :class:`Config` instance.

    Raises:
        ConfigFileNotFoundException: If an explicit ``config_path`` does not exist.
        ConfigValidationException: If the YAML is invalid or validation fails.
    """
    env_map = env if env is not None else dict(os.environ)
    yaml_data = _load_yaml(Path(config_path) if config_path else None)
    merged: dict[str, Any] = {}
    # 1. Built-in defaults (DEFAULT_CONFIG_YAML) — lowest precedence among files.
    try:
        default_data = yaml.safe_load(DEFAULT_CONFIG_YAML) or {}
    except yaml.YAMLError:  # pragma: no cover - static constant, never fails
        default_data = {}
    if isinstance(default_data, dict):
        merged.update(default_data)
    # 2. User YAML overrides defaults.
    merged.update(yaml_data)
    # 3. Environment variables (GRA_*) override the YAML.
    for key, value in env_map.items():
        if not key.startswith(ENV_PREFIX):
            continue
        field = key[len(ENV_PREFIX) :].lower()
        if "__" in field:
            continue  # nested delimiter handled by pydantic-settings
        merged[field] = value
    # 4. Programmatic overrides win.
    if overrides:
        merged.update(overrides)
    try:
        return Config.model_validate(merged)
    except Exception as exc:
        from repo_analyzer.infrastructure.errors import ConfigValidationException

        raise ConfigValidationException(
            f"Configuration validation failed: {exc}",
            context={"config_path": str(config_path) if config_path else "default"},
        ) from exc


__all__ = [
    "AISettings",
    "CacheSettings",
    "Config",
    "LoggingSettings",
    "PluginSettings",
    "ReportSettings",
    "ScoringConfig",
    "ScoringWeights",
    "VCSSettings",
    "load_config",
]
