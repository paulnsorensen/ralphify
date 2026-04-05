# Medium 04 — Peek lock discipline

**Original findings:** M6 (unlocked read of `_peek_enabled`) + M7 (banner print holds `_peek_lock`)
**Severity:** Medium — latently fragile lock order; brief mid-toggle output leak
**Files:** `src/ralphify/_console_emitter.py`

## Problem

Two related issues in `ConsoleEmitter`'s peek state management:

### 1. `_on_agent_output_line` reads `_peek_enabled` without `_peek_lock`

```python
# src/ralphify/_console_emitter.py ~173
def _on_agent_output_line(self, data: AgentOutputLineData) -> None:
    if not self._peek_enabled:
        return
    with self._console_lock:
        line = escape_markup(data["line"])
        self._console.print(f"[dim]{line}[/]")
```

Bool read is GIL-atomic so no tearing, but there's no memory barrier between the user pressing `p` (flipping the flag) and reader threads observing the new value. In practice this means:
- User presses `p` to silence peek.
- Reader thread pumps a line, reads `_peek_enabled` (still sees old value `True`), prints the line.
- The leak is at most a handful of lines, cosmetic only.

### 2. `toggle_peek` holds `_peek_lock` while printing the banner

```python
# src/ralphify/_console_emitter.py ~164
def toggle_peek(self) -> bool:
    with self._peek_lock:
        self._peek_enabled = not self._peek_enabled
        enabled = self._peek_enabled
        with self._console_lock:
            self._console.print("[dim]peek on[/]" if enabled else "[dim]peek off[/]")
    return enabled
```

Nested lock acquisition (`_peek_lock` then `_console_lock`). A comment justifies this as "the only nested-lock site, so the order is uncontested." That's true today. It's also trivially fragile:

- If any future code path acquires `_console_lock` first and then tries to acquire `_peek_lock` (e.g. a future "read peek state to customize render"), you get a classic AB/BA deadlock.
- `self._console.print` can raise on edge cases (closed Rich console, buggy renderable). The exception propagates back into the keypress daemon thread's `_on_key` which has no outer try/except → listener dies silently, `p` stops working.
- Holding `_peek_lock` during the print means any concurrent `toggle_peek` call (improbable, but possible from multiple threads) is serialized longer than necessary.

## Why it matters

- Issue 1 is cosmetic and low-stakes (up to a handful of lines leak on toggle-off).
- Issue 2 is a latent footgun. The nested-lock comment says "uncontested today" but nothing enforces that invariant; a future refactor will eventually violate it.
- Combined, these two issues point at an over-engineered lock design. The simpler fix is to use **one** lock, not two.

## Fix direction

### Option A — Collapse to a single `_console_lock`

`_peek_lock` exists only to make the bool flip atomic with the banner print. But the atomicity doesn't buy anything: there's no invariant between `_peek_enabled` and what's on screen that a second lock protects. One lock (`_console_lock`) is sufficient for:
- the flag flip in `toggle_peek`
- the banner print
- every `_console.print` from every handler
- the `_peek_enabled` read in `_on_agent_output_line`

```python
def toggle_peek(self) -> bool:
    with self._console_lock:
        self._peek_enabled = not self._peek_enabled
        enabled = self._peek_enabled
        self._console.print("[dim]peek on[/]" if enabled else "[dim]peek off[/]")
    return enabled

def _on_agent_output_line(self, data):
    with self._console_lock:
        if not self._peek_enabled:
            return
        line = escape_markup(data["line"])
        self._console.print(f"[dim]{line}[/]")
```

Pros: simplest model, no lock ordering to document, no nested acquisition.
Cons: every output line acquires `_console_lock` even when peek is off. Contention is minimal because `_console.print` is fast, but for a chatty agent this is slightly more lock traffic than needed. Mitigated by `medium-01`'s event filtering (when peek is off, the events aren't even sent).

### Option B — `threading.Event` for peek state + single lock for prints

Replace `_peek_enabled: bool` with `_peek: threading.Event`. Readers call `self._peek.is_set()` without any lock (events have their own internal synchronization). The console lock only covers prints:

```python
def toggle_peek(self) -> bool:
    enabled = not self._peek.is_set()
    if enabled:
        self._peek.set()
    else:
        self._peek.clear()
    with self._console_lock:
        self._console.print("[dim]peek on[/]" if enabled else "[dim]peek off[/]")
    return enabled

def _on_agent_output_line(self, data):
    if not self._peek.is_set():
        return
    with self._console_lock:
        line = escape_markup(data["line"])
        self._console.print(f"[dim]{line}[/]")
```

Pros: lock-free read path when peek is off (zero contention); explicit "this is a flag, not protected state."
Cons: two toggles in rapid succession can race (`not is_set` → `set`) — acceptable for a user pressing `p` twice. If strict atomicity matters, add an outer lock around the toggle. For this use case, it doesn't matter.

### Recommendation

**Option A** is the smallest, simplest change. Take it unless profiling shows the console lock contention matters (it won't). Option B is a minor optimization that's only worth it if this code becomes a hot path later.

Regardless of option, also wrap the `_on_key` callback in `cli.py` (or wherever the keypress listener fires) with a try/except so a raise inside `toggle_peek` doesn't kill the listener thread:

```python
# in cli.py, keypress handler
def _on_key(ch):
    try:
        if ch == "p":
            emitter.toggle_peek()
    except Exception:
        # Don't let a render error kill the listener.
        pass
```

## Done when

- [ ] `_peek_lock` is removed (Option A) OR replaced with `threading.Event` (Option B). No more nested lock acquisition.
- [ ] The nested-lock comment at `src/ralphify/_console_emitter.py:158-162` is removed or updated.
- [ ] `_on_key` (keypress callback in `cli.py`) wraps the toggle call in a try/except to prevent listener thread death on render errors.
- [ ] Existing test `test_concurrent_peek_writes_do_not_interleave` still passes — the console-lock (or equivalent serialization) is still in place to prevent output tearing.
- [ ] New test `tests/test_console_emitter.py::test_toggle_peek_survives_console_print_error` — mock `_console.print` to raise, call `toggle_peek`, assert the emitter is still functional for subsequent calls.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- The two locks are declared in `ConsoleEmitter.__init__` at `src/ralphify/_console_emitter.py` ~128-133. Grep for `_peek_lock` to find all usage sites.
- `_console_lock` also wraps every `self._console.print` call in other handlers (`_on_iteration_started`, etc.) — this task does not change those. Only the peek-state-specific locking.
- **Do not** refactor the rest of the handler locking discipline as part of this task. `medium-05` addresses the iteration-handler interleaving separately.
- **Do not** switch to `RLock`. `RLock` allows re-entry and is slower; it's the wrong tool for this problem. The fix is fewer locks, not a recursive lock.
- Keep the `_console_lock` name even if you collapse `_peek_lock` into it — renaming triggers a cascade of diffs in test helpers and is not worth it.
