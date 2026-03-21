"""Tests for the v2 run engine."""

import subprocess
import threading
import time
from unittest.mock import patch

from helpers import MOCK_SUBPROCESS, drain_events, fail_result, make_config, make_state, ok_result

from ralphify._events import EventType, NullEmitter, QueueEmitter
from ralphify._run_types import RunStatus
from ralphify.engine import run_loop


class TestRunLoop:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_single_iteration(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.completed == 1
        assert state.failed == 0
        assert state.status == RunStatus.COMPLETED
        assert mock_run.call_count == 1

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_multiple_iterations(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=3)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.completed == 3
        assert mock_run.call_count == 3

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_failed_iterations_counted(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=2)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.completed == 0
        assert state.failed == 2

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_stop_on_error(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=5, stop_on_error=True)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_count == 1
        assert state.failed == 1

    @patch(MOCK_SUBPROCESS)
    def test_timeout_counted(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        config = make_config(tmp_path, max_iterations=1, timeout=5)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.timed_out == 1
        assert state.failed == 1

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_prompt_read_from_ralph_file(self, mock_run, tmp_path):
        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir(exist_ok=True)
        (ralph_dir / "RALPH.md").write_text("my prompt text")
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_args.kwargs["input"] == "my prompt text"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_log_dir_creates_files(self, mock_run, tmp_path):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="output\n", stderr=""
        )
        log_dir = tmp_path / "logs"
        config = make_config(tmp_path, max_iterations=2, log_dir=str(log_dir))
        state = make_state()

        run_loop(config, state, NullEmitter())

        log_files = sorted(log_dir.iterdir())
        assert len(log_files) == 2
        assert log_files[0].name.startswith("001_")
        assert log_files[1].name.startswith("002_")


class TestRunLoopEvents:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_events_emitted_in_order(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)
        types = [e.type for e in events]
        assert types[0] == EventType.RUN_STARTED
        assert EventType.ITERATION_STARTED in types
        assert EventType.PROMPT_ASSEMBLED in types
        assert EventType.ITERATION_COMPLETED in types
        assert types[-1] == EventType.RUN_STOPPED

    @patch(MOCK_SUBPROCESS, side_effect=fail_result)
    def test_failure_event_emitted(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)
        types = [e.type for e in events]
        assert EventType.ITERATION_FAILED in types

    @patch(MOCK_SUBPROCESS)
    def test_timeout_event_emitted(self, mock_run, tmp_path):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="echo", timeout=5)
        config = make_config(tmp_path, max_iterations=1, timeout=5)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)
        types = [e.type for e in events]
        assert EventType.ITERATION_TIMED_OUT in types

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_all_events_have_run_id(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        for event in drain_events(q):
            assert event.run_id == "test-run-001"


class TestRunStateControls:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_stop_request(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=100)
        state = make_state()

        def stop_after_first(*args, **kwargs):
            state.request_stop()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = stop_after_first

        run_loop(config, state, NullEmitter())

        assert mock_run.call_count == 1
        assert state.status == RunStatus.STOPPED

    @patch(MOCK_SUBPROCESS)
    def test_keyboard_interrupt_sets_stopped(self, mock_run, tmp_path):
        mock_run.side_effect = KeyboardInterrupt
        config = make_config(tmp_path, max_iterations=5)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.status == RunStatus.STOPPED
        events = drain_events(q)
        stop_event = [e for e in events if e.type == EventType.RUN_STOPPED][0]
        assert stop_event.data["reason"] == "user_requested"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_pause_and_resume(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=3)
        state = make_state()

        call_count = 0

        def track_calls(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                state.request_pause()

                def resume_later():
                    time.sleep(0.1)
                    state.request_resume()

                threading.Thread(target=resume_later, daemon=True).start()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = track_calls

        run_loop(config, state, NullEmitter())

        assert state.completed == 3
        assert state.status == RunStatus.COMPLETED

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_stop_while_paused(self, mock_run, tmp_path):
        config = make_config(tmp_path, max_iterations=100)
        state = make_state()

        def pause_then_stop(*args, **kwargs):
            state.request_pause()

            def stop_later():
                time.sleep(0.1)
                state.request_stop()

            threading.Thread(target=stop_later, daemon=True).start()
            return subprocess.CompletedProcess(args=args, returncode=0)

        mock_run.side_effect = pause_then_stop

        run_loop(config, state, NullEmitter())

        assert state.status == RunStatus.STOPPED
        assert mock_run.call_count == 1


class TestRalphArgs:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_args_resolved_in_prompt(self, mock_run, tmp_path):
        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir(exist_ok=True)
        (ralph_dir / "RALPH.md").write_text(
            "---\nargs:\n  - dir\n  - focus\n---\nResearch {{ args.dir }} focus: {{ args.focus }}"
        )
        config = make_config(
            tmp_path, max_iterations=1,
            args={"dir": "./src", "focus": "perf"},
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert call_input == "Research ./src focus: perf"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_empty_args_clears_placeholders(self, mock_run, tmp_path):
        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir(exist_ok=True)
        (ralph_dir / "RALPH.md").write_text("Before {{ args.opt }} after")
        config = make_config(tmp_path, max_iterations=1, args={})
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert call_input == "Before  after"


class TestCommandExecution:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch("ralphify.engine.run_command")
    def test_commands_output_injected(self, mock_run_cmd, mock_agent, tmp_path):
        from ralphify._runner import RunResult
        mock_run_cmd.return_value = RunResult(success=True, exit_code=0, output="test output\n")

        ralph_dir = tmp_path / "my-ralph"
        ralph_dir.mkdir(exist_ok=True)
        (ralph_dir / "RALPH.md").write_text(
            "---\nagent: echo\ncommands:\n  - name: tests\n    run: uv run pytest\n---\n"
            "Results:\n\n{{ commands.tests }}"
        )
        from ralphify._run_types import Command
        config = make_config(
            tmp_path, max_iterations=1,
            commands=[Command(name="tests", run="uv run pytest")],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_agent.call_args.kwargs["input"]
        assert "test output" in call_input
        assert "{{ commands.tests }}" not in call_input


class TestRunLoopCrashHandling:
    """Tests for the broad exception handler in run_loop (engine.py lines 269-276)."""

    @patch(MOCK_SUBPROCESS)
    def test_unexpected_exception_sets_failed_status(self, mock_run, tmp_path):
        mock_run.side_effect = RuntimeError("disk full")
        config = make_config(tmp_path, max_iterations=5)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert state.status == RunStatus.FAILED

    @patch(MOCK_SUBPROCESS)
    def test_unexpected_exception_emits_log_and_stop_events(self, mock_run, tmp_path):
        mock_run.side_effect = RuntimeError("disk full")
        config = make_config(tmp_path, max_iterations=5)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        events = drain_events(q)
        types = [e.type for e in events]
        assert EventType.LOG_MESSAGE in types
        assert EventType.RUN_STOPPED in types

        log_event = next(e for e in events if e.type == EventType.LOG_MESSAGE)
        assert log_event.data["level"] == "error"
        assert "disk full" in log_event.data["message"]
        assert "traceback" in log_event.data

        stop_event = next(e for e in events if e.type == EventType.RUN_STOPPED)
        assert stop_event.data["reason"] == "error"

    @patch(MOCK_SUBPROCESS)
    def test_unexpected_exception_only_runs_one_iteration(self, mock_run, tmp_path):
        mock_run.side_effect = RuntimeError("boom")
        config = make_config(tmp_path, max_iterations=10)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_count == 1
        assert state.iteration == 1

    @patch("ralphify.engine.parse_frontmatter")
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_crash_in_prompt_assembly_handled(self, mock_run, mock_parse, tmp_path):
        mock_parse.side_effect = ValueError("corrupt YAML")
        config = make_config(tmp_path, max_iterations=1)
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.status == RunStatus.FAILED
        events = drain_events(q)
        log_events = [e for e in events if e.type == EventType.LOG_MESSAGE]
        assert any("corrupt YAML" in e.data["message"] for e in log_events)
