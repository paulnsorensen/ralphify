"""Cross-platform single-keypress listener for interactive CLI toggles.

The ``KeypressListener`` runs a daemon thread that reads one character at
a time from stdin and invokes a user-supplied callback for each key.  It
is used by the ``ralph run`` command to implement the ``p`` peek toggle.

Design notes:

- Only activates when stdin is a real TTY.  In CI, when piped, or during
  tests, ``start()`` is a no-op and the callback is never invoked — so
  piped invocations like ``ralph run ... | cat`` keep working.
- On POSIX the stdin fd is put into cbreak (not raw) mode so that signal
  characters like Ctrl+C continue to deliver SIGINT to the process, which
  leaves the existing ``cli.run`` SIGINT handler intact.
- On Windows the MSVCRT console API has no equivalent signal delivery, so
  we detect ``\\x03`` (Ctrl+C) explicitly and call ``_thread.interrupt_main``
  to raise ``KeyboardInterrupt`` on the main thread — the same exception
  the POSIX SIGINT chain produces.
- The terminal settings are always restored in a ``try/finally`` block
  even if the loop raises, **and** an ``atexit`` hook is registered as a
  safety net so crashes or ``os._exit`` can't leave the user with a wedged
  shell (no echo, no line editing).  The hook is unregistered once the
  loop exits normally.
"""

from __future__ import annotations

import atexit
import os
import signal
import sys
import threading
from collections.abc import Callable
from types import FrameType


_POLL_INTERVAL = 0.1  # seconds between stop-flag checks (POSIX select)
_WIN_POLL_INTERVAL = 0.05  # seconds between kbhit() checks on Windows
_THREAD_JOIN_TIMEOUT = 1.0  # seconds to wait for listener thread on stop()

# Windows console control characters
_CTRL_C = "\x03"
_WIN_SCANCODE_PREFIXES = ("\x00", "\xe0")  # prefix bytes for arrow/function keys


class KeypressListener:
    """Background thread that delivers single keypresses to a callback."""

    def __init__(self, on_key: Callable[[str], None]) -> None:
        self._on_key = on_key
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._atexit_hook: Callable[[], None] | None = None
        self._old_sigcont: Callable[[int, FrameType | None], object] | int | None = (
            signal.SIG_DFL
        )
        self._sigcont_installed = False

    def start(self) -> None:
        """Begin listening for keypresses.

        No-op when stdin is not a TTY — the listener simply does nothing
        and peek is unavailable, but the rest of ``ralph run`` works.
        """
        try:
            if not sys.stdin.isatty():
                return
        except (ValueError, OSError):
            return

        self._stop.clear()

        # Install SIGCONT handler on POSIX so cbreak is re-applied after
        # Ctrl+Z / fg.  Must be installed from the main thread.
        if hasattr(signal, "SIGCONT"):
            try:
                self._old_sigcont = signal.getsignal(signal.SIGCONT)
                signal.signal(signal.SIGCONT, self._on_sigcont)
                self._sigcont_installed = True
            except (OSError, ValueError):
                pass

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _on_sigcont(self, signum: int, frame: FrameType | None) -> None:
        """Re-apply cbreak after the process resumes from Ctrl+Z / fg."""
        import tty

        try:
            fd = sys.stdin.fileno()
            tty.setcbreak(fd)
        except Exception:
            pass
        # Chain to any previously-installed handler.
        old = self._old_sigcont
        if not isinstance(old, int) and old is not None:
            old(signum, frame)

    def stop(self) -> None:
        """Stop the listener and wait for the thread to finish.

        If the thread does not exit within the join timeout we keep the
        reference so a subsequent ``stop()`` call can retry, rather than
        silently dropping the handle and leaking termios state.
        """
        self._stop.set()

        # Restore the previous SIGCONT handler.
        if self._sigcont_installed:
            try:
                signal.signal(signal.SIGCONT, self._old_sigcont)
            except (OSError, ValueError):
                pass
            self._sigcont_installed = False
        thread = self._thread
        if thread is not None:
            thread.join(timeout=_THREAD_JOIN_TIMEOUT)
            if not thread.is_alive():
                self._thread = None
            else:
                # Best-effort warning — the atexit hook registered in the
                # posix loop will still restore the terminal on process
                # exit, so the user's shell will not be wedged.
                try:
                    sys.stderr.write(
                        f"ralphify: keypress listener did not exit within {_THREAD_JOIN_TIMEOUT}s\n"
                    )
                except Exception:
                    pass

    def _loop(self) -> None:
        if os.name == "nt":
            self._loop_windows()
        else:
            self._loop_posix()

    def _loop_posix(self) -> None:
        import select
        import termios
        import tty

        try:
            fd = sys.stdin.fileno()
        except (ValueError, OSError):
            return

        try:
            old_settings = termios.tcgetattr(fd)
        except termios.error:
            return

        def _restore() -> None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except termios.error:
                pass

        # Safety net: if the process crashes or calls os._exit() without
        # running our finally block, atexit still restores the terminal.
        self._atexit_hook = _restore
        atexit.register(_restore)

        try:
            tty.setcbreak(fd)
            while not self._stop.is_set():
                try:
                    ready, _, _ = select.select([sys.stdin], [], [], _POLL_INTERVAL)
                except InterruptedError:
                    continue
                if not ready:
                    continue
                try:
                    ch = sys.stdin.read(1)
                except InterruptedError:
                    continue
                except (ValueError, OSError):
                    return
                if not ch:
                    return
                self._on_key(ch)
        finally:
            _restore()
            try:
                atexit.unregister(_restore)
            except Exception:
                pass
            self._atexit_hook = None

    def _loop_windows(self) -> None:  # pragma: no cover - exercised only on Windows
        import _thread
        import importlib
        import time

        # Look up msvcrt via importlib + getattr so type checkers running
        # on non-Windows platforms don't flag the Windows-only members.
        msvcrt = importlib.import_module("msvcrt")
        kbhit = getattr(msvcrt, "kbhit")
        getwch = getattr(msvcrt, "getwch")

        while not self._stop.is_set():
            if not kbhit():
                time.sleep(_WIN_POLL_INTERVAL)
                continue
            ch = getwch()
            # Ctrl+C: the Windows console API does not deliver SIGINT for
            # us since we've taken over reading stdin — raise it manually.
            if ch == _CTRL_C:
                _thread.interrupt_main()
                return
            # Scancode prefix bytes precede arrow / function / navigation
            # keys.  Drain the scancode byte that follows and ignore it so
            # it never reaches the peek callback as a stray character.
            if ch in _WIN_SCANCODE_PREFIXES:
                try:
                    getwch()
                except Exception:
                    pass
                continue
            self._on_key(ch)
