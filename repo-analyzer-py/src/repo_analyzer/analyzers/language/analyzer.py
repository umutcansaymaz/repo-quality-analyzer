"""Language detector analyzer.

Identifies the programming language of each source file using file-extension
mapping, shebang inspection and content heuristics. Produces a
:class:`LanguageDistribution` summary.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import LanguageDistribution
from repo_analyzer.core.domain.repository import Repository

#: Extension → language mapping.
_EXTENSION_MAP: dict[str, str] = {
    "py": "Python",
    "pyi": "Python",
    "js": "JavaScript",
    "jsx": "JavaScript",
    "mjs": "JavaScript",
    "cjs": "JavaScript",
    "ts": "TypeScript",
    "tsx": "TypeScript",
    "go": "Go",
    "rs": "Rust",
    "java": "Java",
    "kt": "Kotlin",
    "kts": "Kotlin",
    "swift": "Swift",
    "c": "C",
    "h": "C",
    "cpp": "C++",
    "cc": "C++",
    "cxx": "C++",
    "hpp": "C++",
    "hh": "C++",
    "cs": "C#",
    "php": "PHP",
    "rb": "Ruby",
    "sh": "Shell",
    "bash": "Shell",
    "zsh": "Shell",
    "yaml": "YAML",
    "yml": "YAML",
    "json": "JSON",
    "md": "Markdown",
    "markdown": "Markdown",
}

#: Shebang interpreter → language mapping.
_SHEBANG_MAP: dict[str, str] = {
    "python": "Python",
    "python3": "Python",
    "node": "JavaScript",
    "bash": "Shell",
    "sh": "Shell",
    "zsh": "Shell",
    "ruby": "Ruby",
    "php": "PHP",
}


class LanguageDetector(BaseAnalyzer):
    """Detect the language of every source file in the workspace."""

    _analyzer_name = "language-detector"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 0

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run language detection and return a :class:`LanguageDistribution`."""
        file_languages: dict[str, str] = {}
        loc_by_lang: dict[str, int] = defaultdict(int)
        count_by_lang: dict[str, int] = defaultdict(int)

        for path in self._iter_source_files(workspace):
            lang = self._detect_language(path)
            if lang is None:
                continue
            rel = str(path.relative_to(workspace))
            file_languages[rel] = lang
            count_by_lang[lang] += 1
            loc_by_lang[lang] += self._count_lines(path)

        total_loc = sum(loc_by_lang.values()) or 1
        percentages = {lang: round(loc * 100.0 / total_loc, 2) for lang, loc in loc_by_lang.items()}
        distribution = LanguageDistribution(
            percentages=percentages,
            loc=dict(loc_by_lang),
            file_counts=dict(count_by_lang),
            file_languages=file_languages,
        )
        return {"language_distribution": distribution.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_source_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        """Yield source files, skipping ``.git`` and common non-source dirs."""
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        for root, dirs, files in self._walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                yield root / name

    @staticmethod
    def _walk(workspace: Path):  # type: ignore[no-untyped-def]
        import os

        for root, dirs, files in os.walk(workspace):
            yield Path(root), dirs, files

    def _detect_language(self, path: Path) -> str | None:
        """Detect the language of a single file."""
        ext = path.suffix.lower().lstrip(".")
        if ext and ext in _EXTENSION_MAP:
            return _EXTENSION_MAP[ext]
        # No extension: try shebang.
        try:
            with path.open("rb") as handle:
                first = handle.read(64)
        except OSError:
            return None
        if first.startswith(b"#!"):
            try:
                line = first.decode("utf-8", errors="ignore").strip()
            except UnicodeDecodeError:
                return None
            for interp, lang in _SHEBANG_MAP.items():
                if interp in line:
                    return lang
        return None

    @staticmethod
    def _count_lines(path: Path) -> int:
        """Count non-blank lines in a text file."""
        try:
            with path.open("rb") as handle:
                return sum(1 for line in handle if line.strip() and not line.startswith(b"#!"))
        except OSError:
            return 0


__all__ = ["LanguageDetector"]
