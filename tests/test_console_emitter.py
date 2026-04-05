"""Tests for the ConsoleEmitter rich terminal renderer."""

import threading

import pytest
from rich.console import Console

from ralphify._console_emitter import (
    ConsoleEmitter,
    _IterationSpinner,
    _format_run_info,
    _format_summary,
)
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


class TestPeekToggle:
    def test_peek_disabled_by_default_drops_output_lines(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.AGENT_OUTPUT_LINE,
                line="hello world",
                stream="stdout",
                iteration=1,
            )
        )
        assert "hello world" not in console.export_text()

    def test_toggle_peek_enables_rendering(self):
        emitter, console = _capture_emitter()
        assert emitter.toggle_peek() is True
        emitter.emit(
            _make_event(
                EventType.AGENT_OUTPUT_LINE,
                line="visible line",
                stream="stdout",
                iteration=1,
            )
        )
        assert "visible line" in console.export_text()

    def test_toggle_peek_twice_disables_rendering(self):
        emitter, console = _capture_emitter()
        emitter.toggle_peek()  # on
        assert emitter.toggle_peek() is False  # off
        emitter.emit(
            _make_event(
                EventType.AGENT_OUTPUT_LINE,
                line="should not appear",
                stream="stdout",
                iteration=1,
            )
        )
        assert "should not appear" not in console.export_text()

    def test_toggle_peek_prints_status_banner(self):
        emitter, console = _capture_emitter()
        emitter.toggle_peek()
        assert "peek on" in console.export_text()
        emitter.toggle_peek()
        assert "peek off" in console.export_text()

    def test_concurrent_peek_writes_do_not_interleave(self):
        """Two threads hammering ``_on_agent_output_line`` while peek is on
        must produce whole, un-interleaved lines — proving the console lock
        is serialising writes across threads.
        """
        emitter, console = _capture_emitter()
        emitter.toggle_peek()  # turn peek on (console.is_terminal is False
        # in record mode, so the default is off; we flip it explicitly).

        line_a = "A" * 50
        line_b = "B" * 50
        iterations = 20

        def worker(line: str) -> None:
            for _ in range(iterations):
                emitter._on_agent_output_line(
                    {"line": line, "stream": "stdout", "iteration": 1}
                )

        threads = [
            threading.Thread(target=worker, args=(line_a,)),
            threading.Thread(target=worker, args=(line_b,)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        output = console.export_text()
        # Each worker prints ``iterations`` whole copies of its line.  If the
        # lock is working, both substrings appear exactly that many times;
        # any interleaving would split one of them and drop the count.
        assert output.count(line_a) == iterations
        assert output.count(line_b) == iterations

    def test_peek_line_escapes_rich_markup(self):
        """Raw agent lines may contain ``[…]`` that Rich would treat as
        markup — escape so the literal text is preserved."""
        emitter, console = _capture_emitter()
        emitter.toggle_peek()
        emitter.emit(
            _make_event(
                EventType.AGENT_OUTPUT_LINE,
                line="[bold red]not markup[/]",
                stream="stdout",
                iteration=1,
            )
        )
        assert "[bold red]not markup[/]" in console.export_text()

    def test_run_started_shows_ralph_name(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="my-ralph",
                timeout=0,
                commands=0,
                max_iterations=None,
                delay=0,
            )
        )
        output = console.export_text()
        assert "my-ralph" in output
        assert "Running:" in output

    def test_run_started_shows_timeout(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=120,
                commands=0,
                max_iterations=None,
                delay=0,
            )
        )
        output = console.export_text()
        assert "2m 0s" in output

    def test_run_started_shows_command_count(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=0,
                commands=3,
                max_iterations=None,
                delay=0,
            )
        )
        output = console.export_text()
        assert "3 commands" in output

    def test_run_started_singular_command(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=0,
                commands=1,
                max_iterations=None,
                delay=0,
            )
        )
        output = console.export_text()
        assert "1 command" in output
        # Should not say "1 commands"
        assert "1 commands" not in output

    def test_run_started_shows_max_iterations(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=0,
                commands=0,
                max_iterations=5,
                delay=0,
            )
        )
        output = console.export_text()
        assert "max 5 iterations" in output

    def test_run_started_no_info_line_when_no_config(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=0,
                commands=0,
                max_iterations=None,
                delay=0,
            )
        )
        output = console.export_text()
        # Should still show the ralph name header
        assert "Running:" in output
        # But no info line with dots separator
        assert "·" not in output

    def test_run_started_combines_info(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STARTED,
                ralph_name="test",
                timeout=60,
                commands=2,
                max_iterations=3,
                delay=0,
            )
        )
        output = console.export_text()
        assert "timeout 1m 0s" in output
        assert "2 commands" in output
        assert "max 3 iterations" in output
        assert "·" in output


class TestIterationLifecycle:
    def test_iteration_started_prints_header(self):
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        emitter._stop_live()  # clean up the Live display started by the handler
        output = console.export_text()
        assert "Iteration 1" in output

    @pytest.mark.parametrize(
        "event_type,detail,expected",
        [
            (EventType.ITERATION_COMPLETED, "completed (5s)", "completed (5s)"),
            (
                EventType.ITERATION_FAILED,
                "failed with exit code 1 (3s)",
                "failed with exit code 1",
            ),
            (EventType.ITERATION_TIMED_OUT, "timed out after 2m 0s", "timed out"),
        ],
    )
    def test_iteration_ended_shows_detail(self, event_type, detail, expected):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                event_type,
                iteration=1,
                detail=detail,
                log_file=None,
                result_text=None,
            )
        )
        output = console.export_text()
        assert expected in output

    def test_iteration_ended_shows_log_file(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file="/tmp/log.txt",
                result_text=None,
            )
        )
        output = console.export_text()
        assert "/tmp/log.txt" in output

    def test_log_file_with_brackets_not_corrupted(self):
        """Log file paths containing bracket patterns must not be
        swallowed by Rich markup interpretation."""
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file="/tmp/[2024-01-01]/001.log",
                result_text=None,
            )
        )
        output = console.export_text()
        assert "[2024-01-01]" in output

    def test_iteration_ended_shows_result_text(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text="All tests passed",
            )
        )
        output = console.export_text()
        assert "All tests passed" in output

    def test_result_text_renders_markdown(self):
        """Agent result text should be rendered as markdown, preserving
        structure like headers and lists."""
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text="# Summary\n\n- Item one\n- Item two",
            )
        )
        output = console.export_text()
        assert "Summary" in output
        assert "Item one" in output
        assert "Item two" in output


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
        emitter.emit(
            _make_event(EventType.LOG_MESSAGE, message="Waiting 5s...", level="info")
        )
        output = console.export_text()
        assert "Waiting 5s..." in output

    def test_error_message(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(EventType.LOG_MESSAGE, message="Run crashed", level="error")
        )
        output = console.export_text()
        assert "Run crashed" in output

    def test_error_with_traceback(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.LOG_MESSAGE,
                message="Run crashed",
                level="error",
                traceback="Traceback:\n  File ...",
            )
        )
        output = console.export_text()
        assert "Traceback:" in output

    def test_error_message_with_brackets_not_corrupted(self):
        """Error messages containing bracket patterns must not be
        swallowed by Rich markup interpretation."""
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.LOG_MESSAGE,
                message="Run crashed: KeyError('[bold]')",
                level="error",
            )
        )
        output = console.export_text()
        assert "[bold]" in output

    def test_info_message_with_brackets_not_corrupted(self):
        """Info messages containing bracket patterns must not be
        swallowed by Rich markup interpretation."""
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.LOG_MESSAGE,
                message="Processing [section] data",
                level="info",
            )
        )
        output = console.export_text()
        assert "[section]" in output

    def test_traceback_with_brackets_not_corrupted(self):
        """Traceback text containing bracket patterns must not be
        swallowed by Rich markup interpretation."""
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.LOG_MESSAGE,
                message="Run crashed",
                level="error",
                traceback="KeyError: '[red]missing[/red]'",
            )
        )
        output = console.export_text()
        assert "[red]missing[/red]" in output


class TestRunStopped:
    def test_completed_shows_summary(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=5,
                completed=4,
                failed=1,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        assert "5 iterations" in output
        assert "4 succeeded" in output
        assert "1 failed" in output

    def test_completed_shows_separator(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=3,
                completed=3,
                failed=0,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        assert "──" in output

    def test_completed_with_timeouts(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=3,
                completed=2,
                failed=1,
                timed_out_count=1,
            )
        )
        output = console.export_text()
        assert "1 timed out" in output
        # timed_out_count is subset of failed — only non-timeout failures shown as "failed"
        assert "failed" not in output

    def test_completed_with_mixed_failures_and_timeouts(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=5,
                completed=3,
                failed=2,
                timed_out_count=1,
            )
        )
        output = console.export_text()
        assert "3 succeeded" in output
        assert "1 failed" in output
        assert "1 timed out" in output

    def test_non_completed_reason_skips_summary(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="user_requested",
                total=2,
                completed=1,
                failed=0,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        # Non-completed runs don't print the summary line
        assert "Done:" not in output

    def test_run_stopped_stops_active_live_display(self):
        emitter, console = _capture_emitter()
        # Start a live display via iteration_started, then stop via run_stopped
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        assert emitter._live is not None
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="user_requested",
                total=1,
                completed=0,
                failed=0,
                timed_out_count=0,
            )
        )
        assert emitter._live is None

    def test_completed_all_succeeded(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=3,
                completed=3,
                failed=0,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        assert "3 succeeded" in output
        assert "failed" not in output
        assert "timed out" not in output

    def test_completed_singular_iteration(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=1,
                completed=1,
                failed=0,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        assert "1 iteration" in output
        assert "1 iterations" not in output

    def test_completed_plural_iterations(self):
        emitter, console = _capture_emitter()
        emitter.emit(
            _make_event(
                EventType.RUN_STOPPED,
                reason="completed",
                total=3,
                completed=3,
                failed=0,
                timed_out_count=0,
            )
        )
        output = console.export_text()
        assert "3 iterations" in output


class TestFormatSummary:
    def test_all_succeeded(self):
        assert _format_summary(3, 3, 0, 0) == "3 iterations — 3 succeeded"

    def test_singular_iteration(self):
        assert _format_summary(1, 1, 0, 0) == "1 iteration — 1 succeeded"

    def test_with_failures(self):
        result = _format_summary(5, 4, 1, 0)
        assert "4 succeeded" in result
        assert "1 failed" in result
        assert "timed out" not in result

    def test_with_timeouts_only(self):
        result = _format_summary(3, 2, 1, 1)
        assert "2 succeeded" in result
        assert "1 timed out" in result
        # timed_out_count is subset of failed — no separate "failed" category
        assert "failed" not in result

    def test_with_mixed_failures_and_timeouts(self):
        result = _format_summary(5, 3, 2, 1)
        assert "3 succeeded" in result
        assert "1 failed" in result
        assert "1 timed out" in result

    def test_all_failed(self):
        result = _format_summary(3, 0, 3, 0)
        assert "0 succeeded" in result
        assert "3 failed" in result


class TestFormatRunInfo:
    def test_empty_when_no_config(self):
        assert _format_run_info(timeout=0, command_count=0, max_iterations=None) == ""
        assert (
            _format_run_info(timeout=None, command_count=0, max_iterations=None) == ""
        )

    def test_timeout_only(self):
        result = _format_run_info(timeout=120, command_count=0, max_iterations=None)
        assert result == "timeout 2m 0s"

    def test_commands_only(self):
        assert (
            _format_run_info(timeout=0, command_count=3, max_iterations=None)
            == "3 commands"
        )

    def test_singular_command(self):
        assert (
            _format_run_info(timeout=0, command_count=1, max_iterations=None)
            == "1 command"
        )

    def test_max_iterations_only(self):
        assert (
            _format_run_info(timeout=0, command_count=0, max_iterations=5)
            == "max 5 iterations"
        )

    def test_singular_iteration(self):
        assert (
            _format_run_info(timeout=0, command_count=0, max_iterations=1)
            == "max 1 iteration"
        )

    def test_all_fields(self):
        result = _format_run_info(timeout=60, command_count=2, max_iterations=3)
        assert "timeout 1m 0s" in result
        assert "2 commands" in result
        assert "max 3 iterations" in result
        assert " · " in result

    def test_zero_timeout_excluded(self):
        result = _format_run_info(timeout=0, command_count=2, max_iterations=None)
        assert "timeout" not in result

    def test_negative_timeout_excluded(self):
        result = _format_run_info(timeout=-1, command_count=2, max_iterations=None)
        assert "timeout" not in result


class TestEchoOutput:
    def test_echo_does_not_tear_live_spinner(self):
        """Echo output routed through the iteration-ended event must not
        interleave with Rich Live spinner frames — Live is stopped first."""
        emitter, console = _capture_emitter()
        # Start Live via iteration start
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        assert emitter._live is not None
        # End iteration with echo data (simulates peek-off + log-dir)
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text=None,
                echo_stdout="line one\nline two\nline three\n",
                echo_stderr=None,
            )
        )
        assert emitter._live is None
        output = console.export_text()
        assert "line one" in output
        assert "line two" in output
        assert "line three" in output
        # Echo text and status line should both appear cleanly
        assert "completed (1s)" in output
        # No Rich Live spinner frame characters interleaved in the echoed text
        for char in ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"):
            for line in output.splitlines():
                if "line one" in line or "line two" in line or "line three" in line:
                    assert char not in line

    def test_echo_not_shown_when_absent(self):
        """When no echo data is present, only the status line appears."""
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text=None,
            )
        )
        output = console.export_text()
        assert "completed (1s)" in output

    def test_echo_stderr_rendered(self):
        """stderr echo output is rendered when present."""
        emitter, console = _capture_emitter()
        emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text=None,
                echo_stdout=None,
                echo_stderr="warning: something\n",
            )
        )
        output = console.export_text()
        assert "warning: something" in output


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
        emitter.emit(
            _make_event(
                EventType.ITERATION_COMPLETED,
                iteration=1,
                detail="completed (1s)",
                log_file=None,
                result_text=None,
            )
        )
        assert emitter._live is None
