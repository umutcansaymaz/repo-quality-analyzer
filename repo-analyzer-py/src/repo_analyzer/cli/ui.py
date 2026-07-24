"""Terminal UI: Rich theme, banner and version screen."""

from __future__ import annotations

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from repo_analyzer._version import __version__

__all__ = [
    "APP_THEME",
    "Banner",
    "VersionScreen",
    "get_theme",
    "print_banner",
    "render_version_screen",
]

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

APP_THEME = Theme(
    {
        "info": "cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "title": "bold magenta",
        "subtitle": "dim cyan",
        "key": "bold blue",
        "value": "white",
        "muted": "dim",
        "ok": "green",
        "fail": "red",
        "skip": "yellow",
        "banner": "bold cyan",
        "banner.accent": "bold magenta",
    }
)


def get_theme() -> Theme:
    """Return the application :class:`rich.theme.Theme`."""
    return APP_THEME


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------

_BANNER_ASCII = r"""
   ____                      _                       _                   _
  / __ \___  ____ ___  ____ | | ___   _ _ __ __ _| |__   ___  ___  __| |
 / /_/ / _ \/ __ `__ \/ __ \| |/ / | | | '__/ _` | '_ \ / _ \/ __|/ _` |
/ _, _/  __/ / / / / / /_/ />  <| |_| | | | (_| | |_) | (_) \__ \ (_| |
/_/ |_|\___/_/ /_/ /_/\____/_/\_\\__,_|_|  \__,_|_.__/ \___/|___/\___|
"""


class Banner:
    """Renders the application banner."""

    def __init__(self, version: str = __version__) -> None:
        self._version = version

    def render(self, console: Console | None = None) -> None:
        """Render the banner to ``console`` (defaults to a new console)."""
        target = console or Console(theme=APP_THEME)
        title = Text(_BANNER_ASCII, style="banner")
        subtitle = Text(
            f"Professional GitHub Repository Analyzer  v{self._version}",
            style="subtitle",
            justify="center",
        )
        panel = Panel(
            Align.center(Group(title, subtitle)),
            border_style="banner.accent",
            padding=(0, 2),
        )
        target.print(panel)
        target.print()


def print_banner(console: Console | None = None) -> None:
    """Print the application banner."""
    Banner().render(console)


# ---------------------------------------------------------------------------
# Version screen
# ---------------------------------------------------------------------------


class VersionScreen:
    """Renders a detailed version / environment screen."""

    def __init__(self, version: str = __version__) -> None:
        self._version = version

    def render(self, console: Console | None = None) -> None:
        """Render the version screen to ``console``."""
        import platform
        import sys

        target = console or Console(theme=APP_THEME)
        Banner(self._version).render(target)
        table = Table(title="Environment", show_header=True, header_style="title")
        table.add_column("Component", style="key", no_wrap=True)
        table.add_column("Version / Value", style="value")
        table.add_row("repo-analyzer", self._version)
        table.add_row("Python", sys.version.split()[0])
        table.add_row("Implementation", platform.python_implementation())
        table.add_row("Platform", platform.platform())
        table.add_row("Machine", platform.machine())
        target.print(table)
        target.print(
            Text(
                "Use 'repo-analyzer doctor' for a full environment health check.",
                style="muted",
            )
        )


def render_version_screen(console: Console | None = None) -> None:
    """Render the version screen."""
    VersionScreen().render(console)
