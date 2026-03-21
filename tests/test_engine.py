"""Tests for the v2 run engine."""

import subprocess
import threading
import time
from unittest.mock import patch

from helpers import MOCK_RUN_COMMAND, MOCK_SUBPROCESS, drain_events, fail_result, make_config, make_state, ok_result

from ralphify._events import EventType, NullEmitter, QueueEmitter
from ralphify._run_types import REASON_ERROR, REASON_USER_REQUESTED, Command, RunStatus
from ralphify._runner import RunResult
from ralphify.engine import (
    _BoundEmitter,
    _assemble_prompt,
    _delay_if_needed,
    _handle_control_signals,
    _run_commands,
    run_loop,
)


class TestBoundEmitter:
    def test_emits_event_with_fixed_run_id(self):
        q = QueueEmitter()
        emit = _BoundEmitter(q, "run-abc")
        emit(EventType.ITERATION_STARTED, {"iteration": 1})

        events = drain_events(q)
        assert len(events) == 1
        assert events[0].run_id == "run-abc"
        assert events[0].type == EventType.ITERATION_STARTED
        assert events[0].data == {"iteration": 1}

    def test_emits_empty_data_when_none_provided(self):
        q = QueueEmitter()
        emit = _BoundEmitter(q, "run-xyz")
        emit(EventType.RUN_PAUSED)

        events = drain_events(q)
        assert len(events) == 1
        assert events[0].data == {}

    def test_multiple_events_share_run_id(self):
        q = QueueEmitter()
        emit = _BoundEmitter(q, "run-123")
        emit(EventType.RUN_STARTED)
        emit(EventType.ITERATION_STARTED, {"iteration": 1})
        emit(EventType.RUN_STOPPED)

        events = drain_events(q)
        assert all(e.run_id == "run-123" for e in events)
        assert len(events) == 3


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
        config = make_config(tmp_path, "my prompt text", max_iterations=1)
        state = make_state()

        run_loop(config, state, NullEmitter())

        assert mock_run.call_args.kwargs["input"] == "my prompt text"

    @patch(MOCK_SUBPROCESS)
    def test_log_dir_creates_files(self, mock_run, tmp_path):
        mock_run.return_value = ok_result(stdout="output\n")
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
        assert types[-1] == EventType.RUN_STOPPED
        # Verify lifecycle ordering within the iteration
        assert types.index(EventType.ITERATION_STARTED) < types.index(EventType.PROMPT_ASSEMBLED)
        assert types.index(EventType.PROMPT_ASSEMBLED) < types.index(EventType.ITERATION_COMPLETED)
        assert types.index(EventType.ITERATION_COMPLETED) < types.index(EventType.RUN_STOPPED)

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
            return ok_result(*args, **kwargs)

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
        assert stop_event.data["reason"] == REASON_USER_REQUESTED

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
            return ok_result(*args, **kwargs)

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
            return ok_result(*args, **kwargs)

        mock_run.side_effect = pause_then_stop

        run_loop(config, state, NullEmitter())

        assert state.status == RunStatus.STOPPED
        assert mock_run.call_count == 1


class TestRalphArgs:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_args_resolved_in_prompt(self, mock_run, tmp_path):
        config = make_config(
            tmp_path,
            "---\nargs:\n  - dir\n  - focus\n---\nResearch {{ args.dir }} focus: {{ args.focus }}",
            max_iterations=1,
            args={"dir": "./src", "focus": "perf"},
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert call_input == "Research ./src focus: perf"

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    def test_empty_args_clears_placeholders(self, mock_run, tmp_path):
        config = make_config(tmp_path, "Before {{ args.opt }} after", max_iterations=1, args={})
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_run.call_args.kwargs["input"]
        assert call_input == "Before  after"


class TestCommandExecution:
    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch(MOCK_RUN_COMMAND)
    def test_commands_output_injected(self, mock_run_cmd, mock_agent, tmp_path):
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="test output\n")

        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: tests\n    run: uv run pytest\n---\n"
            "Results:\n\n{{ commands.tests }}",
            max_iterations=1,
            commands=[Command(name="tests", run="uv run pytest")],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        call_input = mock_agent.call_args.kwargs["input"]
        assert "test output" in call_input
        assert "{{ commands.tests }}" not in call_input

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch(MOCK_RUN_COMMAND)
    def test_multiple_commands_all_executed(self, mock_run_cmd, mock_agent, tmp_path):
        """All commands in the list are executed and their outputs collected."""

        call_count = 0

        def per_command(**kwargs):
            nonlocal call_count
            call_count += 1
            name = kwargs.get("command", "")
            return RunResult(success=True, returncode=0, output=f"output-{name}")

        mock_run_cmd.side_effect = per_command

        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: tests\n    run: pytest\n"
            "  - name: lint\n    run: ruff check\n---\n"
            "{{ commands.tests }}\n{{ commands.lint }}",
            max_iterations=1,
            commands=[
                Command(name="tests", run="pytest"),
                Command(name="lint", run="ruff check"),
            ],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        assert mock_run_cmd.call_count == 2

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch(MOCK_RUN_COMMAND)
    def test_dotslash_command_uses_ralph_dir_as_cwd(self, mock_run_cmd, mock_agent, tmp_path):
        """Commands starting with ./ run relative to the ralph directory."""
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")

        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: local\n    run: ./check.sh\n---\n"
            "{{ commands.local }}",
            max_iterations=1,
            commands=[Command(name="local", run="./check.sh")],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        passed_cwd = mock_run_cmd.call_args.kwargs["cwd"]
        assert passed_cwd == config.ralph_dir

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch(MOCK_RUN_COMMAND)
    def test_regular_command_uses_project_root_as_cwd(self, mock_run_cmd, mock_agent, tmp_path):
        """Commands without ./ prefix run from the project root."""
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")

        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: tests\n    run: uv run pytest\n---\n"
            "{{ commands.tests }}",
            max_iterations=1,
            commands=[Command(name="tests", run="uv run pytest")],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        passed_cwd = mock_run_cmd.call_args.kwargs["cwd"]
        assert passed_cwd == config.project_root

    @patch(MOCK_SUBPROCESS, side_effect=ok_result)
    @patch(MOCK_RUN_COMMAND)
    def test_command_timeout_passed_through(self, mock_run_cmd, mock_agent, tmp_path):
        """Command timeout from frontmatter is forwarded to run_command."""
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")

        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: slow\n    run: sleep 1\n    timeout: 300\n---\n"
            "{{ commands.slow }}",
            max_iterations=1,
            commands=[Command(name="slow", run="sleep 1", timeout=300)],
        )
        state = make_state()
        run_loop(config, state, NullEmitter())

        passed_timeout = mock_run_cmd.call_args.kwargs["timeout"]
        assert passed_timeout == 300


class TestAgentCommandParsing:
    """Tests for malformed agent command handling in the engine."""

    def test_malformed_agent_command_raises_value_error(self, tmp_path):
        """shlex.split on an agent with unmatched quotes produces a clear error."""
        config = make_config(tmp_path, max_iterations=1, agent="echo 'unterminated")
        state = make_state()
        q = QueueEmitter()

        run_loop(config, state, q)

        assert state.status == RunStatus.FAILED
        events = drain_events(q)
        log_events = [e for e in events if e.type == EventType.LOG_MESSAGE]
        assert any("Invalid agent command syntax" in e.data["message"] for e in log_events)


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
        assert stop_event.data["reason"] == REASON_ERROR

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


class TestDelayIfNeeded:
    def test_no_delay_when_zero(self, tmp_path):
        config = make_config(tmp_path, delay=0, max_iterations=5)
        state = make_state()
        state.iteration = 1
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        start = time.monotonic()
        _delay_if_needed(config, state, emit)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1
        assert drain_events(q) == []

    def test_delay_sleeps_between_iterations(self, tmp_path):
        config = make_config(tmp_path, delay=0.15, max_iterations=5)
        state = make_state()
        state.iteration = 1
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        start = time.monotonic()
        _delay_if_needed(config, state, emit)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.1
        events = drain_events(q)
        assert len(events) == 1
        assert events[0].type == EventType.LOG_MESSAGE
        assert "Waiting" in events[0].data["message"]

    def test_no_delay_on_last_iteration(self, tmp_path):
        config = make_config(tmp_path, delay=0.5, max_iterations=3)
        state = make_state()
        state.iteration = 3  # last iteration
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        start = time.monotonic()
        _delay_if_needed(config, state, emit)
        elapsed = time.monotonic() - start

        assert elapsed < 0.1
        assert drain_events(q) == []

    def test_delay_with_unlimited_iterations(self, tmp_path):
        config = make_config(tmp_path, delay=0.15, max_iterations=None)
        state = make_state()
        state.iteration = 100
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        start = time.monotonic()
        _delay_if_needed(config, state, emit)
        elapsed = time.monotonic() - start

        assert elapsed >= 0.1


class TestHandleControlSignals:
    """Unit tests for _handle_control_signals — stop and pause logic."""

    def test_returns_true_when_no_signals(self):
        state = make_state()
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        result = _handle_control_signals(state, emit)

        assert result is True
        assert state.status == RunStatus.PENDING

    def test_returns_false_when_stop_requested(self):
        state = make_state()
        state.request_stop()
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        result = _handle_control_signals(state, emit)

        assert result is False
        assert state.status == RunStatus.STOPPED

    def test_paused_then_resumed_returns_true(self):
        state = make_state()
        state.request_pause()
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        def resume_soon():
            time.sleep(0.05)
            state.request_resume()

        threading.Thread(target=resume_soon, daemon=True).start()

        result = _handle_control_signals(state, emit)

        assert result is True
        events = drain_events(q)
        types = [e.type for e in events]
        assert EventType.RUN_PAUSED in types
        assert EventType.RUN_RESUMED in types

    def test_paused_then_stop_returns_false(self):
        state = make_state()
        state.request_pause()
        q = QueueEmitter()
        emit = _BoundEmitter(q, state.run_id)

        def stop_soon():
            time.sleep(0.05)
            state.request_stop()

        threading.Thread(target=stop_soon, daemon=True).start()

        result = _handle_control_signals(state, emit)

        assert result is False
        assert state.status == RunStatus.STOPPED
        events = drain_events(q)
        types = [e.type for e in events]
        assert EventType.RUN_PAUSED in types
        assert EventType.RUN_RESUMED not in types


class TestRunCommands:
    """Unit tests for _run_commands — command execution and cwd resolution."""

    @patch(MOCK_RUN_COMMAND)
    def test_returns_name_to_output_mapping(self, mock_run_cmd, tmp_path):
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="test output")
        commands = [Command(name="tests", run="pytest")]

        result = _run_commands(commands, ralph_dir=tmp_path / "ralph", project_root=tmp_path)

        assert result == {"tests": "test output"}

    @patch(MOCK_RUN_COMMAND)
    def test_multiple_commands(self, mock_run_cmd, tmp_path):
        call_count = 0

        def per_command(**kwargs):
            nonlocal call_count
            call_count += 1
            return RunResult(success=True, returncode=0, output=f"out-{call_count}")

        mock_run_cmd.side_effect = per_command
        commands = [
            Command(name="a", run="cmd-a"),
            Command(name="b", run="cmd-b"),
        ]

        result = _run_commands(commands, ralph_dir=tmp_path / "ralph", project_root=tmp_path)

        assert len(result) == 2
        assert result["a"] == "out-1"
        assert result["b"] == "out-2"

    @patch(MOCK_RUN_COMMAND)
    def test_dotslash_uses_ralph_dir(self, mock_run_cmd, tmp_path):
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")
        ralph_dir = tmp_path / "my-ralph"
        commands = [Command(name="local", run="./check.sh")]

        _run_commands(commands, ralph_dir=ralph_dir, project_root=tmp_path)

        assert mock_run_cmd.call_args.kwargs["cwd"] == ralph_dir

    @patch(MOCK_RUN_COMMAND)
    def test_regular_command_uses_project_root(self, mock_run_cmd, tmp_path):
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")
        ralph_dir = tmp_path / "my-ralph"
        commands = [Command(name="tests", run="pytest")]

        _run_commands(commands, ralph_dir=ralph_dir, project_root=tmp_path)

        assert mock_run_cmd.call_args.kwargs["cwd"] == tmp_path

    @patch(MOCK_RUN_COMMAND)
    def test_timeout_passed_to_run_command(self, mock_run_cmd, tmp_path):
        mock_run_cmd.return_value = RunResult(success=True, returncode=0, output="ok")
        commands = [Command(name="slow", run="sleep 1", timeout=300)]

        _run_commands(commands, ralph_dir=tmp_path, project_root=tmp_path)

        assert mock_run_cmd.call_args.kwargs["timeout"] == 300

    def test_empty_commands_returns_empty_dict(self, tmp_path):
        result = _run_commands([], ralph_dir=tmp_path, project_root=tmp_path)

        assert result == {}


class TestAssemblePrompt:
    """Unit tests for _assemble_prompt — reading and resolving the prompt template."""

    def test_reads_prompt_from_ralph_file(self, tmp_path):
        config = make_config(tmp_path, "simple prompt", max_iterations=1)

        result = _assemble_prompt(config, {})

        assert result == "simple prompt"

    def test_resolves_command_placeholders(self, tmp_path):
        config = make_config(
            tmp_path,
            "---\nagent: echo\ncommands:\n  - name: tests\n    run: pytest\n---\n"
            "Results: {{ commands.tests }}",
            max_iterations=1,
        )

        result = _assemble_prompt(config, {"tests": "all passed"})

        assert result == "Results: all passed"

    def test_resolves_args_placeholders(self, tmp_path):
        config = make_config(
            tmp_path,
            "---\nagent: echo\nargs:\n  - dir\n---\nSearch {{ args.dir }}",
            max_iterations=1,
            args={"dir": "./src"},
        )

        result = _assemble_prompt(config, {})

        assert result == "Search ./src"

    def test_clears_unresolved_placeholders(self, tmp_path):
        config = make_config(tmp_path, "Before {{ args.missing }} after", max_iterations=1, args={})

        result = _assemble_prompt(config, {})

        assert result == "Before  after"

    def test_strips_html_comments(self, tmp_path):
        config = make_config(tmp_path, "Before <!-- hidden --> after", max_iterations=1)

        result = _assemble_prompt(config, {})

        assert result == "Before  after"
