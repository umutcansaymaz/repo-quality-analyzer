"""Java Maven ``pom.xml`` parser."""

from __future__ import annotations

import re
from typing import Any

_DEP_PATTERN = re.compile(
    r"<dependency>\s*<groupId>([^<]+)</groupId>\s*<artifactId>([^<]+)</artifactId>"
    r"(?:\s*<version>([^<]+)</version>)?",
    re.DOTALL,
)


def parse_pom_xml(content: str) -> list[dict[str, Any]]:
    """Parse a ``pom.xml`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    for match in _DEP_PATTERN.finditer(content):
        group_id, artifact_id, version = match.groups()
        deps.append(
            {
                "name": f"{group_id}:{artifact_id}",
                "version": version or "",
                "ecosystem": "maven",
                "direct": True,
                "group": group_id,
            }
        )
    return deps


__all__ = ["parse_pom_xml"]
