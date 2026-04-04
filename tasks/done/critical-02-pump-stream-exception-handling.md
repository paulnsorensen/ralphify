# Critical 02 — `_pump_stream` exception containment

**Original findings:** C2 (raising callback wedges subprocess) + M9 (`ValueError` on closed file)
**Severity:** Critical — a single raising callback hangs or spuriously times out the agent
**Files:** `src/ralphify/_agent.py`

## Problem

`_pump_stream` is the reader-thread body used by both the blocking and streaming paths to drain stdout/stderr line-by-line. Its entire body is:

```python
# src/ralphify/_agent.py:320-334
def _pump_stream(
    stream: IO[str],
    buffer: list[str],
    stream_name: OutputStream,
    on_output_line: Callable[[str, OutputStream], None] | None,
) -> None:
    for line in iter(stream.readline, ""):
        buffer.append(line)
        if on_output_line is not None:
            on_output_line(line.rstrip("\r\n"), stream_name)
```

Zero exception handling. Two failure modes:

1. **Callback raises** (`on_output_line` is a lambda that goes through emitter → event construction → Rich print → tty write). Any raise anywhere in that chain — queue-full in a `QueueEmitter`, Rich markup bug, `UnicodeEncodeError` on a weird line, buggy user handler in the Python API — propagates out of the daemon thread. The thread dies silently (daemon thread exceptions are not surfaced), the pipe stops draining, the child fills its OS pipe buffer, and blocks.

2. **`readline` raises** `ValueError("I/O operation on closed file")` if the main thread closes the pipe concurrently (GC, explicit cleanup, `with` block exit). Thread dies, log gets truncated, no warning.

## Why it matters

After the thread dies:

- `proc.wait(timeout=timeout)` either hangs forever (when `timeout is None`) or spuriously times out (the user is told the agent timed out when it actually finished fine, but the output never reached Python).
- The logged output is silently truncated — tail of the iteration is lost, the user has no way to know.
- On CI where the agent produces JSON events consumed by downstream tooling, a single malformed line permanently breaks that run.

Because the feature is on by default in any TTY, this is a live footgun for anyone with a Python-API integration that raises from a handler.

## Fix direction

Wrap the loop so (a) callback exceptions never kill draining, (b) `readline` exceptions let the thread exit cleanly:

```python
def _pump_stream(stream, buffer, stream_name, on_output_line):
    try:
        for line in iter(stream.readline, ""):
            buffer.append(line)
            if on_output_line is not None:
                try:
                    on_output_line(line.rstrip("\r\n"), stream_name)
                except Exception:
                    # Callback is best-effort; draining must not stop.
                    # Consider sys.excepthook for visibility in dev.
                    pass
    except (ValueError, OSError):
        # Pipe closed concurrently — exit cleanly so join() returns.
        pass
```

Two design choices worth thinking through:

- **Should callback exceptions be logged?** Silent `pass` hides real bugs. `sys.excepthook` on a dedicated `sys.exc_info()` call surfaces to stderr in dev but pollutes CI logs. A conservative middle ground: log to a module-level counter and emit one warning at the end of the run if any occurred.
- **Should buffering continue after `readline` fails?** No — if the pipe is closed the fd is gone; there's nothing to read. Exit the loop.

## Done when

- [ ] Both try/except layers are in place.
- [ ] New test `tests/test_agent.py::test_pump_stream_continues_when_callback_raises` — run a real subprocess, pass a callback that raises on the first line, assert that all subsequent lines are still captured in `buffer` and the subprocess exits cleanly.
- [ ] New test `tests/test_agent.py::test_pump_stream_exits_cleanly_on_closed_stream` — start `_pump_stream` on a pipe, close the read end, assert the thread exits within a short bounded join.
- [ ] No regression in existing `_pump_stream` tests.
- [ ] `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run ty check` all pass.

## Context

- `_pump_stream` is called from both `_run_agent_blocking` (two threads) and `_run_agent_streaming` (one thread, stderr only). All three call sites benefit from this fix.
- Daemon threads (`daemon=True`) do not surface exceptions; see `threading.excepthook` (Python 3.8+) if you want a module-level install instead of per-call try/except. Per-call is more localized and preferred here.
- `buffer.append(line)` is GIL-atomic so no lock needed for the append itself.
- Related but **out of scope** for this task: reader-thread join timeouts (that's `critical-04`) and whether the event is even emitted when peek is off (`medium-01`). This task is purely about survivability of the pump loop.
- The fix is small (a few lines) but the test coverage is the real deliverable — these are exactly the flaky-looking "agent timed out" bugs that are impossible to diagnose later without a regression test locking in the behavior.
