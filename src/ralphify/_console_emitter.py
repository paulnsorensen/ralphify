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
from ralphify._agent import CLAUDE_BINARY
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
# _MAX_VISIBLE_SCROLL are rendered inside the compact Live region.
# The full buffer is exposed in the fullscreen peek view (shift+P) so
# users can scroll back through earlier activity within an iteration.
_MAX_SCROLL_LINES = 5000
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

# Shift+P enters full-screen peek mode — a scrollable view of the entire
# activity buffer that takes over the terminal using Rich's alt-screen.
FULLSCREEN_PEEK_KEY = "P"

# Peek status messages shown when peek is toggled or at run startup.
_PEEK_ON_MSG_STRUCTURED = (
    f"[dim]live activity on — press {PEEK_TOGGLE_KEY} to hide, "
    f"shift+{PEEK_TOGGLE_KEY} for full view[/]"
)
_PEEK_ON_MSG_RAW = (
    f"[dim]live output on — press {PEEK_TOGGLE_KEY} to hide, "
    f"shift+{PEEK_TOGGLE_KEY} for full view[/]"
)
_PEEK_OFF_MSG = (
    f"[dim]peek off — press {PEEK_TOGGLE_KEY} to toggle, "
    f"shift+{PEEK_TOGGLE_KEY} for full view[/]"
)

# ── Claude binary detection ───────────────────────────────────────────


def _is_claude_command(agent: str) -> bool:
    """Return True if *agent* is a Claude Code command."""
    try:
        parts = shlex.split(agent)
    except ValueError:
        return False
    if not parts:
        return False
    return Path(parts[0]).stem == CLAUDE_BINARY


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


def _format_params(tool_input: dict[str, Any], keys: list[str]) -> str:
    """Format specified tool parameters as ``key: value`` pairs."""
    parts = []
    for key in keys:
        val = tool_input.get(key)
        if val is not None:
            parts.append(f"{key}: {val}")
    return " · ".join(parts) if parts else ""


def _extract_file_path(i: dict[str, Any]) -> str:
    return _shorten_path(i.get("file_path", ""))

_TOOL_ARG_EXTRACTORS: dict[str, Callable[[dict[str, Any]], str]] = {
    "Read": _extract_file_path,
    "Write": _extract_file_path,
    "Edit": _extract_file_path,
    "MultiEdit": _extract_file_path,
    "Glob": lambda i: i.get("pattern", ""),
    "Grep": lambda i: i.get("pattern", ""),
    "Bash": lambda i: i.get("command", ""),
    "Task": lambda i: _format_params(i, ["description", "prompt"]),
    "WebFetch": lambda i: i.get("url", ""),
    "WebSearch": lambda i: i.get("query", ""),
    "TodoWrite": lambda i: f"{len(i.get('todos', []))} todos",
    "Agent": lambda i: _format_params(i, ["description", "prompt"]),
    "ToolSearch": lambda i: _format_params(i, ["query", "max_results"]),
}


def _extract_tool_arg(name: str, tool_input: dict[str, Any]) -> str:
    """Return the most relevant argument string for a tool call."""
    extractor = _TOOL_ARG_EXTRACTORS.get(name)
    if extractor is not None:
        return extractor(tool_input)
    return ", ".join(sorted(tool_input.keys()))


def _format_tool_summary(name: str, tool_input: dict[str, Any]) -> str:
    """Return a compact one-liner describing a tool call."""
    arg = _extract_tool_arg(name, tool_input)
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


class _LivePanelBase:
    """Shared scroll-buffer state for iteration Live renderables.

    Both :class:`_IterationPanel` (Claude structured output) and
    :class:`_IterationSpinner` (raw agent output) need the same scroll
    buffer, peek visibility toggle, and body-rendering logic.  This base
    class provides all of that so neither subclass has to duplicate it.
    """

    def __init__(self) -> None:
        self._spinner = Spinner("dots", style=f"bold {_brand.PURPLE}")
        self._start = time.monotonic()
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

    # ── Shared rendering ─────────────────────────────────────────────

    def _build_footer(self) -> Table:
        """Subclasses must override to provide the footer summary row."""
        raise NotImplementedError

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


class _IterationPanel(_LivePanelBase):
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
        super().__init__()
        self._model: str = ""
        self._tool_count: int = 0
        self._tool_categories: dict[str, int] = {}
        self._input_tokens: int = 0
        self._output_tokens: int = 0
        self._cache_read_tokens: int = 0

    # ── Stream-json processing ───────────────────────────────────────

    def apply(self, raw: dict[str, Any]) -> None:
        """Update panel state from a parsed stream-json dict.

        Each handler appends its own scroll lines to the buffer so that
        multi-line blocks (thinking, long text) can produce several rows.
        """
        event_type = raw.get("type")

        if event_type == "system" and raw.get("subtype") == "init":
            self._model = raw.get("model", "")
        elif event_type == "assistant":
            self._apply_assistant(raw)
        elif event_type == "user":
            self._apply_user(raw)
        elif event_type == "rate_limit_event":
            info = raw.get("rate_limit_info", {})
            status = info.get("status", "")
            resets = info.get("resetsAt", "")
            self.add_scroll_line(
                f"[bold {_brand.PEACH}]⚠ rate limit:[/]"
                f" [dim]{escape_markup(str(status))}"
                f", resets {escape_markup(str(resets))}[/]"
            )

    def _apply_assistant(self, raw: dict[str, Any]) -> None:
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
            return

        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")

            if block_type == "thinking":
                text = block.get("thinking", "")
                if text:
                    for tline in text.split("\n"):
                        self.add_scroll_line(f"[dim italic]{escape_markup(tline)}[/]")

            elif block_type == "text":
                text = block.get("text", "")
                if text:
                    for tline in text.split("\n"):
                        if tline.strip():
                            self.add_scroll_line(
                                f'[italic {_brand.LAVENDER}]"{escape_markup(tline)}"[/]'
                            )

            elif block_type == "tool_use":
                name = block.get("name", "?")
                tool_input = block.get("input", {})
                if not isinstance(tool_input, dict):
                    tool_input = {}

                self._tool_count += 1
                color, cat = _tool_style_for(name)
                self._tool_categories[cat] = self._tool_categories.get(cat, 0) + 1

                arg = _extract_tool_arg(name, tool_input)

                # Pad short names to a fixed column so arguments line up;
                # longer names get a guaranteed two-space gap so the arg
                # never collides with the tool label.
                if len(name) < _TOOL_NAME_COL:
                    name_col = f"{name:<{_TOOL_NAME_COL}}"
                else:
                    name_col = f"{name}  "
                if arg:
                    self.add_scroll_line(
                        f"[bold {color}]{escape_markup(name_col)}[/]"
                        f"[dim]{escape_markup(arg)}[/]"
                    )
                else:
                    self.add_scroll_line(f"[bold {color}]{escape_markup(name)}[/]")

    def _apply_user(self, raw: dict[str, Any]) -> None:
        msg = raw.get("message", {})
        content = msg.get("content", [])
        if not isinstance(content, list):
            return
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result" and block.get("is_error"):
                snippet = _truncate(str(block.get("content", "")), 100)
                self.add_scroll_line(
                    f"[bold {_brand.DEEP_ORANGE}]{_ICON_FAILURE} tool error:[/]"
                    f" [dim]{escape_markup(snippet)}[/]"
                )
                return

    def _format_tokens(self) -> str:
        """Format token counts as compact ctx/out string."""
        parts: list[str] = []
        total_in = self._input_tokens
        if total_in > 0:
            parts.append(f"ctx {self._format_count(total_in)}")
        if self._output_tokens > 0:
            parts.append(f"out {self._format_count(self._output_tokens)}")
        return " · ".join(parts)

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
        """Bottom row of the panel: spinner + tool counts + peek hint."""
        summary = Text(no_wrap=True, overflow="ellipsis")
        if self._tool_count > 0:
            summary.append(
                _plural(self._tool_count, "tool"),
                style=f"bold {_brand.PURPLE}",
            )
            cats = self._format_categories()
            if cats:
                summary.append("  ·  ", style="dim")
                summary.append(cats, style="dim")
        else:
            summary.append("waiting for first tool call…", style="dim italic")

        hint = Text("Shift+P full screen", style="dim", no_wrap=True)

        grid = Table.grid(expand=True)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_column(no_wrap=True, justify="right")
        grid.add_row(self._spinner, summary, hint)
        return grid

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


# ── Full-screen peek ─────────────────────────────────────────────────

# Chrome rows that the fullscreen peek reserves on top of its viewport:
# panel top border + header row + header gap + footer gap + footer row +
# panel bottom border.  Used to size the visible viewport to the terminal.
_FULLSCREEN_CHROME_ROWS = 6
_FULLSCREEN_MIN_VISIBLE = 5


class _FullscreenPeek:
    """Scrollable alt-screen view of the activity buffer.

    Reads ``_scroll_lines`` from a source :class:`_LivePanelBase` subclass
    (either :class:`_IterationPanel` or :class:`_IterationSpinner`).
    The source keeps receiving agent events in the background, so as new
    lines land the view follows the tail when ``_auto_scroll`` is set.

    The offset is anchored to the *bottom* of the buffer: ``_offset=0``
    shows the latest lines, ``_offset=1`` hides the newest line, and so
    on up to ``len(buffer) - visible``.  This keeps "follow mode" cheap —
    auto-scroll just means "keep offset at 0".
    """

    def __init__(self, source: _LivePanelBase) -> None:
        self._source = source
        self._offset: int = 0
        self._auto_scroll: bool = True

    def _viewport_height(self, console_height: int) -> int:
        return max(_FULLSCREEN_MIN_VISIBLE, console_height - _FULLSCREEN_CHROME_ROWS)

    def _max_offset(self, visible: int) -> int:
        return max(0, len(self._source._scroll_lines) - visible)

    # ── Scroll commands ──────────────────────────────────────────────

    def scroll_up(self, lines: int = 1) -> None:
        """Scroll toward older lines (offset grows)."""
        visible = self._viewport_height(self._console_height)
        new_offset = min(self._offset + lines, self._max_offset(visible))
        if new_offset != self._offset:
            self._offset = new_offset
            self._auto_scroll = False

    def scroll_down(self, lines: int = 1) -> None:
        """Scroll toward newer lines (offset shrinks)."""
        new_offset = max(0, self._offset - lines)
        self._offset = new_offset
        if new_offset == 0:
            self._auto_scroll = True

    def scroll_to_top(self) -> None:
        visible = self._viewport_height(self._console_height)
        self._offset = self._max_offset(visible)
        self._auto_scroll = False

    def scroll_to_bottom(self) -> None:
        self._offset = 0
        self._auto_scroll = True

    # ── Rendering ────────────────────────────────────────────────────

    _console_height: int = 40  # updated on every render

    def _build_header(self, total: int, visible: int) -> Text:
        header = Text(no_wrap=True, overflow="ellipsis")
        header.append(" Full peek ", style=f"bold {_brand.PURPLE}")
        header.append(f"· {_plural(total, 'line')}", style="dim")
        if self._auto_scroll:
            header.append("  ·  ", style="dim")
            header.append("following", style=f"italic {_brand.GREEN}")
        else:
            start = max(0, total - self._offset - visible) + 1
            end = total - self._offset
            header.append("  ·  ", style="dim")
            header.append(f"lines {start}–{end}", style=f"italic {_brand.LAVENDER}")
        return header

    def _build_footer(self) -> Text:
        hint = Text(no_wrap=True, overflow="ellipsis")
        hint.append(
            " ↑/k up · ↓/j down · b page up · space page down · g/G top/bottom · q/",
            style="dim",
        )
        hint.append(FULLSCREEN_PEEK_KEY, style=f"bold {_brand.PURPLE}")
        hint.append(" exit ", style="dim")
        return hint

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        self._console_height = options.max_height or console.size.height
        visible = self._viewport_height(self._console_height)
        lines = self._source._scroll_lines
        total = len(lines)

        # Clamp offset whenever the buffer shrinks (edge case) or the
        # terminal was resized since the last render.
        max_off = self._max_offset(visible)
        if self._offset > max_off:
            self._offset = max_off
        if self._auto_scroll:
            self._offset = 0

        end = total - self._offset
        start = max(0, end - visible)
        window = lines[start:end]

        # Scrollbar metrics
        show_scrollbar = total > visible
        thumb_start = 0
        thumb_size = visible
        if show_scrollbar:
            thumb_size = max(1, visible * visible // total)
            max_off_val = max(total - visible, 1)
            frac = 1.0 - (self._offset / max_off_val)
            track_space = visible - thumb_size
            thumb_start = int(frac * track_space)

        rows: list[Any] = []
        rows.append(self._build_header(total, visible))
        rows.append(Text(""))

        # Content area with optional scrollbar column
        content = Table.grid(expand=True)
        content.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        if show_scrollbar:
            content.add_column(width=1, no_wrap=True)

        for i in range(visible):
            if i < len(window):
                line = window[i]
                line.no_wrap = True
                line.overflow = "ellipsis"
            else:
                line = Text("")
            if show_scrollbar:
                in_thumb = thumb_start <= i < thumb_start + thumb_size
                bar = Text(
                    "█" if in_thumb else "│",
                    style=_brand.PURPLE if in_thumb else "dim",
                )
                content.add_row(line, bar)
            else:
                content.add_row(line)

        if not window and not show_scrollbar:
            # Replace the empty grid with a waiting message
            rows.append(Text("  (waiting for activity…)", style="dim italic"))
            for _ in range(max(0, visible - 1)):
                rows.append(Text(""))
        else:
            rows.append(content)

        rows.append(Text(""))
        rows.append(self._build_footer())

        panel = Panel(
            Group(*rows),
            box=box.ROUNDED,
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
        # Fullscreen peek state — a second Live using Rich's alt-screen
        # that shows the entire activity buffer with scroll navigation.
        # When active, the compact ``_live`` is stopped; the underlying
        # panel/spinner keeps buffering events so exiting fullscreen
        # resumes the compact view with the latest state.
        self._fullscreen_view: _FullscreenPeek | None = None
        self._fullscreen_live: Live | None = None
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
                fs_live = self._fullscreen_live
                fs_view = self._fullscreen_view
                if fs_live is not None and fs_view is not None:
                    fs_live.update(fs_view)
                elif self._live is not None:
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
                # Update whichever Live is currently on top.  Fullscreen
                # wins — it gets the refresh so scroll-follow mode picks
                # up new lines in real time.  Otherwise the compact Live
                # re-renders with new counters + scroll lines.
                fs_live = self._fullscreen_live
                fs_view = self._fullscreen_view
                if fs_live is not None and fs_view is not None:
                    fs_live.update(fs_view)
                elif self._live is not None:
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
        """Stop the iteration panel/spinner.  Caller must hold ``_console_lock``.

        Also tears down the fullscreen peek view if active — the
        underlying buffer belongs to the iteration we're ending, so
        leaving the user stuck in an alt screen showing stale data would
        be worse than dropping them back to the normal terminal.
        """
        if self._fullscreen_live is not None:
            self._fullscreen_live.stop()
            self._fullscreen_live = None
        self._fullscreen_view = None
        if self._live is not None:
            self._live.stop()
            self._live = None
        self._iteration_panel = None
        self._iteration_spinner = None

    def _stop_live(self) -> None:
        with self._console_lock:
            self._stop_live_unlocked()

    # ── Fullscreen peek ──────────────────────────────────────────────

    def enter_fullscreen(self) -> bool:
        """Enter fullscreen peek mode.  Safe to call from any thread.

        Returns ``True`` if fullscreen is now active, ``False`` if the
        caller tried to enter when no iteration was running (nothing to
        show) or when already in fullscreen.
        """
        with self._console_lock:
            if self._fullscreen_view is not None:
                return True  # already active — no-op
            source: _LivePanelBase | None = (
                self._iteration_panel or self._iteration_spinner
            )
            if source is None:
                self._console.print("[dim]Full peek: no active iteration yet[/]")
                return False
            view = _FullscreenPeek(source)
            self._fullscreen_view = view
            # Stop the compact Live before taking over the terminal so
            # the two Rich renderers don't fight for the same console.
            if self._live is not None:
                self._live.stop()
                self._live = None
            self._fullscreen_live = Live(
                view,
                console=self._console,
                screen=True,
                refresh_per_second=_LIVE_REFRESH_RATE,
            )
            try:
                self._fullscreen_live.start()
            except Exception:
                # Alt-screen can fail in unusual terminals — clean up
                # and silently fall back to compact mode rather than
                # wedging the user.
                self._fullscreen_live = None
                self._fullscreen_view = None
                self._restart_compact_unlocked()
                return False
            return True

    def exit_fullscreen(self) -> None:
        """Exit fullscreen peek mode.  Safe to call from any thread."""
        with self._console_lock:
            if self._fullscreen_view is None:
                return
            if self._fullscreen_live is not None:
                self._fullscreen_live.stop()
                self._fullscreen_live = None
            self._fullscreen_view = None
            self._restart_compact_unlocked()

    def _restart_compact_unlocked(self) -> None:
        """Bring the compact Live back after a fullscreen exit.

        Uses the existing panel/spinner (and its accumulated buffer) if
        an iteration is still running.  No-op when the iteration has
        already ended.
        """
        source: _LivePanelBase | None = (
            self._iteration_panel or self._iteration_spinner
        )
        if source is None:
            return
        self._live = Live(
            source,
            console=self._console,
            transient=True,
            refresh_per_second=_LIVE_REFRESH_RATE,
        )
        self._live.start()

    def _fullscreen_page_size(self) -> int:
        """Lines to jump on space/b (page down/up)."""
        try:
            height = self._console.size.height
        except Exception:
            height = 40
        return max(1, height - _FULLSCREEN_CHROME_ROWS - 2)

    def handle_key(self, key: str) -> None:
        """Dispatch a single keypress from the KeypressListener.

        The emitter owns key routing because the keybindings differ
        between compact mode (``p`` / ``P``) and fullscreen mode (vim +
        less style navigation).  Errors are swallowed so a render bug
        never kills the listener thread.
        """
        try:
            if self._fullscreen_view is not None:
                self._handle_fullscreen_key(key)
                return
            if key == PEEK_TOGGLE_KEY:
                self.toggle_peek()
            elif key == FULLSCREEN_PEEK_KEY:
                self.enter_fullscreen()
        except Exception:
            pass

    def _handle_fullscreen_key(self, key: str) -> None:
        """Scroll navigation while fullscreen peek is active."""
        with self._console_lock:
            view = self._fullscreen_view
            if view is None:
                return  # raced with exit
            if key in ("q", FULLSCREEN_PEEK_KEY):
                # Release lock before exit_fullscreen re-acquires it.
                pass
            else:
                page = self._fullscreen_page_size()
                handled = True
                if key == "j":
                    view.scroll_down(1)
                elif key == "k":
                    view.scroll_up(1)
                elif key == " ":
                    view.scroll_down(page)
                elif key == "b":
                    view.scroll_up(page)
                elif key == "g":
                    view.scroll_to_top()
                elif key == "G":
                    view.scroll_to_bottom()
                else:
                    handled = False
                if handled and self._fullscreen_live is not None:
                    self._fullscreen_live.update(view)
                return
        # Exit path runs outside the lock to avoid re-entry.
        self.exit_fullscreen()

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


class _IterationSpinner(_LivePanelBase):
    """Rich renderable for non-Claude agents that emit raw stdout.

    Same panel chrome as :class:`_IterationPanel` so the visual feels
    consistent across agents — only the body content differs (raw text
    lines vs. structured tool rows).
    """

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
                _plural(line_count, "line"),
                style=f"bold {_brand.PURPLE}",
            )
            summary.append(" of agent output", style="dim")
        else:
            summary.append("waiting for agent output…", style="dim italic")

        hint = Text("Shift+P full screen", style="dim", no_wrap=True)

        grid = Table.grid(expand=True)
        grid.add_column(width=2, no_wrap=True)
        grid.add_column(ratio=1, no_wrap=True, overflow="ellipsis")
        grid.add_column(no_wrap=True, justify="right")
        grid.add_row(self._spinner, summary, hint)
        return grid

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
