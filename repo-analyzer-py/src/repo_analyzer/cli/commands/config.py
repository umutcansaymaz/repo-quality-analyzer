"""``repo-analyzer config`` command."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from repo_analyzer.infrastructure.config import Config
from repo_analyzer.infrastructure.logging import configure_logging


def run_config(console: Console, config: Config) -> None:
    """Show the resolved configuration.

    Args:
        console: Rich console.
        config: Resolved :class:`Config`.
    """
    configure_logging(config)
    payload = config.model_dump(mode="json")
    pretty = json.dumps(payload, indent=2, sort_keys=True, default=str)
    console.print(
        Panel(
            Syntax(pretty, "json", theme="ansi_dark", line_numbers=False, word_wrap=True),
            title="Resolved Configuration",
            border_style="info",
            expand=True,
        )
    )


__all__ = ["run_config"]
