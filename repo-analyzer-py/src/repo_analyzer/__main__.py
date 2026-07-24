"""Entry point for ``python -m repo_analyzer``."""

from __future__ import annotations

from repo_analyzer.cli.app import app


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
