"""REST API entry point for ``python -m repo_analyzer.api``."""

from __future__ import annotations

from repo_analyzer.api.app import run_api


def main() -> None:
    """Run the API server."""
    run_api()


if __name__ == "__main__":
    main()
