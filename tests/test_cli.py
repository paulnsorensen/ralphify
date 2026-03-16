import subprocess
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ralphify import __version__
from ralphify.checks import Check, CheckResult
from ralphify.contexts import Context, ContextResult
from ralphify.cli import app, CONFIG_FILENAME
from ralphify._templates import RALPH_TOML_TEMPLATE, ROOT_RALPH_TEMPLATE

runner = CliRunner()


def _ok(*args, **kwargs):
    return subprocess.CompletedProcess(args=args, returncode=0)


def _fail(*args, **kwargs):
    return subprocess.CompletedProcess(args=args, returncode=1)


class TestVersion:
    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert f"ralphify {__version__}" in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert f"ralphify {__version__}" in result.output


class TestInit:
    def test_creates_config_and_ralph(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / CONFIG_FILENAME).exists()
        assert (tmp_path / "RALPH.md").exists()
        assert (tmp_path / CONFIG_FILENAME).read_text() == RALPH_TOML_TEMPLATE
        assert (tmp_path / "RALPH.md").read_text() == ROOT_RALPH_TEMPLATE

    def test_refuses_overwrite_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text("existing")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 1
        assert (tmp_path / CONFIG_FILENAME).read_text() == "existing"

    def test_force_overwrites(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text("old")
        (tmp_path / "RALPH.md").write_text("my custom prompt")
        result = runner.invoke(app, ["init", "--force"])
        assert result.exit_code == 0
        assert (tmp_path / CONFIG_FILENAME).read_text() == RALPH_TOML_TEMPLATE
        assert (tmp_path / "RALPH.md").read_text() == "my custom prompt"

    def test_skips_ralph_if_exists_without_force(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "RALPH.md").write_text("my custom prompt")
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "RALPH.md").read_text() == "my custom prompt"


class TestRun:
    def test_errors_without_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_errors_with_missing_prompt(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("ralphify.cli.shutil.which", return_value=None)
    def test_errors_when_command_not_on_path(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 1
        assert "not found on PATH" in result.output

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_runs_when_command_on_path(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_count == 1

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_runs_n_iterations(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("test prompt")

        result = runner.invoke(app, ["run", "-n", "3"])
        assert result.exit_code == 0
        assert mock_run.call_count == 3
        for call in mock_run.call_args_list:
            assert call.kwargs["input"] == "test prompt"
            assert call.kwargs["text"] is True

    @patch("ralphify._agent.subprocess.run")
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_reads_prompt_each_iteration(self, mock_which, mock_run, tmp_path, monkeypatch):
        """Prompt file is re-read each iteration so edits take effect."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        prompt_path = tmp_path / "RALPH.md"
        prompt_path.write_text("v1")

        call_count = 0

        def update_prompt(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                prompt_path.write_text("v2")
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = update_prompt

        result = runner.invoke(app, ["run", "-n", "2"])
        assert result.exit_code == 0
        assert mock_run.call_args_list[0].kwargs["input"] == "v1"
        assert mock_run.call_args_list[1].kwargs["input"] == "v2"

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/myagent")
    def test_custom_command_and_args(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = '[agent]\ncommand = "myagent"\nargs = ["--fast"]\nralph = "RALPH.md"\n'
        (tmp_path / CONFIG_FILENAME).write_text(config)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            ["myagent", "--fast"], input="go", text=True, timeout=None, capture_output=False
        )

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_shows_success_per_iteration(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "2"])
        assert result.exit_code == 0
        assert "Iteration 1 completed" in result.output
        assert "Iteration 2 completed" in result.output
        assert "2 succeeded" in result.output

    @patch("ralphify._agent.subprocess.run", side_effect=_fail)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_continues_on_error_by_default(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "3"])
        assert result.exit_code == 0
        assert mock_run.call_count == 3
        assert "3 failed" in result.output

    @patch("ralphify._agent.subprocess.run", side_effect=_fail)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_stop_on_error(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "5", "--stop-on-error"])
        assert result.exit_code == 0
        assert mock_run.call_count == 1
        assert "Stopping due to --stop-on-error" in result.output
        assert "1 failed" in result.output

    @patch("ralphify._agent.subprocess.run")
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_mixed_success_and_failure(self, mock_which, mock_run, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=1),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]

        result = runner.invoke(app, ["run", "-n", "3"])
        assert result.exit_code == 0
        assert "2 succeeded" in result.output
        assert "1 failed" in result.output

    @patch("ralphify.engine.time.sleep")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_delay_between_iterations(self, mock_which, mock_run, mock_sleep, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "3", "--delay", "5"])
        assert result.exit_code == 0
        # Delay between iterations, not after the last one
        assert mock_sleep.call_count == 2
        for call in mock_sleep.call_args_list:
            assert call.args[0] == 5

    @patch("ralphify.engine.time.sleep")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    @patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
    def test_no_delay_with_single_iteration(self, mock_which, mock_run, mock_sleep, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1", "--delay", "5"])
        assert result.exit_code == 0
        mock_sleep.assert_not_called()


class TestRunRejectsInlinePrompt:
    def test_unknown_name_errors(self, tmp_path, monkeypatch):
        """A value that doesn't match a named ralph produces an error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        result = runner.invoke(app, ["run", "do something", "-n", "1"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()


@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunCheckScriptValidation:
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_errors_when_check_script_not_executable(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [my-check]\n---\ngo")

        check_dir = tmp_path / ".ralphify" / "checks" / "my-check"
        check_dir.mkdir(parents=True)
        (check_dir / "CHECK.md").write_text("---\nenabled: true\n---\nFix it.")
        script = check_dir / "run.sh"
        script.write_text("#!/bin/bash\necho ok")
        script.chmod(0o644)  # not executable

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0  # engine catches the error
        assert "not executable" in result.output

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_runs_when_check_script_is_executable(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [my-check]\n---\ngo")

        check_dir = tmp_path / ".ralphify" / "checks" / "my-check"
        check_dir.mkdir(parents=True)
        (check_dir / "CHECK.md").write_text("---\nenabled: true\n---\nFix it.")
        script = check_dir / "run.sh"
        script.write_text("#!/bin/bash\necho ok")
        script.chmod(0o755)  # executable

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert "not executable" not in result.output


@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunLogging:
    @patch("ralphify._agent.subprocess.run")
    def test_creates_log_files(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "logs"

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="agent output\n", stderr=""
        )

        result = runner.invoke(app, ["run", "-n", "2", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        log_files = sorted(log_dir.iterdir())
        assert len(log_files) == 2
        assert log_files[0].name.startswith("001_")
        assert log_files[1].name.startswith("002_")

    @patch("ralphify._agent.subprocess.run")
    def test_log_file_contains_output(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "logs"

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="hello from agent\n", stderr="warning\n"
        )

        result = runner.invoke(app, ["run", "-n", "1", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        log_files = list(log_dir.iterdir())
        content = log_files[0].read_text()
        assert "hello from agent" in content
        assert "warning" in content

    @patch("ralphify._agent.subprocess.run")
    def test_log_dir_created_automatically(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "nested" / "log" / "dir"

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="out\n", stderr=""
        )

        result = runner.invoke(app, ["run", "-n", "1", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        assert log_dir.exists()
        assert len(list(log_dir.iterdir())) == 1

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_no_log_files_without_flag(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        # No .ralphify or logs directory should be created
        assert not (tmp_path / ".ralphify").exists()
        assert not (tmp_path / "logs").exists()

    @patch("ralphify._agent.subprocess.run")
    def test_log_shows_path_in_status(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "logs"

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="out\n", stderr=""
        )

        result = runner.invoke(app, ["run", "-n", "1", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        assert "001_" in result.output
        assert ".log" in result.output

    @patch("ralphify._agent.subprocess.run")
    def test_log_uses_capture_output(self, mock_run, mock_which, tmp_path, monkeypatch):
        """When logging, subprocess.run is called with capture_output=True."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "logs"

        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )

        runner.invoke(app, ["run", "-n", "1", "--log-dir", str(log_dir)])
        assert mock_run.call_args.kwargs["capture_output"] is True


@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunTimeout:
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_timeout_passed_to_subprocess(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1", "--timeout", "30"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["timeout"] == 30

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_no_timeout_by_default(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["timeout"] is None

    @patch("ralphify._agent.subprocess.run")
    def test_timeout_counts_as_failure(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)

        result = runner.invoke(app, ["run", "-n", "1", "--timeout", "10"])
        assert result.exit_code == 0
        assert "timed out" in result.output
        assert "1 failed" in result.output
        assert "1 timed out" in result.output

    @patch("ralphify._agent.subprocess.run")
    def test_timeout_continues_by_default(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        mock_run.side_effect = [
            subprocess.TimeoutExpired(cmd="claude", timeout=10),
            subprocess.CompletedProcess(args=[], returncode=0),
        ]

        result = runner.invoke(app, ["run", "-n", "2", "--timeout", "10"])
        assert result.exit_code == 0
        assert mock_run.call_count == 2
        assert "1 succeeded" in result.output
        assert "1 failed" in result.output

    @patch("ralphify._agent.subprocess.run")
    def test_timeout_stops_with_stop_on_error(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        mock_run.side_effect = subprocess.TimeoutExpired(cmd="claude", timeout=10)

        result = runner.invoke(app, ["run", "-n", "3", "--timeout", "10", "--stop-on-error"])
        assert result.exit_code == 0
        assert mock_run.call_count == 1
        assert "Stopping due to --stop-on-error" in result.output

    @patch("ralphify._agent.subprocess.run")
    def test_timeout_with_logging(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")
        log_dir = tmp_path / "logs"

        exc = subprocess.TimeoutExpired(cmd="claude", timeout=10)
        exc.stdout = b"partial output\n"
        exc.stderr = b""
        mock_run.side_effect = exc

        result = runner.invoke(app, ["run", "-n", "1", "--timeout", "10", "--log-dir", str(log_dir)])
        assert result.exit_code == 0
        log_files = list(log_dir.iterdir())
        assert len(log_files) == 1
        content = log_files[0].read_text()
        assert "partial output" in content

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_timeout_shows_in_header(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("go")

        result = runner.invoke(app, ["run", "-n", "1", "--timeout", "300"])
        assert result.exit_code == 0
        assert "5m 0s per iteration" in result.output


def _setup_check(tmp_path, name="ruff-lint", command="ruff check .", enabled=True,
                 body="Fix lint errors."):
    """Helper to create a check directory with CHECK.md."""
    check_dir = tmp_path / ".ralphify" / "checks" / name
    check_dir.mkdir(parents=True, exist_ok=True)
    enabled_str = "true" if enabled else "false"
    (check_dir / "CHECK.md").write_text(
        f"---\ncommand: {command}\nenabled: {enabled_str}\n---\n{body}"
    )
    return check_dir


def _make_check_result(name="lint", passed=True, exit_code=0, output="ok\n",
                       timed_out=False, failure_instruction=""):
    """Helper to create a CheckResult for tests."""
    check = Check(
        name=name,
        path=Path("/fake"),
        command="echo",
        script=None,
        failure_instruction=failure_instruction,
    )
    return CheckResult(
        check=check,
        passed=passed,
        exit_code=exit_code,
        output=output,
        timed_out=timed_out,
    )


@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunChecks:
    @patch("ralphify.engine.run_all_checks")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_checks_run_after_iteration(self, mock_agent, mock_run_checks, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [lint]\n---\ntest prompt")
        _setup_check(tmp_path, "lint", "ruff check .")

        mock_run_checks.return_value = [_make_check_result()]

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run_checks.call_count == 1
        assert "1 passed" in result.output

    @patch("ralphify.engine.run_all_checks")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_failure_text_appended_to_next_prompt(self, mock_agent, mock_run_checks, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [lint]\n---\nbase prompt")
        _setup_check(tmp_path, "lint", "ruff check .", body="Fix lint errors.")

        mock_run_checks.return_value = [
            _make_check_result(
                passed=False, exit_code=1, output="error: bad code\n",
                failure_instruction="Fix lint errors.",
            )
        ]

        result = runner.invoke(app, ["run", "-n", "2"])
        assert result.exit_code == 0

        # First iteration gets base prompt only
        first_call_input = mock_agent.call_args_list[0].kwargs["input"]
        assert first_call_input == "base prompt"

        # Second iteration gets check failure appended
        second_call_input = mock_agent.call_args_list[1].kwargs["input"]
        assert "base prompt" in second_call_input
        assert "Check Failures" in second_call_input
        assert "bad code" in second_call_input
        assert "Fix lint errors." in second_call_input

    @patch("ralphify.engine.run_all_checks")
    @patch("ralphify._agent.subprocess.run", side_effect=_fail)
    def test_checks_run_even_when_agent_fails(self, mock_agent, mock_run_checks, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [lint]\n---\nprompt")
        _setup_check(tmp_path, "lint", "ruff check .")

        mock_run_checks.return_value = [_make_check_result()]

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run_checks.call_count == 1

    @patch("ralphify.engine.run_all_checks")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_check_failure_does_not_trigger_stop_on_error(self, mock_agent, mock_run_checks, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [lint]\n---\nprompt")
        _setup_check(tmp_path, "lint", "ruff check .")

        mock_run_checks.return_value = [
            _make_check_result(passed=False, exit_code=1, output="fail\n")
        ]

        # Agent succeeds, but check fails — should NOT stop
        result = runner.invoke(app, ["run", "-n", "2", "--stop-on-error"])
        assert result.exit_code == 0
        # Both iterations should run (agent didn't fail)
        assert mock_agent.call_count == 2

    @patch("ralphify.engine.run_all_checks")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_disabled_checks_not_run(self, mock_agent, mock_run_checks, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\nchecks: [enabled, disabled]\n---\nprompt")
        _setup_check(tmp_path, "enabled", "echo ok", enabled=True)
        _setup_check(tmp_path, "disabled", "echo skip", enabled=False)

        mock_run_checks.return_value = [_make_check_result()]

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        # run_all_checks is called with only enabled checks
        checks_arg = mock_run_checks.call_args.args[0]
        assert len(checks_arg) == 1
        assert checks_arg[0].name == "enabled"


class TestNew:
    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_installs_skill_and_launches_agent(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        result = runner.invoke(app, ["new", "my-task"])
        assert result.exit_code == 0
        skill_file = tmp_path / ".claude" / "skills" / "new-ralph" / "SKILL.md"
        assert skill_file.exists()
        assert "new-ralph" in skill_file.read_text()
        mock_execvp.assert_called_once_with("claude", ["claude", "/new-ralph my-task"])

    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_name_is_optional(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        result = runner.invoke(app, ["new"])
        assert result.exit_code == 0
        mock_execvp.assert_called_once_with("claude", ["claude", "/new-ralph"])

    @patch("shutil.which", return_value=None)
    def test_errors_when_no_agent_found(self, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["new"])
        assert result.exit_code == 1
        assert "No agent found" in result.output

    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_auto_detects_agent_without_config(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # No ralph.toml — should fall back to PATH detection

        result = runner.invoke(app, ["new", "my-task"])
        assert result.exit_code == 0
        mock_execvp.assert_called_once()

    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/codex")
    def test_codex_skill_installation(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = '[agent]\ncommand = "codex"\nargs = []\nralph = "RALPH.md"\n'
        (tmp_path / CONFIG_FILENAME).write_text(config)

        result = runner.invoke(app, ["new", "my-task"])
        assert result.exit_code == 0
        skill_file = tmp_path / ".agents" / "skills" / "new-ralph" / "SKILL.md"
        assert skill_file.exists()
        mock_execvp.assert_called_once_with("codex", ["codex", "$new-ralph my-task"])

    @patch("ralphify.cli.os.execvp")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_overwrites_existing_skill(self, mock_which, mock_execvp, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        # Pre-existing skill file with old content
        skill_dir = tmp_path / ".claude" / "skills" / "new-ralph"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("old content")

        result = runner.invoke(app, ["new", "my-task"])
        assert result.exit_code == 0
        assert (skill_dir / "SKILL.md").read_text() != "old content"




def _setup_context(tmp_path, name="git-history", command="git log --oneline -5",
                   enabled=True, body=""):
    """Helper to create a context directory with CONTEXT.md."""
    ctx_dir = tmp_path / ".ralphify" / "contexts" / name
    ctx_dir.mkdir(parents=True, exist_ok=True)
    enabled_str = "true" if enabled else "false"
    parts = [f"---\nenabled: {enabled_str}"]
    if command:
        parts[0] = f"---\ncommand: {command}\nenabled: {enabled_str}"
    parts.append(f"---\n{body}")
    (ctx_dir / "CONTEXT.md").write_text("\n".join(parts))
    return ctx_dir




@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunContexts:
    @patch("ralphify.engine.run_all_contexts")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_contexts_injected_into_prompt(self, mock_agent, mock_run_contexts, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\ncontexts: [git-log]\n---\nBase.\n\n{{ contexts.git-log }}")
        _setup_context(tmp_path, "git-log", "git log --oneline -5")

        ctx = Context(name="git-log", path=Path("/fake"), command="git log", enabled=True)
        mock_run_contexts.return_value = [
            ContextResult(context=ctx, output="abc123 fix bug\n", success=True)
        ]

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        prompt_sent = mock_agent.call_args.kwargs["input"]
        assert "abc123 fix bug" in prompt_sent
        assert "{{ contexts.git-log }}" not in prompt_sent

    @patch("ralphify.engine.run_all_contexts")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_disabled_contexts_not_run(self, mock_agent, mock_run_contexts, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\ncontexts: [enabled, disabled]\n---\nprompt")
        _setup_context(tmp_path, "enabled", "echo ok", enabled=True)
        _setup_context(tmp_path, "disabled", "echo skip", enabled=False)

        ctx = Context(name="enabled", path=Path("/fake"), command="echo ok", enabled=True)
        mock_run_contexts.return_value = [
            ContextResult(context=ctx, output="ok\n", success=True)
        ]

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        # run_all_contexts called with only enabled contexts
        contexts_arg = mock_run_contexts.call_args.args[0]
        assert len(contexts_arg) == 1
        assert contexts_arg[0].name == "enabled"

    @patch("ralphify.engine.run_all_contexts")
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_contexts_run_each_iteration(self, mock_agent, mock_run_contexts, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("---\ncontexts: [info]\n---\n{{ contexts.info }}")
        _setup_context(tmp_path, "info", "echo hi")

        ctx = Context(name="info", path=Path("/fake"), command="echo hi", enabled=True)
        mock_run_contexts.return_value = [
            ContextResult(context=ctx, output="hi\n", success=True)
        ]

        result = runner.invoke(app, ["run", "-n", "3"])
        assert result.exit_code == 0
        assert mock_run_contexts.call_count == 3


def _setup_ralph(tmp_path, name="improve-docs", description="Improve docs", enabled=True, content="Fix the docs."):
    """Helper to create a ralph directory with RALPH.md."""
    p_dir = tmp_path / ".ralphify" / "ralphs" / name
    p_dir.mkdir(parents=True, exist_ok=True)
    enabled_str = "true" if enabled else "false"
    (p_dir / "RALPH.md").write_text(
        f"---\ndescription: {description}\nenabled: {enabled_str}\n---\n{content}"
    )
    return p_dir





@patch("ralphify.cli.shutil.which", return_value="/usr/bin/claude")
class TestRunRalphName:
    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_run_with_ralph_name(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        _setup_ralph(tmp_path, "improve-docs", content="Fix the docs.")

        result = runner.invoke(app, ["run", "improve-docs", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "Fix the docs."

    def test_nonexistent_name_errors(self, mock_which, tmp_path, monkeypatch):
        """A value that doesn't match a named ralph produces an error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        result = runner.invoke(app, ["run", "nonexistent", "-n", "1"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_run_without_name_falls_back_to_toml(self, mock_run, mock_which, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)
        (tmp_path / "RALPH.md").write_text("default prompt")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "default prompt"

    @patch("ralphify._agent.subprocess.run", side_effect=_ok)
    def test_toml_ralph_as_name(self, mock_run, mock_which, tmp_path, monkeypatch):
        """When ralph.toml agent.ralph is a ralph name, resolve it."""
        monkeypatch.chdir(tmp_path)
        config = '[agent]\ncommand = "claude"\nargs = ["-p"]\nralph = "improve-docs"\n'
        (tmp_path / CONFIG_FILENAME).write_text(config)
        _setup_ralph(tmp_path, "improve-docs", content="Fix the docs.")

        result = runner.invoke(app, ["run", "-n", "1"])
        assert result.exit_code == 0
        assert mock_run.call_args.kwargs["input"] == "Fix the docs."

    def test_inline_text_rejected(self, mock_which, tmp_path, monkeypatch):
        """Inline text that isn't a ralph name produces an error."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / CONFIG_FILENAME).write_text(RALPH_TOML_TEMPLATE)

        result = runner.invoke(app, ["run", "inline text", "-n", "1"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()
