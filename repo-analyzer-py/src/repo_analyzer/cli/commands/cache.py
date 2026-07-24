"""``repo-analyzer cache`` sub-commands."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.infrastructure.config import Config
from repo_analyzer.infrastructure.logging import configure_logging
from repo_analyzer.utils.size import bytes_to_human
from repo_analyzer.utils.time import format_duration


def _open_cache(config: Config) -> SQLiteCacheAdapter:
    """Build a :class:`SQLiteCacheAdapter` from the config."""
    return SQLiteCacheAdapter(f"{config.cache.dir}/cache.db")


def run_cache_list(console: Console, config: Config) -> None:
    """List cached entries.

    Args:
        console: Rich console.
        config: Resolved configuration.
    """
    configure_logging(config)
    adapter = _open_cache(config)
    try:
        entries = adapter.list_entries()
        if not entries:
            console.print("[muted]Cache is empty.[/muted]")
            return
        table = Table(title="Cache Entries", show_header=True, header_style="title")
        table.add_column("Key", style="key", no_wrap=False)
        table.add_column("Type", style="value")
        table.add_column("Repository", style="value")
        table.add_column("Size", justify="right", style="value")
        table.add_column("Created", style="value")
        table.add_column("Accesses", justify="right", style="value")
        for entry in entries:
            table.add_row(
                entry.key[:12] + "…",
                entry.entry_type.value,
                entry.repository_url,
                bytes_to_human(entry.size_bytes),
                entry.created_at.strftime("%Y-%m-%d %H:%M"),
                str(entry.access_count),
            )
        console.print(table)
        console.print(
            f"[muted]{len(entries)} entr"
            + ("y" if len(entries) == 1 else "ies")
            + " · purge expired with 'repo-analyzer cache clear'[/muted]"
        )
    finally:
        adapter.close()


def run_cache_clear(console: Console, config: Config) -> None:
    """Clear all cache entries.

    Args:
        console: Rich console.
        config: Resolved configuration.
    """
    configure_logging(config)
    adapter = _open_cache(config)
    try:
        count = adapter.clear()
        elapsed = format_duration(0.0)
        if count == 0:
            console.print("[muted]Cache was already empty.[/muted]")
        else:
            console.print(
                f"[success]✓ Cleared {count} cache entr"
                + ("y" if count == 1 else "ies")
                + f"[/success] [muted]({elapsed})[/muted]"
            )
    finally:
        adapter.close()


__all__ = ["run_cache_clear", "run_cache_list"]
