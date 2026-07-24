"""repo-analyzer: Professional GitHub repository analyzer.

A CLI tool that performs static analysis, security auditing, architecture
review and produces AI-enriched technical reports for any GitHub repository.

The project follows a Hexagonal (Ports & Adapters) architecture with a
plugin-based analysis engine. See ``docs/SDD-github-repo-analyzer.md`` for
the full Software Design Document.
"""

from __future__ import annotations

from repo_analyzer._version import __version__

__all__ = ["__version__"]
