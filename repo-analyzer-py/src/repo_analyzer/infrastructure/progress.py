"""Progress system built on top of :mod:`rich`.

Provides:

- :class:`ProgressUI`: a façade exposing spinner, progress bar and status
  helpers backed by a single shared :class:`rich.console.Console`.
- :func:`get_console`: access to the shared console.
- :func:`progress_context`: a context manager that yields a :class:`ProgressUI`.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.spinner import Spinner
from rich.status import Status

__all__ = [
    "ProgressUI",
    "get_console",
    "progress_context",
    "set_console",
]

_console: Console = Console()


def get_console() -> Console:
    """Return the shared :class:`rich.console.Console`."""
    return _console


def set_console(console: Console) -> None:
    """Replace the shared console (used in tests)."""
    global _console
    _console = console


class ProgressUI:
    """A façade over Rich's progress / spinner / status primitives.

    Every method is a thin, well-typed wrapper so that the rest of the
    codebase never touches Rich directly and can be tested with a mocked
    console.
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or _console
        self._progress: Progress | None = None

    @property
    def console(self) -> Console:
        """The underlying console."""
        return self._console

    # ----- spinner / status -----------------------------------------------------
    @contextlib.contextmanager
    def spinner(self, message: str, *, spinner_name: str = "dots") -> Iterator[Spinner]:
        """Show a spinner while the block runs.

        Args:
            message: Text shown next to the spinner.
            spinner_name: Name of the Rich spinner animation.

        Yields:
            The :class:`rich.spinner.Spinner` instance.
        """
        spin = Spinner(spinner_name, text=message)
        with self._console.status(message, spinner=spinner_name):
            yield spin

    @contextlib.contextmanager
    def status(self, message: str) -> Iterator[Status]:
        """Show a status line while the block runs.

        Args:
            message: Status text.

        Yields:
            The :class:`rich.status.Status` instance.
        """
        with self._console.status(message) as status:
            yield status

    # ----- progress bar ---------------------------------------------------------
    @contextlib.contextmanager
    def progress_bar(
        self,
        description: str = "Working",
        *,
        total: float | None = 100.0,
        show_remaining: bool = True,
    ) -> Iterator[Progress]:
        """Context manager yielding a configured :class:`rich.progress.Progress`.

        A single task is pre-created with the given ``total``; update it with
        ``progress.update(task_id, advance=...)``.

        Args:
            description: Label shown before the bar.
            total: The total amount (use ``None`` for indeterminate).
            show_remaining: Whether to show the estimated remaining time.

        Yields:
            A :class:`Progress` with one task already added.
        """
        columns: list[Any] = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
        ]
        if total is not None:
            columns.append(MofNCompleteColumn())
        columns.append(TimeElapsedColumn())
        if show_remaining:
            columns.append(TimeRemainingColumn())
        progress = Progress(*columns, console=self._console, transient=False)
        progress.add_task(description, total=total)
        try:
            self._progress = progress
            with progress:
                yield progress
        finally:
            self._progress = None

    # ----- plain output ---------------------------------------------------------
    def print(self, message: str, *, style: str | None = None) -> None:
        """Print a message to the console."""
        self._console.print(message, style=style)

    def info(self, message: str) -> None:
        """Print an informational message."""
        self._console.print(f"[cyan]ℹ[/cyan] {message}")

    def success(self, message: str) -> None:
        """Print a success message."""
        self._console.print(f"[green]✓[/green] {message}")

    def warning(self, message: str) -> None:
        """Print a warning message."""
        self._console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str) -> None:
        """Print an error message."""
        self._console.print(f"[red]✗[/red] {message}")


@contextlib.contextmanager
def progress_context(console: Console | None = None) -> Iterator[ProgressUI]:
    """Context manager yielding a :class:`ProgressUI`.

    Args:
        console: Optional console override.

    Yields:
        A :class:`ProgressUI` instance.
    """
    ui = ProgressUI(console=console)
    try:
        yield ui
    finally:
        pass
