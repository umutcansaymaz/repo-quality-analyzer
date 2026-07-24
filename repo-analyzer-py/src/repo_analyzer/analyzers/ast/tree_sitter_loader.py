"""Tree-sitter language loader.

Lazily loads tree-sitter parsers for supported languages and caches them.
Falls back gracefully when a grammar is not installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Extension → tree-sitter language name.
_EXT_TO_LANGUAGE: dict[str, str] = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "tsx": "tsx",
    "go": "go",
    "rs": "rust",
    "java": "java",
    "kt": "kotlin",
    "kts": "kotlin",
    "swift": "swift",
    "c": "c",
    "h": "c",
    "cpp": "cpp",
    "cc": "cpp",
    "cxx": "cpp",
    "hpp": "cpp",
    "hh": "cpp",
    "cs": "csharp",
    "rb": "ruby",
    "php": "php",
    "sh": "bash",
    "bash": "bash",
}


class TreeSitterLoader:
    """Lazily load and cache tree-sitter parsers."""

    def __init__(self) -> None:
        self._parsers: dict[str, Any] = {}
        self._languages: dict[str, Any] = {}
        self._available: set[str] | None = None

    def language_for_file(self, path: Path) -> str | None:
        """Return the tree-sitter language name for ``path``, or ``None``."""
        ext = path.suffix.lower().lstrip(".")
        return _EXT_TO_LANGUAGE.get(ext)

    def parse(self, language: str, content: str) -> Any | None:
        """Parse ``content`` and return the tree, or ``None`` on failure."""
        parser = self._get_parser(language)
        if parser is None:
            return None
        try:
            return parser.parse(content.encode("utf-8"))
        except Exception as exc:  # pragma: no cover - defensive
            _logger.debug("Failed to parse with %s: %s", language, exc)
            return None

    def _get_parser(self, language: str) -> Any | None:
        """Return a cached parser for ``language``, loading it if needed."""
        if language in self._parsers:
            return self._parsers[language]
        parser = self._load_parser(language)
        self._parsers[language] = parser
        return parser

    def _load_parser(self, language: str) -> Any | None:
        """Load a parser for ``language`` from ``tree_sitter_languages``."""
        try:
            from tree_sitter_language_pack import get_parser

            parser = get_parser(language)
            _logger.debug("Loaded tree-sitter parser for %s", language)
            return parser
        except ImportError:
            _logger.debug("tree_sitter_language_pack not available")
            return None
        except Exception as exc:
            _logger.debug("No tree-sitter grammar for %s: %s", language, exc)
            return None

    def available_languages(self) -> set[str]:
        """Return the set of languages with available grammars."""
        if self._available is not None:
            return self._available
        available: set[str] = set()
        for lang in set(_EXT_TO_LANGUAGE.values()):
            if self._get_parser(lang) is not None:
                available.add(lang)
        self._available = available
        return available


__all__ = ["TreeSitterLoader"]
