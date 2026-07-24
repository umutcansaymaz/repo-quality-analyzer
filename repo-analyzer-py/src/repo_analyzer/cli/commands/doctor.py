"""``repo-analyzer doctor`` command.

Verifies that the runtime environment is healthy:

- Python version meets the minimum requirement.
- Git is installed and reachable.
- SQLite is importable and a test database can be opened.
- The working directory is writable.
- The temp directory is writable.
- The config file (if any) is readable.
- Relevant environment variables are present.

Results are rendered as a Rich table with OK / FAIL / SKIP status icons.
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repo_analyzer.infrastructure.config import Config, get_default_config_path
from repo_analyzer.infrastructure.logging import configure_logging
from repo_analyzer.utils.size import bytes_to_human

MIN_PYTHON = (3, 12)

_OK = "[ok]OK[/ok]"
_FAIL = "[fail]FAIL[/fail]"
_SKIP = "[skip]SKIP[/skip]"


@dataclass
class CheckResult:
    """The outcome of a single doctor check."""

    name: str
    status: str
    detail: str

    @property
    def passed(self) -> bool:
        return self.status in {_OK, _SKIP}


def run_doctor(console: Console, config: Config) -> None:
    """Run all environment checks and render the result table.

    Args:
        console: The Rich console to render to.
        config: The resolved :class:`Config`.
    """
    configure_logging(config)

    results: list[CheckResult] = []
    results.append(_check_python())
    results.append(_check_git())
    results.append(_check_sqlite())
    results.append(_check_working_directory())
    results.append(_check_temp_directory())
    results.append(_check_config_file())
    results.append(_check_environment_variables())
    results.append(_check_cache_directory(config))

    table = Table(title="Environment Health Check", show_header=True, header_style="title")
    table.add_column("Check", style="key", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Detail", style="value")
    for result in results:
        table.add_row(result.name, result.status, result.detail)
    console.print(table)

    passed = sum(1 for r in results if r.passed)
    total = len(results)
    if passed == total:
        console.print(
            Panel(
                f"[bold green]✓ All {total} checks passed[/bold green]",
                border_style="success",
                expand=False,
            )
        )
    else:
        console.print(
            Panel(
                f"[bold red]✗ {total - passed} of {total} checks failed[/bold red]",
                border_style="error",
                expand=False,
            )
        )
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_python() -> CheckResult:
    """Verify the Python version meets the minimum."""
    current = sys.version_info
    if current[:2] >= MIN_PYTHON:
        return CheckResult(
            "Python version",
            _OK,
            f"{current.major}.{current.minor}.{current.micro} (>= {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
        )
    return CheckResult(
        "Python version",
        _FAIL,
        f"{current.major}.{current.minor}.{current.micro} (< {MIN_PYTHON[0]}.{MIN_PYTHON[1]})",
    )


def _check_git() -> CheckResult:
    """Verify ``git`` is installed and callable."""
    git_path = shutil.which("git")
    if not git_path:
        return CheckResult("Git", _FAIL, "git not found on PATH")
    try:
        proc = subprocess.run(
            [git_path, "--version"],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return CheckResult("Git", _FAIL, f"git invocation failed: {exc}")
    if proc.returncode != 0:
        return CheckResult("Git", _FAIL, f"git --version exited {proc.returncode}")
    version_line = (proc.stdout or proc.stderr).strip().splitlines()[0]
    return CheckResult("Git", _OK, f"{version_line} ({git_path})")


def _check_sqlite() -> CheckResult:
    """Verify the ``sqlite3`` module works and report its version."""
    try:
        version = sqlite3.sqlite_version
    except AttributeError:
        return CheckResult("SQLite", _FAIL, "sqlite3 module has no sqlite_version")
    # Try opening an in-memory database.
    try:
        with sqlite3.connect(":memory:") as conn:
            conn.execute("CREATE TABLE _ra_doctor (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO _ra_doctor (id) VALUES (1)")
            row = conn.execute("SELECT COUNT(*) FROM _ra_doctor").fetchone()
            assert row is not None
            assert row[0] == 1
    except sqlite3.Error as exc:
        return CheckResult("SQLite", _FAIL, f"sqlite test failed: {exc}")
    return CheckResult("SQLite", _OK, f"SQLite {version} (read/write OK)")


def _check_working_directory() -> CheckResult:
    """Verify the current working directory is writable."""
    cwd = Path.cwd()
    try:
        test_file = cwd / f".ra_doctor_{os.getpid()}.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        return CheckResult("Working directory", _FAIL, f"{cwd} not writable: {exc}")
    return CheckResult("Working directory", _OK, f"{cwd} (writable)")


def _check_temp_directory() -> CheckResult:
    """Verify the system temp directory is writable."""
    try:
        with tempfile.NamedTemporaryFile(prefix="ra_doctor_", delete=True) as tmp:
            tmp.write(b"ok")
            tmp.flush()
    except OSError as exc:
        return CheckResult("Temp directory", _FAIL, f"{tempfile.gettempdir()} not writable: {exc}")
    return CheckResult("Temp directory", _OK, f"{tempfile.gettempdir()} (writable)")


def _check_config_file() -> CheckResult:
    """Verify the config file (if present) is readable."""
    path = get_default_config_path()
    if not path.exists():
        return CheckResult(
            "Config file",
            _SKIP,
            f"no config at {path} (using defaults)",
        )
    try:
        path.read_text(encoding="utf-8")
    except OSError as exc:
        return CheckResult("Config file", _FAIL, f"{path} not readable: {exc}")
    size = bytes_to_human(path.stat().st_size)
    return CheckResult("Config file", _OK, f"{path} ({size})")


def _check_environment_variables() -> CheckResult:
    """Report on relevant ``GRA_*`` environment variables."""
    relevant = sorted(k for k in os.environ if k.startswith("GRA_"))
    if not relevant:
        return CheckResult(
            "Environment variables",
            _SKIP,
            "no GRA_* variables set",
        )
    return CheckResult(
        "Environment variables",
        _OK,
        ", ".join(relevant),
    )


def _check_cache_directory(config: Config) -> CheckResult:
    """Verify the cache directory is usable."""
    cache_dir = Path(config.cache.dir)
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        test_file = cache_dir / f".ra_doctor_{os.getpid()}.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
    except OSError as exc:
        return CheckResult("Cache directory", _FAIL, f"{cache_dir} not writable: {exc}")
    return CheckResult("Cache directory", _OK, f"{cache_dir} (writable)")


__all__ = ["CheckResult", "run_doctor"]
