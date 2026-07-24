"""Tests for ``repo_analyzer.utils.time``."""

from __future__ import annotations

from repo_analyzer.utils.time import format_duration, utc_now_iso


def test_utc_now_iso_returns_iso_string() -> None:
    """The result should be an ISO-8601 string with timezone info."""
    result = utc_now_iso()
    assert isinstance(result, str)
    assert "T" in result
    assert result.endswith("+00:00")


def test_format_duration_milliseconds() -> None:
    """Sub-second durations should render as milliseconds."""
    assert format_duration(0.5) == "500ms"
    assert format_duration(0.001) == "1ms"


def test_format_duration_seconds() -> None:
    """Durations under a minute should render as seconds."""
    assert format_duration(12.3) == "12.30s"


def test_format_duration_minutes_and_seconds() -> None:
    """Durations over a minute should include both."""
    assert format_duration(75) == "1m 15s"


def test_format_duration_hours() -> None:
    """Durations over an hour should include hours."""
    assert format_duration(3700) == "1h 1m 40s"


def test_format_duration_zero() -> None:
    """Zero seconds should render as '0ms' (sub-second range)."""
    assert format_duration(0) == "0ms"


def test_format_duration_negative() -> None:
    """Negative durations should be prefixed with '-'."""
    assert format_duration(-5).startswith("-")


def test_format_duration_exactly_one_minute() -> None:
    """Exactly 60 seconds should render as '1m' (no zero seconds)."""
    assert format_duration(60) == "1m"


def test_format_duration_exactly_one_hour() -> None:
    """Exactly 3600 seconds should render as '1h' (no zero minutes/seconds)."""
    assert format_duration(3600) == "1h"
