# Critical 01 — Capture strategy: three-way branch

**Original findings:** C1 (silent output regression) + M1 (unbounded buffering)
**Severity:** Critical — silently swallows agent output in common setups
**Files:** `src/ralphify/_agent.py`, `src/ralphify/engine.py`, `src/ralphify/_console_emitter.py`

## Problem

`_run_agent_blocking` used to pass `stdout=None, stderr=None` to `subprocess.Popen` whenever `log_path_dir` was `None`, letting the child's fds inherit straight through to the terminal. The live-peek refactor changed it to **always pipe** stdout/stderr and drain via reader threads, capturing everything into `stdout_lines`/`stderr_lines`.

The echo guard is:

```python
# src/ralphify/_agent.py ~line 435
if log_path_dir is not None:
    _echo_output(stdout, stderr)
```

with a comment claiming "When logging is disabled, live peek (if enabled) has already shown the lines."

That claim is **false** whenever peek is not active. `_interactive_default_peek` in `_console_emitter.py:105` returns `False` unless both `console.is_terminal` AND `sys.stdin.isatty()` are true.

## Why it matters

Concrete user-visible regressions from `main`:

1. `ralph run my-ralph | cat` → stdout is not a TTY → peek off → no echo → **user sees zero agent output**.
2. `ralph run my-ralph | tee run.log`, `ralph run ... 2>&1 | grep ERROR`, `nohup ralph run`, `ralph run` from a systemd unit — all silently swallow agent output.
3. Interactive user presses `p` to mute peek → subsequent iterations' output is discarded forever (no echo catches it because `log_path_dir is None`).
4. Secondary issue (M1): even when nobody needs the bytes, every iteration accumulates full stdout+stderr into Python `list`s. For a chatty agent running for hours, one iteration can buffer hundreds of MB that is immediately thrown away by `_write_log(None, …)`.

## Fix direction

Replace the binary "always capture" with a three-way branch:

1. **No log, peek unavailable** → `stdout=None, stderr=None` (inherit, no reader threads, no capture). Matches pre-refactor behavior and fixes both issues in one move.
2. **Peek available (TTY user wants live output)** → reader threads + `on_output_line` callback. Buffer only if logging needs it.
3. **`log_path_dir` set** → reader threads that accumulate into lists for log writing.

The hard part: `_run_agent_blocking` has to know at spawn time whether peek is enabled. Peek state currently lives in `ConsoleEmitter._peek_enabled`, one layer above the agent. Pick one approach:

- **A — signal via `on_output_line`:** the engine (which has the emitter) passes `on_output_line=None` when no subscriber will render output. `_run_agent_blocking` treats `on_output_line=None AND log_path_dir=None` as "use inheritance." This is the simplest change and dovetails with `medium-01` (event filtering).
- **B — add a capability method to the emitter** (e.g. `emitter.wants_agent_output_lines()`) and have the engine check it. More explicit but more plumbing.

**Prefer option A.** It requires `ConsoleEmitter` to expose peek state so the engine can pass `None` when peek is off, or the engine can simply pass the callback always and let `_run_agent_blocking` decide based on whether peek *might* become enabled mid-iteration (which it can, via `p`). If toggling mid-iteration matters, you have to capture — in which case document it and keep the echo-on-log path, plus add echo when peek was off for the whole iteration.

Simpler user-facing model: **peek being on/off does not change whether the iteration's output is eventually shown.** Echo at iteration end whenever the inherit path wasn't taken AND peek wasn't visible for the full iteration. See `high-01` for the Live spinner coordination this requires.

## Done when

- [ ] `ralph run my-ralph | cat` shows agent output (regression test: subprocess pipe, assert stdout non-empty).
- [ ] `ralph run my-ralph` with `--log-dir` set still writes the log file and the user still sees the output in the terminal (exactly once — see `high-01`).
- [ ] `ralph run my-ralph` in an interactive TTY with peek on shows live output (no regression).
- [ ] No per-iteration unbounded buffering when neither log nor peek is active (verify by checking the `Popen` kwargs in the non-capture branch).
- [ ] `uv run pytest` passes. Add a new test in `tests/test_agent.py` that asserts the non-capture `Popen` path is used when `log_path_dir=None and on_output_line=None`.
- [ ] `uv run ruff check . && uv run ruff format --check . && uv run ty check` all pass.

## Context

- The old `_run_agent_blocking` is in the diff — recover it via `git log -p src/ralphify/_agent.py` to see the pre-refactor shape.
- `_echo_output` is defined at `src/ralphify/_agent.py:153`. It writes directly to `sys.stdout`/`sys.stderr`, which itself is a bug — see `high-01`.
- `_interactive_default_peek` is at `src/ralphify/_console_emitter.py:105`. The checks are `console.is_terminal and sys.stdin.isatty()`.
- `execute_agent` at `src/ralphify/_agent.py:455` is the single entry point; it dispatches to streaming or blocking. Both paths need the same three-way logic, though streaming has fewer escape valves (it always needs to read the JSON stream, so inheritance is only an option for stderr). Keep the scope of this task to the blocking path; the streaming path already captures stdout for JSON parsing, so it's a separate (smaller) consideration.
- Engine wiring: `src/ralphify/engine.py` around `_run_agent_phase` builds the `on_output_line` lambda. That's the place to pass `None` when no subscriber cares.
- **Do not** merge the `medium-01` event-filtering work into this task — that one is strictly an optimization on top of the capability signal introduced here.
