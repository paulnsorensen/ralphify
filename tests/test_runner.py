"""Tests for ralphify._runner — execute shell commands with timeout."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from helpers import MOCK_RUNNER_SUBPROCESS, fail_result, ok_result
from ralphify._runner import run_command


class TestRunCommand:
    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_success_with_command(self, mock_run):
        mock_run.return_value = ok_result(stdout="ok\n")
        result = run_command(command="echo hello", cwd=Path("/project"), timeout=60)

        assert result.success is True
        assert result.returncode == 0
        assert "ok" in result.output
        assert result.timed_out is False
        mock_run.assert_called_once()
        assert mock_run.call_args.args[0] == ["echo", "hello"]

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_failure_with_command(self, mock_run):
        mock_run.return_value = fail_result(stderr="error\n")
        result = run_command(command="ruff check", cwd=Path("/project"), timeout=60)

        assert result.success is False
        assert result.returncode == 1
        assert "error" in result.output

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_shlex_splits_command(self, mock_run):
        mock_run.return_value = ok_result()
        run_command(command="ruff check --fix .", cwd=Path("/project"), timeout=60)

        assert mock_run.call_args.args[0] == ["ruff", "check", "--fix", "."]

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_passes_cwd(self, mock_run):
        mock_run.return_value = ok_result()
        run_command(command="echo", cwd=Path("/my/project"), timeout=60)

        assert mock_run.call_args.kwargs["cwd"] == Path("/my/project")

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_passes_timeout(self, mock_run):
        mock_run.return_value = ok_result()
        run_command(command="echo", cwd=Path("/project"), timeout=120)

        assert mock_run.call_args.kwargs["timeout"] == 120

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_timeout_expired(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=60)
        result = run_command(command="echo", cwd=Path("/project"), timeout=60)

        assert result.success is False
        assert result.returncode is None
        assert result.timed_out is True

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_combines_stdout_and_stderr(self, mock_run):
        mock_run.return_value = ok_result(stdout="out\n", stderr="err\n")
        result = run_command(command="echo", cwd=Path("/project"), timeout=60)

        assert "out" in result.output
        assert "err" in result.output

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_env_merged_with_parent(self, mock_run):
        mock_run.return_value = ok_result()
        run_command(command="echo", cwd=Path("/project"), timeout=60, env={"RALPH_NAME": "docs"})

        passed_env = mock_run.call_args.kwargs["env"]
        assert passed_env["RALPH_NAME"] == "docs"
        # Parent env vars (like PATH) should be preserved
        assert "PATH" in passed_env

    @patch(MOCK_RUNNER_SUBPROCESS)
    def test_env_none_inherits_parent(self, mock_run):
        mock_run.return_value = ok_result()
        run_command(command="echo", cwd=Path("/project"), timeout=60, env=None)

        # env=None means subprocess.run inherits parent env
        assert mock_run.call_args.kwargs["env"] is None

    def test_raises_when_command_is_whitespace_only(self):
        with pytest.raises(ValueError, match="no tokens after parsing"):
            run_command(command="   ", cwd=Path("/project"), timeout=60)
