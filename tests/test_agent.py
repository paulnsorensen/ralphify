"""Tests for the _agent module — subprocess execution, log writing, and stream parsing."""

import io
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from helpers import MOCK_POPEN, MOCK_SUBPROCESS, fail_result, make_mock_popen, ok_result

from ralphify._agent import (
    AgentResult,
    _read_agent_stream,
    _run_agent_streaming,
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

    @pytest.mark.parametrize("line", ["42\n", '"hello"\n', "[1,2,3]\n", "true\n", "null\n"])
    def test_ignores_valid_json_non_object_lines(self, line):
        """Valid JSON that is not a JSON object (e.g. number, string, array)
        should be silently skipped, not crash with AttributeError."""
        activities = []
        stream = io.StringIO(line)
        result = _read_agent_stream(stream, deadline=None, on_activity=activities.append)

        assert len(result.stdout_lines) == 1
        assert len(activities) == 0
        assert result.result_text is None

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

    def test_non_string_result_field_ignored(self):
        stream = io.StringIO('{"type": "result", "result": 42}\n')
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
    def test_success(self, mock_run):
        mock_run.return_value = ok_result()
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.log_file is None
        assert result.elapsed >= 0

    @patch(MOCK_SUBPROCESS)
    def test_failure(self, mock_run):
        mock_run.return_value = fail_result()
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
        mock_run.return_value = ok_result(stdout="agent output\n")
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
        mock_run.return_value = ok_result()
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.log_file is None

    @patch(MOCK_SUBPROCESS)
    def test_file_not_found_propagates(self, mock_run):
        mock_run.side_effect = FileNotFoundError("not found")

        with pytest.raises(FileNotFoundError):
            execute_agent(
                ["nonexistent"], "prompt", timeout=None, log_path_dir=None, iteration=1,
            )


class TestAgentResult:
    def test_defaults(self):
        result = AgentResult(returncode=0, elapsed=1.0, log_file=None)
        assert result.result_text is None
        assert result.timed_out is False

    def test_timed_out(self):
        result = AgentResult(returncode=None, elapsed=5.0, log_file=None, timed_out=True)
        assert result.timed_out is True
        assert result.returncode is None

    def test_success_when_zero_exit(self):
        result = AgentResult(returncode=0, elapsed=1.0, log_file=None)
        assert result.success is True

    def test_not_success_when_nonzero_exit(self):
        result = AgentResult(returncode=1, elapsed=1.0, log_file=None)
        assert result.success is False

    def test_not_success_when_timed_out(self):
        result = AgentResult(returncode=None, elapsed=5.0, log_file=None, timed_out=True)
        assert result.success is False


class TestExecuteAgentDispatch:
    """Tests for execute_agent routing to streaming vs blocking mode."""

    @patch(MOCK_POPEN)
    def test_dispatches_to_streaming_for_claude(self, mock_popen, monkeypatch):
        """execute_agent uses the streaming path when the agent supports it."""
        monkeypatch.setattr("ralphify._agent._supports_stream_json", lambda cmd: True)
        mock_popen.return_value = make_mock_popen(
            stdout_lines='{"type": "result", "result": "done"}\n',
            returncode=0,
        )
        result = execute_agent(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.returncode == 0
        assert result.result_text == "done"
        mock_popen.assert_called_once()


class TestExecuteAgentStreaming:
    """Tests for the streaming execution path (_run_agent_streaming)."""

    @patch(MOCK_POPEN)
    def test_success(self, mock_popen):
        mock_popen.return_value = make_mock_popen(
            stdout_lines='{"type": "status", "msg": "working"}\n',
            returncode=0,
        )
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.elapsed >= 0

    @patch(MOCK_POPEN)
    def test_failure(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=1)
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.returncode == 1
        assert result.timed_out is False
        assert result.success is False

    @patch(MOCK_POPEN)
    def test_captures_result_text(self, mock_popen):
        mock_popen.return_value = make_mock_popen(
            stdout_lines='{"type": "result", "result": "All tests passed"}\n',
            returncode=0,
        )
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.result_text == "All tests passed"

    @patch(MOCK_POPEN)
    def test_sends_prompt_to_stdin(self, mock_popen):
        proc = make_mock_popen(returncode=0)
        mock_popen.return_value = proc
        _run_agent_streaming(
            ["claude", "-p"], "my prompt text", timeout=None, log_path_dir=None, iteration=1,
        )

        proc.stdin.write.assert_called_once_with("my prompt text")
        proc.stdin.close.assert_called_once()

    @patch(MOCK_POPEN)
    def test_adds_stream_json_flags(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=0)
        _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert "--output-format" in cmd
        assert "stream-json" in cmd
        assert "--verbose" in cmd

    @patch(MOCK_POPEN)
    def test_writes_log_on_success(self, mock_popen, tmp_path):
        mock_popen.return_value = make_mock_popen(
            stdout_lines="agent output\n",
            stderr_text="some stderr\n",
            returncode=0,
        )
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=tmp_path, iteration=3,
        )

        assert result.log_file is not None
        assert result.log_file.exists()
        assert result.log_file.name.startswith("003_")
        content = result.log_file.read_text()
        assert "agent output" in content
        assert "some stderr" in content

    @patch(MOCK_POPEN)
    def test_no_log_when_dir_not_set(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=0)
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.log_file is None

    @patch(MOCK_POPEN)
    def test_on_activity_callback_invoked(self, mock_popen):
        mock_popen.return_value = make_mock_popen(
            stdout_lines='{"type": "status", "msg": "working"}\n{"type": "progress"}\n',
            returncode=0,
        )
        activities = []
        _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
            on_activity=activities.append,
        )

        assert len(activities) == 2
        assert activities[0]["type"] == "status"
        assert activities[1]["type"] == "progress"

    @patch("ralphify._agent.time.monotonic")
    @patch(MOCK_POPEN)
    def test_timeout_kills_process(self, mock_popen, mock_time):
        # Simulate: start=0, deadline check after reading first line = 100 (past deadline)
        mock_time.side_effect = [0.0, 100.0, 100.0]
        proc = make_mock_popen(
            stdout_lines="line1\nline2\n",
            returncode=0,
        )
        proc.poll.return_value = None  # process still running when timeout fires
        mock_popen.return_value = proc

        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=5, log_path_dir=None, iteration=1,
        )

        assert result.timed_out is True
        assert result.returncode is None
        proc.kill.assert_called()
