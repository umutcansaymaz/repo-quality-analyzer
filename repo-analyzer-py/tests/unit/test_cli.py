"""End-to-end CLI tests using Typer's ``CliRunner``."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from repo_analyzer.cli.app import app


@pytest.fixture()
def runner() -> CliRunner:
    """A CliRunner that does not mix stdout/stderr."""
    return CliRunner(mix_stderr=False)


@pytest.fixture()
def env_isolated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """Isolate cache + config + log dirs to ``tmp_path``."""
    cache = tmp_path / "cache"
    cache.mkdir()
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("GRA_CACHE_DIR", str(cache))
    monkeypatch.setenv("GRA_LOGGING_FILE", str(log_dir / "ra.log"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


class TestVersionCommand:
    def test_version_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0

    def test_version_prints_banner(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["version"])
        assert "repo-analyzer" in result.output.lower() or "Repo Analyzer" in result.output

    def test_version_shows_version_number(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["version"])
        assert "0.1.0" in result.output


class TestDoctorCommand:
    def test_doctor_exits_zero(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0

    def test_doctor_renders_table(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Environment Health Check" in result.output

    def test_doctor_checks_python(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Python version" in result.output

    def test_doctor_checks_git(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "Git" in result.output

    def test_doctor_checks_sqlite(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor"])
        assert "SQLite" in result.output


class TestAnalyzeCommand:
    @pytest.mark.network
    def test_analyze_valid_url(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["analyze", "https://github.com/octocat/Hello-World"])
        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "initialized" in result.output.lower()

    @pytest.mark.network
    def test_analyze_prints_repository_info(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["analyze", "https://github.com/octocat/Hello-World"])
        assert "octocat/Hello-World" in result.output

    def test_analyze_invalid_url_exits_nonzero(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["analyze", "not-a-valid-url"])
        assert result.exit_code != 0


class TestCacheCommands:
    def test_cache_list_empty(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["cache", "list"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_cache_clear_empty(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["cache", "clear"])
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "already empty" in result.output.lower()

    def test_cache_clear_after_list(self, runner: CliRunner, env_isolated: Path) -> None:
        # List then clear — both should succeed.
        runner.invoke(app, ["cache", "list"])
        result = runner.invoke(app, ["cache", "clear"])
        assert result.exit_code == 0


class TestConfigCommand:
    def test_config_exits_zero(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0

    def test_config_shows_resolved_config(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["config"])
        assert "Resolved Configuration" in result.output
        assert "log_level" in result.output


class TestUpdateCommand:
    def test_update_exits_zero(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 0

    def test_update_shows_version(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["update"])
        assert "0.1.0" in result.output

    def test_update_mentions_manual_upgrade(self, runner: CliRunner) -> None:
        result = runner.invoke(app, ["update"])
        assert "upgrade" in result.output.lower()


class TestGlobalFlags:
    def test_verbose_flag_on_doctor(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor", "--verbose"])
        assert result.exit_code == 0

    def test_debug_flag_on_doctor(self, runner: CliRunner, env_isolated: Path) -> None:
        result = runner.invoke(app, ["doctor", "--debug"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self, runner: CliRunner) -> None:
        result = runner.invoke(app, [])
        # Typer with no_args_is_help should exit 0 (or 2) and show usage.
        assert "Usage" in result.output or "usage" in result.output.lower()
