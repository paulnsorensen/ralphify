"""Live-mode TUI dev harness: spawn real ``ralph run`` in a pty, capture
ANSI, render the terminal state to a PNG.

This is the highest-fidelity feedback path.  Unlike ``snapshot.py`` which
drives ``ConsoleEmitter`` in-process, this harness runs the real CLI as a
subprocess over a pseudo-terminal, lets Rich's ``Live`` actually refresh,
and captures the exact ANSI byte stream a real terminal would receive.
A pyte terminal emulator reduces the capture to a final screen state,
then Rich renders that state to an SVG which Chrome converts to a PNG.

Requires pyte — installed on-demand via ``uv run --with pyte``.  See the
``run.sh`` launcher in this directory for the one-liner.
"""

from __future__ import annotations

import io
import os
import pty
import select
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from render import svg_to_png  # noqa: E402

FAKE_BIN = SCRIPT_DIR / "fake_bin"
DEMO_RALPH = SCRIPT_DIR / "demo_ralph"
OUTPUT_DIR = SCRIPT_DIR / "output"

TERM_COLS = 120
TERM_LINES = 40
# Capture freezes mid-iteration so the peek Live panel is still active.
# Stub paces events at 1.8s each; at t~=9s we've seen ~5 events.
CAPTURE_SECONDS = 9.0


def _spawn_ralph() -> tuple[int, subprocess.Popen[bytes]]:
    """Spawn ``ralph run`` attached to a pty so peek thinks it's interactive.

    Returns (master_fd, process).  The caller reads from master_fd to
    capture everything the CLI writes to the terminal.
    """
    master_fd, slave_fd = pty.openpty()

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLUMNS"] = str(TERM_COLS)
    env["LINES"] = str(TERM_LINES)
    env["PATH"] = f"{FAKE_BIN}:{env.get('PATH', '')}"
    # Force-color in case Rich's TTY detection is fooled; the pty is
    # real, so this is a belt-and-braces guarantee.
    env["FORCE_COLOR"] = "1"

    # Use the venv's ralph directly so we don't get uv's VIRTUAL_ENV
    # mismatch warning in the captured output.
    ralph_bin = REPO_ROOT / ".venv" / "bin" / "ralph"
    cmd: list[str]
    if ralph_bin.exists():
        cmd = [str(ralph_bin), "run", str(DEMO_RALPH), "-n", "1"]
    else:
        cmd = ["uv", "run", "ralph", "run", str(DEMO_RALPH), "-n", "1"]

    proc = subprocess.Popen(
        cmd,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        env=env,
        cwd=str(REPO_ROOT),
        close_fds=True,
        start_new_session=True,
    )
    os.close(slave_fd)
    return master_fd, proc


def _capture_until_deadline(master_fd: int, deadline: float) -> bytes:
    """Read everything the child writes to the pty until *deadline*.

    Non-blocking loop: ``select`` waits at most until the deadline, reads
    up to 64 KB per iteration, and stops when the child closes the pty.
    """
    buf = bytearray()
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([master_fd], [], [], min(0.1, remaining))
        if not ready:
            continue
        try:
            chunk = os.read(master_fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _terminate(proc: subprocess.Popen[bytes]) -> None:
    """Best-effort stop of the ralph process group."""
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _render_terminal_to_svg(ansi_bytes: bytes, svg_path: Path, title: str) -> None:
    """Feed ANSI bytes through pyte, then render the screen grid via Rich.

    pyte is a pure-Python terminal emulator — it processes cursor moves,
    clears, and color codes into a stable row-by-row grid of styled
    cells.  That's exactly what a real terminal would display at the
    moment of capture.  We then hand those cells to Rich to produce an
    SVG, keeping the rendering stack identical to ``snapshot.py``.
    """
    import pyte  # lazy — requires ``uv run --with pyte``
    from rich.console import Console
    from rich.text import Text

    screen = pyte.Screen(TERM_COLS, TERM_LINES)
    stream = pyte.Stream(screen)
    stream.feed(ansi_bytes.decode("utf-8", errors="replace"))

    # ``file=StringIO()`` suppresses real-stdout echo; record=True still
    # captures styled output for save_svg.
    console = Console(
        record=True,
        file=io.StringIO(),
        force_terminal=True,
        color_system="truecolor",
        width=TERM_COLS + 2,
        height=TERM_LINES + 2,
        legacy_windows=False,
    )

    # Find the last non-blank row so the SVG doesn't end with dead space.
    last_row = 0
    for y in range(screen.lines):
        row = screen.buffer[y]
        if any(row[x].data.strip() for x in range(screen.columns)):
            last_row = y

    for y in range(last_row + 1):
        row = screen.buffer[y]
        line = Text()
        for x in range(screen.columns):
            cell = row[x]
            style_parts: list[str] = []
            fg = cell.fg
            bg = cell.bg
            if fg and fg != "default":
                style_parts.append(_format_color(fg))
            if bg and bg != "default":
                style_parts.append(f"on {_format_color(bg)}")
            if cell.bold:
                style_parts.append("bold")
            if cell.italics:
                style_parts.append("italic")
            if cell.underscore:
                style_parts.append("underline")
            style = " ".join(style_parts) if style_parts else None
            line.append(cell.data or " ", style=style)
        console.print(line)

    console.save_svg(str(svg_path), title=title)


def _format_color(color: str) -> str:
    """Translate a pyte color token into a Rich color string."""
    if len(color) == 6 and all(c in "0123456789abcdefABCDEF" for c in color):
        return f"#{color}"
    return color


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Spawning real ralph run (pty {TERM_COLS}x{TERM_LINES})…")
    master_fd, proc = _spawn_ralph()
    try:
        deadline = time.monotonic() + CAPTURE_SECONDS
        ansi_bytes = _capture_until_deadline(master_fd, deadline)
    finally:
        _terminate(proc)
        try:
            os.close(master_fd)
        except OSError:
            pass

    ansi_path = OUTPUT_DIR / "live_capture.ansi"
    ansi_path.write_bytes(ansi_bytes)
    print(f"  captured {len(ansi_bytes)} bytes -> {ansi_path.relative_to(REPO_ROOT)}")

    svg_path = OUTPUT_DIR / "live_capture.svg"
    png_path = OUTPUT_DIR / "live_capture.png"
    _render_terminal_to_svg(
        ansi_bytes, svg_path, title="ralphify TUI — live pty capture"
    )
    svg_to_png(svg_path, png_path)
    print(f"  rendered -> {png_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
