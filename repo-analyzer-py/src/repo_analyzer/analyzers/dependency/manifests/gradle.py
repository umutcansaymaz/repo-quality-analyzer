"""Java Gradle ``build.gradle`` parser."""

from __future__ import annotations

import re
from typing import Any

_IMPL_PATTERN = re.compile(
    r"(?:implementation|api|compileOnly|runtimeOnly|testImplementation)"
    r"\s+['\"]([^:'\"]+):([^:'\"]+):([^'\"]+)['\"]"
)


def parse_build_gradle(content: str) -> list[dict[str, Any]]:
    """Parse a ``build.gradle`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    for match in _IMPL_PATTERN.finditer(content):
        group_id, artifact_id, version = match.groups()
        deps.append(
            {
                "name": f"{group_id}:{artifact_id}",
                "version": version,
                "ecosystem": "gradle",
                "direct": True,
                "group": group_id,
            }
        )
    return deps


__all__ = ["parse_build_gradle"]
