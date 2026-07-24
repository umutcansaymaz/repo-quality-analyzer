"""Go ``go.mod`` parser."""

from __future__ import annotations

import re
from typing import Any

_REQUIRE_PATTERN = re.compile(r"^\s*(\S+)\s+(\S+)(?:\s+//\s*(.+))?")


def parse_go_mod(content: str) -> list[dict[str, Any]]:
    """Parse a ``go.mod`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    in_require_block = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block and stripped == ")":
            in_require_block = False
            continue
        if in_require_block:
            match = _REQUIRE_PATTERN.match(stripped)
            if match:
                deps.append(
                    {
                        "name": match.group(1),
                        "version": match.group(2),
                        "ecosystem": "go",
                        "direct": True,
                    }
                )
        elif stripped.startswith("require "):
            parts = stripped[len("require ") :].split()
            if len(parts) >= 2:
                deps.append(
                    {
                        "name": parts[0],
                        "version": parts[1],
                        "ecosystem": "go",
                        "direct": True,
                    }
                )
    return deps


__all__ = ["parse_go_mod"]
