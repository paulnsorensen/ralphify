---
description: Use ralphify as a Python library — run loops programmatically, listen to events, manage multiple runs, and discover primitives without the CLI.
---

# Python API

Ralphify can be used as a Python library, not just a CLI. This is useful when you want to:

- Embed the loop in a larger automation pipeline
- Build custom orchestration on top of ralphify
- Listen to events and react programmatically (e.g. send Slack alerts on failures)
- Script runs with more control than the CLI provides

## Quick start

```python
from ralphify import run_loop, RunConfig, RunState

config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    prompt_file="RALPH.md",
    max_iterations=3,
)
state = RunState(run_id="my-run")
run_loop(config, state)
```

This runs the same loop as `ralph run -n 3`, using `RALPH.md` as the prompt. When the loop finishes, `state` contains the results.

## Core function

### `run_loop(config, state, emitter=None)`

The main loop. Discovers primitives, assembles prompts, pipes them to the agent, runs checks, and repeats.

```python
from ralphify import run_loop, RunConfig, RunState, NullEmitter

config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    prompt_file="RALPH.md",
    max_iterations=5,
    stop_on_error=True,
    timeout=300,
    log_dir="ralph_logs",
)
state = RunState(run_id="build-features")

run_loop(config, state)

print(f"Completed: {state.completed}")
print(f"Failed: {state.failed}")
print(f"Total: {state.total}")
```

| Parameter | Type | Description |
|---|---|---|
| `config` | `RunConfig` | All settings for the run |
| `state` | `RunState` | Observable state — counters, status, control methods |
| `emitter` | `EventEmitter | None` | Event listener. `None` uses `NullEmitter` (silent) |

The function blocks until the loop finishes (iteration limit reached, stop requested, error, or `KeyboardInterrupt`).

## Configuration

### `RunConfig`

A dataclass with all run settings. Fields match the CLI options.

```python
from pathlib import Path
from ralphify import RunConfig

config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    prompt_file="RALPH.md",
    prompt_text=None,       # Ad-hoc prompt text (overrides prompt_file)
    prompt_name=None,       # Named ralph from .ralphify/ralphs/
    max_iterations=10,
    delay=2.0,
    timeout=300,
    stop_on_error=True,
    log_dir="ralph_logs",
    project_root=Path("."),
)
```

| Field | Type | Default | CLI equivalent |
|---|---|---|---|
| `command` | `str` | — | `ralph.toml [agent] command` |
| `args` | `list[str]` | — | `ralph.toml [agent] args` |
| `prompt_file` | `str` | — | `ralph.toml [agent] ralph` or `-f` |
| `prompt_text` | `str | None` | `None` | `-p` |
| `prompt_name` | `str | None` | `None` | `ralph run <name>` |
| `max_iterations` | `int | None` | `None` | `-n` |
| `delay` | `float` | `0` | `-d` / `--delay` |
| `timeout` | `float | None` | `None` | `-t` / `--timeout` |
| `stop_on_error` | `bool` | `False` | `-s` / `--stop-on-error` |
| `log_dir` | `str | None` | `None` | `-l` / `--log-dir` |
| `project_root` | `Path` | `Path(".")` | Working directory |

`RunConfig` is mutable — you can change fields mid-run (e.g. increase `max_iterations`), and the loop picks up changes at the next iteration boundary.

### `RunState`

Observable state for a running loop. Created with a `run_id` and updated by the engine as iterations execute.

```python
from ralphify import RunState

state = RunState(run_id="my-run")

# After run_loop() finishes:
print(state.status)      # RunStatus.COMPLETED
print(state.iteration)   # 5 (last iteration number)
print(state.completed)   # 4
print(state.failed)      # 1
print(state.timed_out)   # 0 (subset of failed)
print(state.total)       # 5 (completed + failed)
print(state.started_at)  # datetime (UTC)
```

| Property / Field | Type | Description |
|---|---|---|
| `run_id` | `str` | Unique identifier for this run |
| `status` | `RunStatus` | Current lifecycle status |
| `iteration` | `int` | Current iteration number (1-indexed) |
| `completed` | `int` | Iterations that succeeded |
| `failed` | `int` | Iterations that failed (includes timed out) |
| `timed_out` | `int` | Iterations that timed out (subset of `failed`) |
| `total` | `int` | `completed + failed` |
| `started_at` | `datetime | None` | UTC timestamp when the run started |

#### Control methods

`RunState` provides thread-safe methods to control the loop from another thread:

```python
state.request_stop()      # Stop after current iteration
state.request_pause()     # Pause between iterations
state.request_resume()    # Resume a paused loop
state.request_reload()    # Re-discover primitives before next iteration

state.stop_requested      # bool — whether stop was requested
state.paused              # bool — whether currently paused
```

These are useful when running the loop in a background thread (see [Multi-run management](#multi-run-management) below).

### `RunStatus`

Enum representing the lifecycle of a run.

| Value | Description |
|---|---|
| `PENDING` | Created but not started |
| `RUNNING` | Loop is executing iterations |
| `PAUSED` | Paused between iterations |
| `STOPPED` | Stopped by user request |
| `COMPLETED` | Reached iteration limit or finished naturally |
| `FAILED` | Crashed with an exception |

## Event system

The loop emits structured events so you can observe progress without coupling to the engine internals.

### Listening to events

Implement the `EventEmitter` protocol — a single `emit(event)` method:

```python
from ralphify import Event, EventEmitter, EventType, RunConfig, RunState, run_loop


class MyEmitter:
    """Custom event listener that prints iteration results."""

    def emit(self, event: Event) -> None:
        if event.type == EventType.ITERATION_COMPLETED:
            duration = event.data["duration_formatted"]
            print(f"Iteration {event.data['iteration']} completed ({duration})")
        elif event.type == EventType.ITERATION_FAILED:
            print(f"Iteration {event.data['iteration']} failed (exit {event.data['returncode']})")
        elif event.type == EventType.CHECK_FAILED:
            print(f"  Check '{event.data['name']}' failed")


config = RunConfig(command="claude", args=["-p"], prompt_file="RALPH.md", max_iterations=3)
state = RunState(run_id="observed-run")
run_loop(config, state, emitter=MyEmitter())
```

### `Event`

Every event has these fields:

| Field | Type | Description |
|---|---|---|
| `type` | `EventType` | What happened |
| `run_id` | `str` | Which run produced this event |
| `data` | `dict` | Event-specific data |
| `timestamp` | `datetime` | UTC timestamp |

Use `event.to_dict()` to serialize for JSON transport.

### `EventType`

Events cover the full run lifecycle: `RUN_STARTED`, `RUN_STOPPED`, `RUN_PAUSED`, `RUN_RESUMED`, iteration events (`ITERATION_STARTED`, `ITERATION_COMPLETED`, `ITERATION_FAILED`, `ITERATION_TIMED_OUT`), check events (`CHECKS_STARTED`, `CHECK_PASSED`, `CHECK_FAILED`, `CHECKS_COMPLETED`), prompt assembly (`CONTEXTS_RESOLVED`, `PROMPT_ASSEMBLED`), and streaming (`AGENT_ACTIVITY`, `LOG_MESSAGE`).

Each event's `data` dict contains relevant fields (iteration number, exit codes, durations, output text, etc.). Inspect `event.data.keys()` or see the `EventType` enum in source for the full schema.

### Built-in emitters

| Emitter | Description | Use case |
|---|---|---|
| `NullEmitter` | Discards all events | Tests, silent runs |
| `QueueEmitter` | Pushes events into a `queue.Queue` | Async consumers, UI layers |
| `FanoutEmitter` | Broadcasts to multiple emitters | Combining logging + monitoring |

```python
from ralphify import QueueEmitter, FanoutEmitter

# Queue for async consumption
q_emitter = QueueEmitter()

# Combine multiple listeners
fanout = FanoutEmitter([q_emitter, MyEmitter()])

run_loop(config, state, emitter=fanout)

# Drain events from the queue
while not q_emitter.queue.empty():
    event = q_emitter.queue.get()
    print(event.to_dict())
```

## Multi-run management

`RunManager` orchestrates concurrent runs in background threads.

```python
from ralphify import RunManager, RunConfig

manager = RunManager()

# Create and start a run
config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    prompt_file="RALPH.md",
    max_iterations=5,
)
managed = manager.create_run(config)
manager.start_run(managed.state.run_id)

# Check status
print(managed.state.status)       # RunStatus.RUNNING
print(managed.state.completed)    # 2

# Control the run
manager.pause_run(managed.state.run_id)
manager.resume_run(managed.state.run_id)
manager.stop_run(managed.state.run_id)

# List all runs
for run in manager.list_runs():
    print(f"{run.state.run_id}: {run.state.status.value}")
```

`RunManager` provides `create_run(config)`, `start_run(run_id)`, `stop_run(run_id)`, `pause_run(run_id)`, `resume_run(run_id)`, `list_runs()`, and `get_run(run_id)`. Each run is wrapped in a `ManagedRun` with `config`, `state`, `emitter` (QueueEmitter), and `thread` fields. Use `managed.add_listener(emitter)` to register additional event listeners before starting.

## Primitive discovery

Discover checks, contexts, instructions, and ralphs without running the loop.

```python
from pathlib import Path
from ralphify import discover_checks, discover_contexts, discover_instructions, discover_ralphs

root = Path(".")

checks = discover_checks(root)
for check in checks:
    print(f"Check: {check.name}, command: {check.command}, enabled: {check.enabled}")

contexts = discover_contexts(root)
for ctx in contexts:
    print(f"Context: {ctx.name}, command: {ctx.command}")

instructions = discover_instructions(root)
for inst in instructions:
    print(f"Instruction: {inst.name}, enabled: {inst.enabled}")

ralphs = discover_ralphs(root)
for ralph in ralphs:
    print(f"Ralph: {ralph.name}, description: {ralph.description}")
```

### Running primitives

```python
from ralphify import run_all_checks, run_all_contexts

# Run all checks and get results
enabled_checks = [c for c in discover_checks(root) if c.enabled]
results = run_all_checks(enabled_checks, root)
for r in results:
    print(f"  {r.check.name}: {'PASS' if r.passed else 'FAIL'} (exit {r.exit_code})")

# Run all contexts and get output
enabled_contexts = [c for c in discover_contexts(root) if c.enabled]
context_results = run_all_contexts(enabled_contexts, root)
for cr in context_results:
    print(f"  {cr.context.name}: {len(cr.output)} chars of output")
```

### Resolving ralphs

```python
from ralphify import resolve_ralph_name

# Look up a named ralph and get the path to its RALPH.md
ralph_path = resolve_ralph_name("docs", Path("."))
if ralph_path:
    print(f"Found: {ralph_path}")
else:
    print("Named ralph 'docs' not found")
```

## Example: Slack notification on failure

A practical example combining the API with external integrations:

```python
import requests
from ralphify import Event, EventType, RunConfig, RunState, run_loop


class SlackNotifier:
    """Send a Slack message when a run finishes with failures."""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def emit(self, event: Event) -> None:
        if event.type != EventType.RUN_STOPPED:
            return
        failed = event.data.get("failed", 0)
        if failed == 0:
            return
        total = event.data.get("total", 0)
        completed = event.data.get("completed", 0)
        requests.post(self.webhook_url, json={
            "text": f"Ralph loop finished: {completed}/{total} passed, {failed} failed."
        })


config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    prompt_file="RALPH.md",
    max_iterations=10,
)
state = RunState(run_id="monitored-run")

notifier = SlackNotifier("https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
run_loop(config, state, emitter=notifier)
```

All public API is available from the top-level `ralphify` package (e.g. `from ralphify import run_loop, RunConfig, RunState`).
