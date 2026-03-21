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
from rich.spinner import Spinner
from rich.text import Text

from ralphify._events import Event, EventType
from ralphify._output import format_duration
from ralphify._run_types import REASON_COMPLETED

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
        self._handlers: dict[EventType, Callable[[dict], None]] = {
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

    def _on_run_started(self, data: dict) -> None:
        timeout = data.get("timeout") or 0
        if timeout > 0:
            self._console.print(f"[dim]Timeout: {format_duration(timeout)} per iteration[/dim]")
        command_count = data.get("commands", 0)
        if command_count > 0:
            self._console.print(f"[dim]Commands: {command_count} configured[/dim]")

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

    def _on_iteration_started(self, data: dict) -> None:
        iteration = data.get("iteration", "?")
        self._console.print(f"\n[bold blue]── Iteration {iteration} ──[/bold blue]")
        self._start_live()

    def _on_iteration_ended(self, data: dict, color: str, icon: str) -> None:
        self._stop_live()
        iteration = data.get("iteration", "?")
        detail = data.get("detail", "")
        status_msg = f"[{color}]{icon} Iteration {iteration} {detail}"
        log_file = data.get("log_file")
        if log_file:
            status_msg += f" {_ICON_ARROW}\n{log_file}"
        status_msg += f"[/{color}]"
        self._console.print(status_msg)
        result_text = data.get("result_text")
        if result_text:
            self._console.print(f"  [dim]{result_text}[/dim]")

    def _on_commands_completed(self, data: dict) -> None:
        count = data.get("count", 0)
        if count:
            self._console.print(f"  [bold]Commands:[/bold] {count} ran")

    def _on_log_message(self, data: dict) -> None:
        msg = data.get("message", "")
        level = data.get("level", "info")
        if level == "error":
            self._console.print(f"[red]{msg}[/red]")
            tb = data.get("traceback")
            if tb:
                self._console.print(f"[dim]{tb}[/dim]")
        else:
            self._console.print(f"[dim]{msg}[/dim]")

    def _on_run_stopped(self, data: dict) -> None:
        self._stop_live()
        if data.get("reason") != REASON_COMPLETED:
            return

        total = data.get("total", 0)
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        timed_out_count = data.get("timed_out", 0)

        # timed_out is a subset of failed — show non-timeout failures
        # and timeouts as separate categories for clarity.
        errored = failed - timed_out_count
        parts = [f"{completed} succeeded"]
        if errored:
            parts.append(f"{errored} failed")
        if timed_out_count:
            parts.append(f"{timed_out_count} timed out")
        detail = ", ".join(parts)
        self._console.print(f"\n[green]Done: {total} iteration(s) {_ICON_DASH} {detail}[/green]")
