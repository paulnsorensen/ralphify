# Medium 03 — Keypress listener: EINTR / SIGTSTP / SIGCONT handling

**Original finding:** M5
**Severity:** Medium — breaks `p` after Ctrl+Z `fg` and silently dies on signal races
**Files:** `src/ralphify/_keypress.py`

## Problem

The POSIX keypress loop in `_keypress.py` has three signal-handling gaps:

### 1. `select.select` not wrapped in EINTR retry

```python
# src/ralphify/_keypress.py ~line 122 (POSIX loop)
def _loop_posix(self, fd, old_settings):
    try:
        tty.setcbreak(fd)
        while not self._stop.is_set():
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if not ready:
                continue
            ch = sys.stdin.read(1)
            if not ch:
                return
            self._on_key(ch)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
```

`select.select` can raise `InterruptedError` (Python 3's wrapper around EINTR) when a signal is delivered during the call. The current code doesn't catch it — the exception propagates out of the loop, the daemon thread dies, and the terminal state may be left in cbreak mode (atexit handler should restore, but an active interactive session keeps the broken state until the next full run).

### 2. No SIGTSTP / SIGCONT handling

The user hits Ctrl+Z. The process is stopped. They type `fg` to resume. The shell restores the foreground terminal to cooked mode (standard POSIX job control behavior). The listener thread is still running in cbreak-assuming mode, but the terminal is now cooked. Pressing `p` no longer fires `_on_key` until the user hits Enter, because cooked mode waits for a newline.

The listener doesn't install any SIGCONT handler to re-apply `tty.setcbreak` on resume.

### 3. No documentation of the limitation

`docs/cli.md`'s Peeking section doesn't mention that Ctrl+Z + `fg` breaks `p` until the listener reinitializes. Users who background ralphify will see `p` stop working and have no way to know why.

## Why it matters

- **EINTR is rare but real.** Any signal delivery during a select — even a SIGWINCH from resizing the terminal — can trigger it. A dead listener thread means `p` silently stops working until the next `ralph run`.
- **Ctrl+Z + `fg` is common.** Users routinely background long-running processes to check something in another shell. ralphify runs can be long. Losing `p` after `fg` is a real user-facing paper cut.
- **Low cost fix.** One try/except and one signal handler.

## Fix direction

### 1. EINTR retry loop

Wrap `select.select` in a retry:

```python
while not self._stop.is_set():
    try:
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
    except InterruptedError:
        continue
    if not ready:
        continue
    ...
```

This is the canonical POSIX pattern. `sys.stdin.read(1)` can also raise `InterruptedError` on some platforms; wrap it the same way or bundle both in one outer try.

### 2. SIGCONT handler to re-apply cbreak

Install a SIGCONT handler in the listener's `start()` method that re-applies `tty.setcbreak(fd)`:

```python
import signal

def start(self):
    ...
    self._old_sigcont = signal.signal(signal.SIGCONT, self._on_sigcont)
    ...

def _on_sigcont(self, signum, frame):
    try:
        tty.setcbreak(self._fd)
    except (OSError, termios.error):
        pass  # terminal closed or listener stopped
    # Chain to any previously-installed handler
    if callable(self._old_sigcont) and self._old_sigcont not in (signal.SIG_DFL, signal.SIG_IGN):
        self._old_sigcont(signum, frame)
```

And restore on `stop()`:

```python
def stop(self):
    ...
    signal.signal(signal.SIGCONT, self._old_sigcont)
    ...
```

**Caveat:** `signal.signal` can only be called from the main thread in Python. The listener runs in a daemon thread. Install the SIGCONT handler in the main thread before starting the daemon — i.e., do it in `KeypressListener.start()` on the caller's thread, not inside `_loop_posix`.

### 3. Document the SIGTSTP edge case

Add a line to `docs/cli.md`'s Peeking section:

> **Note:** If you background ralphify with Ctrl+Z, the `p` keybinding automatically re-initializes when you resume with `fg`. If you see `p` stop working after job-control operations, run `ralph run` again to re-attach the listener.

(If the SIGCONT fix works cleanly, this note may be unnecessary. Include it only if you find edge cases during testing.)

### Optional — SIGTSTP handler to restore terminal before suspend

Symmetric to SIGCONT: on SIGTSTP, restore `old_settings` so the shell sees a cooked terminal when the process is suspended. This is what a well-behaved curses app does. Usually not needed — the default SIGTSTP handler stops the process, and the shell restores the foreground terminal itself. Test first; add only if needed.

## Done when

- [ ] `select.select` and `sys.stdin.read` are wrapped in `InterruptedError` retry loops.
- [ ] SIGCONT handler re-applies `tty.setcbreak` on resume. Installed from the main thread in `start()`, restored in `stop()`.
- [ ] Manual test: run `ralph run my-ralph`, press Ctrl+Z, type `fg`, press `p`. Peek should toggle immediately without needing Enter.
- [ ] New test (if feasible): `tests/test_keypress.py::test_sigcont_reinitializes_cbreak` — mock `tty.setcbreak` and `signal.signal`, deliver SIGCONT manually via `os.kill(os.getpid(), signal.SIGCONT)`, assert `tty.setcbreak` is called again. May need careful fixture setup to avoid polluting the test runner's signal state.
- [ ] No regression in existing `test_keypress.py` tests.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_keypress.py` has separate POSIX and Windows paths (`_loop_posix`, `_loop_windows`). This task is POSIX-only; the Windows path uses `msvcrt.kbhit()` polling which has no equivalent issue.
- Windows has no SIGCONT/SIGTSTP equivalents — don't install handlers on Windows.
- `signal.signal` from a non-main thread raises `ValueError("signal only works in main thread of the main interpreter")`. Install from the caller of `KeypressListener.start()`.
- `termios.tcsetattr` calls during signal handlers are **not async-signal-safe** in the POSIX sense, but Python's signal handlers run between bytecode instructions (not in the kernel's signal context), so Python-level signal handlers can call non-reentrant functions safely. This is a Python implementation detail and is fine to rely on.
- `tty.setcbreak(fd)` is idempotent; safe to call multiple times.
- **Scope discipline:** do not rewrite the listener. This is three surgical changes (EINTR retry + SIGCONT handler + optional docs line). Any temptation to refactor the start/stop lifecycle belongs in a separate task.
