# High 01 — `_echo_output` + Live spinner coordination

**Original findings:** H1 (`_echo_output` tears Rich Live) + M8 (double-print when `--log-dir` + peek both active)
**Severity:** High — corrupts terminal output and can double-print every line
**Files:** `src/ralphify/_agent.py`, `src/ralphify/_console_emitter.py`, `src/ralphify/engine.py`

## Problem

### 1. `_echo_output` bypasses the Rich Live lock

`_echo_output` at `src/ralphify/_agent.py:153` writes directly to `sys.stdout` / `sys.stderr`:

```python
def _echo_output(stdout: str | bytes | None, stderr: str | bytes | None) -> None:
    if stdout:
        sys.stdout.write(ensure_str(stdout))
    if stderr:
        sys.stderr.write(ensure_str(stderr))
```

It is called from **inside `_run_agent_blocking`**, which runs while `ConsoleEmitter._live` is still active (the iteration-started handler starts a Rich `Live` spinner and the iteration-ended handler stops it — echo happens *before* the iteration-ended event fires).

Rich's `Live` assumes it owns all writes to the terminal while active. Raw writes to `sys.stdout` tear the spinner's refresh loop: you get garbled output, half-redrawn spinners, and sometimes cursor-position artifacts that persist after the Live stops.

### 2. Double-print when `--log-dir` + peek are both on

When the user runs `ralph run --log-dir logs/` in an interactive TTY:
- Live peek is on by default → each line is printed as it streams from the agent (via `AGENT_OUTPUT_LINE` events).
- At iteration end, `_echo_output` dumps the full captured stdout+stderr again.

Result: **every line appears twice.** The CHANGELOG flags this as intended ("captured to the log and also echoed after each iteration"), but the combined effect with peek is visual noise nobody asked for.

## Why it matters

- Spinner tearing makes the CLI look broken for anyone using `--log-dir` in a TTY.
- Double-printing every line turns a 1000-line iteration into 2000 lines of terminal output. Scrollback becomes useless.
- The two issues compound: the tearing happens specifically in the code path where the double-print also happens.

## Fix direction

Two problems, one coordinated fix. Pick an approach:

### Approach A — Route echo through the emitter (preferred)

Replace the direct `sys.stdout.write` with an emitter event. Either:
- **Reuse `AGENT_OUTPUT_LINE`** — emit one event per line of captured output at iteration-end. The `ConsoleEmitter` handler already knows how to render these under `_console_lock` and check peek state.
- **Add `AGENT_OUTPUT_BATCH`** — a new event type for "here's the full captured output to echo." The handler stops Live, prints the batch, restarts Live.

Reusing `AGENT_OUTPUT_LINE` is simpler and gives you the de-duplication for free: if peek was on for the iteration, the lines were already rendered, and the handler can skip them based on a "was peek on during this iteration?" flag the emitter maintains.

### Approach B — Skip `_echo_output` when peek was on

Track a per-iteration `peek_was_visible` flag in `ConsoleEmitter` (set when peek is on at iteration start, cleared when iteration ends). The engine passes this to `execute_agent` → `_run_agent_blocking`, which only calls `_echo_output` when the flag is false. Still needs to stop Live before calling `_echo_output` to fix the tearing.

### Approach C — Drop `_echo_output` entirely

Since `--log-dir` is supposed to *save* output to a file, maybe the user doesn't need it echoed at all. Document that `--log-dir` silences terminal output unless peek is on.

**Prefer Approach A.** It unifies the "show agent output to the user" path and fixes both bugs with one event type. The handler is the natural place to know whether Live is active and coordinate the print.

Whichever approach you take, `_echo_output` must **not** write to `sys.stdout`/`sys.stderr` directly while Live is active. The write must either:
- go through `self._live.console.print(...)` (Rich's Live-aware print), or
- be preceded by `self._live.stop()` and followed by `self._live.start()` (same `_console_lock` region).

## Done when

- [ ] No direct `sys.stdout.write` / `sys.stderr.write` from `_echo_output` while a Rich `Live` is active. Either delete `_echo_output`, or make it route through the emitter.
- [ ] When `--log-dir` is set AND peek was on for the iteration, each line of agent output appears **exactly once** in the terminal.
- [ ] When `--log-dir` is set AND peek was off (non-TTY, or user toggled off), the user still sees the output somewhere (either echoed at iteration end with Live properly coordinated, or streamed live during the iteration — pick one and make it consistent).
- [ ] New test `tests/test_console_emitter.py::test_echo_does_not_tear_live_spinner` — use `Console(record=True)` with Live active, emit the echo path, assert the recorded output doesn't contain Live-region artifacts (specifically: no interleaved spinner frames in the echoed text).
- [ ] New test `tests/test_engine.py::test_no_double_print_with_log_dir_and_peek` — run a fake agent that produces 3 lines, with `--log-dir` set and peek forced on; assert each line appears exactly once in captured console output.
- [ ] `uv run pytest`, lint, format, ty check all pass.

## Context

- `_echo_output` definition: `src/ralphify/_agent.py:153-165`. Only caller is `_run_agent_blocking` at `:439`.
- `ConsoleEmitter._start_live` / `_stop_live` wrap iteration-level spinner setup. See `src/ralphify/_console_emitter.py` — handlers for `EventType.ITERATION_STARTED` and `EventType.ITERATION_ENDED`.
- Rich's `Live.console.print(...)` safely prints above the Live region without tearing. If you go that route, the emitter needs to know whether Live is currently running.
- Related but out of scope: `medium-05` handles the lock-release gap between iteration handlers; that's a separate cosmetic issue and does not block this task.
- If `critical-01` lands first and adopts the "inherit fds when no capture needed" path, `_echo_output` is only invoked when `log_path_dir is not None`. That narrows the scope of this fix to the logging-enabled case, which is cleaner.
- **Task ordering:** this task is easier to land after `critical-01` but can be done standalone — the two-write-targets issue exists regardless.
