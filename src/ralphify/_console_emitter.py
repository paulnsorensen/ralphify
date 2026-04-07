"""Rich console renderer for run-loop events.

The ``ConsoleEmitter`` translates structured :class:`Event` objects into
Rich-formatted terminal output.
"""

from __future__ import annotations

import shlex
import sys
import threading
import time
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.markup import escape as escape_markup
from rich.spinner import Spinner
from rich.text import Text

from ralphify._events import (
    LOG_ERROR,
    STOP_COMPLETED,
    AgentActivityData,
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
_ICON_PLAY = "▶"

# Horizontal rules used to visually bracket iteration and run sections.
_RULE_THIN = "──"
_RULE_HEAVY = "──────────────────────"

_LIVE_REFRESH_RATE = 4  # Hz — how often the spinner redraws

# The key that toggles live peek of agent output.  Used here for status
# messages and imported by cli.py for the keypress handler.
PEEK_TOGGLE_KEY = "p"

# Peek status messages shown when peek is toggled or at run startup.
_PEEK_ON_MSG_STRUCTURED = f"[dim]live activity on — press {PEEK_TOGGLE_KEY} to hide[/]"
_PEEK_ON_MSG_RAW = f"[dim]live output on — press {PEEK_TOGGLE_KEY} to hide[/]"
_PEEK_OFF_MSG = f"[dim]peek off — press {PEEK_TOGGLE_KEY} to toggle[/]"

# ── Claude binary detection ───────────────────────────────────────────

_CLAUDE_BINARY = "claude"


def _is_claude_command(agent: str) -> bool:
    """Return True if *agent* is a Claude Code command."""
    try:
        parts = shlex.split(agent)
    except ValueError:
        return False
    if not parts:
        return False
    return Path(parts[0]).stem == _CLAUDE_BINARY


# ── Tool argument abbreviation ────────────────────────────────────────


def _truncate(text: str, maxlen: int = 60) -> str:
    if len(text) <= maxlen:
        return text
    return text[:maxlen] + "…"


_TOOL_ARG_EXTRACTORS: dict[str, Callable[[dict[str, Any]], str]] = {
    "Read": lambda i: i.get("file_path", ""),
    "Write": lambda i: i.get("file_path", ""),
    "Edit": lambda i: i.get("file_path", ""),
    "Glob": lambda i: i.get("pattern", ""),
    "Grep": lambda i: i.get("pattern", ""),
    "Bash": lambda i: _truncate(i.get("command", ""), 60),
    "Task": lambda i: _truncate(i.get("description", i.get("prompt", "")), 60),
    "WebFetch": lambda i: i.get("url", ""),
    "WebSearch": lambda i: i.get("query", ""),
    "TodoWrite": lambda i: f"{len(i.get('todos', []))} todos",
}


def _format_tool_summary(name: str, tool_input: dict[str, Any]) -> str:
    """Return a compact one-liner describing a tool call."""
    extractor = _TOOL_ARG_EXTRACTORS.get(name)
    if extractor is not None:
        arg = extractor(tool_input)
    else:
        arg = ", ".join(sorted(tool_input.keys()))
    if arg:
        return f"{name}  {arg}"
    return name


# ── Helpers ───────────────────────────────────────────────────────────


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


# ── Iteration panel ──────────────────────────────────────────────────

_TOOL_CATEGORY_LABELS: dict[str, str] = {
    "Read": "read",
    "Write": "write",
    "Edit": "edit",
    "Bash": "bash",
    "Glob": "glob",
    "Grep": "grep",
    "WebFetch": "web",
    "WebSearch": "web",
}


class _IterationPanel:
    """Rich renderable that shows spinner, elapsed time, and activity counters."""

    def __init__(self) -> None:
        self._spinner = Spinner("dots")
        self._start = time.monotonic()
        # Mutable state set by apply() — renders at the Live refresh rate.
        self._status: str = ""
        self._model: str = ""
        self._tool_count: int = 0
        self._tool_categories: dict[str, int] = {}
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._cache_read_tokens: int = 0

    def apply(self, raw: dict[str, Any]) -> str | None:
        """Update panel state from a parsed stream-json dict.

        Returns a string to print above the Live region (scroll log), or
        ``None`` when no scroll output is needed.
        """
        event_type = raw.get("type")

        if event_type == "system" and raw.get("subtype") == "init":
            self._model = raw.get("model", "")
            return None

        if event_type == "assistant":
            return self._apply_assistant(raw)

        if event_type == "user":
            return self._apply_user(raw)

        if event_type == "rate_limit_event":
            info = raw.get("rate_limit_info", {})
            status = info.get("status", "")
            resets = info.get("resetsAt", "")
            return f"[dim]⏱ rate limit: {escape_markup(str(status))}, resets {escape_markup(str(resets))}[/]"

        # Unknown type — silent drop
        return None

    def _apply_assistant(self, raw: dict[str, Any]) -> str | None:
        msg = raw.get("message", {})

        # Update token counts from usage
        usage = msg.get("usage")
        if isinstance(usage, dict):
            self._input_tokens = usage.get("input_tokens", self._input_tokens)
            self._output_tokens = usage.get("output_tokens", self._output_tokens)
            self._cache_read_tokens = usage.get(
                "cache_read_input_tokens", self._cache_read_tokens
            )

        content = msg.get("content", [])
        if not isinstance(content, list):
            return None

        scroll_line: str | None = None
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")

            if block_type == "thinking":
                self._status = "💭 thinking…"

            elif block_type == "text":
                text = block.get("text", "")
                preview = _truncate(text.replace("\n", " "), 80)
                if preview:
                    scroll_line = f'[dim]💬 "{escape_markup(preview)}"[/]'
                self._status = ""

            elif block_type == "tool_use":
                name = block.get("name", "?")
                tool_input = block.get("input", {})
                if not isinstance(tool_input, dict):
                    tool_input = {}

                self._tool_count += 1
                cat = _TOOL_CATEGORY_LABELS.get(name, "other")
                self._tool_categories[cat] = self._tool_categories.get(cat, 0) + 1

                summary = _format_tool_summary(name, tool_input)
                self._status = f"→ {summary}"
                scroll_line = f"[dim]🔧 {escape_markup(summary)}[/]"

        return scroll_line

    def _apply_user(self, raw: dict[str, Any]) -> str | None:
        msg = raw.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            return None
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result" and block.get("is_error"):
                snippet = _truncate(str(block.get("content", "")), 80)
                return f"[dim red]✗ tool error: {escape_markup(snippet)}[/]"
        return None

    def _format_tokens(self) -> str:
        """Format token counts as compact ↑in ↓out string."""
        parts: list[str] = []
        total_in = self._input_tokens
        if total_in > 0:
            parts.append(f"↑{self._format_count(total_in)}")
        if self._output_tokens > 0:
            parts.append(f"↓{self._format_count(self._output_tokens)}")
        return " ".join(parts)

    @staticmethod
    def _format_count(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            # Use rounded value to avoid "1000.0k" when rounding crosses
            # into the next unit (same guard as format_duration's 59.95→1m).
            if round(n / 1_000, 1) >= 1_000:
                return f"{n / 1_000_000:.1f}M"
            return f"{n / 1_000:.1f}k"
        return str(n)

    def _format_categories(self) -> str:
        if not self._tool_categories:
            return ""
        parts = [f"{v} {k}" for k, v in self._tool_categories.items()]
        return " · ".join(parts)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        elapsed = time.monotonic() - self._start
        # Line 1: spinner + elapsed + tokens
        tokens = self._format_tokens()
        header_parts = [f" {format_duration(elapsed)}"]
        if tokens:
            header_parts.append(tokens)
        header = " · ".join(header_parts)
        yield self._spinner
        yield Text(header, style="dim")

        # Line 2: current status (tool in progress, thinking, etc.)
        if self._status:
            yield Text(f"\n    {self._status}", style="dim")

        # Line 3: tool count + categories
        if self._tool_count > 0:
            cats = self._format_categories()
            line3 = f"\n    {self._tool_count} tools"
            if cats:
                line3 += f" · {cats}"
            yield Text(line3, style="dim")

        # Line 4: model
        if self._model:
            yield Text(f"\n    model: {self._model}", style="dim")


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
        self._structured_agent: bool = False
        self._peek_broken: bool = False
        self._iteration_panel: _IterationPanel | None = None
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
            EventType.AGENT_ACTIVITY: self._on_agent_activity,
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
            if enabled:
                msg = (
                    _PEEK_ON_MSG_STRUCTURED
                    if self._structured_agent
                    else _PEEK_ON_MSG_RAW
                )
            else:
                msg = _PEEK_OFF_MSG
            self._console.print(msg)
        return enabled

    def _on_agent_output_line(self, data: AgentOutputLineData) -> None:
        with self._console_lock:
            if not self._peek_enabled:
                return
            # When we have structured rendering, raw lines are redundant noise.
            if self._structured_agent:
                return
            line = escape_markup(data["line"])
            self._console.print(f"[dim]{line}[/]")

    def _on_agent_activity(self, data: AgentActivityData) -> None:
        """Handle structured agent activity events (Claude stream-json).

        Peek is best-effort — a failure here must never kill the run loop.
        """
        if not self._structured_agent:
            return

        with self._console_lock:
            if not self._peek_enabled:
                return
            if self._peek_broken:
                return

            try:
                panel = self._iteration_panel
                if panel is None:
                    return
                scroll_line = panel.apply(data["raw"])
                if scroll_line is not None:
                    self._console.print(scroll_line)
                # Update the Live renderable so it reflects new counters
                if self._live is not None:
                    self._live.update(panel)
            except Exception:
                self._peek_broken = True
                self._console.print(
                    "[dim]peek: live activity unavailable (continuing)[/]"
                )

    def emit(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler is not None:
            handler(event.data)

    def _on_run_started(self, data: RunStartedData) -> None:
        ralph_name = data["ralph_name"]
        agent = data.get("agent", "")
        self._structured_agent = _is_claude_command(agent)
        with self._console_lock:
            self._console.print(
                f"\n[bold {_brand.PURPLE}]{_ICON_PLAY} Running:[/] [bold]{escape_markup(ralph_name)}[/]"
            )
            info = _format_run_info(
                data["timeout"], data["commands"], data["max_iterations"]
            )
            if info:
                self._console.print(f"  [dim]{info}[/]")
            if self._peek_enabled:
                msg = (
                    _PEEK_ON_MSG_STRUCTURED
                    if self._structured_agent
                    else _PEEK_ON_MSG_RAW
                )
                self._console.print(msg)

    def _start_live_unlocked(self) -> None:
        """Start the iteration panel.  Caller must hold ``_console_lock``."""
        if self._structured_agent:
            panel = _IterationPanel()
            self._iteration_panel = panel
            renderable = panel
        else:
            renderable = _IterationSpinner()
            self._iteration_panel = None
        self._live = Live(
            renderable,
            console=self._console,
            transient=True,
            refresh_per_second=_LIVE_REFRESH_RATE,
        )
        self._live.start()

    def _stop_live_unlocked(self) -> None:
        """Stop the iteration panel/spinner.  Caller must hold ``_console_lock``."""
        if self._live is not None:
            self._live.stop()
            self._live = None
        self._iteration_panel = None

    def _stop_live(self) -> None:
        with self._console_lock:
            self._stop_live_unlocked()

    def _on_iteration_started(self, data: IterationStartedData) -> None:
        iteration = data["iteration"]
        with self._console_lock:
            self._peek_broken = False
            self._console.print(
                f"\n[bold {_brand.BLUE}]{_RULE_THIN} Iteration {iteration} {_RULE_THIN}[/]"
            )
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
                from rich.markdown import Markdown

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
                data["total"],
                data["completed"],
                data["failed"],
                data["timed_out_count"],
            )
            self._console.print(f"\n[bold {_brand.BLUE}]{_RULE_HEAVY}[/]")
            self._console.print(f"[bold {_brand.GREEN}]Done:[/] {summary}")


class _IterationSpinner:
    """Rich renderable that shows a spinner with elapsed time.

    Used for non-Claude agents that don't emit structured activity events.
    """

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
