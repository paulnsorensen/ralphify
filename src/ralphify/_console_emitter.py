"""Rich console renderer for run-loop events.

The ``ConsoleEmitter`` translates structured :class:`Event` objects into
Rich-formatted terminal output.
"""

from __future__ import annotations

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
    CommandsCompletedData,
    Event,
    EventType,
    IterationEndedData,
    IterationStartedData,
    LogMessageData,
    RunStartedData,
    RunStoppedData,
)
from ralphify._output import format_duration

_ICON_SUCCESS = "✓"
_ICON_FAILURE = "✗"
_ICON_TIMEOUT = "⏱"
_ICON_ARROW = "→"
_ICON_DASH = "—"

_LIVE_REFRESH_RATE = 4  # Hz — how often the spinner redraws


class _IterationSpinner:
    """Rich renderable that shows a spinner with elapsed time."""

    def __init__(self) -> None:
        self._spinner = Spinner("dots")
        self._start = time.monotonic()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        elapsed = time.monotonic() - self._start
        text = Text(f" {format_duration(elapsed)}", style="dim")
        yield self._spinner
        yield text


class ConsoleEmitter:
    """Renders engine events to the Rich console."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._live: Live | None = None
        self._handlers: dict[EventType, Callable[..., None]] = {
            EventType.RUN_STARTED: self._on_run_started,
            EventType.ITERATION_STARTED: self._on_iteration_started,
            EventType.ITERATION_COMPLETED: partial(self._on_iteration_ended, color="green", icon=_ICON_SUCCESS),
            EventType.ITERATION_FAILED: partial(self._on_iteration_ended, color="red", icon=_ICON_FAILURE),
            EventType.ITERATION_TIMED_OUT: partial(self._on_iteration_ended, color="yellow", icon=_ICON_TIMEOUT),
            EventType.COMMANDS_COMPLETED: self._on_commands_completed,
            EventType.LOG_MESSAGE: self._on_log_message,
            EventType.RUN_STOPPED: self._on_run_stopped,
        }

    def emit(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler is not None:
            handler(event.data)

    def _on_run_started(self, data: RunStartedData) -> None:
        ralph_name = data["ralph_name"]
        self._console.print(f"\n[bold #A78BF5]▶ Running:[/bold #A78BF5] [bold]{escape_markup(ralph_name)}[/bold]")

        info_parts: list[str] = []
        timeout = data["timeout"]
        if timeout is not None and timeout > 0:
            info_parts.append(f"timeout {format_duration(timeout)}")
        command_count = data["commands"]
        if command_count > 0:
            info_parts.append(f"{command_count} command{'s' if command_count != 1 else ''}")
        max_iter = data.get("max_iterations")
        if max_iter is not None:
            info_parts.append(f"max {max_iter} iteration{'s' if max_iter != 1 else ''}")
        if info_parts:
            self._console.print(f"  [dim]{' · '.join(info_parts)}[/dim]")

    def _start_live(self) -> None:
        spinner = _IterationSpinner()
        self._live = Live(
            spinner,
            console=self._console,
            transient=True,
            refresh_per_second=_LIVE_REFRESH_RATE,
        )
        self._live.start()

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _on_iteration_started(self, data: IterationStartedData) -> None:
        iteration = data["iteration"]
        self._console.print(f"\n[bold blue]── Iteration {iteration} ──[/bold blue]")
        self._start_live()

    def _on_iteration_ended(self, data: IterationEndedData, color: str, icon: str) -> None:
        self._stop_live()
        iteration = data["iteration"]
        detail = data["detail"]
        self._console.print(f"[{color}]{icon} Iteration {iteration} {detail}[/{color}]")
        log_file = data["log_file"]
        if log_file:
            self._console.print(f"  [dim]{_ICON_ARROW} {escape_markup(log_file)}[/dim]")
        result_text = data["result_text"]
        if result_text:
            self._console.print(Markdown(result_text))

    def _on_commands_completed(self, data: CommandsCompletedData) -> None:
        count = data["count"]
        if count:
            self._console.print(f"  [bold]Commands:[/bold] {count} ran")

    def _on_log_message(self, data: LogMessageData) -> None:
        msg = escape_markup(data["message"])
        level = data["level"]
        if level == LOG_ERROR:
            self._console.print(f"[red]{msg}[/red]")
            tb = data.get("traceback")
            if tb:
                self._console.print(f"[dim]{escape_markup(tb)}[/dim]")
        else:
            self._console.print(f"[dim]{msg}[/dim]")

    def _on_run_stopped(self, data: RunStoppedData) -> None:
        self._stop_live()
        if data["reason"] != STOP_COMPLETED:
            return

        total = data["total"]
        completed = data["completed"]
        failed = data["failed"]
        timed_out_count = data["timed_out_count"]

        # timed_out_count is a subset of failed — show non-timeout failures
        # and timeouts as separate categories for clarity.
        non_timeout_failures = failed - timed_out_count
        parts = [f"{completed} succeeded"]
        if non_timeout_failures:
            parts.append(f"{non_timeout_failures} failed")
        if timed_out_count:
            parts.append(f"{timed_out_count} timed out")
        detail = ", ".join(parts)
        self._console.print(f"\n[bold blue]──────────────────────[/bold blue]")
        self._console.print(f"[bold green]Done:[/bold green] {total} iteration{'s' if total != 1 else ''} {_ICON_DASH} {detail}")
