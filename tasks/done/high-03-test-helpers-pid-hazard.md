# High 03 — Test helpers `pid=12345` hazard

**Original finding:** H4
**Severity:** High — test could kill an unrelated real process on the host
**Files:** `tests/helpers.py`, possibly `tests/test_agent.py`

## Problem

`tests/helpers.py` around lines 199-202 sets a mock subprocess's `pid` to `12345` and wires `proc.wait.side_effect = [subprocess.TimeoutExpired, 0]` for a timeout-simulation helper. The test flow invokes `_kill_process_group(proc)`, which on POSIX does roughly:

```python
def _kill_process_group(proc):
    try:
        pgid = os.getpgid(proc.pid)
        os.killpg(pgid, signal.SIGTERM)
        proc.wait(timeout=_SIGTERM_GRACE_PERIOD)
        ...
```

With `proc.pid = 12345`:
- `os.getpgid(12345)` asks the kernel for the pgid of **whatever real process happens to have pid 12345** on the test machine.
- If such a process exists and is owned by the test user, `os.killpg(pgid, SIGTERM)` **sends SIGTERM to a real process group**. On a developer's laptop running `uv run pytest`, this could be a browser tab, an editor, a shell — anything.
- If pid 12345 doesn't exist, `ProcessLookupError` is raised and caught.

Additionally, `proc.wait.side_effect = [subprocess.TimeoutExpired, 0]` is a 2-element list. If the graceful-kill path consumes one value (by calling `proc.wait(timeout=_SIGTERM_GRACE_PERIOD)`) and then the timeout-expired branch later calls `proc.wait()` again, you get `StopIteration` from an exhausted side-effect list.

## Why it matters

1. **Data loss risk for developers.** A random pid collision on the test user's machine causes their unrelated process to receive SIGTERM. On CI runners this is low probability (short-lived ephemeral VMs), but on developer laptops it's a real hazard. Security-wise it's also a sandbox-escape vector (not that this is a security tool, but it's bad hygiene).
2. **Flaky tests from `StopIteration`.** When the side-effect list runs dry, the mock raises `StopIteration` which propagates as a confusing error instead of a clean test failure.
3. **Test intent is fake-a-timeout, not kill-real-stuff.** The helper shouldn't need to touch the real OS at all.

## Fix direction

Pick **one** of the following. Both are fine; Option A is smaller.

### Option A — Sentinel pid + short-circuit

Use an obviously-invalid pid like `-1` or `0`, and short-circuit `_kill_process_group` for non-positive pids:

```python
# src/ralphify/_agent.py in _kill_process_group
def _kill_process_group(proc):
    if proc.pid is None or proc.pid <= 0:
        return  # Test mock or already-dead process; nothing to do.
    ...
```

Then in `tests/helpers.py`:

```python
mock_proc.pid = 0  # sentinel: skip process-group manipulation
```

This is defense-in-depth: even real code that somehow ends up with `pid <= 0` won't accidentally kill init.

### Option B — Patch `os.killpg` / `os.getpgid` in the test fixture

Use `unittest.mock.patch("os.killpg")` and `patch("os.getpgid")` in the helper so the real OS is never touched. More explicit about the test's contract but requires touching every test that uses this helper.

**Prefer Option A.** It's a smaller change, adds a real safety net to production code, and the sentinel pid makes test intent obvious.

### Also fix the side_effect exhaustion

Replace the 2-element list with a pattern that won't `StopIteration`:

```python
# Option: always return 0 after the first timeout
wait_calls = [0]
def wait_side_effect(*args, **kwargs):
    wait_calls[0] += 1
    if wait_calls[0] == 1:
        raise subprocess.TimeoutExpired(cmd="fake", timeout=args[0] if args else None)
    return 0
mock_proc.wait.side_effect = wait_side_effect
```

Or simply `mock_proc.wait.side_effect = [subprocess.TimeoutExpired, 0, 0, 0, 0]` with enough slots for any realistic call count. The function-based approach is more robust.

## Done when

- [ ] No test helper sets `proc.pid` to a positive integer that could collide with a real pid. Either sentinel (`0` or `-1`) or `None`.
- [ ] If using Option A: `_kill_process_group` short-circuits on non-positive pids and has a test asserting that (`test_kill_process_group_short_circuits_on_sentinel_pid`).
- [ ] `proc.wait.side_effect` is function-based or has enough elements that test reorderings can't `StopIteration`.
- [ ] Run the test suite under `strace -e trace=kill,tkill,tgkill` (or `dtruss` on macOS) during development to verify no real `killpg` / `kill` syscalls are made to non-test pids. Optional but recommended as one-time verification.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- The helper to fix is in `tests/helpers.py` around line 199. Git blame it to see the test(s) that depend on it.
- `_kill_process_group` is defined in `src/ralphify/_agent.py`. Check its exact shape to see where the sentinel check fits cleanest.
- `_SIGTERM_GRACE_PERIOD` is a module-level constant in `_agent.py`; no need to change it.
- **Do not** change real-production behavior of `_kill_process_group` beyond the sentinel check — the point is to make the helper safe, not refactor the kill path.
- Scope is small: one helper, one short-circuit, maybe one new test. Should land in under 100 lines of diff.
