# Critical 03 — `stdin.write` timeout enforcement

**Original finding:** C3
**Severity:** Critical — `--timeout` silently stops enforcing in a realistic case
**Files:** `src/ralphify/_agent.py`

## Problem

The blocking path is now:

```python
# src/ralphify/_agent.py ~396
try:
    proc.stdin.write(prompt)
except BrokenPipeError:
    pass
finally:
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass

try:
    returncode = proc.wait(timeout=timeout)
except subprocess.TimeoutExpired:
    ...
```

The streaming path at `:283-288` has the same shape. **`proc.stdin.write(prompt)` has no timeout.** The pre-refactor code used `proc.communicate(input=prompt, timeout=timeout)`, which enforced the user's `--timeout` across both stdin delivery AND wait. The new split design only enforces it on `wait`.

## Why it matters

Concrete failure case: an agent that starts up, blocks on a network call before reading stdin, eventually decides to exit. The sequence:

1. Parent spawns child, starts reader threads for stdout/stderr.
2. Parent calls `proc.stdin.write(prompt)`. Prompt is, say, 120 KB.
3. Pipe buffer (~64 KB on Linux) fills. `write` blocks waiting for the child to drain its stdin.
4. Child is stuck in a `requests.get(...)` call with no outer timeout. It never reads stdin.
5. Parent is now blocked in `write` forever. `proc.wait(timeout=…)` is never reached. The user's `--timeout 60` does nothing.

This is exactly the hang `ralph run --timeout` is supposed to prevent. The feature flag is a lie in this code path.

Secondary concern: even a well-behaved agent that is momentarily slow to read stdin (busy importing modules, JIT warm-up, etc.) briefly blocks the main thread in `write`. Normally fine, but combined with `critical-04`'s unbounded joins, any extra blocking on the main thread compounds the hang surface.

## Fix direction

You have three reasonable options. Pick one based on complexity vs fidelity tradeoff.

### Option A — Write on a background thread with a deadline (recommended)

Spawn a short-lived writer thread alongside the reader threads:

```python
write_error: list[BaseException] = []
def _write():
    try:
        proc.stdin.write(prompt)
    except BaseException as exc:
        write_error.append(exc)
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass

writer = threading.Thread(target=_write, daemon=True)
writer.start()

try:
    returncode = proc.wait(timeout=timeout)
except subprocess.TimeoutExpired:
    _kill_process_group(proc)
    ...
writer.join(timeout=1.0)
```

Pros: minimal change, same timeout applies to the whole stdin-delivery-plus-wait pipeline because killing the process group makes the writer's blocked `write` return with `BrokenPipeError`, which is already swallowed.

Cons: one extra thread per agent invocation (cheap).

### Option B — Revert to `proc.communicate`

`communicate` enforces the timeout across everything but spawns its own reader threads that conflict with ours. You'd have to drop the pre-spawned readers and lose the "start readers before writing stdin" property that fixed the original deadlock. **Do not use this option** — it reintroduces the bug the refactor was supposed to fix.

### Option C — Non-blocking write + `select`

Put stdin in non-blocking mode, loop on `select.select([], [stdin], [], remaining_deadline)`, write chunks. Maximally correct, fairly invasive, and Windows doesn't support `select` on pipes.

**Use Option A.**

## Done when

- [ ] Both `_run_agent_blocking` and `_run_agent_streaming` use the writer-thread pattern (or equivalent that enforces `timeout` across stdin delivery).
- [ ] The writer thread is joined with a bounded timeout in `finally`.
- [ ] New test `tests/test_agent.py::test_timeout_enforced_when_agent_does_not_read_stdin` — launch a real Python subprocess that reads zero bytes from stdin and sleeps for 30 seconds, pass a `timeout=1.0`, assert the call returns within ~3 seconds with `timed_out=True`. Use a prompt large enough (>64 KB on Linux, >8 KB on macOS) to fill the pipe buffer.
- [ ] Existing `test_large_prompt_with_concurrent_stderr_does_not_deadlock` still passes (large prompt + chatty child is still fine).
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `SUBPROCESS_TEXT_KWARGS` in `src/ralphify/_output.py` opens stdin in text mode with a text encoder, so chunk writes mid-string are fine but partial-surrogate edges can corrupt encoding — just write the whole prompt in one `write` call.
- `_kill_process_group(proc)` on POSIX sends SIGTERM to the group, waits briefly, then SIGKILL. The child's death closes the pipe on its end, which unblocks the parent's blocked `write` with `BrokenPipeError`. That's why Option A's error handling is mostly "swallow `BrokenPipeError`."
- On Windows, `_kill_process_group` falls back to `proc.kill()` (just the direct child), and `start_new_session` is not set. Grandchild processes can still hold the pipe — but that's `critical-04`'s problem, not this one.
- The writer thread must be daemon=True so it cannot block interpreter shutdown, but it must be joined on the main thread's exit path so the caller sees any write errors it should care about (practically: `BrokenPipeError` is expected and swallowed; other errors you might want to surface).
- The existing `BrokenPipeError` swallow is still needed after the move — the writer thread will hit it when the child exits early.
