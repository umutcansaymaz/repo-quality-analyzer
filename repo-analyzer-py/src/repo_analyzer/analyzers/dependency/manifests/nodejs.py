"""Node.js ``package.json`` parser."""

from __future__ import annotations

import json
from typing import Any


def parse_package_json(content: str) -> list[dict[str, Any]]:
    """Parse a ``package.json`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return deps
    for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, version in data.get(section, {}).items():
            deps.append(
                {
                    "name": name,
                    "version": version,
                    "ecosystem": "npm",
                    "direct": True,
                    "group": section,
                }
            )
    return deps


__all__ = ["parse_package_json"]
