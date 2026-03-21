"""Tests for the v2 CLI."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from helpers import MOCK_ENGINE_SLEEP, MOCK_SUBPROCESS, MOCK_WHICH, ok_result, fail_result
from ralphify import __version__
from ralphify.cli import app, _parse_commands, _parse_user_args

runner = CliRunner()


def _make_ralph(tmp_path, prompt="go", agent="claude -p --dangerously-skip-permissions",
                commands=None, args=None):
    """Create a ralph directory with RALPH.md for tests."""
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    fm_lines = [f"agent: {agent}"]
    if commands:
        fm_lines.append("commands:")
        for cmd in commands:
            fm_lines.append(f"  - name: {cmd['name']}")
            fm_lines.append(f"    run: {cmd['run']}")
    if args:
        fm_lines.append("args:")
        for a in args:
            fm_lines.append(f"  - {a}")
    fm = "\n".join(fm_lines)
    (ralph_dir / "RALPH.md").write_text(f"---\n{fm}\n---\n{prompt}")
    return ralph_dir


class TestVersion:
    @pytest.mark.parametrize("flag", ["--version", "-V"])
    def test_version_flag(self, flag):
        result = runner.invoke(app, [flag])
        assert result.exit_code == 0
        assert f"ralphify {__version__}" in result.output


@patch(MOCK_WHICH, return_value="/usr/bin/claude")
class TestRun:
    def test_errors_with_nonexistent_path(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run", "nonexistent"])
        assert result.exit_code == 1
        assert "not" in result.output.lower()

    def test_errors_without_ralph_md(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        result = runner.invoke(app, ["run", str(empty_dir)])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_errors_without_agent_field(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir()
        (ralph_dir / "RALPH.md").write_text("just a prompt, no frontmatter")
        result = runner.invoke(app, ["run", str(ralph_dir)])
        assert result.exit_code == 1
        assert "agent" in result.output.lower()

    def test_errors_when_agent_not_on_path(self, mock_which, tmp_path, monkeypatch):
        mock_which.return_value = None
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 1
        assert "not found on PATH" in result.output

    @pytest.mark.parametrize("frontmatter, expected_error", [
        ("commands:\n  - name: \"\"\n    run: echo hi", "name"),
        ("commands:\n  - name: status\n    run: \"\"", "run"),
        ("commands: not-a-list", "must be a list"),
        (
            "commands:\n  - name: status\n    run: git status\n"
            "  - name: status\n    run: echo hi",
            "duplicate",
        ),
    ], ids=["empty-name", "empty-run", "not-a-list", "duplicate-names"])
    def test_errors_with_invalid_commands(self, mock_which, tmp_path, monkeypatch,
                                          frontmatter, expected_error):
        monkeypatch.chdir(tmp_path)
        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir()
        (ralph_dir / "RALPH.md").write_text(
            f"---\nagent: claude -p\n{frontmatter}\n---\ngo"
        )
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 1
        assert expected_error in result.output.lower()

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_runs_when_valid(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_count == 1

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_runs_n_iterations(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path, prompt="test prompt")
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "3"])
        assert result.exit_code == 0
        assert mock_run.call_count == 3
        for call in mock_run.call_args_list:
            assert call.kwargs["input"] == "test prompt"

    @patch(MOCK_SUBPROCESS)
    def test_reads_prompt_each_iteration(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path, prompt="v1")
        ralph_file = ralph_dir / "RALPH.md"

        call_count = 0

        def update_prompt(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Rewrite with same frontmatter but different body
                ralph_file.write_text(
                    "---\nagent: claude -p --dangerously-skip-permissions\n---\nv2"
                )
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = update_prompt

        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "2"])
        assert result.exit_code == 0
        assert mock_run.call_args_list[0].kwargs["input"] == "v1"
        assert mock_run.call_args_list[1].kwargs["input"] == "v2"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_shows_success_per_iteration(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "2"])
        assert result.exit_code == 0
        assert "Iteration 1 completed" in result.output
        assert "Iteration 2 completed" in result.output
        assert "2 succeeded" in result.output

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_continues_on_error_by_default(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "3"])
        assert result.exit_code == 0
        assert mock_run.call_count == 3
        assert "3 failed" in result.output

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_stop_on_error(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "5", "--stop-on-error"])
        assert result.exit_code == 0
        assert mock_run.call_count == 1
        assert "Stopping due to --stop-on-error" in result.output
        assert "1 failed" in result.output

    @patch(MOCK_SUBPROCESS)
    def test_mixed_success_and_failure(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        mock_run.side_effect = [ok_result(), fail_result(), ok_result()]
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "3"])
        assert result.exit_code == 0
        assert "2 succeeded" in result.output
        assert "1 failed" in result.output

    @patch(MOCK_ENGINE_SLEEP)
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_delay_between_iterations(self, mock_run, mock_sleep, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "3", "--delay", "5"])
        assert result.exit_code == 0
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 5

    @patch(MOCK_ENGINE_SLEEP)
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_no_delay_with_single_iteration(self, mock_run, mock_sleep, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--delay", "5"])
        assert result.exit_code == 0
        mock_sleep.assert_not_called()

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_accepts_ralph_md_file_path(self, mock_run, mock_which, tmp_path, monkeypatch):
        """Can pass path to RALPH.md file directly."""
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir / "RALPH.md"), "-n", "1"])
        assert result.exit_code == 0


@patch(MOCK_WHICH, return_value="/usr/bin/claude")
class TestRunLogging:
    @patch(MOCK_SUBPROCESS)
    def test_creates_log_files(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        log_dir = tmp_path / "logs"
        mock_run.return_value = ok_result(stdout="agent output\n")
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "2", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        log_files = sorted(log_dir.iterdir())
        assert len(log_files) == 2
        assert log_files[0].name.startswith("001_")
        assert log_files[1].name.startswith("002_")

    @patch(MOCK_SUBPROCESS)
    def test_log_file_contains_output(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        log_dir = tmp_path / "logs"
        mock_run.return_value = ok_result(stdout="hello from agent\n", stderr="warning\n")
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        log_files = list(log_dir.iterdir())
        content = log_files[0].read_text()
        assert "hello from agent" in content
        assert "warning" in content

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_no_log_files_without_flag(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 0
        assert not (tmp_path / "logs").exists()


@patch(MOCK_WHICH, return_value="/usr/bin/claude")
class TestRunTimeout:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_timeout_passed_to_subprocess(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--timeout", "30"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["timeout"] == 30

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_no_timeout_by_default(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["timeout"] is None

    @patch(MOCK_SUBPROCESS)
    def test_timeout_counts_as_failure(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--timeout", "10"])
        assert result.exit_code == 0
        assert "timed out" in result.output
        assert "1 failed" in result.output
        assert "1 timed out" in result.output

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_timeout_shows_in_header(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path)
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--timeout", "300"])
        assert result.exit_code == 0
        assert "5m 0s per iteration" in result.output


class TestNew:
    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_installs_skill_and_launches_agent(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new", "my-task"])
        assert result.exit_code == 0
        skill_file = tmp_path / ".claude" / "skills" / "new-ralph" / "SKILL.md"
        assert skill_file.exists()
        assert "new-ralph" in skill_file.read_text()
        mock_execvp.assert_called_once_with("claude", ["claude", "--dangerously-skip-permissions", "/new-ralph my-task"])

    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_name_is_optional(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new"])
        assert result.exit_code == 0
        mock_execvp.assert_called_once_with("claude", ["claude", "--dangerously-skip-permissions", "/new-ralph"])

    @patch("shutil.which", return_value=None)
    def test_errors_when_no_agent_found(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["new"])
        assert result.exit_code == 1
        assert "No agent found" in result.output


class TestParseUserArgs:
    def test_named_flag(self):
        result = _parse_user_args(["--dir", "./src"], None)
        assert result == {"dir": "./src"}

    def test_multiple_named_flags(self):
        result = _parse_user_args(["--dir", "./src", "--focus", "perf"], None)
        assert result == {"dir": "./src", "focus": "perf"}

    def test_positional_with_declared_names(self):
        result = _parse_user_args(["./src", "perf"], ["dir", "focus"])
        assert result == {"dir": "./src", "focus": "perf"}

    def test_mixed_positional_and_named(self):
        result = _parse_user_args(["./src", "--focus", "perf"], ["dir", "focus"])
        assert result == {"dir": "./src", "focus": "perf"}

    def test_positional_without_declaration_errors(self):
        with pytest.raises(typer.BadParameter, match="requires args declared"):
            _parse_user_args(["./src"], None)

    def test_too_many_positionals_errors(self):
        with pytest.raises(typer.BadParameter, match="Too many positional"):
            _parse_user_args(["./src", "extra"], ["dir"])

    def test_flag_without_value_errors(self):
        with pytest.raises(typer.BadParameter, match="requires a value"):
            _parse_user_args(["--dir"], None)

    def test_empty_args(self):
        result = _parse_user_args([], None)
        assert result == {}


@patch(MOCK_WHICH, return_value="/usr/bin/claude")
class TestRunWithUserArgs:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_named_args_resolved_in_prompt(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path, prompt="Research {{ args.dir }}")
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "--dir", "./my-project"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "Research ./my-project"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_positional_args_with_declared_names(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(
            tmp_path,
            prompt="Research {{ args.dir }} with focus on {{ args.focus }}",
            args=["dir", "focus"],
        )
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1", "./my-project", "performance"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "Research ./my-project with focus on performance"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_unused_arg_placeholders_cleared(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        ralph_dir = _make_ralph(tmp_path, prompt="Before {{ args.opt }} after")
        result = runner.invoke(app, ["run", str(ralph_dir), "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "Before  after"


class TestParseCommands:
    def test_valid_commands(self):
        raw = [
            {"name": "tests", "run": "uv run pytest"},
            {"name": "lint", "run": "ruff check"},
        ]
        commands = _parse_commands(raw)
        assert len(commands) == 2
        assert commands[0].name == "tests"
        assert commands[0].run == "uv run pytest"
        assert commands[1].name == "lint"

    def test_empty_list(self):
        assert _parse_commands([]) == []

    def test_custom_timeout(self):
        raw = [{"name": "slow", "run": "sleep 10", "timeout": 300}]
        commands = _parse_commands(raw)
        assert commands[0].timeout == 300

    def test_default_timeout(self):
        from ralphify._run_types import DEFAULT_COMMAND_TIMEOUT
        raw = [{"name": "fast", "run": "echo hi"}]
        commands = _parse_commands(raw)
        assert commands[0].timeout == DEFAULT_COMMAND_TIMEOUT

    def test_missing_name_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands([{"run": "echo hi"}])

    def test_missing_run_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands([{"name": "test"}])

    def test_empty_name_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands([{"name": "", "run": "echo hi"}])

    def test_empty_run_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands([{"name": "test", "run": ""}])

    def test_duplicate_names_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands([
                {"name": "test", "run": "echo 1"},
                {"name": "test", "run": "echo 2"},
            ])

    def test_non_dict_entry_errors(self):
        with pytest.raises(typer.Exit):
            _parse_commands(["not-a-dict"])
