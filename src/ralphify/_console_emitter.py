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
        self._rprint = console.print
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
        timeout = data.get("timeout")
        if timeout is not None and timeout > 0:
            self._rprint(f"[dim]Timeout: {format_duration(timeout)} per iteration[/dim]")
        command_count = data.get("commands")
        if command_count is not None and command_count > 0:
            self._rprint(f"[dim]Commands: {command_count} configured[/dim]")

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
        self._rprint(f"\n[bold blue]── Iteration {data['iteration']} ──[/bold blue]")
        self._start_live()

    def _on_iteration_ended(self, data: dict, color: str, icon: str) -> None:
        self._stop_live()
        status_msg = f"[{color}]{icon} Iteration {data['iteration']} {data['detail']}"
        if data.get("log_file"):
            status_msg += f" {_ICON_ARROW}\n{data['log_file']}"
        status_msg += f"[/{color}]"
        self._rprint(status_msg)
        if data.get("result_text"):
            self._rprint(f"  [dim]{data['result_text']}[/dim]")

    def _on_commands_completed(self, data: dict) -> None:
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)
        if passed or failed:
            parts = []
            if passed:
                parts.append(f"{passed} passed")
            if failed:
                parts.append(f"{failed} failed")
            self._rprint(f"  [bold]Commands:[/bold] {', '.join(parts)}")

    def _on_log_message(self, data: dict) -> None:
        msg = data.get("message", "")
        level = data.get("level", "info")
        if level == "error":
            self._rprint(f"[red]{msg}[/red]")
            tb = data.get("traceback")
            if tb:
                self._rprint(f"[dim]{tb}[/dim]")
        else:
            self._rprint(f"[dim]{msg}[/dim]")

    def _on_run_stopped(self, data: dict) -> None:
        self._stop_live()
        if data.get("reason") != REASON_COMPLETED:
            return

        total = data.get("total", 0)
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        timed_out_count = data.get("timed_out", 0)

        parts = [f"{completed} succeeded"]
        if failed:
            parts.append(f"{failed} failed")
        detail = ", ".join(parts)
        if timed_out_count:
            detail += f" ({timed_out_count} timed out)"
        self._rprint(f"\n[green]Done: {total} iteration(s) {_ICON_DASH} {detail}[/green]")
