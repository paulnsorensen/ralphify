"""Tests for the _agent module — subprocess execution, log writing, and stream parsing."""

import io
import itertools
import signal
import subprocess
import sys
from unittest.mock import MagicMock, patch

import pytest
from helpers import MOCK_SUBPROCESS, fail_proc, make_mock_popen, ok_proc, timeout_proc

from ralphify._agent import (
    AgentResult,
    _kill_process_group,
    _read_agent_stream,
    _run_agent_blocking,
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
        result = _read_agent_stream(
            stream, deadline=None, on_activity=activities.append
        )

        assert len(result.stdout_lines) == 1
        assert len(activities) == 0

    @pytest.mark.parametrize(
        "line", ["42\n", '"hello"\n', "[1,2,3]\n", "true\n", "null\n"]
    )
    def test_ignores_valid_json_non_object_lines(self, line):
        """Valid JSON that is not a JSON object (e.g. number, string, array)
        should be silently skipped, not crash with AttributeError."""
        activities = []
        stream = io.StringIO(line)
        result = _read_agent_stream(
            stream, deadline=None, on_activity=activities.append
        )

        assert len(result.stdout_lines) == 1
        assert len(activities) == 0
        assert result.result_text is None

    def test_skips_empty_lines(self):
        activities = []
        stream = io.StringIO("\n\n")
        result = _read_agent_stream(
            stream, deadline=None, on_activity=activities.append
        )

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

    def test_timeout_still_processes_last_line(self):
        """When timeout fires on a line containing a result event, the result
        text must still be extracted — the deadline check should not skip
        processing of the already-read line."""
        stream = io.StringIO('{"type": "result", "result": "Done"}\n')
        result = _read_agent_stream(stream, deadline=0.001, on_activity=None)

        assert result.timed_out is True
        assert result.result_text == "Done"

    def test_timeout_still_calls_on_activity_for_last_line(self):
        """When timeout fires on a line, on_activity must still be called
        for that line so the last event is not silently swallowed."""
        activities = []
        stream = io.StringIO('{"type": "status", "msg": "working"}\n')
        result = _read_agent_stream(
            stream, deadline=0.001, on_activity=activities.append
        )

        assert result.timed_out is True
        assert len(activities) == 1
        assert activities[0]["type"] == "status"

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
        result = execute_agent(
            ["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1
        )

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.log_file is None
        assert result.elapsed >= 0

    @patch(MOCK_SUBPROCESS, side_effect=fail_proc)
    def test_failure(self, mock_popen):
        result = execute_agent(
            ["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1
        )

        assert result.returncode == 1
        assert result.timed_out is False

    @patch(MOCK_SUBPROCESS, side_effect=timeout_proc)
    def test_timeout(self, mock_popen):
        result = execute_agent(
            ["echo"], "prompt", timeout=5, log_path_dir=None, iteration=1
        )

        assert result.returncode is None
        assert result.timed_out is True

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_success(self, mock_popen, tmp_path):
        mock_popen.return_value = ok_proc(stdout_text="agent output\n")
        result = execute_agent(
            ["echo"],
            "prompt",
            timeout=None,
            log_path_dir=tmp_path,
            iteration=3,
        )

        assert result.log_file is not None
        assert result.log_file.exists()
        assert result.log_file.name.startswith("003_")
        assert "agent output" in result.log_file.read_text()

    @patch(MOCK_SUBPROCESS)
    def test_writes_log_on_timeout(self, mock_popen, tmp_path):
        mock_popen.return_value = timeout_proc(stdout_text="partial", stderr_text="err")
        result = execute_agent(
            ["echo"],
            "prompt",
            timeout=5,
            log_path_dir=tmp_path,
            iteration=1,
        )

        assert result.log_file is not None
        assert result.log_file.exists()

    @patch(MOCK_SUBPROCESS)
    def test_timeout_echoes_captured_output(self, mock_popen, tmp_path, capsys):
        """When logging is enabled and the agent times out, partial output
        should be echoed to the terminal — same as on normal completion."""
        mock_popen.return_value = timeout_proc(
            stdout_text="partial stdout", stderr_text="partial stderr"
        )
        execute_agent(
            ["echo"],
            "prompt",
            timeout=5,
            log_path_dir=tmp_path,
            iteration=1,
        )

        captured = capsys.readouterr()
        assert "partial stdout" in captured.out
        assert "partial stderr" in captured.err

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_no_log_when_dir_not_set(self, mock_popen):
        result = execute_agent(
            ["echo"], "prompt", timeout=None, log_path_dir=None, iteration=1
        )

        assert result.log_file is None

    @patch(MOCK_SUBPROCESS)
    def test_file_not_found_propagates(self, mock_popen):
        mock_popen.side_effect = FileNotFoundError("not found")

        with pytest.raises(FileNotFoundError):
            execute_agent(
                ["nonexistent"],
                "prompt",
                timeout=None,
                log_path_dir=None,
                iteration=1,
            )


class TestAgentResult:
    def test_defaults(self):
        result = AgentResult(returncode=0, elapsed=1.0, log_file=None)
        assert result.result_text is None
        assert result.timed_out is False

    def test_timed_out(self):
        result = AgentResult(
            returncode=None, elapsed=5.0, log_file=None, timed_out=True
        )
        assert result.timed_out is True
        assert result.returncode is None

    def test_success_when_zero_exit(self):
        result = AgentResult(returncode=0, elapsed=1.0, log_file=None)
        assert result.success is True

    def test_not_success_when_nonzero_exit(self):
        result = AgentResult(returncode=1, elapsed=1.0, log_file=None)
        assert result.success is False

    def test_not_success_when_timed_out(self):
        result = AgentResult(
            returncode=None, elapsed=5.0, log_file=None, timed_out=True
        )
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
        )

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.elapsed >= 0

    @patch(MOCK_SUBPROCESS)
    def test_failure(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=1)
        result = _run_agent_streaming(
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
        )

        assert result.result_text == "All tests passed"

    @patch(MOCK_SUBPROCESS)
    def test_sends_prompt_to_stdin(self, mock_popen):
        proc = make_mock_popen(returncode=0)
        mock_popen.return_value = proc
        _run_agent_streaming(
            ["claude", "-p"],
            "my prompt text",
            timeout=None,
            log_path_dir=None,
            iteration=1,
        )

        proc.stdin.write.assert_called_once_with("my prompt text")
        proc.stdin.close.assert_called_once()

    @patch(MOCK_SUBPROCESS)
    def test_adds_stream_json_flags(self, mock_popen):
        mock_popen.return_value = make_mock_popen(returncode=0)
        _run_agent_streaming(
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=tmp_path,
            iteration=3,
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
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
            ["claude", "-p"],
            "prompt",
            timeout=5,
            log_path_dir=None,
            iteration=1,
        )

        assert result.timed_out is True
        assert result.returncode is None
        proc.kill.assert_called()


class TestProcessGroupCleanup:
    """Process group cleanup, isolation, and _kill_process_group tests."""

    pytestmark = pytest.mark.skipif(
        sys.platform == "win32", reason="POSIX-only behavior"
    )

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
    def test_sigkill_failure_falls_back_to_proc_kill(self, mock_getpgid, mock_killpg):
        """When SIGTERM times out and SIGKILL also fails, fall back to proc.kill()."""
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        proc.wait.side_effect = subprocess.TimeoutExpired(cmd="agent", timeout=3)
        mock_getpgid.return_value = 42
        # SIGTERM succeeds but SIGKILL fails (process vanished between attempts)
        mock_killpg.side_effect = [None, ProcessLookupError("No such process")]

        _kill_process_group(proc)

        mock_killpg.assert_any_call(42, signal.SIGTERM)
        mock_killpg.assert_any_call(42, signal.SIGKILL)
        proc.kill.assert_called_once()

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
            ["claude", "-p"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
        )
        assert mock_popen.call_args[1].get("start_new_session") is True

    @patch("ralphify._agent.os.killpg")
    @patch("ralphify._agent.os.getpgid")
    def test_killpg_oserror_falls_back_to_proc_kill(self, mock_getpgid, mock_killpg):
        """When os.killpg raises OSError (e.g. process already gone), fall back to proc.kill()."""
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        mock_getpgid.return_value = 42  # session leader
        mock_killpg.side_effect = OSError("No such process")

        _kill_process_group(proc)

        mock_killpg.assert_called_once_with(42, signal.SIGTERM)
        proc.kill.assert_called_once()

    @patch("ralphify._agent.os.killpg")
    @patch("ralphify._agent.os.getpgid")
    def test_killpg_process_lookup_error_falls_back_to_proc_kill(
        self, mock_getpgid, mock_killpg
    ):
        """When os.killpg raises ProcessLookupError, fall back to proc.kill()."""
        proc = MagicMock(pid=42, poll=MagicMock(return_value=None))
        mock_getpgid.return_value = 42
        mock_killpg.side_effect = ProcessLookupError("No such process")

        _kill_process_group(proc)

        proc.kill.assert_called_once()


class TestRunAgentStreamingPipeGuard:
    """Test the defensive RuntimeError when Popen fails to create PIPE streams."""

    @patch(MOCK_SUBPROCESS)
    def test_raises_when_stdin_is_none(self, mock_popen):
        proc = make_mock_popen(returncode=0)
        proc.stdin = None
        proc.poll.return_value = None  # process still running for finally cleanup
        mock_popen.return_value = proc

        with pytest.raises(RuntimeError, match="PIPE streams"):
            _run_agent_streaming(
                ["claude", "-p"],
                "prompt",
                timeout=None,
                log_path_dir=None,
                iteration=1,
            )


class TestRunAgentBlockingKeyboardInterrupt:
    """Test that KeyboardInterrupt during blocking execution kills the process and re-raises."""

    @patch(MOCK_SUBPROCESS)
    def test_keyboard_interrupt_kills_and_reraises(self, mock_popen):
        proc = MagicMock()
        proc.pid = 12345
        proc.stdin = MagicMock()
        proc.stdout = io.StringIO("")
        proc.stderr = io.StringIO("")
        # First wait() raises KeyboardInterrupt; all subsequent calls
        # return -2.  Uses itertools.chain so the exact number of wait()
        # calls made by cleanup paths can drift without breaking the test.
        proc.wait.side_effect = itertools.chain(
            [KeyboardInterrupt], itertools.repeat(-2)
        )
        # First poll() (inside _kill_process_group) sees a live process;
        # every later poll() sees it as reaped so cleanup paths don't
        # re-enter kill/wait.
        proc.poll.side_effect = itertools.chain([None], itertools.repeat(0))
        mock_popen.return_value = proc

        with pytest.raises(KeyboardInterrupt):
            execute_agent(
                ["echo"],
                "prompt",
                timeout=None,
                log_path_dir=None,
                iteration=1,
            )

        proc.kill.assert_called()
        proc.wait.assert_called()


class TestRunAgentBlockingLineStreaming:
    """Real-subprocess tests for live line streaming via _run_agent_blocking.

    Uses tiny ``python -c`` subprocesses rather than mocks so we exercise
    the actual reader-thread path and observe lines as the process runs.
    """

    def test_on_output_line_receives_lines_in_order(self, tmp_path):
        script = "import sys; print('first'); print('second'); print('third')"
        received: list[tuple[str, str]] = []

        result = _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt="",
            timeout=10,
            log_path_dir=tmp_path,
            iteration=1,
            on_output_line=lambda line, stream: received.append((line, stream)),
        )

        assert result.returncode == 0
        assert [line for line, _ in received] == ["first", "second", "third"]
        assert all(stream == "stdout" for _, stream in received)

        # Log file still receives the full output (behavior preserved).
        assert result.log_file is not None
        log_text = result.log_file.read_text()
        assert "first" in log_text
        assert "second" in log_text
        assert "third" in log_text

    def test_on_output_line_captures_stderr_separately(self, tmp_path):
        script = (
            "import sys; "
            "print('out-line', file=sys.stdout); "
            "print('err-line', file=sys.stderr); "
            "sys.stdout.flush(); sys.stderr.flush()"
        )
        received: list[tuple[str, str]] = []

        _run_agent_blocking(
            [sys.executable, "-u", "-c", script],
            prompt="",
            timeout=10,
            log_path_dir=tmp_path,
            iteration=1,
            on_output_line=lambda line, stream: received.append((line, stream)),
        )

        streams = {stream for _, stream in received}
        assert streams == {"stdout", "stderr"}
        lines_by_stream = {stream: line for line, stream in received}
        assert lines_by_stream["stdout"] == "out-line"
        assert lines_by_stream["stderr"] == "err-line"

    def test_stdin_prompt_delivered_to_subprocess(self, tmp_path):
        """The prompt must reach the child via stdin so real agents get it."""
        script = "import sys; sys.stdout.write(sys.stdin.read())"
        received: list[str] = []

        _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt="hello-from-prompt\n",
            timeout=10,
            log_path_dir=tmp_path,
            iteration=1,
            on_output_line=lambda line, stream: received.append(line),
        )

        assert received == ["hello-from-prompt"]

    def test_large_prompt_with_concurrent_stderr_does_not_deadlock(self, tmp_path):
        """Regression guard for the pipe-buffer deadlock.

        If the child writes a burst of stderr larger than the OS pipe
        buffer before reading its stdin, and the parent is simultaneously
        writing a stdin prompt larger than the buffer, the only way to
        avoid deadlock is for the parent to drain stderr concurrently on
        a reader thread that was started **before** the stdin write began.

        This test fails (hangs) if the reader threads are started after
        the stdin write.
        """
        script = (
            "import sys\n"
            "sys.stderr.write('y' * 200000)\n"
            "sys.stderr.flush()\n"
            "sys.stdin.read()\n"
            "sys.stdout.write('done\\n')\n"
        )
        large_prompt = "x" * 200000

        result = _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt=large_prompt,
            timeout=15,
            log_path_dir=tmp_path,
            iteration=1,
        )

        assert result.returncode == 0
        assert result.timed_out is False

    def test_early_exit_with_large_prompt_does_not_crash(self, tmp_path):
        """If the agent exits without consuming its stdin, the parent's
        write will raise ``BrokenPipeError``; the blocking path must
        swallow it and still return the child's real exit code.
        """
        script = "import sys; sys.exit(0)"
        large_prompt = "x" * 200000

        result = _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt=large_prompt,
            timeout=10,
            log_path_dir=tmp_path,
            iteration=1,
        )

        assert result.returncode == 0
        assert result.timed_out is False

    def test_streaming_large_stderr_drained_concurrently(self, tmp_path):
        """Regression guard for the streaming path.

        An agent that writes substantial stderr before emitting its result
        event would previously deadlock the streaming path because stderr
        was only read after ``proc.wait()``.  With a concurrent stderr
        pump thread this finishes normally.
        """
        script = (
            "import sys\n"
            "sys.stderr.write('y' * 200000)\n"
            "sys.stderr.flush()\n"
            "sys.stdin.read()\n"
            'sys.stdout.write(\'{"type": "result", "result": "ok"}\\n\')\n'
        )

        result = _run_agent_streaming(
            [sys.executable, "-c", script],
            prompt="hi",
            timeout=15,
            log_path_dir=tmp_path,
            iteration=1,
        )

        assert result.returncode == 0
        assert result.timed_out is False
        assert result.result_text == "ok"


class TestBlockingInheritPath:
    """Tests for the fd-inheritance path in _run_agent_blocking.

    When both ``log_path_dir`` and ``on_output_line`` are ``None``, the
    blocking path should inherit stdout/stderr from the parent (no PIPE,
    no reader threads) so that ``ralph run | cat`` shows output.
    """

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_no_pipe_when_no_log_no_callback(self, mock_popen):
        """Popen must NOT receive stdout/stderr=PIPE when no one needs capture."""
        result = _run_agent_blocking(
            ["echo"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
            on_output_line=None,
        )

        call_kwargs = mock_popen.call_args[1]
        assert "stdout" not in call_kwargs
        assert "stderr" not in call_kwargs
        assert result.returncode == 0
        assert result.log_file is None

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_still_pipes_when_callback_set(self, mock_popen):
        """When on_output_line is provided, stdout/stderr must be PIPE'd."""
        _run_agent_blocking(
            ["echo"],
            "prompt",
            timeout=None,
            log_path_dir=None,
            iteration=1,
            on_output_line=lambda line, stream: None,
        )

        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("stdout") == subprocess.PIPE
        assert call_kwargs.get("stderr") == subprocess.PIPE

    @patch(MOCK_SUBPROCESS, side_effect=ok_proc)
    def test_still_pipes_when_log_dir_set(self, mock_popen, tmp_path):
        """When log_path_dir is provided, stdout/stderr must be PIPE'd."""
        _run_agent_blocking(
            ["echo"],
            "prompt",
            timeout=None,
            log_path_dir=tmp_path,
            iteration=1,
            on_output_line=None,
        )

        call_kwargs = mock_popen.call_args[1]
        assert call_kwargs.get("stdout") == subprocess.PIPE
        assert call_kwargs.get("stderr") == subprocess.PIPE

    def test_inherit_path_shows_output(self, capfd):
        """Real subprocess in inherit mode: child output reaches the parent's
        stdout, verifying the ``ralph run | cat`` scenario works.

        Uses ``capfd`` (fd-level capture) rather than ``capsys`` because
        the inherit path writes to the raw file descriptor, bypassing
        Python's ``sys.stdout``.
        """
        script = "import sys; print('visible-output')"

        result = _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt="",
            timeout=10,
            log_path_dir=None,
            iteration=1,
            on_output_line=None,
        )

        assert result.returncode == 0
        captured = capfd.readouterr()
        assert "visible-output" in captured.out

    def test_callback_only_does_not_buffer(self, tmp_path):
        """When on_output_line is set but log_path_dir is None, lines should
        be forwarded to the callback but NOT accumulated (no unbounded
        buffering).  Verified indirectly: log_file is None (no buffer to
        write) but the callback still receives lines."""
        script = "import sys; print('line1'); print('line2')"
        received: list[str] = []

        result = _run_agent_blocking(
            [sys.executable, "-c", script],
            prompt="",
            timeout=10,
            log_path_dir=None,
            iteration=1,
            on_output_line=lambda line, stream: received.append(line),
        )

        assert result.returncode == 0
        assert result.log_file is None
        assert received == ["line1", "line2"]
