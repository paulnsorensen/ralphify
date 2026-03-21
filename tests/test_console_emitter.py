"""Tests for the ConsoleEmitter rich terminal renderer."""

from rich.console import Console

from ralphify._console_emitter import ConsoleEmitter
from ralphify._events import Event, EventType


def _make_event(event_type, **data):
    return Event(type=event_type, run_id="test-run", data=data)


def _capture_emitter():
    """Return a ConsoleEmitter and Console that captures output."""
    console = Console(record=True, width=120)
    emitter = ConsoleEmitter(console)
    return emitter, console


class TestEmitDispatch:
    def test_unknown_event_type_does_not_raise(self):
        emitter, _ = _capture_emitter()
        # AGENT_ACTIVITY has no handler registered — should be silently ignored
        emitter.emit(_make_event(EventType.AGENT_ACTIVITY, raw="data"))

    def test_run_started_shows_timeout(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.RUN_STARTED, timeout=120, commands=0))
        output = console.export_text()
        assert "2m 0s" in output

    def test_run_started_shows_command_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.RUN_STARTED, timeout=0, commands=3))
        output = console.export_text()
        assert "3 configured" in output

    def test_run_started_no_output_when_no_timeout_or_commands(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.RUN_STARTED, timeout=0, commands=0))
        output = console.export_text()
        assert output.strip() == ""


class TestIterationLifecycle:
    def test_iteration_started_prints_header(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        output = console.export_text()
        assert "Iteration 1" in output

    def test_iteration_completed_shows_detail(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.ITERATION_COMPLETED,
            iteration=1, detail="completed (5s)", log_file=None, result_text=None,
        ))
        output = console.export_text()
        assert "completed (5s)" in output

    def test_iteration_failed_shows_detail(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.ITERATION_FAILED,
            iteration=2, detail="failed with exit code 1 (3s)", log_file=None, result_text=None,
        ))
        output = console.export_text()
        assert "failed with exit code 1" in output

    def test_iteration_timed_out_shows_detail(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.ITERATION_TIMED_OUT,
            iteration=3, detail="timed out after 2m 0s", log_file=None, result_text=None,
        ))
        output = console.export_text()
        assert "timed out" in output

    def test_iteration_ended_shows_log_file(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.ITERATION_COMPLETED,
            iteration=1, detail="completed (1s)", log_file="/tmp/log.txt", result_text=None,
        ))
        output = console.export_text()
        assert "/tmp/log.txt" in output

    def test_iteration_ended_shows_result_text(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.ITERATION_COMPLETED,
            iteration=1, detail="completed (1s)", log_file=None, result_text="All tests passed",
        ))
        output = console.export_text()
        assert "All tests passed" in output


class TestCommandsCompleted:
    def test_shows_passed_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED, passed=3, failed=0))
        output = console.export_text()
        assert "3 passed" in output

    def test_shows_failed_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED, passed=2, failed=1))
        output = console.export_text()
        assert "1 failed" in output
        assert "2 passed" in output

    def test_no_output_when_zero_counts(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED, passed=0, failed=0))
        output = console.export_text()
        assert output.strip() == ""


class TestLogMessage:
    def test_info_message(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.LOG_MESSAGE, message="Waiting 5s...", level="info"))
        output = console.export_text()
        assert "Waiting 5s..." in output

    def test_error_message(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.LOG_MESSAGE, message="Run crashed", level="error"))
        output = console.export_text()
        assert "Run crashed" in output

    def test_error_with_traceback(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.LOG_MESSAGE,
            message="Run crashed", level="error", traceback="Traceback:\n  File ...",
        ))
        output = console.export_text()
        assert "Traceback:" in output


class TestRunStopped:
    def test_completed_shows_summary(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="completed", total=5, completed=4, failed=1, timed_out=0,
        ))
        output = console.export_text()
        assert "5 iteration(s)" in output
        assert "4 succeeded" in output
        assert "1 failed" in output

    def test_completed_with_timeouts(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="completed", total=3, completed=2, failed=0, timed_out=1,
        ))
        output = console.export_text()
        assert "1 timed out" in output

    def test_non_completed_reason_skips_summary(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="user_requested", total=2, completed=1, failed=0, timed_out=0,
        ))
        output = console.export_text()
        # Non-completed runs don't print the summary line
        assert "iteration(s)" not in output
