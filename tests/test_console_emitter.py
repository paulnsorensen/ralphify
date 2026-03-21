"""Tests for the ConsoleEmitter rich terminal renderer."""

import pytest
from rich.console import Console

from ralphify._console_emitter import ConsoleEmitter, _IterationSpinner
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
        emitter._stop_live()  # clean up the Live display started by the handler
        output = console.export_text()
        assert "Iteration 1" in output

    def test_iteration_started_uses_fallback_when_iteration_missing(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED))
        emitter._stop_live()
        output = console.export_text()
        assert "Iteration ?" in output

    @pytest.mark.parametrize("event_type,detail,expected", [
        (EventType.ITERATION_COMPLETED, "completed (5s)", "completed (5s)"),
        (EventType.ITERATION_FAILED, "failed with exit code 1 (3s)", "failed with exit code 1"),
        (EventType.ITERATION_TIMED_OUT, "timed out after 2m 0s", "timed out"),
    ])
    def test_iteration_ended_shows_detail(self, event_type, detail, expected):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            event_type,
            iteration=1, detail=detail, log_file=None, result_text=None,
        ))
        output = console.export_text()
        assert expected in output

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
    def test_shows_command_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED, count=3))
        output = console.export_text()
        assert "3 ran" in output

    def test_no_output_when_zero_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED, count=0))
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
            reason="completed", total=3, completed=2, failed=1, timed_out=1,
        ))
        output = console.export_text()
        assert "1 timed out" in output
        # timed_out is subset of failed — only non-timeout failures shown as "failed"
        assert "failed" not in output

    def test_completed_with_mixed_failures_and_timeouts(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="completed", total=5, completed=3, failed=2, timed_out=1,
        ))
        output = console.export_text()
        assert "3 succeeded" in output
        assert "1 failed" in output
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

    def test_run_stopped_stops_active_live_display(self):
        emitter, console = _capture_emitter()
        # Start a live display via iteration_started, then stop via run_stopped
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        assert emitter._live is not None
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="user_requested", total=1, completed=0, failed=0, timed_out=0,
        ))
        assert emitter._live is None

    def test_completed_all_succeeded(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(
            EventType.RUN_STOPPED,
            reason="completed", total=3, completed=3, failed=0, timed_out=0,
        ))
        output = console.export_text()
        assert "3 succeeded" in output
        assert "failed" not in output
        assert "timed out" not in output


class TestMissingEventData:
    """Verify handlers degrade gracefully when event data keys are missing."""

    def test_run_started_with_empty_data(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.RUN_STARTED))
        output = console.export_text()
        # No timeout or commands → no output
        assert output.strip() == ""

    def test_run_started_with_none_timeout(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.RUN_STARTED, timeout=None, commands=2))
        output = console.export_text()
        # None timeout treated as 0 via `or 0` → no timeout line
        assert "Timeout" not in output
        assert "2 configured" in output

    def test_iteration_ended_with_empty_data(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_COMPLETED))
        output = console.export_text()
        assert "Iteration ?" in output

    def test_log_message_with_empty_data(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.LOG_MESSAGE))
        # Should not raise — defaults to empty message, info level

    def test_commands_completed_with_empty_data(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.COMMANDS_COMPLETED))
        output = console.export_text()
        # count defaults to 0 → no output
        assert output.strip() == ""

    def test_run_stopped_with_empty_data(self):
        emitter, console = _capture_emitter()
        # reason won't match "completed", so handler returns early
        emitter.emit(_make_event(EventType.RUN_STOPPED))
        output = console.export_text()
        assert output.strip() == ""


class TestIterationSpinner:
    def test_renders_elapsed_time(self):
        spinner = _IterationSpinner()
        console = Console(record=True, width=80)
        console.print(spinner)
        output = console.export_text()
        # Should contain a duration string (e.g. "0.0s")
        assert "s" in output

    def test_stop_live_is_idempotent(self):
        emitter, _ = _capture_emitter()
        # Calling _stop_live when no Live is active should not raise
        assert emitter._live is None
        emitter._stop_live()
        assert emitter._live is None

    def test_full_iteration_lifecycle_cleans_up_live(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        assert emitter._live is not None
        emitter.emit(_make_event(
            EventType.ITERATION_COMPLETED,
            iteration=1, detail="completed (1s)", log_file=None, result_text=None,
        ))
        assert emitter._live is None
