"""``repo-analyzer analyze`` command.

At the infrastructure stage this only:

- Validates the repository URL.
- Loads configuration and configures logging.
- Initializes the plugin manager and cache adapter (wiring).
- Prints a confirmation that the pipeline has been initialized.

No actual analysis is performed.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.infrastructure.config import Config
from repo_analyzer.infrastructure.errors import ConfigurationException
from repo_analyzer.infrastructure.logging import configure_logging
from repo_analyzer.infrastructure.progress import ProgressUI
from repo_analyzer.plugins import PluginManager
from repo_analyzer.utils.validation import is_valid_git_url


def run_analyze(console: Console, config: Config, repository_url: str) -> None:
    """Run the ``analyze`` command.

    Args:
        console: The Rich console to render output to.
        config: The resolved :class:`Config`.
        repository_url: The repository URL provided by the user.
    """
    logger = configure_logging(config)
    ui = ProgressUI(console=console)

    # Validate URL.
    if not is_valid_git_url(repository_url):
        console.print(f"[error]✗ Invalid repository URL:[/error] {repository_url}")
        raise ConfigurationException(
            f"Invalid repository URL: {repository_url!r}",
            field="repository",
        )

    repository = parse_repository_url(repository_url)
    logger.info(
        "Repository parsed: host=%s owner=%s name=%s",
        repository.host,
        repository.owner,
        repository.name,
    )

    # Initialize wiring (cache + plugins) to prove the infrastructure works.
    cache_dir = config.cache.dir
    db_path = f"{cache_dir}/cache.db"
    cache_adapter = SQLiteCacheAdapter(db_path)

    plugin_manager = PluginManager()
    plugin_dirs = config.plugins.dirs
    loaded = plugin_manager.load_all(plugin_dirs)

    # Render a summary.
    ui.print("")
    console.print(f"[title]Repository[/title]  [key]{repository.owner}/{repository.name}[/key]")
    console.print(f"[title]Host[/title]       [value]{repository.host}[/value]")
    console.print(f"[title]Access[/title]     [value]{repository.access.value}[/value]")
    console.print(f"[title]Plugins[/title]    [value]{loaded} loaded[/value]")
    console.print(
        f"[title]Cache[/title]       [value]{len(cache_adapter.list_entries())} entries[/value]"
    )
    ui.print("")

    # Final confirmation per the brief.
    console.print(
        Panel(
            "[bold green]✓ Analyzer pipeline initialized[/bold green]",
            border_style="success",
            expand=False,
        ),
        justify="center",
    )

    # Cleanup.
    plugin_manager.dispose_all()
    cache_adapter.close()


__all__ = ["run_analyze"]
