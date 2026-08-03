"""Sample module for analyzer tests.

This module intentionally contains a variety of constructs: functions,
classes, imports (used and unused), docstrings, comments and nesting, so
that the analyzers (AST, metrics, complexity, imports, documentation) have
non-trivial input to work with.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import unused_module

# A module-level constant.
MAX_RETRIES = 3


def greet(name: str) -> str:
    """Return a greeting for ``name``.

    Args:
        name: The name to greet.

    Returns:
        A greeting string.
    """
    return f"Hello, {name}!"


def complex_function(a: int, b: int, c: int) -> int:
    """A deliberately complex function for cyclomatic-complexity tests."""
    result = 0
    if a > 0:
        result += a
        if b > 0:
            result += b
            for i in range(c):
                if i % 2 == 0:
                    result += i
                else:
                    result -= i
    elif b < 0:
        result = -b
    else:
        while a < c:
            a += 1
            result += a
    return result


class Animal:
    """A base animal class."""

    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> str:
        """Return the animal's sound."""
        return "..."

    def describe(self) -> str:
        """Describe the animal."""
        return f"{self.name} says {self.speak()}"


class Dog(Animal):
    """A dog, inheriting from :class:`Animal`."""

    def speak(self) -> str:
        return "Woof!"

    def fetch(self, item: str) -> str:
        """Fetch an item."""
        return f"{self.name} fetches {item}"


def serialize(obj: Any) -> str:
    """Serialize an object to JSON."""
    return json.dumps(obj, default=str)


def read_config(path: Path) -> dict[str, Any]:
    """Read a JSON config file."""
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}
