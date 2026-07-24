"""Hashing utilities for deterministic key generation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any


def hash_string(value: str, *, length: int = 0) -> str:
    """SHA-256 hash of a string, optionally truncated to ``length`` chars.

    Args:
        value: The string to hash.
        length: If positive, truncate the hex digest to this many characters.

    Returns:
        The hexadecimal digest (possibly truncated).
    """
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return digest[:length] if length > 0 else digest


def deterministic_hash(*parts: Any, length: int = 0) -> str:
    """Deterministically hash an arbitrary sequence of parts.

    Each part is converted to its ``repr()`` so that the hash is stable across
    runs (unlike ``hash()`` which is randomized per process).

    Args:
        parts: Values to include in the hash.
        length: If positive, truncate the hex digest.

    Returns:
        The hexadecimal digest.
    """
    material = "|".join(repr(p) for p in parts)
    return hash_string(material, length=length)


def hash_dict(data: Mapping[str, Any], *, length: int = 0) -> str:
    """Hash a mapping deterministically by serializing it with sorted keys.

    Args:
        data: Mapping to hash.
        length: If positive, truncate the hex digest.

    Returns:
        The hexadecimal digest.
    """
    serialized = json.dumps(data, sort_keys=True, default=str, ensure_ascii=False)
    return hash_string(serialized, length=length)


__all__ = ["deterministic_hash", "hash_dict", "hash_string"]
