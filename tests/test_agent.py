"""Tests for the _agent module — subprocess execution, log writing, and stream parsing."""

import io
import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from helpers import MOCK_SUBPROCESS, fail_proc, make_mock_popen, ok_proc, timeout_proc

from ralphify._agent import (
    AgentResult,
    _kill_process_group,
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

    def test_claude_with_cmd_extension(self):
        """On Windows, npm installs claude as claude.cmd — streaming must
        still be detected."""
        assert _supports_stream_json(["claude.cmd", "-p"]) is True

    def test_claude_with_exe_extension(self):
        assert _supports_stream_json(["claude.exe", "-p"]) is True


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

    def test_timeout_preserves_last_read_line(self):
        """When timeout fires after reading a line, that line must still be
        included in stdout_lines — otherwise log output silently loses data."""
        stream = io.StringIO("line1\nline2\n")
        result = _read_agent_stream(stream, deadline=0.001, on_activity=None)

        assert result.timed_out is True
        # The stream reader already consumed at least one line before
        # noticing the deadline — that line must be in stdout_lines.
        assert len(result.stdout_lines) >= 1
        assert result.stdout_lines[0] == "line1\n"

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
    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_success(self, mock_popen):
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.log_file is None
        assert result.elapsed >= 0

    @patch(MOCK_SUBPROCESS, side_effect=fail_proc)
    def test_failure(self, mock_popen):
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.returncode == 1
        assert result.timed_out is False

    @patch(MOCK_SUBPROCESS, side_effect=timeout_proc)
    def test_timeout(self, mock_popen):
        result = execute_agent(["echo"], "prompt", timeout=5, log_path_dir=None, iteration=1)

        assert result.returncode is None
        assert result.timed_out is True

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_success(self, mock_popen, tmp_path):
        mock_popen.return_value = ok_proc(stdout="agent output\n")
        result = execute_agent(
            ["echo"], "prompt", timeout=None, log_path_dir=tmp_path, iteration=3,
        )

        assert result.log_file is not None
        assert result.log_file.exists()
        assert result.log_file.name.startswith("003_")
        assert "agent output" in result.log_file.read_text()

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_timeout(self, mock_popen, tmp_path):
        mock_popen.return_value = timeout_proc(stdout="partial", stderr="err")
        result = execute_agent(
            ["echo"], "prompt", timeout=5, log_path_dir=tmp_path, iteration=1,
        )

        assert result.log_file is not None
        assert result.log_file.exists()

    @patch(MOCK_SUBPROCESS)
    def test_timeout_echoes_captured_output(self, mock_popen, tmp_path, capsys):
        """When logging is enabled and the agent times out, partial output
        should be echoed to the terminal — same as on normal completion."""
        mock_popen.return_value = timeout_proc(stdout="partial stdout", stderr="partial stderr")
        execute_agent(
            ["echo"], "prompt", timeout=5, log_path_dir=tmp_path, iteration=1,
        )

        captured = capsys.readouterr()
        assert "partial stdout" in captured.out
        assert "partial stderr" in captured.err

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_no_log_when_dir_not_set(self, mock_popen):
        result = execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)

        assert result.log_file is None

    @patch(MOCK_SUBPROCESS)
    def test_file_not_found_propagates(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("not found")

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

    @patch(MOCK_SUBPROCESS)
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

    @patch(MOCK_SUBPROCESS)
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

    @patch(MOCK_SUBPROCESS)
    def test_failure(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=1)
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.returncode == 1
        assert result.timed_out is False
        assert result.success is False

    @patch(MOCK_SUBPROCESS)
    def test_captures_result_text(self, mock_popen):
        mock_popen.return_value = make_mock_popen(
            stdout_lines='{"type": "result", "result": "All tests passed"}\n',
            returncode=0,
        )
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.result_text == "All tests passed"

    @patch(MOCK_SUBPROCESS)
    def test_sends_prompt_to_stdin(self, mock_popen):
        proc = make_mock_popen(returncode=0)
        mock_popen.return_value = proc
        _run_agent_streaming(
            ["claude", "-p"], "my prompt text", timeout=None, log_path_dir=None, iteration=1,
        )

        proc.stdin.write.assert_called_once_with("my prompt text")
        proc.stdin.close.assert_called_once()

    @patch(MOCK_SUBPROCESS)
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

    @patch(MOCK_SUBPROCESS)
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

    @patch(MOCK_SUBPROCESS)
    def test_no_log_when_dir_not_set(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=0)
        result = _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )

        assert result.log_file is None

    @patch(MOCK_SUBPROCESS)
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
    @patch(MOCK_SUBPROCESS)
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


class TestProcessGroupCleanup:
    """Process group cleanup, isolation, and _kill_process_group tests."""

    pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only behavior")

    @patch("ralphify._agent.os.killpg")
    @patch("ralphify._agent.os.getpgid")
    def test_session_leader_gets_sigterm(self, mock_getpgid, mock_killpg):
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        mock_getpgid.return_value = 42

        _kill_process_group(proc)

        mock_killpg.assert_any_call(42, signal.SIGTERM)
        proc.wait.assert_called_once_with(timeout=3)

    @patch("ralphify._agent.os.killpg")
    @patch("ralphify._agent.os.getpgid")
    def test_escalates_to_sigkill_on_timeout(self, mock_getpgid, mock_killpg):
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="agent", timeout=3)
        mock_getpgid.return_value = 42

        _kill_process_group(proc)

        mock_killpg.assert_any_call(42, signal.SIGTERM)
        mock_killpg.assert_any_call(42, signal.SIGKILL)

    @patch("ralphify._agent.os.killpg")
    @patch("ralphify._agent.os.getpgid")
    def test_not_session_leader_falls_back_to_kill(self, mock_getpgid, mock_killpg):
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        mock_getpgid.return_value = 1

        _kill_process_group(proc)

        mock_killpg.assert_not_called()
        proc.kill.assert_called_once()

    def test_already_exited_falls_back_to_kill(self):
        proc = MagicMock(pid=42, poll=MagicMock(return_value=0))

        _kill_process_group(proc)

        proc.kill.assert_called_once()

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_blocking_uses_start_new_session(self, mock_popen):
        execute_agent(["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1)
        assert mock_popen.call_args[1].get("start_new_session") is True

    @patch(MOCK_SUBPROCESS)
    def test_streaming_uses_start_new_session(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=0)
        _run_agent_streaming(
            ["claude", "-p"], "prompt", timeout=None, log_path_dir=None, iteration=1,
        )
        assert mock_popen.call_args[1].get("start_new_session") is True
