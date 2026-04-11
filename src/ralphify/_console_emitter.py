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

from rich import box
from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.live import Live
from rich.markup import escape as escape_markup
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.table import Table
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

# Horizontal rule used to visually bracket the run summary at the bottom.
_RULE_HEAVY = "──────────────────────"

_LIVE_REFRESH_RATE = 8  # Hz — how often the spinner redraws

# Scroll-line buffer limits for the Live renderable.  Lines beyond
# _MAX_SCROLL_LINES are dropped from memory; only the most recent
# _MAX_VISIBLE_SCROLL are rendered inside the Live region.
_MAX_SCROLL_LINES = 50
_MAX_VISIBLE_SCROLL = 10

# Home directory used by ``_shorten_path`` to collapse $HOME → ~ in
# tool argument display.  Captured once at import time so a missing
# $HOME doesn't slow down every render.
try:
    _HOME = str(Path.home())
except (RuntimeError, OSError):
    _HOME = ""

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


def _truncate(text: str, maxlen: int = 80) -> str:
    if len(text) <= maxlen:
        return text
    return text[: maxlen - 1] + "…"


def _shorten_path(path: str, max_len: int = 48) -> str:
    """Make a file path readable in the activity feed.

    Collapses $HOME → ``~`` and, when still too long, drops middle path
    segments so the parent + filename remain visible (the parts a reader
    actually scans for).  Pure paths shorter than ``max_len`` are
    returned unchanged.
    """
    if _HOME and path.startswith(_HOME + "/"):
        path = "~" + path[len(_HOME) :]
    elif _HOME and path == _HOME:
        return "~"
    if len(path) <= max_len:
        return path
    # Path is still too long: keep the leading anchor and the trailing
    # parent/file segments, drop the middle.
    parts = path.split("/")
    if len(parts) <= 3:
        return "…" + path[-(max_len - 1) :]
    head = parts[0]
    tail = "/".join(parts[-2:])
    candidate = f"{head}/…/{tail}"
    if len(candidate) <= max_len:
        return candidate
    return "…/" + tail[-(max_len - 2) :]


_TOOL_ARG_EXTRACTORS: dict[str, Callable[[dict[str, Any]], str]] = {
    "Read": lambda i: _shorten_path(i.get("file_path", "")),
    "Write": lambda i: _shorten_path(i.get("file_path", "")),
    "Edit": lambda i: _shorten_path(i.get("file_path", "")),
    "MultiEdit": lambda i: _shorten_path(i.get("file_path", "")),
    "Glob": lambda i: i.get("pattern", ""),
    "Grep": lambda i: i.get("pattern", ""),
    "Bash": lambda i: _truncate(i.get("command", ""), 80),
    "Task": lambda i: _truncate(i.get("description", i.get("prompt", "")), 80),
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

# (color, category) for each known tool.  Color is applied to the tool
# name in scroll lines so the activity feed scans visually by intent —
# blue=read/search, orange=mutate, green=execute, lavender=web, etc.
# Category is the bucket used in the footer's compact tool counter.
_TOOL_STYLES: dict[str, tuple[str, str]] = {
    "Read": (_brand.BLUE, "read"),
    "Glob": (_brand.BLUE, "glob"),
    "Grep": (_brand.BLUE, "grep"),
    "Edit": (_brand.ORANGE, "edit"),
    "MultiEdit": (_brand.ORANGE, "edit"),
    "Write": (_brand.ORANGE, "write"),
    "Bash": (_brand.GREEN, "bash"),
    "BashOutput": (_brand.GREEN, "bash"),
    "WebFetch": (_brand.LAVENDER, "web"),
    "WebSearch": (_brand.LAVENDER, "web"),
    "Task": (_brand.VIOLET, "task"),
    "TodoWrite": (_brand.PURPLE, "todo"),
}

_DEFAULT_TOOL_STYLE: tuple[str, str] = ("white", "other")

# Width reserved for the colored tool name column in the activity feed.
# Most common tools (Read/Edit/Bash/Grep) are 4 chars; longer ones like
# TodoWrite/WebFetch overflow gracefully into the argument column.
_TOOL_NAME_COL = 9


def _tool_style_for(name: str) -> tuple[str, str]:
    return _TOOL_STYLES.get(name, _DEFAULT_TOOL_STYLE)


class _IterationPanel:
    """Rich renderable for the live peek panel.

    Shows a bordered Rich :class:`Panel` whose title carries elapsed time
    and token counts, body holds the most recent activity rows, and
    footer holds a spinner + tool counters + model name.

    The activity feed is the centerpiece — each row shows a colored tool
    name (color-coded by intent: blue for read/search, orange for
    mutating, green for execution, lavender for web) followed by its
    primary argument (file path, pattern, command) in dim text.
    """

    def __init__(self) -> None:
        self._spinner = Spinner("dots", style=f"bold {_brand.PURPLE}")
        self._start = time.monotonic()
        self._model: str = ""
        self._tool_count: int = 0
        self._tool_categories: dict[str, int] = {}
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._cache_read_tokens: int = 0
        self._scroll_lines: list[Text] = []
        self._peek_message: Text | None = None
        # Visibility flag controlled by toggle_peek.  Buffering keeps
        # happening behind the scenes regardless — toggling peek back on
        # reveals the latest state with full catch-up.
        self._peek_visible: bool = True

    # ── Scroll buffer management ─────────────────────────────────────

    def add_scroll_line(self, markup: str) -> None:
        """Append a Rich-markup scroll line to the transient buffer."""
        self._scroll_lines.append(Text.from_markup(markup))
        if len(self._scroll_lines) > _MAX_SCROLL_LINES:
            self._scroll_lines.pop(0)

    def clear_scroll(self) -> None:
        """Drop all buffered scroll lines."""
        self._scroll_lines.clear()

    def set_peek_message(self, markup: str) -> None:
        """Set a transient status message shown inside the Live region."""
        self._peek_message = Text.from_markup(markup)

    def set_peek_visible(self, visible: bool) -> None:
        """Show or hide the scroll feed without touching the buffer."""
        self._peek_visible = visible

    # ── Stream-json processing ───────────────────────────────────────

    def apply(self, raw: dict[str, Any]) -> str | None:
        """Update panel state from a parsed stream-json dict.

        Returns the scroll-line markup string (or ``None``).  The line is
        also appended to the internal scroll buffer so it renders inside
        the Live region.
        """
        event_type = raw.get("type")

        if event_type == "system" and raw.get("subtype") == "init":
            self._model = raw.get("model", "")
            return None

        scroll_line: str | None = None

        if event_type == "assistant":
            scroll_line = self._apply_assistant(raw)
        elif event_type == "user":
            scroll_line = self._apply_user(raw)
        elif event_type == "rate_limit_event":
            info = raw.get("rate_limit_info", {})
            status = info.get("status", "")
            resets = info.get("resetsAt", "")
            scroll_line = (
                f"[bold {_brand.PEACH}]⚠ rate limit:[/]"
                f" [dim]{escape_markup(str(status))}"
                f", resets {escape_markup(str(resets))}[/]"
            )

        if scroll_line is not None:
            self.add_scroll_line(scroll_line)

        return scroll_line

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

            if block_type == "text":
                text = block.get("text", "")
                preview = _truncate(text.replace("\n", " "), 100)
                if preview:
                    scroll_line = (
                        f"[italic {_brand.LAVENDER}]“{escape_markup(preview)}”[/]"
                    )

            elif block_type == "tool_use":
                name = block.get("name", "?")
                tool_input = block.get("input", {})
                if not isinstance(tool_input, dict):
                    tool_input = {}

                self._tool_count += 1
                color, cat = _tool_style_for(name)
                self._tool_categories[cat] = self._tool_categories.get(cat, 0) + 1

                if _TOOL_ARG_EXTRACTORS.get(name) is not None:
                    arg = _TOOL_ARG_EXTRACTORS[name](tool_input)
                else:
                    arg = ", ".join(sorted(tool_input.keys()))

                # Pad short names to a fixed column so arguments line up;
                # longer names get a guaranteed two-space gap so the arg
                # never collides with the tool label.
                if len(name) < _TOOL_NAME_COL:
                    name_col = f"{name:<{_TOOL_NAME_COL}}"
                else:
                    name_col = f"{name}  "
                if arg:
                    scroll_line = (
                        f"[bold {color}]{escape_markup(name_col)}[/]"
                        f"[dim]{escape_markup(arg)}[/]"
                    )
                else:
                    scroll_line = f"[bold {color}]{escape_markup(name)}[/]"

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
                snippet = _truncate(str(block.get("content", "")), 100)
                return (
                    f"[bold {_brand.DEEP_ORANGE}]{_ICON_FAILURE} tool error:[/]"
                    f" [dim]{escape_markup(snippet)}[/]"
                )
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

    # ── Rich renderable ───────────────────────────────────────────────

    def _build_title(self) -> Text:
        """Title bar text: elapsed time + token usage."""
        elapsed = time.monotonic() - self._start
        title = Text()
        title.append(" ⏱ ", style=_brand.PURPLE)
        title.append(format_duration(elapsed), style=f"bold {_brand.PURPLE}")
        tokens = self._format_tokens()
        if tokens:
            title.append("   ", style="dim")
            title.append(tokens, style=f"bold {_brand.LAVENDER}")
        title.append(" ", style="dim")
        return title

    def _build_subtitle(self) -> Text | None:
        """Subtitle: model name, when known."""
        if not self._model:
            return None
        sub = Text()
        sub.append(" ", style="dim")
        sub.append(self._model, style=f"dim italic {_brand.LAVENDER}")
        sub.append(" ", style="dim")
        return sub

    def _build_footer(self) -> Table:
        """Bottom row of the panel: spinner + tool counts."""
        summary = Text(no_wrap=True, overflow="ellipsis")
        if self._tool_count > 0:
            summary.append(
                f"{self._tool_count} tool{'s' if self._tool_count != 1 else ''}",
                style=f"bold {_brand.PURPLE}",
            )
            cats = self._format_categories()
            if cats:
                summary.append("  ·  ", style="dim")
                summary.append(cats, style="dim")
        else:
            summary.append("waiting for first tool call…", style="dim italic")

        grid = Table.grid(expand=True)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_row(self._spinner, summary)
        return grid

    def _build_body(self) -> Group:
        """Body group: scroll lines (or peek message) + spacer + footer."""
        rows: list[Any] = []
        if self._peek_visible:
            visible = self._scroll_lines[-_MAX_VISIBLE_SCROLL:]
            if visible:
                for line in visible:
                    line.no_wrap = True
                    line.overflow = "ellipsis"
                    rows.append(line)
            elif self._peek_message is not None:
                rows.append(self._peek_message)
        elif self._peek_message is not None:
            rows.append(self._peek_message)
        rows.append(Text(""))  # spacer above footer
        rows.append(self._build_footer())
        return Group(*rows)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        panel = Panel(
            self._build_body(),
            box=box.ROUNDED,
            title=self._build_title(),
            title_align="left",
            subtitle=self._build_subtitle(),
            subtitle_align="right",
            border_style=_brand.PURPLE,
            padding=(0, 2),
        )
        yield panel


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
        self._iteration_spinner: _IterationSpinner | None = None
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
        # Returns the peek state so the engine still gets a "no, drop
        # raw line events" signal when peek is off.  This lets the
        # engine package captured output for end-of-iteration echo when
        # ``--log-dir`` is set, preserving that recovery path for users
        # who keep peek off the whole run.  Persistence for structured
        # (Claude) agents goes through ``_on_agent_activity`` which is
        # always called regardless of this gate.
        return self._peek_enabled

    def toggle_peek(self) -> bool:
        """Flip live-output rendering on or off.

        Safe to call from a non-main thread (e.g. the keypress listener).
        Returns the new peek state.  Toggling never clears the scroll
        buffer — the panel keeps recording behind the scenes so toggling
        peek back on shows the latest state.
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

            renderable = self._iteration_panel or self._iteration_spinner
            if renderable is not None:
                renderable.set_peek_visible(enabled)
                renderable.set_peek_message(msg)
                if self._live is not None:
                    self._live.update(renderable)
            else:
                self._console.print(msg)
        return enabled

    def _on_agent_output_line(self, data: AgentOutputLineData) -> None:
        with self._console_lock:
            # When we have structured rendering, raw lines are redundant noise.
            if self._structured_agent:
                return
            line = escape_markup(data["line"])
            spinner = self._iteration_spinner
            if spinner is not None:
                spinner.add_scroll_line(f"[white]{line}[/]")
                if self._live is not None:
                    self._live.update(spinner)

    def _on_agent_activity(self, data: AgentActivityData) -> None:
        """Handle structured agent activity events (Claude stream-json).

        Peek is best-effort — a failure here must never kill the run loop.
        Events are always buffered into the panel regardless of peek
        state; visibility is controlled by the panel's _peek_visible flag.
        """
        if not self._structured_agent:
            return

        with self._console_lock:
            if self._peek_broken:
                return

            try:
                panel = self._iteration_panel
                if panel is None:
                    return
                panel.apply(data["raw"])
                # Update the Live renderable so it reflects new counters
                # (scroll lines are now stored inside the panel).
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
            self._iteration_spinner = None
            renderable = panel
        else:
            spinner = _IterationSpinner()
            self._iteration_panel = None
            self._iteration_spinner = spinner
            renderable = spinner
        # Carry the current peek visibility into the new renderable so
        # an iteration that starts with peek already off doesn't flash
        # the empty scroll feed before the first event lands.
        renderable.set_peek_visible(self._peek_enabled)
        if not self._peek_enabled:
            renderable.set_peek_message(_PEEK_OFF_MSG)
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
        self._iteration_spinner = None

    def _stop_live(self) -> None:
        with self._console_lock:
            self._stop_live_unlocked()

    def _on_iteration_started(self, data: IterationStartedData) -> None:
        iteration = data["iteration"]
        with self._console_lock:
            self._peek_broken = False
            self._console.print()
            self._console.print(
                Rule(
                    title=f"[bold {_brand.PURPLE}]Iteration {iteration}[/]",
                    align="left",
                    style=_brand.PURPLE,
                    characters="─",
                )
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
    """Rich renderable for non-Claude agents that emit raw stdout.

    Same panel chrome as :class:`_IterationPanel` so the visual feels
    consistent across agents — only the body content differs (raw text
    lines vs. structured tool rows).
    """

    def __init__(self) -> None:
        self._spinner = Spinner("dots", style=f"bold {_brand.PURPLE}")
        self._start = time.monotonic()
        self._scroll_lines: list[Text] = []
        self._peek_message: Text | None = None
        self._peek_visible: bool = True

    def add_scroll_line(self, markup: str) -> None:
        """Append a Rich-markup scroll line to the transient buffer."""
        self._scroll_lines.append(Text.from_markup(markup))
        if len(self._scroll_lines) > _MAX_SCROLL_LINES:
            self._scroll_lines.pop(0)

    def clear_scroll(self) -> None:
        """Drop all buffered scroll lines."""
        self._scroll_lines.clear()

    def set_peek_message(self, markup: str) -> None:
        """Set a transient status message shown inside the Live region."""
        self._peek_message = Text.from_markup(markup)

    def set_peek_visible(self, visible: bool) -> None:
        """Show or hide the scroll feed without touching the buffer."""
        self._peek_visible = visible

    def _build_title(self) -> Text:
        elapsed = time.monotonic() - self._start
        title = Text()
        title.append(" ⏱ ", style=_brand.PURPLE)
        title.append(format_duration(elapsed), style=f"bold {_brand.PURPLE}")
        title.append(" ", style="dim")
        return title

    def _build_footer(self) -> Table:
        line_count = len(self._scroll_lines)
        summary = Text(no_wrap=True, overflow="ellipsis")
        if line_count > 0:
            summary.append(
                f"{line_count} line{'s' if line_count != 1 else ''}",
                style=f"bold {_brand.PURPLE}",
            )
            summary.append(" of agent output", style="dim")
        else:
            summary.append("waiting for agent output…", style="dim italic")
        grid = Table.grid(expand=True)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_row(self._spinner, summary)
        return grid

    def _build_body(self) -> Group:
        rows: list[Any] = []
        if self._peek_visible:
            visible = self._scroll_lines[-_MAX_VISIBLE_SCROLL:]
            if visible:
                for line in visible:
                    line.no_wrap = True
                    line.overflow = "ellipsis"
                    rows.append(line)
            elif self._peek_message is not None:
                rows.append(self._peek_message)
        elif self._peek_message is not None:
            rows.append(self._peek_message)
        rows.append(Text(""))
        rows.append(self._build_footer())
        return Group(*rows)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        panel = Panel(
            self._build_body(),
            box=box.ROUNDED,
            title=self._build_title(),
            title_align="left",
            border_style=_brand.PURPLE,
            padding=(0, 2),
        )
        yield panel
