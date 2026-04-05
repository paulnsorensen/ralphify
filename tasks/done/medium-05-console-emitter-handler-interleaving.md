# Medium 05 — Console emitter: handler interleaving

**Original finding:** M10
**Severity:** Medium — cosmetic output splicing at iteration boundaries
**Files:** `src/ralphify/_console_emitter.py`

## Problem

`ConsoleEmitter`'s iteration handlers release `_console_lock` between sub-operations, allowing reader-thread peek prints to splice in between logically-atomic output blocks.

### Example 1 — `_on_iteration_started`

```python
# src/ralphify/_console_emitter.py ~214-218
def _on_iteration_started(self, data: IterationStartedData) -> None:
    iteration = data["iteration"]
    with self._console_lock:
        self._console.print(f"── Iteration {iteration} ──")
    self._start_live()  # ← lock released; re-acquired inside _start_live
```

Between the `print("── Iteration N ──")` and `_start_live()`, a reader thread can fire `_on_agent_output_line` and print a peek line. The terminal now shows:

```
── Iteration 5 ──
[dim]some agent output line[/]
⠋ Running iteration 5...
```

The peek line belongs to iteration 5 logically, but it appears **before** the spinner starts, which looks wrong.

### Example 2 — `_on_iteration_ended`

Similar pattern: `_stop_live()` releases the lock, then the handler prints the result summary. A late peek line from the just-finished iteration can appear between "iteration ended" output and the Markdown-rendered result.

## Why it matters

- **Cosmetic only.** Output is still correct; the splicing is just visually disorienting.
- **Users will file bugs** thinking the spinner is broken or that peek lines belong to the wrong iteration.
- **Trivially fixable.** The fix is a three-line refactor per handler to widen the lock region.

## Fix direction

Inline `_start_live` / `_stop_live` into the same `with self._console_lock:` block as their enclosing handler. The lock must cover both the text prints AND the Live start/stop, so reader threads see the atomic transition.

### Before

```python
def _on_iteration_started(self, data):
    iteration = data["iteration"]
    with self._console_lock:
        self._console.print(f"── Iteration {iteration} ──")
    self._start_live()

def _start_live(self):
    with self._console_lock:
        # ... set up and start Rich Live ...
```

### After

Two options:

### Option A — Widen the lock in the handler, make `_start_live` lock-free

```python
def _on_iteration_started(self, data):
    iteration = data["iteration"]
    with self._console_lock:
        self._console.print(f"── Iteration {iteration} ──")
        self._start_live_unlocked()

def _start_live_unlocked(self):
    # Caller must hold _console_lock.
    # ... set up and start Rich Live ...
```

Pros: explicit lock ownership transfer via method naming.
Cons: if `_start_live` is called from other handlers that don't already hold the lock, you introduce a new bug. Audit all call sites.

### Option B — Make `_start_live` reentrant-safe by using `RLock`

Replace `_console_lock: Lock` with `_console_lock: RLock`. Then the nested acquisition inside `_start_live` (called from inside the handler's `with` block) just re-enters.

Pros: no method renaming; works for all call sites.
Cons: `RLock` is slightly slower than `Lock`. Not measurable for this hot path (iteration start/end is rare). **But:** `RLock` in combination with `medium-04`'s lock simplification needs coordination — if both tasks land, `medium-04` should not remove the `RLock` behavior `medium-05` depends on.

### Recommendation

**Option A** — explicit and less magic. The rename makes the invariant ("caller must hold the lock") obvious. Audit of call sites is a one-time cost; the code stays simpler long-term.

Apply the same pattern to `_on_iteration_ended` → widen the lock to cover `_stop_live_unlocked()` + the iteration-ended print block.

### What about peek lines during the wide lock?

While `_on_iteration_started` holds `_console_lock`, reader threads that call `_on_agent_output_line` block until the handler finishes. For iteration start/end, this is a few milliseconds at most (one Markdown render) — negligible. Peek lines get queued behind the handler, which is exactly the desired behavior. No starvation risk because the lock is held briefly.

## Done when

- [ ] `_on_iteration_started` holds `_console_lock` for both the header print AND the Live start.
- [ ] `_on_iteration_ended` holds `_console_lock` for both the Live stop AND the result block print.
- [ ] `_start_live` / `_stop_live` either (A) have `_unlocked` variants called from inside the widened lock region, or (B) use `RLock` for reentrancy.
- [ ] All existing call sites of `_start_live` / `_stop_live` are audited — no one tries to acquire the lock twice unless the lock is reentrant.
- [ ] New test `tests/test_console_emitter.py::test_peek_lines_do_not_splice_between_iteration_header_and_spinner` — use `Console(record=True)`, emit an iteration-started event and a peek line from a background thread racing with it, assert the peek line appears **after** the spinner starts (or that the header+spinner are contiguous in the recorded output).
- [ ] Existing `test_concurrent_peek_writes_do_not_interleave` still passes.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_on_iteration_started` is around `src/ralphify/_console_emitter.py:214`. `_on_iteration_ended` is a little lower.
- `_start_live` / `_stop_live` are helper methods on `ConsoleEmitter`. Check whether they already acquire `_console_lock` internally (most likely yes) — that's the nested acquisition this task removes.
- `Console(record=True)` in tests is the standard way to capture output without a real terminal. Check `tests/helpers.py` for `_capture_emitter` or similar.
- **Task ordering:** `medium-04` and this task both touch `_console_lock`. Coordinate:
  - If `medium-04` lands first and collapses `_peek_lock` into `_console_lock`, this task proceeds as normal.
  - If this task lands first, `medium-04` will collapse `_peek_lock` into whatever locking structure this task leaves behind.
  - If both use Option A (explicit `_unlocked` suffix methods), the two tasks are independent. **Prefer Option A for both.**
- **Do not** widen the lock region beyond what's needed for atomicity. Do not, for instance, hold the lock across the Markdown render of a huge result — that blocks peek lines for noticeable time. The lock should cover the logical output unit (header + spinner start) and release before anything long-running.
