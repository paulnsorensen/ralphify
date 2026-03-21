"""Tests for the _agent module — subprocess execution, log writing, and stream parsing."""

import io
import subprocess
import time
from pathlib import Path
from unittest.mock import patch

from conftest import MOCK_SUBPROCESS

from ralphify._agent import (
    AgentResult,
    _read_agent_stream,
    _supports_stream_json,
    _write_log,
    execute_agent,
)


class TestSupportsStreamJson:
    def test_claude_binary(self):
        assert _supports_stream_json(["claude", "-p"]) is True

    def test_claude_absolute_path(self):
        assert _supports_stream_json(["/usr/local/bin/claude", "-p"]) is True

    def test_non_claude_binary(self):
        assert _supports_stream_json(["aider", "--yes"]) is False

    def test_empty_command(self):
        assert _supports_stream_json([]) is False

    def test_claude_like_name(self):
        assert _supports_stream_json(["claude-code"]) is False


class TestWriteLog:
    def test_creates_log_file(self, tmp_path):
        log_file = _write_log(tmp_path, 1, "stdout output", "stderr output")

        assert log_file.exists()
        assert log_file.parent == tmp_path
        content = log_file.read_text()
        assert "stdout output" in content
        assert "stderr output" in content

    def test_log_filename_format(self, tmp_path):
        log_file = _write_log(tmp_path, 5, "out", "")

        assert log_file.name.startswith("005_")
        assert log_file.suffix == ".log"

    def test_none_outputs(self, tmp_path):
        log_file = _write_log(tmp_path, 1, None, None)

        assert log_file.exists()
        assert log_file.read_text() == ""

    def test_bytes_outputs(self, tmp_path):
        log_file = _write_log(tmp_path, 1, b"binary out\n", b"binary err\n")

        content = log_file.read_text()
        assert "binary out" in content
        assert "binary err" in content

    def test_iteration_zero_padding(self, tmp_path):
        log_file = _write_log(tmp_path, 42, "out", "")
        assert log_file.name.startswith("042_")


class TestReadAgentStream:
    def test_collects_all_lines(self):
        stream = io.StringIO("line1\nline2\nline3\n")
        result = _read_agent_stream(stream, deadline=None, on_activity=None)

        assert len(result.stdout_lines) == 3
        assert result.timed_out is False

    def test_parses_json_lines(self):
        activities = []
        stream = io.StringIO('{"type": "status", "msg": "ok"}\n')
        _read_agent_stream(stream, deadline=None, on_activity=activities.append)

        assert len(activities) == 1
        assert activities[0]["type"] == "status"

    def test_captures_result_text(self):
        stream = io.StringIO('{"type": "result", "result": "All done"}\n')
        result = _read_agent_stream(stream, deadline=None, on_activity=None)

        assert result.result_text == "All done"

    def test_ignores_non_json_lines(self):
        activities = []
        stream = io.StringIO("not json\n")
        result = _read_agent_stream(stream, deadline=None, on_activity=activities.append)

        assert len(result.stdout_lines) == 1
        assert len(activities) == 0

    def test_skips_empty_lines(self):
        activities = []
        stream = io.StringIO("\n\n")
        result = _read_agent_stream(stream, deadline=None, on_activity=activities.append)

        assert len(result.stdout_lines) == 2
        assert len(activities) == 0

    def test_timeout_returns_early(self):
        stream = io.StringIO("line1\nline2\n")
        # Deadline already in the past (must be > 0 since 0.0 is falsy)
        result = _read_agent_stream(stream, deadline=0.001, on_activity=None)

        assert result.timed_out is True

    def test_result_type_without_result_field_ignored(self):
        stream = io.StringIO('{"type": "result"}\n')
        result = _read_agent_stream(stream, deadline=None, on_activity=None)

        assert result.result_text is None

    def test_last_result_wins(self):
        stream = io.StringIO(
            '{"type": "result", "result": "first"}\n'
            '{"type": "result", "result": "second"}\n'
        )
        result = _read_agent_stream(stream, deadline=None, on_activity=None)

        assert result.result_text == "second"


class TestExecuteAgentBlocking:
    @patch(MOCK_SUBPROCESS)
    def test_success(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.log_file is None
        assert result.elapsed >= 0

    @patch(MOCK_SUBPROCESS)
    def test_failure(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr=""
        )
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.returncode == 1
        assert result.timed_out is False

    @patch(MOCK_SUBPROCESS)
    def test_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        result = execute_agent(["echo"], "prompt", timeout=5, log_path_dir=None, iteration=1)

        assert result.returncode is None
        assert result.timed_out is True

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_success(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="agent output\n", stderr=""
        )
        result = execute_agent(
            ["echo"], "prompt", timeout=None, log_path_dir=tmp_path, iteration=3,
        )

        assert result.log_file is not None
        assert result.log_file.exists()
        assert result.log_file.name.startswith("003_")
        assert "agent output" in result.log_file.read_text()

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_timeout(self, mock_run, tmp_path):
        exc = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        exc.stdout = "partial"
        exc.stderr = "err"
        mock_run.side_effect = exc
        result = execute_agent(
            ["echo"], "prompt", timeout=5, log_path_dir=tmp_path, iteration=1,
        )

        assert result.log_file is not None
        assert result.log_file.exists()

    @patch(MOCK_SUBPROCESS)
    def test_no_log_when_dir_not_set(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.log_file is None

    @patch(MOCK_SUBPROCESS)
    def test_file_not_found_propagates(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")

        try:
            execute_agent(
                ["nonexistent"], "prompt", timeout=None, log_path_dir=None, iteration=1,
            )
            assert False, "Expected FileNotFoundError"
        except FileNotFoundError:
            pass


class TestAgentResult:
    def test_defaults(self):
        result = AgentResult(returncode=0, elapsed=1.0, log_file=None)
        assert result.result_text is None
        assert result.timed_out is False

    def test_timed_out(self):
        result = AgentResult(returncode=None, elapsed=5.0, log_file=None, timed_out=True)
        assert result.timed_out is True
        assert result.returncode is None
