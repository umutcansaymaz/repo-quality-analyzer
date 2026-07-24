"""Python manifest parsers (``requirements.txt`` and ``pyproject.toml``)."""

from __future__ import annotations

import re
import tomllib
from typing import Any

_REQUIREMENT_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)\s*(?:\[[^\]]+\])?\s*(?:[<>=!~]=?[A-Za-z0-9._*+]+)?"
)


def parse_requirements(content: str) -> list[dict[str, Any]]:
    """Parse a ``requirements.txt`` content into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        # Strip inline comments.
        if "#" in stripped:
            stripped = stripped.split("#", 1)[0].strip()
        match = _REQUIREMENT_PATTERN.match(stripped)
        if not match:
            continue
        name = match.group(1)
        version_match = re.search(r"[<>=!~]=?[A-Za-z0-9._*+]+", stripped)
        version = version_match.group(0) if version_match else ""
        deps.append(
            {
                "name": name,
                "version": version,
                "ecosystem": "pypi",
                "direct": True,
            }
        )
    return deps


def parse_pyproject(content: str) -> list[dict[str, Any]]:
    """Parse a ``pyproject.toml`` content into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    try:
        data = tomllib.loads(content)
    except Exception:
        return deps
    project = data.get("project", {})
    dependencies = project.get("dependencies", [])
    optional = project.get("optional-dependencies", {})
    for dep_str in dependencies:
        parsed = _parse_pep508(dep_str)
        if parsed:
            parsed["direct"] = True
            deps.append(parsed)
    for group, group_deps in optional.items():
        for dep_str in group_deps:
            parsed = _parse_pep508(dep_str)
            if parsed:
                parsed["direct"] = True
                parsed["group"] = group
                deps.append(parsed)
    # Poetry-style.
    tool_poetry = data.get("tool", {}).get("poetry", {})
    for section in ("dependencies", "dev-dependencies"):
        for name, spec in tool_poetry.get(section, {}).items():
            if name == "python":
                continue
            version = spec if isinstance(spec, str) else ""
            deps.append(
                {
                    "name": name,
                    "version": version,
                    "ecosystem": "pypi",
                    "direct": True,
                }
            )
    return deps


def _parse_pep508(spec: str) -> dict[str, Any] | None:
    """Parse a PEP 508 dependency specifier."""
    match = re.match(r"^([A-Za-z0-9_.-]+)\s*(.*)$", spec.strip())
    if not match:
        return None
    return {
        "name": match.group(1),
        "version": match.group(2).strip(),
        "ecosystem": "pypi",
    }


__all__ = ["parse_requirements", "parse_pyproject"]
