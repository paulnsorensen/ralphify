"""Snapshot-mode TUI dev harness.

Drives the real ``ConsoleEmitter`` through synthesized events to produce
a gallery of PNG snapshots — one per interesting terminal state.  This
is the fast-iteration path for TUI design work: edit
``_console_emitter.py`` -> rerun this script -> ``Read`` the PNGs to see
exactly what changed.

Two snapshot kinds are supported:

1. **Peek panel scenarios** (``ALL_SCENARIOS`` in ``fixtures.py``).
   Drive ``AGENT_ACTIVITY`` events through the panel and render its
   internal state directly.  Used for iterating on the live activity
   feed (the bordered panel shown when peek is on).

2. **Event-sequence scenarios** (``EVENT_SCENARIOS`` in ``fixtures.py``).
   Drive any sequence of ``Event`` objects and capture whatever the
   emitter prints to the recording console.  Used for iterating on
   anything else — iteration result lines, run summaries, error logs,
   markdown result rendering.

Rendering fidelity is Rich's own ``save_svg`` output, which reflects
what Rich emits to the terminal (same renderables, same colors, same
layout).  For subprocess-level end-to-end truth, see ``live.py``.
"""

from __future__ import annotations

import io
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console

# Import after sys.path manipulation.
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from ralphify import _console_emitter  # noqa: E402
from ralphify._console_emitter import (  # noqa: E402
    ConsoleEmitter,
    _IterationPanel,
    _IterationSpinner,
)
from ralphify._events import (  # noqa: E402
    Event,
    EventType,
)

# Fixtures use /Users/kasper/... as a stand-in user.  Override the home
# the renderer uses so its `~/...` collapsing fires for demo paths
# regardless of which machine runs the harness.
_console_emitter._HOME = "/Users/kasper"


class _SnapshotConsoleEmitter(ConsoleEmitter):
    """ConsoleEmitter that never starts a Live display.

    In snapshot mode we want a single, frozen rendering of the iteration
    panel — not a Live refresh loop that writes the panel to the record
    console multiple times.  Overriding ``_start_live_unlocked`` creates
    the panel/spinner but leaves ``_live=None``, so ``_on_agent_activity``
    still routes to ``panel.apply()`` without triggering any draw.
    """

    def _start_live_unlocked(self) -> None:  # type: ignore[override]
        if self._structured_agent:
            self._iteration_panel = _IterationPanel()
            self._iteration_spinner = None
        else:
            self._iteration_panel = None
            self._iteration_spinner = _IterationSpinner()
        self._live = None


from fixtures import ALL_SCENARIOS, EVENT_SCENARIOS  # noqa: E402
from render import svg_to_png  # noqa: E402


OUTPUT_DIR = Path(__file__).parent / "output"
SNAPSHOT_WIDTH = 120  # terminal columns for rendering
SNAPSHOT_TITLE_PREFIX = "ralphify TUI —"


def _make_event(event_type: EventType, **data) -> Event:
    return Event(type=event_type, run_id="dev-preview", data=data)


def _build_console() -> Console:
    """Make a recording Console that behaves like a real terminal.

    - ``record=True`` so we can ``save_svg`` at the end.
    - ``file=StringIO()`` suppresses echo to our own stdout; recording
      still captures the styled output via Rich's internal buffer.
    - ``force_terminal=True`` so Rich keeps ANSI/styling active.
    - ``color_system='truecolor'`` so colors match the real output.
    """
    return Console(
        record=True,
        file=io.StringIO(),
        force_terminal=True,
        color_system="truecolor",
        width=SNAPSHOT_WIDTH,
        height=60,
        legacy_windows=False,
    )


def _save(console: Console, name: str) -> None:
    """Persist the console's recorded output as SVG + PNG."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    svg_path = OUTPUT_DIR / f"{name}.svg"
    png_path = OUTPUT_DIR / f"{name}.png"
    console.save_svg(str(svg_path), title=f"{SNAPSHOT_TITLE_PREFIX} {name}")
    svg_to_png(svg_path, png_path)
    print(f"  {name}: {svg_path.relative_to(REPO_ROOT)}  ->  {png_path.name}")


def _emit_run_start(emitter: ConsoleEmitter, ralph_name: str, structured: bool) -> None:
    agent = "claude --output-format stream-json" if structured else "bash ./agent.sh"
    emitter.emit(
        _make_event(
            EventType.RUN_STARTED,
            ralph_name=ralph_name,
            agent=agent,
            commands=2,
            max_iterations=None,
            timeout=600.0,
            delay=0.0,
        )
    )


def _snapshot_peek_scenario(name: str, raw_events: list[dict]) -> None:
    """Render one peek-panel scenario to SVG + PNG.

    Drives the emitter through RUN_STARTED -> ITERATION_STARTED -> a
    sequence of AGENT_ACTIVITY events, then prints the panel directly
    so we capture its mid-iteration state (the Live region would
    otherwise be transient).
    """
    console = _build_console()
    emitter = _SnapshotConsoleEmitter(console)
    emitter._peek_enabled = True
    emitter._structured_agent = True

    _emit_run_start(emitter, ralph_name=f"peek-demo / {name}", structured=True)
    emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))

    for raw in raw_events:
        emitter.emit(_make_event(EventType.AGENT_ACTIVITY, raw=raw, iteration=1))

    panel = emitter._iteration_panel
    assert panel is not None, "panel missing — did ITERATION_STARTED run?"
    panel._start -= 42.7  # fake elapsed so the "0.0s" header isn't misleading
    # The 09_peek_off scenario shows the placeholder state with the
    # buffer still intact — verifies the persistence fix visually.
    if name == "09_peek_off":
        emitter.toggle_peek()
    console.print(panel)
    _save(console, name)


def _snapshot_raw_spinner() -> None:
    """Render the ``_IterationSpinner`` (non-Claude agent) path."""
    console = _build_console()
    emitter = _SnapshotConsoleEmitter(console)
    emitter._peek_enabled = True
    emitter._structured_agent = False

    _emit_run_start(emitter, ralph_name="peek-demo / 08_raw_spinner", structured=False)
    emitter.emit(_make_event(EventType.ITERATION_STARTED, iteration=1))

    raw_lines = [
        "Running shell agent v2.3",
        "→ analyzing repo structure",
        "→ found 42 files to process",
        "→ scanning for TODOs",
        "  src/core/main.py:112  TODO: handle edge case",
        "  src/core/utils.py:45   TODO: add retry logic",
        "→ checking test coverage",
        "  coverage: 87.3%",
        "→ building plan of attack",
        "→ executing step 1/5: refactor core/main.py",
        "  wrote 23 lines, deleted 11",
        "  tests: 124 passed, 0 failed",
        "→ executing step 2/5: update utils.py",
    ]
    for line in raw_lines:
        emitter.emit(
            _make_event(
                EventType.AGENT_OUTPUT_LINE,
                line=line,
                stream="stdout",
                iteration=1,
            )
        )

    spinner: _IterationSpinner | None = emitter._iteration_spinner
    assert spinner is not None
    spinner._start -= 18.2
    console.print(spinner)
    _save(console, "08_raw_spinner")


def _snapshot_event_sequence(name: str, events: list[tuple[EventType, dict]]) -> None:
    """Render a generic event-sequence scenario to SVG + PNG.

    Used for any TUI state that doesn't need access to the panel
    internals — iteration result lines, run summaries, error logs,
    markdown result rendering.  The emitter prints to the recording
    console as events arrive, and we save whatever ended up there.
    """
    console = _build_console()
    emitter = _SnapshotConsoleEmitter(console)
    emitter._peek_enabled = False
    for event_type, data in events:
        emitter.emit(Event(type=event_type, run_id="dev-preview", data=data))
    _save(console, name)


def main() -> int:
    start = time.monotonic()
    print(f"Writing snapshots to {OUTPUT_DIR.relative_to(REPO_ROOT)}/")
    print("  Peek panel scenarios:")
    for name, raw_events in ALL_SCENARIOS.items():
        _snapshot_peek_scenario(name, raw_events)
    _snapshot_raw_spinner()
    print("  Event-sequence scenarios:")
    for name, events in EVENT_SCENARIOS.items():
        _snapshot_event_sequence(name, events)
    elapsed = time.monotonic() - start
    total = len(ALL_SCENARIOS) + 1 + len(EVENT_SCENARIOS)
    print(f"Done in {elapsed:.1f}s — {total} snapshots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
