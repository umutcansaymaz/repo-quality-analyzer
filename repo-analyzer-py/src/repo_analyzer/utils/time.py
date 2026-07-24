"""Time / duration utilities."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        The current time in ``YYYY-MM-DDTHH:MM:SS.ffffff+00:00`` format.
    """
    return datetime.now(tz=UTC).isoformat()


def format_duration(seconds: float) -> str:
    """Format a duration in seconds into a human-readable string.

    Examples:
        >>> format_duration(0.5)
        '500ms'
        >>> format_duration(12.3)
        '12.30s'
        >>> format_duration(75)
        '1m 15s'
        >>> format_duration(3700)
        '1h 1m 40s'

    Args:
        seconds: Duration in seconds.

    Returns:
        A short human-readable duration string.
    """
    if seconds < 0:
        return f"-{format_duration(-seconds)}"
    if seconds < 1:
        return f"{int(seconds * 1000)}ms"
    if seconds < 60:
        return f"{seconds:.2f}s"
    total_seconds = int(round(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


__all__ = ["format_duration", "utc_now_iso"]
