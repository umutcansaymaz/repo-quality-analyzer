"""``repo-analyzer update`` command.

At the infrastructure stage this is a stub: it reports the current version
and notes that update-checking is not yet implemented. The command always
exits successfully so that automation scripts are not broken.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel


def run_update(console: Console, current_version: str) -> None:
    """Check for a newer release (stub).

    Args:
        console: Rich console.
        current_version: The currently installed version.
    """
    console.print(
        Panel(
            f"[key]Current version:[/key] [value]{current_version}[/value]\n\n"
            "[muted]Update checking is not implemented at the infrastructure stage.[/muted]\n"
            "[muted]To upgrade manually: pip install --upgrade repo-analyzer[/muted]",
            title="Update",
            border_style="info",
            expand=False,
        )
    )


__all__ = ["run_update"]
