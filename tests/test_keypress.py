"""Tests for the KeypressListener.

Real TTYs aren't available under pytest, so these tests exercise two
things:

1. ``start()`` no-ops when stdin is not a TTY (the CI/pipe path).
2. The Unix loop delivers single keystrokes to the callback when given a
   stdin-like object that ``select`` reports as readable.
"""

from __future__ import annotations

import os
import signal
import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from ralphify._keypress import KeypressListener


class TestStartNoopWithoutTty:
    def test_no_thread_spawned_when_stdin_not_tty(self):
        calls: list[str] = []
        listener = KeypressListener(lambda key: calls.append(key))

        with patch.object(sys.stdin, "isatty", return_value=False):
            listener.start()

        try:
            assert listener._thread is None
            assert calls == []
        finally:
            listener.stop()


@pytest.mark.skipif(os.name == "nt", reason="Unix-only posix keypress loop")
class TestPosixLoopDispatch:
    def test_keypress_invokes_callback(self):
        """Drive ``_loop_posix`` without a real TTY by stubbing the tty/termios
        setup and feeding a fake readable stdin through ``select.select``.

        The stdin ``read`` side_effect yields ``"p"`` then ``""`` — the empty
        string causes the loop to return on EOF, so the test is deterministic
        and does not rely on the stop flag being checked between polls.
        """
        received: list[str] = []
        callback_event = threading.Event()

        def on_key(key: str) -> None:
            received.append(key)
            callback_event.set()

        listener = KeypressListener(on_key)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([sys.stdin], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
            patch.object(sys.stdin, "read", side_effect=["p", ""]),
        ):
            listener.start()
            assert callback_event.wait(timeout=2.0), "callback was not invoked"
            listener.stop()

        assert received == ["p"]

    def test_stop_is_idempotent(self):
        listener = KeypressListener(lambda key: None)
        # No thread running — stop() must not raise.
        listener.stop()
        listener.stop()

    def test_loop_exits_on_stop_flag(self):
        """The loop must observe the stop flag between polls and exit
        without requiring any input."""
        listener = KeypressListener(lambda key: None)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
        ):
            listener.start()
            # Let the loop poll at least once, then stop.
            time.sleep(0.05)
            listener.stop()

        # If the thread didn't exit, ``stop()`` would time out and the
        # thread would still be alive.
        assert listener._thread is None

    def test_stop_restores_termios_with_tcsadrain(self):
        """On normal stop, ``_loop_posix`` must call ``tcsetattr`` with the
        saved settings and ``TCSADRAIN`` so the terminal is returned to the
        same mode we captured in ``tcgetattr``."""
        import termios

        saved_settings = ["saved-termios-snapshot"]
        tcsetattr_calls: list[tuple] = []

        def fake_tcsetattr(fd, when, settings):
            tcsetattr_calls.append((fd, when, settings))

        listener = KeypressListener(lambda key: None)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([], [], [])),
            patch("termios.tcgetattr", return_value=saved_settings),
            patch("termios.tcsetattr", side_effect=fake_tcsetattr),
            patch("tty.setcbreak"),
        ):
            listener.start()
            time.sleep(0.05)
            listener.stop()

        assert any(
            when == termios.TCSADRAIN and settings == saved_settings
            for _fd, when, settings in tcsetattr_calls
        ), f"expected TCSADRAIN restore call; got {tcsetattr_calls!r}"

    def test_atexit_hook_cleared_after_normal_stop(self):
        """After a normal stop, the atexit safety hook should be cleared so
        it does not fire on process exit (the terminal was already restored
        by the loop's finally block)."""
        listener = KeypressListener(lambda key: None)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
        ):
            listener.start()
            time.sleep(0.05)
            listener.stop()

        assert listener._atexit_hook is None

    def test_eintr_on_select_does_not_kill_loop(self):
        """An InterruptedError from select.select (e.g. SIGWINCH during
        poll) must be retried, not propagated out of the loop."""
        received: list[str] = []
        callback_event = threading.Event()

        def on_key(key: str) -> None:
            received.append(key)
            callback_event.set()

        # First call raises InterruptedError, second returns readable,
        # then the stdin read yields "p" then EOF.
        select_side_effects = [
            InterruptedError,
            ([sys.stdin], [], []),
            ([sys.stdin], [], []),
        ]

        def fake_select(*args, **kwargs):
            effect = select_side_effects.pop(0)
            if isinstance(effect, type) and issubclass(effect, BaseException):
                raise effect()
            return effect

        listener = KeypressListener(on_key)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", side_effect=fake_select),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
            patch.object(sys.stdin, "read", side_effect=["p", ""]),
        ):
            listener.start()
            assert callback_event.wait(timeout=2.0), "callback was not invoked"
            listener.stop()

        assert received == ["p"]

    def test_eintr_on_stdin_read_does_not_kill_loop(self):
        """An InterruptedError from sys.stdin.read(1) must be retried."""
        received: list[str] = []
        callback_event = threading.Event()

        def on_key(key: str) -> None:
            received.append(key)
            callback_event.set()

        read_side_effects = [InterruptedError, "x", ""]

        def fake_read(n):
            effect = read_side_effects.pop(0)
            if isinstance(effect, type) and issubclass(effect, BaseException):
                raise effect()
            return effect

        listener = KeypressListener(on_key)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([sys.stdin], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
            patch.object(sys.stdin, "read", side_effect=fake_read),
        ):
            listener.start()
            assert callback_event.wait(timeout=2.0), "callback was not invoked"
            listener.stop()

        assert received == ["x"]


@pytest.mark.skipif(os.name == "nt", reason="Unix-only SIGCONT handling")
@pytest.mark.skipif(not hasattr(signal, "SIGCONT"), reason="SIGCONT not available")
class TestSigcontHandler:
    def test_sigcont_reinstalls_cbreak(self):
        """Delivering SIGCONT to the process should re-apply tty.setcbreak
        so that the peek keypress listener works after Ctrl+Z / fg."""
        setcbreak_mock = MagicMock()
        listener = KeypressListener(lambda key: None)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak", setcbreak_mock),
        ):
            listener.start()
            time.sleep(0.05)

            # setcbreak is called once during loop startup.
            initial_calls = setcbreak_mock.call_count

            # Deliver SIGCONT — the handler should call setcbreak again.
            os.kill(os.getpid(), signal.SIGCONT)
            time.sleep(0.05)

            assert setcbreak_mock.call_count > initial_calls, (
                "tty.setcbreak was not re-called after SIGCONT"
            )

            listener.stop()

    def test_sigcont_handler_restored_after_stop(self):
        """stop() must restore the previous SIGCONT handler."""
        original_handler = signal.getsignal(signal.SIGCONT)
        listener = KeypressListener(lambda key: None)

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch.object(sys.stdin, "fileno", return_value=0),
            patch("select.select", return_value=([], [], [])),
            patch("termios.tcgetattr", return_value=[]),
            patch("termios.tcsetattr"),
            patch("tty.setcbreak"),
        ):
            listener.start()
            time.sleep(0.05)

            # While running, the handler should be our custom one.
            assert listener._sigcont_installed is True

            listener.stop()

        # After stop, the original handler should be restored.
        assert listener._sigcont_installed is False
        restored_handler = signal.getsignal(signal.SIGCONT)
        assert restored_handler == original_handler

    def test_sigcont_chains_to_previous_handler(self):
        """The SIGCONT handler should chain to any previously-installed
        callable handler."""
        chained_calls: list[int] = []

        def previous_handler(signum, frame):
            chained_calls.append(signum)

        old = signal.signal(signal.SIGCONT, previous_handler)
        try:
            listener = KeypressListener(lambda key: None)

            with (
                patch.object(sys.stdin, "isatty", return_value=True),
                patch.object(sys.stdin, "fileno", return_value=0),
                patch("select.select", return_value=([], [], [])),
                patch("termios.tcgetattr", return_value=[]),
                patch("termios.tcsetattr"),
                patch("tty.setcbreak"),
            ):
                listener.start()
                time.sleep(0.05)

                os.kill(os.getpid(), signal.SIGCONT)
                time.sleep(0.05)

                listener.stop()

            assert len(chained_calls) >= 1, "previous handler was not chained"
            assert chained_calls[0] == signal.SIGCONT
        finally:
            signal.signal(signal.SIGCONT, old)
