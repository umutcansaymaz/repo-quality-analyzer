"""Tests for ``repo_analyzer.utils.size``."""

from __future__ import annotations

import pytest

from repo_analyzer.utils.size import bytes_to_human, human_to_bytes


def test_bytes_to_human_zero() -> None:
    """Zero bytes should render as '0 B'."""
    assert bytes_to_human(0) == "0 B"


def test_bytes_to_human_bytes() -> None:
    """Small values should render in bytes."""
    assert bytes_to_human(512) == "512 B"


def test_bytes_to_human_decimal_kb() -> None:
    """Decimal KB should use 1000 base."""
    assert bytes_to_human(1500) == "1.50 KB"


def test_bytes_to_human_binary_kib() -> None:
    """Binary KiB should use 1024 base."""
    assert bytes_to_human(1536, binary=True) == "1.50 KiB"


def test_bytes_to_human_mb() -> None:
    """MB conversion should work."""
    assert bytes_to_human(2_500_000) == "2.50 MB"


def test_bytes_to_human_negative() -> None:
    """Negative values should be prefixed with '-'."""
    result = bytes_to_human(-1024)
    assert result.startswith("-")


def test_human_to_bytes_plain_int() -> None:
    """A plain integer should be treated as bytes."""
    assert human_to_bytes("100") == 100


def test_human_to_bytes_kb() -> None:
    """'1 KB' should equal 1000 bytes."""
    assert human_to_bytes("1 KB") == 1000


def test_human_to_bytes_kib() -> None:
    """'1 KiB' should equal 1024 bytes."""
    assert human_to_bytes("1 KiB") == 1024


def test_human_to_bytes_mb_decimal() -> None:
    """'2.5 MB' should equal 2,500,000 bytes."""
    assert human_to_bytes("2.5 MB") == 2_500_000


def test_human_to_bytes_case_insensitive() -> None:
    """Units should be case-insensitive."""
    assert human_to_bytes("1 kb") == 1000


def test_human_to_bytes_empty_raises() -> None:
    """An empty string should raise ValueError."""
    with pytest.raises(ValueError):
        human_to_bytes("")


def test_human_to_bytes_unknown_unit_raises() -> None:
    """An unknown unit should raise ValueError."""
    with pytest.raises(ValueError):
        human_to_bytes("1 XB")


def test_human_to_bytes_round_trip() -> None:
    """bytes_to_human then human_to_bytes should roughly round-trip."""
    original = 5_000_000
    rendered = bytes_to_human(original)
    assert human_to_bytes(rendered) == original
