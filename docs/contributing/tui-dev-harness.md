# TUI dev harness

The `ralph` CLI's terminal output — the iteration headers, peek panel,
result lines, run summary, and error logs — is rendered by
`ConsoleEmitter` in `src/ralphify/_console_emitter.py`. Iterating on
that visual design needs visual feedback, but coding agents running in
a non-interactive environment can't watch a live terminal. The harness
at `scripts/tui_dev/` solves this — it generates PNG snapshots of any
`ConsoleEmitter` state that any agent (or human) can view.

## Usage

```bash
./scripts/tui_dev/run.sh            # regenerate everything (~15s)
./scripts/tui_dev/run.sh snapshot   # fixture-driven mode only
./scripts/tui_dev/run.sh live       # real ralph run via pty only
```

Outputs land in `scripts/tui_dev/output/*.png` (gitignored). The
iteration cycle is: edit `_console_emitter.py` → rerun the harness →
view the PNGs → repeat.

## Modes

### Snapshot mode (`snapshot.py`)

Drives the real `ConsoleEmitter` in-process through canned fixtures
defined in `fixtures.py`. Two flavours of fixture are supported:

#### Peek-panel scenarios (`ALL_SCENARIOS`)

Each scenario is a list of parsed Claude stream-json dicts that get
fed through a real `_IterationPanel`. Used for iterating on the live
activity feed (the bordered panel shown when peek is on).

| Scenario | What it shows |
|---|---|
| `01_empty` | Peek toggled on, zero scroll lines yet |
| `02_single_tool` | First tool call after peek turns on |
| `03_mixed_activity` | Thinking, tool calls, text preview — typical mid-iteration |
| `04_scroll_buffer_full` | 17 tool calls — exceeds the visible scroll cap |
| `05_heavy_tokens` | 1M+ input tokens, exercising the `M` unit in the token formatter |
| `06_rate_limit` | Rate-limit event mixed with normal activity |
| `07_tool_error` | Red `tool_result` error branch |
| `08_raw_spinner` | `_IterationSpinner` path for non-Claude agents |
| `09_peek_off` | Peek toggled off mid-iteration — verifies the buffer persists |

#### Event-sequence scenarios (`EVENT_SCENARIOS`)

Each scenario is a list of `(EventType, dict)` tuples that get fed
through the real emitter. Whatever the emitter prints to the recording
console is what ends up in the snapshot. Used for iterating on
**anything that isn't the peek panel** — iteration result lines, run
summaries, error logs, markdown result rendering.

| Scenario | What it shows |
|---|---|
| `10_iteration_success` | Happy path: green checkmark + markdown result |
| `11_iteration_failed` | Red failure with exit code and log file path |
| `12_iteration_timeout` | Yellow timeout branch |
| `13_run_summary_mixed` | Multi-iteration run with success / failure / timeout |
| `14_log_error` | Error log message with traceback |

Snapshot mode subclasses `ConsoleEmitter` to disable `Live.start`, so
each scenario produces exactly one frozen render. Rendering goes
through Rich's own `save_svg` → headless Chrome → PNG — no lossy
intermediaries, and colors/fonts match what Rich emits to the terminal.

Fast (~15s total), deterministic, no subprocess — this is the mode to
use for most design work.

### Live mode (`live.py`)

Maximum fidelity. Spawns the real `ralph` binary in a pseudo-terminal
via `pty.openpty()`, with `fake_bin/claude` (a Python script named
`claude` so `_is_claude_command` treats it as a structured agent)
emitting realistic stream-json on a 1.8s cadence. The capture
deliberately freezes at t=9s so the `Live` panel is still
mid-iteration, then feeds the raw ANSI byte stream through
[`pyte`](https://github.com/selectel/pyte) — a pure-Python terminal
emulator — to reduce cursor moves and clears to a stable screen grid.
That grid is then rendered through Rich for the final SVG → PNG.

pyte is installed on-demand via `uv run --with pyte` (not a project
dep).

## Adding a new scenario

### Peek-panel scenario

Append a builder function to `scripts/tui_dev/fixtures.py` and
register it in `ALL_SCENARIOS`:

```python
def scenario_my_new_case() -> list[dict[str, Any]]:
    return [
        system_init(),
        assistant_tool_use("Bash", {"command": "pytest -x"}, input_tokens=1200),
        # ...
    ]


ALL_SCENARIOS = {
    # ...
    "15_my_new_case": scenario_my_new_case(),
}
```

### Event-sequence scenario

Append an events builder and register it in `EVENT_SCENARIOS`:

```python
def events_my_new_case() -> list[tuple[EventType, dict[str, Any]]]:
    return [
        _run_started("demo / 16_my_new_case"),
        (EventType.ITERATION_STARTED, {"iteration": 1}),
        (EventType.ITERATION_COMPLETED, {
            "iteration": 1,
            "detail": "completed (5s)",
            "log_file": None,
            "result_text": "all good",
        }),
    ]


EVENT_SCENARIOS = {
    # ...
    "16_my_new_case": events_my_new_case(),
}
```

The next `./scripts/tui_dev/run.sh snapshot` will produce
`scripts/tui_dev/output/16_my_new_case.png`.

## Files

```
scripts/tui_dev/
├── run.sh              # one-command launcher
├── snapshot.py         # mode A: in-process ConsoleEmitter + fixtures
├── live.py             # mode B: real ralph run via pty + pyte
├── fixtures.py         # canned event sequences (peek + general)
├── render.py           # shared SVG → PNG via headless Chrome
├── fake_bin/claude     # stub Claude agent used by live mode
├── demo_ralph/RALPH.md # minimal ralph dir used by live mode
└── output/             # PNG + SVG snapshots (gitignored)
```
