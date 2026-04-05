# Critical 04 — Bounded reader-thread joins in `finally`

**Original findings:** C4 (unbounded joins, Windows/grandchild hangs) + C5 (joins not in `finally`) + M3 (streaming-path unsynchronized read after timed join)
**Severity:** Critical — guaranteed hang on realistic subprocess topologies
**Files:** `src/ralphify/_agent.py`

## Problem

Three related defects in the reader-thread lifecycle:

### 1. Unbounded joins (`C4`)

```python
# src/ralphify/_agent.py ~414
returncode = proc.wait(timeout=timeout)
...
stdout_thread.join()  # NO timeout
stderr_thread.join()  # NO timeout
```

`readline()` on an OS pipe only returns EOF when the **write end** is closed. If the agent spawned a grandchild that inherited the stdout/stderr fds (extremely common — any coding agent that shells out to `pytest`, `make`, `npm`, `docker`, …), the grandchild keeps the write end open after the parent agent exits. The reader thread blocks on `readline()` forever. The main thread blocks on `join()` forever. The CLI appears frozen.

On Windows this is worse: `SESSION_KWARGS` is empty → `_kill_process_group` only kills the direct child, never the subtree → grandchildren always escape.

### 2. Joins not in `finally` (`C5`)

```python
# src/ralphify/_agent.py ~378
try:
    ...
    stdout_thread.start(); stderr_thread.start()
    proc.stdin.write(prompt); proc.stdin.close()
    returncode = proc.wait(timeout=timeout)
    stdout_thread.join(); stderr_thread.join()   # ← inside try
except KeyboardInterrupt:
    _kill_process_group(proc); proc.wait()
    stdout_thread.join(timeout=1.0)              # ← also in KbdInt branch
    stderr_thread.join(timeout=1.0)
    raise
finally:
    if proc.poll() is None:
        _kill_process_group(proc); proc.wait()
    # ← no join here
```

Any exception other than `KeyboardInterrupt` (`OSError`, `RuntimeError`, bug in the pump) skips the joins entirely. Threads leak as daemons. The main thread returns to the engine with live readers still touching the pipes.

### 3. Streaming-path race after timed join (`M3`)

```python
# src/ralphify/_agent.py ~304
if stderr_thread is not None:
    stderr_thread.join(timeout=1.0)

log_file = _write_log(..., "".join(stderr_lines))
```

If the 1-second join times out (e.g. slow kernel, grandchild holding the pipe), the main thread reads `stderr_lines` while the pump thread is still appending. `list.append` is GIL-atomic so no crash, but **late writes arrive after `"".join`** and are clipped from the log with no warning.

## Why it matters

- Any ralph whose agent shells out to a subprocess can wedge the parent after the agent exits. Claude Code, Aider, Codex, `bash`-backed agents — all realistic.
- On Windows this is a hard regression: the pre-refactor path didn't join at all (`proc.communicate` handled draining), so this is a new class of hang that ships with the feature.
- The timed-join-then-read race silently truncates logs on any remotely slow system, which is the single worst failure mode for a tool whose purpose is to keep a run log.

## Fix direction

Three coordinated changes:

### A. Close parent-side pipes after `proc.wait()` returns

`proc.stdout.close()` / `proc.stderr.close()` **on the parent side** forces EOF to propagate even if grandchildren still hold the write end, because the parent's read fd is gone. The pump's `readline()` returns `""` and the loop exits. Do this in a `finally` just before joining:

```python
finally:
    if proc.poll() is None:
        _kill_process_group(proc)
        proc.wait(timeout=5.0)  # note: bounded; see below
    for pipe in (proc.stdout, proc.stderr):
        if pipe is not None:
            try:
                pipe.close()
            except Exception:
                pass
    for t in (stdout_thread, stderr_thread):
        if t is not None and t.is_alive():
            t.join(timeout=5.0)
            if t.is_alive():
                # Daemon thread; log a warning and let it die with the process.
                ...
```

### B. Bound every blocking call in the teardown path

- `proc.wait()` in the post-kill finally → add `timeout=5.0`, catch `TimeoutExpired`, log warning.
- `thread.join()` → always pass a timeout (5s is generous; the pipes should EOF within milliseconds of the parent-side close).
- Log a warning (via emitter or `sys.stderr`) if any join times out — this is the signal that a grandchild is holding the fds and the user should know their log may be incomplete.

### C. Move joins into `finally` and remove from `except KeyboardInterrupt`

Joins belong in one place: `finally`. The `except KeyboardInterrupt` branch should only handle the SIGINT semantics (kill the process group and re-raise); cleanup is shared.

After these changes, apply the same shape to the streaming path (`_run_agent_streaming`): close `proc.stderr` before joining `stderr_thread`, bound the join, do it in `finally`.

## Done when

- [ ] Joins live exclusively in `finally` with a bounded timeout (5s recommended) in both `_run_agent_blocking` and `_run_agent_streaming`.
- [ ] Parent-side `proc.stdout.close()` / `proc.stderr.close()` happens in `finally` before the joins.
- [ ] `proc.wait()` in the finally block is also bounded.
- [ ] Join timeout exceeded → log warning (stderr or via the emitter) naming which stream failed to drain. This is visible feedback that something is off; do not silently swallow.
- [ ] New test: `tests/test_agent.py::test_grandchild_inheriting_stdout_does_not_hang` — spawn a Python process that forks a grandchild that inherits stdout and sleeps 10s; the parent exits after 0.1s; assert `_run_agent_blocking` returns within ~6s (grace for the 5s join timeout) with partial output captured.
- [ ] New test: `tests/test_agent.py::test_joins_happen_in_finally` — inject an exception after threads start but before `proc.wait`; assert both threads have exited (`.is_alive() is False`) by the time the exception propagates.
- [ ] Existing tests still pass (`test_streaming_large_stderr_drained_concurrently` in particular).
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_kill_process_group` is in `src/ralphify/_agent.py` — on POSIX it `os.killpg(pgid, SIGTERM)` then SIGKILL; on Windows it falls back to `proc.kill()`. Windows has no pgid, so the grandchild hazard is permanent until the user fixes the topology.
- `proc.stdout.close()` / `proc.stderr.close()` is safe even if the reader thread is mid-`readline`; the thread wakes with either `""` (EOF) or `ValueError("I/O operation on closed file")`. `critical-02` already handles both cases if it's landed first. If `critical-02` is not yet landed, you should land that one first — the exception handling in `_pump_stream` is load-bearing for this fix.
- **Task ordering:** this task depends on `critical-02`. Do `critical-02` first.
- `threading.Thread.is_alive()` returns False for unstarted or completed threads; safe to call unconditionally.
- The 5-second timeout is a suggestion; tune based on observed kernel latency. The principle is "bounded, with a loud signal on timeout," not a specific number.
- **Do not** try to kill grandchildren from Python — that's a rabbit hole (PG on POSIX is only reliable if the agent didn't `setsid`, and Windows needs Job Objects). Logging a warning and letting the main thread move on is the right call.
