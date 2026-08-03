"""Rust ``Cargo.toml`` parser."""

from __future__ import annotations

import tomllib
from typing import Any


def parse_cargo_toml(content: str) -> list[dict[str, Any]]:
    """Parse a ``Cargo.toml`` into a list of dependency dicts."""
    deps: list[dict[str, Any]] = []
    try:
        data = tomllib.loads(content)
    except Exception:
        return deps
    cargo = data.get("dependencies", {})
    for name, spec in cargo.items():
        if isinstance(spec, str):
            version = spec
        elif isinstance(spec, dict):
            version = spec.get("version", "")
        else:
            version = ""
        deps.append(
            {
                "name": name,
                "version": version,
                "ecosystem": "cargo",
                "direct": True,
            }
        )
    dev_deps = data.get("dev-dependencies", {})
    for name, spec in dev_deps.items():
        version = spec if isinstance(spec, str) else spec.get("version", "")
        deps.append(
            {
                "name": name,
                "version": version,
                "ecosystem": "cargo",
                "direct": True,
                "group": "dev",
            }
        )
    return deps


__all__ = ["parse_cargo_toml"]
