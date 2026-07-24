"""Typer CLI application for repo-analyzer.

Exposes the following commands (all functional at the infrastructure stage):

- ``analyze``    — initialize the analyzer pipeline (stub output).
- ``version``    — print version + environment banner.
- ``doctor``     — run environment health checks.
- ``cache list`` — list cached entries.
- ``cache clear``— clear the cache.
- ``config``     — show the resolved configuration.
- ``update``     — check for a newer release (stub).

No analysis is performed at this stage: ``analyze`` only initializes the
pipeline and prints a confirmation, as required by the brief.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from repo_analyzer._version import __version__
from repo_analyzer.cli.ui import APP_THEME
from repo_analyzer.infrastructure.config import Config, load_config

# Sub-applications ----------------------------------------------------------
app = typer.Typer(
    name="repo-analyzer",
    help="Professional GitHub repository analyzer.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False,
    pretty_exceptions_show_locals=False,
)
cache_app = typer.Typer(name="cache", help="Manage the local cache.", no_args_is_help=True)
app.add_typer(cache_app, name="cache")

# Shared console with the application theme.
console = Console(theme=APP_THEME)


def _build_config(
    config_path: Path | None,
    verbose: bool,
    debug: bool,
) -> Config:
    """Load configuration with CLI overrides applied."""
    overrides: dict[str, object] = {}
    if verbose:
        overrides["verbose"] = True
    if debug:
        overrides["debug"] = True
    return load_config(config_path=config_path, overrides=overrides or None)


# Common option type aliases for readability.
ConfigOption = typer.Option(
    None,
    "--config",
    "-c",
    help="Path to a config.yaml file (default: ~/.config/repo-analyzer/config.yaml).",
    exists=False,
    dir_okay=False,
    resolve_path=False,
)
VerboseOption = typer.Option(False, "--verbose", "-v", help="Enable verbose output.")
DebugOption = typer.Option(False, "--debug", help="Enable debug logging.")


# ---------------------------------------------------------------------------
# Top-level commands
# ---------------------------------------------------------------------------


@app.callback(invoke_without_command=False)
def main_callback() -> None:
    """repo-analyzer — see ``--help`` for available commands."""


@app.command()
def version() -> None:
    """Print the version and environment banner."""
    from repo_analyzer.cli.ui import VersionScreen

    VersionScreen(__version__).render(console)


@app.command()
def doctor(
    config_path: Path | None = ConfigOption,
    verbose: bool = VerboseOption,
    debug: bool = DebugOption,
) -> None:
    """Run environment health checks and display a status table."""
    from repo_analyzer.cli.commands.doctor import run_doctor

    config = _build_config(config_path, verbose, debug)
    run_doctor(console, config)


@app.command()
def analyze(
    repository: str = typer.Argument(..., help="Repository URL to analyze."),
    config_path: Path | None = ConfigOption,
    verbose: bool = VerboseOption,
    debug: bool = DebugOption,
) -> None:
    """Initialize the analyzer pipeline for a repository.

    At this infrastructure stage no analysis is performed: the command
    validates the repository URL, loads configuration, sets up logging and
    prints a confirmation that the pipeline has been initialized.
    """
    from repo_analyzer.cli.commands.analyze import run_analyze

    config = _build_config(config_path, verbose, debug)
    run_analyze(console, config, repository)


@app.command()
def config(
    config_path: Path | None = ConfigOption,
    verbose: bool = VerboseOption,
    debug: bool = DebugOption,
) -> None:
    """Show the resolved configuration."""
    from repo_analyzer.cli.commands.config import run_config

    resolved = _build_config(config_path, verbose, debug)
    run_config(console, resolved)


@app.command()
def update() -> None:
    """Check for a newer release of repo-analyzer."""
    from repo_analyzer.cli.commands.update import run_update

    run_update(console, __version__)


# ---------------------------------------------------------------------------
# Cache sub-commands
# ---------------------------------------------------------------------------


@cache_app.command("list")
def cache_list(
    config_path: Path | None = ConfigOption,
    verbose: bool = VerboseOption,
    debug: bool = DebugOption,
) -> None:
    """List cached repository entries."""
    from repo_analyzer.cli.commands.cache import run_cache_list

    config = _build_config(config_path, verbose, debug)
    run_cache_list(console, config)


@cache_app.command("clear")
def cache_clear(
    config_path: Path | None = ConfigOption,
    verbose: bool = VerboseOption,
    debug: bool = DebugOption,
) -> None:
    """Remove all cache entries."""
    from repo_analyzer.cli.commands.cache import run_cache_clear

    config = _build_config(config_path, verbose, debug)
    run_cache_clear(console, config)


def run() -> None:
    """Entry point used by the ``repo-analyzer`` console script."""
    app()


if __name__ == "__main__":
    run()
