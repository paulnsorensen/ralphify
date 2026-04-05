"""Rich console renderer for run-loop events.

The ``ConsoleEmitter`` translates structured :class:`Event` objects into
Rich-formatted terminal output.
"""

from __future__ import annotations

import sys
import threading
import time
from collections.abc import Callable
from functools import partial

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.markdown import Markdown
from rich.markup import escape as escape_markup
from rich.spinner import Spinner
from rich.text import Text

from ralphify._events import (
    LOG_ERROR,
    STOP_COMPLETED,
    AgentOutputLineData,
    CommandsCompletedData,
    Event,
    EventType,
    IterationEndedData,
    IterationStartedData,
    LogMessageData,
    RunStartedData,
    RunStoppedData,
)
from ralphify import _brand
from ralphify._output import format_duration

_ICON_SUCCESS = "✓"
_ICON_FAILURE = "✗"
_ICON_TIMEOUT = "⏱"
_ICON_ARROW = "→"
_ICON_DASH = "—"

_LIVE_REFRESH_RATE = 4  # Hz — how often the spinner redraws

# The key that toggles live peek of agent output.  Used here for status
# messages and imported by cli.py for the keypress handler.
PEEK_TOGGLE_KEY = "p"

# Peek status messages shown when peek is toggled or at run startup.
_PEEK_ON_MSG = f"[dim]peek on — press {PEEK_TOGGLE_KEY} to toggle[/]"
_PEEK_OFF_MSG = f"[dim]peek off — press {PEEK_TOGGLE_KEY} to toggle[/]"


def _plural(count: int, word: str) -> str:
    """Return *count* followed by *word*, pluralised when count is not 1."""
    return f"{count} {word}{'s' if count != 1 else ''}"


def _format_summary(
    total: int, completed: int, failed: int, timed_out_count: int
) -> str:
    """Build a plain-text run summary string from iteration counters.

    ``timed_out_count`` is a subset of ``failed`` — non-timeout failures
    and timeouts are shown as separate categories for clarity.
    """
    non_timeout_failures = failed - timed_out_count
    parts = [f"{completed} succeeded"]
    if non_timeout_failures:
        parts.append(f"{non_timeout_failures} failed")
    if timed_out_count:
        parts.append(f"{timed_out_count} timed out")
    detail = ", ".join(parts)
    return f"{_plural(total, 'iteration')} {_ICON_DASH} {detail}"


def _format_run_info(
    timeout: float | None, command_count: int, max_iterations: int | None
) -> str:
    """Build a plain-text run info string from configuration values.

    Returns an empty string when no information is available.  Used by
    :meth:`ConsoleEmitter._on_run_started` to show the config summary
    beneath the "Running:" header.
    """
    parts: list[str] = []
    if timeout is not None and timeout > 0:
        parts.append(f"timeout {format_duration(timeout)}")
    if command_count > 0:
        parts.append(_plural(command_count, "command"))
    if max_iterations is not None:
        parts.append(f"max {_plural(max_iterations, 'iteration')}")
    return " · ".join(parts)


class _IterationSpinner:
    """Rich renderable that shows a spinner with elapsed time."""

    def __init__(self) -> None:
        self._spinner = Spinner("dots")
        self._start = time.monotonic()

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        elapsed = time.monotonic() - self._start
        text = Text(f" {format_duration(elapsed)}", style="dim")
        yield self._spinner
        yield text


def _interactive_default_peek(console: Console) -> bool:
    """Return True when live peek should be on by default.

    Peek is only useful when both (a) the console is attached to a real
    terminal (so the user can see the extra lines) and (b) stdin is a TTY
    (so the keypress listener is actually active and the user can turn
    peek back off).  Recording consoles used in tests fail check (a).
    """
    if not console.is_terminal:
        return False
    try:
        return sys.stdin.isatty()
    except (ValueError, OSError):
        return False


class ConsoleEmitter:
    """Renders engine events to the Rich console."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._live: Live | None = None
        self._peek_enabled = _interactive_default_peek(console)
        # Single lock that serialises every ``_console.print`` call and
        # protects ``_peek_enabled`` mutations so that reader-thread /
        # keypress-thread writes cannot interleave with main-thread event
        # handlers while a Rich ``Live`` region is active.
        self._console_lock = threading.Lock()
        self._handlers: dict[EventType, Callable[..., None]] = {
            EventType.RUN_STARTED: self._on_run_started,
            EventType.ITERATION_STARTED: self._on_iteration_started,
            EventType.ITERATION_COMPLETED: partial(
                self._on_iteration_ended, color="green", icon=_ICON_SUCCESS
            ),
            EventType.ITERATION_FAILED: partial(
                self._on_iteration_ended, color="red", icon=_ICON_FAILURE
            ),
            EventType.ITERATION_TIMED_OUT: partial(
                self._on_iteration_ended, color="yellow", icon=_ICON_TIMEOUT
            ),
            EventType.COMMANDS_COMPLETED: self._on_commands_completed,
            EventType.LOG_MESSAGE: self._on_log_message,
            EventType.RUN_STOPPED: self._on_run_stopped,
            EventType.AGENT_OUTPUT_LINE: self._on_agent_output_line,
        }

    def wants_agent_output_lines(self) -> bool:
        return self._peek_enabled

    def toggle_peek(self) -> bool:
        """Flip live-output rendering on or off.

        Safe to call from a non-main thread (e.g. the keypress listener).
        Returns the new peek state.  A short status banner is printed so
        the user gets visible feedback that the toggle took effect.
        """
        with self._console_lock:
            self._peek_enabled = not self._peek_enabled
            enabled = self._peek_enabled
            self._console.print(_PEEK_ON_MSG if enabled else _PEEK_OFF_MSG)
        return enabled

    def _on_agent_output_line(self, data: AgentOutputLineData) -> None:
        with self._console_lock:
            if not self._peek_enabled:
                return
            line = escape_markup(data["line"])
            self._console.print(f"[dim]{line}[/]")

    def emit(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler is not None:
            handler(event.data)

    def _on_run_started(self, data: RunStartedData) -> None:
        ralph_name = data["ralph_name"]
        with self._console_lock:
            self._console.print(
                f"\n[bold {_brand.PURPLE}]▶ Running:[/] [bold]{escape_markup(ralph_name)}[/]"
            )
            info = _format_run_info(
                data["timeout"], data["commands"], data["max_iterations"]
            )
            if info:
                self._console.print(f"  [dim]{info}[/]")
            if self._peek_enabled:
                self._console.print(_PEEK_ON_MSG)

    def _start_live_unlocked(self) -> None:
        """Start the iteration spinner.  Caller must hold ``_console_lock``."""
        spinner = _IterationSpinner()
        self._live = Live(
            spinner,
            console=self._console,
            transient=True,
            refresh_per_second=_LIVE_REFRESH_RATE,
        )
        self._live.start()

    def _stop_live_unlocked(self) -> None:
        """Stop the iteration spinner.  Caller must hold ``_console_lock``."""
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _stop_live(self) -> None:
        with self._console_lock:
            self._stop_live_unlocked()

    def _on_iteration_started(self, data: IterationStartedData) -> None:
        iteration = data["iteration"]
        with self._console_lock:
            self._console.print(f"\n[bold {_brand.BLUE}]── Iteration {iteration} ──[/]")
            self._start_live_unlocked()

    def _echo_stream(self, text: str | None) -> None:
        """Print captured stream output, ensuring a trailing newline.

        Caller must hold ``_console_lock``.  No-ops when *text* is falsy.
        """
        if text:
            self._console.print(Text(text), end="")
            if not text.endswith("\n"):
                self._console.print()

    def _on_iteration_ended(
        self, data: IterationEndedData, color: str, icon: str
    ) -> None:
        iteration = data["iteration"]
        detail = data["detail"]
        log_file = data["log_file"]
        result_text = data["result_text"]
        with self._console_lock:
            self._stop_live_unlocked()
            # Echo captured output before the status line — Live is already
            # stopped so this cannot tear the spinner.  Only present when
            # peek was off and logging captured the output.
            self._echo_stream(data.get("echo_stdout"))
            self._echo_stream(data.get("echo_stderr"))
            self._console.print(f"[{color}]{icon} Iteration {iteration} {detail}[/]")
            if log_file:
                self._console.print(
                    f"  [dim]{_ICON_ARROW} {escape_markup(log_file)}[/]"
                )
            if result_text:
                self._console.print(Markdown(result_text))

    def _on_commands_completed(self, data: CommandsCompletedData) -> None:
        count = data["count"]
        if count:
            with self._console_lock:
                self._console.print(f"  [bold]Commands:[/] {count} ran")

    def _on_log_message(self, data: LogMessageData) -> None:
        msg = escape_markup(data["message"])
        level = data["level"]
        with self._console_lock:
            if level == LOG_ERROR:
                self._console.print(f"[red]{msg}[/]")
                tb = data.get("traceback")
                if tb:
                    self._console.print(f"[dim]{escape_markup(tb)}[/]")
            else:
                self._console.print(f"[dim]{msg}[/]")

    def _on_run_stopped(self, data: RunStoppedData) -> None:
        with self._console_lock:
            self._stop_live_unlocked()
            if data["reason"] != STOP_COMPLETED:
                return

            summary = _format_summary(
                data["total"], data["completed"], data["failed"], data["timed_out_count"]
            )
            self._console.print(f"\n[bold {_brand.BLUE}]──────────────────────[/]")
            self._console.print(f"[bold {_brand.GREEN}]Done:[/] {summary}")
