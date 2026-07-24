"""Byte-size formatting utilities."""

from __future__ import annotations

_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
_BINARY_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]


def bytes_to_human(num_bytes: int | float, *, binary: bool = False) -> str:
    """Convert a byte count into a human-readable string.

    Args:
        num_bytes: Number of bytes.
        binary: If ``True`` use binary (1024-based) units (KiB, MiB...),
            otherwise use decimal (1000-based) units (KB, MB...).

    Returns:
        A human-readable size string such as ``"1.50 MB"``.

    Examples:
        >>> bytes_to_human(0)
        '0 B'
        >>> bytes_to_human(1536)
        '1.54 KB'
        >>> bytes_to_human(1536, binary=True)
        '1.50 KiB'
    """
    if num_bytes < 0:
        return f"-{bytes_to_human(-num_bytes, binary=binary)}"
    if num_bytes == 0:
        return "0 B"
    base = 1024 if binary else 1000
    units = _BINARY_UNITS if binary else _UNITS
    size = float(num_bytes)
    unit_idx = 0
    while size >= base and unit_idx < len(units) - 1:
        size /= base
        unit_idx += 1
    if unit_idx == 0:
        return f"{int(size)} {units[unit_idx]}"
    return f"{size:.2f} {units[unit_idx]}"


def human_to_bytes(text: str) -> int:
    """Parse a human-readable size string into bytes.

    Supports both decimal (KB, MB...) and binary (KiB, MiB...) units,
    case-insensitively. Plain integers are interpreted as bytes.

    Args:
        text: Size string such as ``"1.5 MB"`` or ``"100"``.

    Returns:
        The number of bytes.

    Raises:
        ValueError: If the string cannot be parsed.

    Examples:
        >>> human_to_bytes("100")
        100
        >>> human_to_bytes("1 KB")
        1000
        >>> human_to_bytes("1 KiB")
        1024
        >>> human_to_bytes("2.5 MB")
        2500000
    """
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("Empty size string")
    number_part = ""
    unit_part = ""
    for i, ch in enumerate(cleaned):
        if ch.isdigit() or ch in ".-":
            number_part += ch
        else:
            unit_part = cleaned[i:].strip()
            break
    if not number_part:
        raise ValueError(f"Cannot parse numeric portion from {text!r}")
    value = float(number_part)
    if not unit_part or unit_part.upper() == "B":
        return int(value)
    unit_clean = unit_part.upper().replace(" ", "")
    binary = unit_clean.endswith("IB")
    lookup = {u.upper(): 1000**i for i, u in enumerate(_UNITS)}
    lookup_binary = {u.upper(): 1024**i for i, u in enumerate(_BINARY_UNITS)}
    table = lookup_binary if binary else lookup
    if unit_clean not in table:
        raise ValueError(f"Unknown size unit {unit_part!r}")
    return int(value * table[unit_clean])


__all__ = ["bytes_to_human", "human_to_bytes"]
