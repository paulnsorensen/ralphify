# High 02 — `_read_agent_stream` deadline + readahead buffering

**Original findings:** H2 (deadline not enforced on silent agents) + H3 (8KB readahead → peek bursts)
**Severity:** High — `--timeout` not enforced in streaming mode; peek stutters on Claude Code
**Files:** `src/ralphify/_agent.py`

## Problem

`_read_agent_stream` in the streaming path uses:

```python
# src/ralphify/_agent.py ~203
for line in stdout:
    stdout_lines.append(line)
    if on_output_line is not None:
        on_output_line(line.rstrip("\r\n"), _STDOUT)
    ...
    if deadline is not None and time.monotonic() > deadline:
        return _StreamResult(..., timed_out=True)
```

Two problems with `for line in stdout:`:

### 1. Deadline not enforced on silent agents

`for line in stdout` calls `TextIOWrapper.__next__`, which internally blocks in `readline()` until a line arrives. The deadline check happens **only between lines**. A slow or hung agent that produces no output blocks indefinitely — the loop body never runs — and `--timeout 60` never fires.

The old blocking path used `proc.communicate(timeout=…)` which enforced the deadline regardless of output. The streaming path now has a strictly weaker guarantee.

### 2. 8KB readahead buffering → peek bursts

`TextIOWrapper.__iter__` reads in chunks of `_CHUNK_SIZE` (typically 8192 bytes). It fills its internal buffer, then yields lines from it. If the agent emits lines slowly, they stay buffered in Python until the chunk fills or the stream flushes. The peek feature shows them in bursts instead of line-at-a-time.

This is **inconsistent** with the blocking path, which uses `iter(stream.readline, "")` in `_pump_stream` — that's unbuffered-at-the-Python-layer and flows line-at-a-time. Claude Code users (streaming path) get a choppy peek experience; Aider users (blocking path) don't.

## Why it matters

- **H2 is a safety regression:** `--timeout` is the escape hatch for hung agents. In streaming mode (the default for Claude Code, ralphify's flagship agent), that escape hatch is broken. If Claude hangs on a network call with no output, ralphify waits forever.
- **H3 is a UX regression:** the whole point of the peek feature is "see what the agent is doing in real time." Buffered bursts defeat that. The bug is especially visible for Claude Code since its `stream-json` output is one JSON object per line at relatively slow cadence.

## Fix direction

One change fixes both problems: replace `for line in stdout:` with `iter(stdout.readline, "")` **and** add a `select`-based wait with a per-call timeout so the deadline is polled between reads.

```python
import select

def _read_agent_stream(stdout, deadline, on_activity, on_output_line=None):
    stdout_lines: list[str] = []
    last_event: dict[str, Any] | None = None

    while True:
        if deadline is not None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return _StreamResult(
                    stdout_lines=stdout_lines,
                    last_event=last_event,
                    timed_out=True,
                )
            # Wait for data or deadline, whichever comes first.
            ready, _, _ = select.select([stdout], [], [], remaining)
            if not ready:
                return _StreamResult(
                    stdout_lines=stdout_lines,
                    last_event=last_event,
                    timed_out=True,
                )

        line = stdout.readline()
        if not line:  # EOF
            return _StreamResult(
                stdout_lines=stdout_lines,
                last_event=last_event,
                timed_out=False,
            )
        stdout_lines.append(line)
        if on_output_line is not None:
            on_output_line(line.rstrip("\r\n"), _STDOUT)
        # ... existing JSON parsing / on_activity logic ...
```

Key properties:

- `select.select(..., remaining)` blocks up to `remaining` seconds, returning immediately if data arrives. No deadline slippage beyond select's own granularity (sub-millisecond).
- `stdout.readline()` after a positive `select` may still block briefly if only a partial line is buffered — that's OK, it's bounded by the line length.
- When `deadline is None`, skip the `select` entirely and just `readline()`.
- `select.select` is raising-safe: wrap in `try: except InterruptedError: continue` for EINTR (same issue as `medium-03`, but localized here).

### Caveat — file handles vs raw fds

`proc.stdout` is a `TextIOWrapper` around a `BufferedReader` around a raw fd. `select.select` works on the wrapper because `TextIOWrapper.fileno()` returns the underlying fd. However, the `BufferedReader` may have data already buffered that `select` can't see — it only sees the kernel-side pipe. If you've done a previous `readline` that buffered extra bytes, `select` will report no data while `readline` would actually return from the buffer.

Fix: check `stdout.buffer.peek(1)` (returns bytes already buffered) before `select`. If non-empty, skip `select` and call `readline` directly. Alternatively, reopen stdout with `bufsize=1` in `Popen` to get line-buffered mode, which eliminates readahead entirely.

**Prefer line-buffering at the `Popen` level** (`bufsize=1` + `text=True`) if `SUBPROCESS_TEXT_KWARGS` doesn't already set it. That removes the readahead problem cleanly and the `select` path works as-is.

## Done when

- [ ] `_read_agent_stream` polls the deadline between reads, not just between lines.
- [ ] Peek lines in streaming mode flow line-at-a-time (not in 8KB bursts). Verify with a fake agent that emits one line every 200ms and observe the callback fires at ~200ms intervals, not in bursts.
- [ ] `SUBPROCESS_TEXT_KWARGS` uses line-buffered mode (`bufsize=1`) — or the `buffer.peek` workaround is in place. Pick one and document.
- [ ] `select.InterruptedError` is caught and the loop retries (signal safety).
- [ ] New test `tests/test_agent.py::test_streaming_timeout_enforced_on_silent_agent` — spawn a Python subprocess that reads stdin, sleeps 10s, then writes nothing; pass `timeout=1.0`, assert the call returns with `timed_out=True` within ~2s.
- [ ] New test `tests/test_agent.py::test_streaming_peek_flows_line_at_a_time` — use a fake agent that emits timestamped lines with small sleeps, assert the `on_output_line` callback fires promptly (no line is delayed by more than, say, 500ms after emission).
- [ ] Existing streaming tests pass.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_read_agent_stream` is at `src/ralphify/_agent.py:182-228`. It's called from `_run_agent_streaming` (the Claude Code path).
- `SUBPROCESS_TEXT_KWARGS` is in `src/ralphify/_output.py` — check whether `bufsize` is set there. If not, setting `bufsize=1` globally affects both execution paths, which is desired.
- `_pump_stream` (used in the blocking path) already uses `iter(stream.readline, "")` and benefits from line-buffering; this task aligns the streaming path with it.
- `select.select` is POSIX only; on Windows, `select` on pipes doesn't work. If ralphify targets Windows (it does, per the `IS_WINDOWS` guards elsewhere), the Windows path needs a different strategy: spawn a reader thread that shovels lines into a `queue.Queue`, then `queue.get(timeout=remaining)` on the main thread. This is architecturally heavier. Consider scoping: does ralphify support the Claude Code streaming path on Windows at all? Check `_output.py:IS_WINDOWS` and related guards before committing to a cross-platform fix.
- **Do not** modify the blocking path's `_pump_stream` — it's already correct. This task is strictly about `_read_agent_stream`.
- Test fakes: `tests/helpers.py` has subprocess-spawning utilities. Prefer spawning a real `python -c '...'` to fake-mocking, because the bugs here live at the I/O layer.
