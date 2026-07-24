"""``repo-analyzer analyze`` command.

Runs the full analysis pipeline (clone → analyzers → AnalysisResult) and
prints a summary. No AI review, no report generation at this stage — the
structured :class:`AnalysisResult` is the output.
"""

from __future__ import annotations

import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repo_analyzer.adapters.cache import SQLiteCacheAdapter
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.orchestrator import Orchestrator
from repo_analyzer.infrastructure.config import Config
from repo_analyzer.infrastructure.errors import ConfigurationException
from repo_analyzer.infrastructure.logging import configure_logging
from repo_analyzer.infrastructure.progress import ProgressUI
from repo_analyzer.utils.size import bytes_to_human
from repo_analyzer.utils.validation import is_valid_git_url


def run_analyze(
    console: Console,
    config: Config,
    repository_url: str,
    *,
    output: Path | None = None,
) -> None:
    """Run the ``analyze`` command.

    Args:
        console: The Rich console to render output to.
        config: The resolved :class:`Config`.
        repository_url: The repository URL provided by the user.
        output: Optional path to write the JSON :class:`AnalysisResult`.
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

    # Set up cache + orchestrator.
    cache_adapter = SQLiteCacheAdapter(f"{config.cache.dir}/cache.db")
    orchestrator = Orchestrator(
        cache_adapter,
        max_workers=4,
        clone_depth=config.vcs.clone_depth,
        timeout=config.vcs.timeout_sec,
    )

    ui.print("")
    console.print(f"[title]Analyzing[/title] [key]{repository.owner}/{repository.name}[/key]")
    console.print(f"[title]Host[/title]       [value]{repository.host}[/value]")
    console.print(f"[title]Access[/title]     [value]{repository.access.value}[/value]")
    ui.print("")

    try:
        result = orchestrator.analyze(repository, progress=ui)
    finally:
        cache_adapter.close()

    _render_summary(console, result)

    if output:
        payload = result.model_dump(mode="json")
        output.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        console.print(f"\n[muted]Analysis result written to {output}[/muted]")

    console.print(
        Panel(
            "[bold green]✓ Analyzer pipeline completed[/bold green]",
            border_style="success",
            expand=False,
        ),
        justify="center",
    )


def _render_summary(console: Console, result: object) -> None:
    """Render a summary table from the analysis result."""
    table = Table(title="Analysis Summary", show_header=True, header_style="title")
    table.add_column("Metric", style="key", no_wrap=True)
    table.add_column("Value", style="value")

    # Repository metadata.
    meta = getattr(result, "repository_metadata", None)
    if meta:
        table.add_row("Repository", f"{meta.owner}/{meta.name}")
        if meta.description:
            table.add_row("Description", meta.description[:80])
        if meta.default_branch:
            table.add_row("Default branch", meta.default_branch)
        if meta.license:
            table.add_row("License", meta.license)
        if meta.total_commits is not None:
            table.add_row("Total commits", str(meta.total_commits))
        if meta.total_branches is not None:
            table.add_row("Total branches", str(meta.total_branches))
        if meta.contributors:
            table.add_row("Contributors", str(len(meta.contributors)))
        if meta.size_bytes is not None:
            table.add_row("Repository size", bytes_to_human(meta.size_bytes))

    # File inventory.
    inv = getattr(result, "file_inventory", None)
    if inv:
        table.add_row("Total files", str(inv.total_files))
        table.add_row("Total directories", str(inv.total_directories))
        table.add_row("Total bytes", bytes_to_human(inv.total_bytes))
        table.add_row("Binary files", str(inv.binary_files))
        table.add_row("Duplicate files", str(inv.duplicate_files))

    # Language distribution.
    lang = getattr(result, "language_distribution", None)
    if lang and lang.loc:
        top_langs = sorted(lang.loc.items(), key=lambda kv: kv[1], reverse=True)[:5]
        table.add_row(
            "Top languages",
            ", ".join(f"{name} ({loc})" for name, loc in top_langs),
        )

    # Metrics.
    metrics = getattr(result, "metrics_report", None)
    if metrics:
        table.add_row("Total LOC", str(metrics.total_loc))
        table.add_row("Total SLOC", str(metrics.total_sloc))
        table.add_row("Functions", str(metrics.total_functions))
        table.add_row("Classes", str(metrics.total_classes))

    # Complexity.
    complexity = getattr(result, "complexity_report", None)
    if complexity:
        table.add_row("Avg complexity", str(complexity.average_complexity))

    # Dependencies.
    deps = getattr(result, "dependency_analysis", None)
    if deps:
        table.add_row("Dependencies", str(deps.total_dependencies))
        table.add_row("Unused deps", str(len(deps.unused_dependencies)))

    # Documentation.
    doc = getattr(result, "documentation_report", None)
    if doc:
        table.add_row("README score", f"{doc.readme_score:.0%}")
        table.add_row("Docstring coverage", f"{doc.docstring_coverage:.0%}")

    # Tests.
    tests = getattr(result, "test_analysis", None)
    if tests:
        table.add_row("Test frameworks", ", ".join(tests.frameworks) or "none")
        table.add_row("Test files", str(tests.total_test_files))
        if tests.estimated_coverage is not None:
            table.add_row("Est. coverage", f"{tests.estimated_coverage:.1f}%")

    # Status.
    status = getattr(result, "status", None)
    if status:
        table.add_row("Status", str(status.value))
    errors = getattr(result, "errors", [])
    if errors:
        table.add_row("Errors", str(len(errors)))

    console.print(table)


__all__ = ["run_analyze"]
