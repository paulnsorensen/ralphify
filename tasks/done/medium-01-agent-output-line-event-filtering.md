# Medium 01 — Filter `AGENT_OUTPUT_LINE` events when no subscriber renders them

**Original finding:** M2
**Severity:** Medium — measurable CPU waste + unbounded `QueueEmitter` growth
**Files:** `src/ralphify/engine.py`, `src/ralphify/_events.py`, `src/ralphify/_console_emitter.py`, `src/ralphify/_agent.py`

## Problem

Every line of agent output produces an event:

1. `_pump_stream` calls `on_output_line(line, stream)`.
2. The engine's lambda wraps the line in an `AgentOutputLineData` TypedDict.
3. Wraps *that* in an `Event` dataclass with a fresh `datetime.now(timezone.utc)`.
4. Dispatches through the emitter (`FanoutEmitter` / `QueueEmitter` / `ConsoleEmitter`).
5. In `ConsoleEmitter._on_agent_output_line`, checks `self._peek_enabled`.
6. **Drops the event** when peek is off.

Steps 2-5 run on every line, peek on or off. For a chatty agent (Claude Code with `--verbose` stream-json, or any agent piping its full stdlib logs), that's thousands of allocations per second entirely wasted.

Worse, in multi-run mode (`manager.py`), `QueueEmitter` accumulates every event onto a `queue.Queue` that may not be consumed until the run finishes. `AGENT_OUTPUT_LINE` events can push memory use into unbounded territory for long-running runs.

## Why it matters

- **Hot-path CPU cost.** `datetime.now(timezone.utc)` is not free; neither is dict allocation. At 10k lines/sec this is a measurable chunk of the main thread's budget, stolen from the reader threads (GIL contention).
- **Multi-run memory leak.** `QueueEmitter`'s queue grows without bound. For a ralph that runs overnight with `-n 100` iterations of a chatty agent, memory use can be hundreds of MB of dropped events. This is a real OOM surface on smaller CI runners.
- **Trivially avoidable** — the engine already knows whether anyone will actually render output lines. It just doesn't use that knowledge.

## Fix direction

Short-circuit the callback at the **lowest** possible layer. The cleanest place is in the engine: when building the `on_output_line` lambda, pass `None` if no subscriber will render.

### Step 1 — Let the emitter declare capability

Add a method to the emitter protocol (or directly to `ConsoleEmitter`):

```python
# src/ralphify/_events.py or _console_emitter.py
class Emitter(Protocol):
    ...
    def wants_agent_output_lines(self) -> bool:
        """Return True if this emitter will actually render AGENT_OUTPUT_LINE events.

        Used by the engine to avoid per-line event allocation when no subscriber cares.
        This is a hint, not a contract — emitters may still receive the events if
        the caller chooses to send them anyway.
        """
        return False
```

Implementations:
- `NullEmitter.wants_agent_output_lines()` → `False`
- `QueueEmitter.wants_agent_output_lines()` → `False` (the queue is not a renderer)
- `ConsoleEmitter.wants_agent_output_lines()` → `self._peek_enabled` (only when peek is on)
- `FanoutEmitter.wants_agent_output_lines()` → `any(e.wants_agent_output_lines() for e in self._emitters)`

### Step 2 — Engine checks and passes `None`

In `engine.py:_run_agent_phase` (or wherever the `on_output_line` lambda is constructed):

```python
if emitter.wants_agent_output_lines():
    on_output_line = lambda line, stream: emitter.emit(Event(
        type=EventType.AGENT_OUTPUT_LINE,
        data={"line": line, "stream": stream},
        ...
    ))
else:
    on_output_line = None
```

### Step 3 — Handle mid-iteration toggle

There's one subtle case: the user can press `p` mid-iteration to **enable** peek. If `on_output_line` was passed as `None` at iteration start, turning peek on mid-iteration can't retroactively start rendering. Options:

- **A. Accept the limitation** — mid-iteration enable only takes effect on the next iteration. Document this in the docs/cli.md Peeking section.
- **B. Always pass the callback, but short-circuit inside** — keeps the callback cheap when peek is off (the check is a single atomic bool read). Still pays the allocation cost on every line, partially defeating the purpose.
- **C. Recheck before each emit** — the engine's lambda closes over the emitter and checks `emitter.wants_agent_output_lines()` on every call. That moves the check from "per iteration" to "per line," which is cheap enough (one method call + one bool) but still allocates the event object if `True`.

**Prefer Option C.** The cost of the check is a branch and a method call; you save the datetime + dict + Event allocation when peek is off. It preserves mid-iteration toggle semantics.

```python
on_output_line = lambda line, stream: (
    emitter.emit(Event(type=EventType.AGENT_OUTPUT_LINE, ...))
    if emitter.wants_agent_output_lines()
    else None
)
```

### Step 4 — Coordinate with `critical-01`

`critical-01` introduces a three-way branch in `_run_agent_blocking` that uses `on_output_line=None` as the signal for "no one wants output → use fd inheritance." If you land this task after `critical-01`, make sure `on_output_line` is **genuinely `None`** (not a no-op lambda) when peek is off and log is off, so the inherit branch still triggers. That means engine must pass `None` explicitly in that case, not a short-circuiting lambda.

The cleanest resolution is to combine both signals:

```python
wants_lines = emitter.wants_agent_output_lines()
needs_capture = log_path_dir is not None
if wants_lines or needs_capture:
    on_output_line = lambda line, stream: (
        emitter.emit(...) if emitter.wants_agent_output_lines() else None
    )
else:
    on_output_line = None  # allows _run_agent_blocking to inherit fds
```

## Done when

- [ ] `Emitter` protocol has a `wants_agent_output_lines()` method.
- [ ] All three emitter implementations (`NullEmitter`, `QueueEmitter`, `ConsoleEmitter`) implement it correctly.
- [ ] `FanoutEmitter` (if present) fans out the check.
- [ ] Engine checks the capability before emitting per-line events. Mid-iteration toggle still works (verify via test).
- [ ] When peek is off AND log is off, `on_output_line` passed to `execute_agent` is `None` (enables the inherit branch from `critical-01`).
- [ ] New test `tests/test_engine.py::test_agent_output_line_not_emitted_when_peek_off` — force peek off, run an iteration, assert zero `AGENT_OUTPUT_LINE` events in the emitter's recorded event list.
- [ ] New test `tests/test_engine.py::test_agent_output_line_emitted_when_peek_toggled_mid_iteration` — start iteration with peek off, toggle on after first line, assert subsequent lines appear as events.
- [ ] No regression in existing peek tests.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_events.py` defines `EventType`, event dataclasses, and the emitter protocol. Look for `NullEmitter`, `QueueEmitter`, `FanoutEmitter`, `BoundEmitter`.
- `_console_emitter.py` has `_peek_enabled` and `_peek_lock`. Reading the flag without the lock is fine (it's a bool, GIL-atomic) and is what `medium-04` is about — don't worry about locks here.
- Engine wiring: look for `execute_agent(` call sites in `src/ralphify/engine.py`. The `on_output_line=` kwarg is where you plumb the lambda.
- **Task ordering:** ideally lands after `critical-01` so the `None`-triggers-inherit contract is already in place. Can land before as long as you preserve the `None` signal for the inherit branch.
- Do not add metrics, counters, or "events dropped" logging. Keep it a silent optimization.
