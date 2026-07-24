"""PHP ``composer.json`` parser."""

from __future__ import annotations

import json
from typing import Any


def parse_composer_json(content: str) -> list[dict[str, Any]]:
    """Parse a ``composer.json`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return deps
    for section in ("require", "require-dev"):
        for name, version in data.get(section, {}).items():
            if name == "php":
                continue
            deps.append(
                {
                    "name": name,
                    "version": version,
                    "ecosystem": "composer",
                    "direct": True,
                    "group": section,
                }
            )
    return deps


__all__ = ["parse_composer_json"]
