"""Configuration snapshot domain model.

A frozen, serializable snapshot of the :class:`Config` used for an analysis
run. Stored on :class:`ReportMeta` so reports are reproducible.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConfigSnapshot(BaseModel):
    """A snapshot of the configuration used for a run."""

    model_config = ConfigDict(extra="forbid")

    captured_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    log_level: str = "INFO"
    verbose: bool = False
    debug: bool = False
    cache_enabled: bool = True
    cache_dir: str = ""
    report_formats: list[str] = Field(default_factory=list)
    scoring_weights: dict[str, float] = Field(default_factory=dict)
    ai_enabled: bool = False
    ai_provider: str | None = None
    ai_model: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Any) -> ConfigSnapshot:
        """Build a snapshot from a :class:`Config` instance.

        Args:
            config: A configuration object exposing the expected attributes.

        Returns:
            A :class:`ConfigSnapshot`.
        """
        return cls(
            log_level=getattr(config, "log_level", "INFO"),
            verbose=getattr(config, "verbose", False),
            debug=getattr(config, "debug", False),
            cache_enabled=getattr(config.cache, "enabled", True),
            cache_dir=getattr(config.cache, "dir", ""),
            report_formats=list(getattr(config.reports, "formats", [])),
            scoring_weights=config.scoring.weights.model_dump(),
            ai_enabled=getattr(config.ai, "enabled", False),
            ai_provider=getattr(config.ai, "provider", None),
            ai_model=getattr(config.ai, "model", None),
        )


__all__ = ["ConfigSnapshot"]
