---
description: Use ralphify as a Python library — run loops programmatically, manage concurrent runs, listen to events, and configure ralphs without the CLI.
keywords: ralphify Python API, programmatic agent loops, RunConfig, run_loop, concurrent runs, event listeners
---

# Python API

Ralphify can be used as a Python library. This is useful when you want to embed the loop in a larger automation pipeline, react to events programmatically, manage concurrent runs, or script runs with more control than the CLI provides.

All public API is available from the top-level `ralphify` package.

## Quick start

```python
from pathlib import Path
from ralphify import run_loop, RunConfig, RunState

config = RunConfig(
    agent="claude -p --dangerously-skip-permissions",
    ralph_dir=Path("my-ralph"),
    ralph_file=Path("my-ralph/RALPH.md"),
    commands=[],
    max_iterations=3,
)
state = RunState(run_id="my-run")
run_loop(config, state)
```

This runs the same loop as `ralph run my-ralph -n 3`. When the loop finishes, `state` contains the results.

---

## `run_loop(config, state, emitter=None)`

The main loop. Reads RALPH.md, runs commands, assembles prompts, pipes them to the agent, and repeats. **Blocks until the loop finishes.**

| Parameter | Type | Description |
|---|---|---|
| `config` | `RunConfig` | All settings for the run |
| `state` | `RunState` | Observable state — counters, status, control methods |
| `emitter` | `EventEmitter | None` | Event listener. `None` uses `NullEmitter` (silent) |

---

## `RunConfig`

All settings for a single run. Fields match the CLI options.

```python
from pathlib import Path
from ralphify import RunConfig, Command

config = RunConfig(
    agent="claude -p --dangerously-skip-permissions",
    ralph_dir=Path("my-ralph"),
    ralph_file=Path("my-ralph/RALPH.md"),
    commands=[
        Command(name="tests", run="uv run pytest -x"),
        Command(name="lint", run="uv run ruff check ."),
    ],
    args={"dir": "./src", "focus": "performance"},
    max_iterations=10,
    delay=2.0,
    timeout=300,
    stop_on_error=True,
    log_dir=Path("ralph_logs"),
    project_root=Path("."),
)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `agent` | `str` | -- | Full agent command string |
| `ralph_dir` | `Path` | -- | Path to the ralph directory |
| `ralph_file` | `Path` | -- | Path to the RALPH.md file |
| `commands` | `list[Command]` | `[]` | Commands to run each iteration |
| `args` | `dict[str, str]` | `{}` | User argument values |
| `max_iterations` | `int | None` | `None` | Max iterations (`None` = unlimited) |
| `delay` | `float` | `0` | Seconds to wait between iterations |
| `timeout` | `float | None` | `None` | Max seconds per iteration |
| `stop_on_error` | `bool` | `False` | Stop loop if agent exits non-zero or times out |
| `log_dir` | `Path | None` | `None` | Directory for iteration log files |
| `credit` | `bool` | `True` | Append co-author trailer instruction to prompt |
| `project_root` | `Path` | `Path(".")` | Project root directory |

`RunConfig` is mutable — you can change fields mid-run, and the loop picks up changes at the next iteration boundary.

---

## `Command`

A command that runs each iteration.

```python
from ralphify import Command

cmd = Command(name="tests", run="uv run pytest -x")
cmd_slow = Command(name="integration", run="uv run pytest tests/integration", timeout=300)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | `str` | (required) | Identifier used in `{{ commands.<name> }}` placeholders. Letters, digits, hyphens, and underscores only. |
| `run` | `str` | (required) | Shell command to execute |
| `timeout` | `float` | `60` | Max seconds before the command is killed |

---

## `RunState`

Observable state for a running loop. Thread-safe control methods let you stop, pause, and resume from another thread.

```python
state = RunState(run_id="my-run")
run_loop(config, state)

print(state.status)      # RunStatus.COMPLETED
print(state.completed)   # 4
print(state.failed)      # 1
print(state.timed_out)   # 0  (subset of failed)
print(state.total)       # 5  (completed + failed)
print(state.iteration)   # 5  (current iteration number)
print(state.started_at)  # datetime or None
```

| Property | Type | Description |
|---|---|---|
| `run_id` | `str` | Unique identifier for this run |
| `status` | `RunStatus` | Current lifecycle status |
| `iteration` | `int` | Current iteration number (starts at 0) |
| `completed` | `int` | Number of successful iterations |
| `failed` | `int` | Number of failed iterations (includes timed out) |
| `timed_out` | `int` | Number of timed-out iterations (subset of `failed`) |
| `total` | `int` | `completed + failed` |
| `started_at` | `datetime | None` | When the run started |
| `paused` | `bool` | Whether the run is currently paused |
| `stop_requested` | `bool` | Whether a stop has been requested |

!!! note "Counter invariant"
    `timed_out` is a **subset** of `failed`, not an independent category. A timed-out iteration increments both `timed_out` and `failed`. Therefore `completed + failed == total`.

### Control methods

Thread-safe methods for controlling the loop from another thread:

```python
state.request_stop()      # Stop after current iteration
state.request_pause()     # Pause between iterations
state.request_resume()    # Resume a paused loop
```

---

## `RunStatus`

Lifecycle status of a run.

| Status | Value | Description |
|---|---|---|
| `PENDING` | `"pending"` | Created but not yet started |
| `RUNNING` | `"running"` | Loop is executing iterations |
| `PAUSED` | `"paused"` | Paused between iterations, waiting for resume |
| `STOPPED` | `"stopped"` | Stopped by user via `request_stop()` |
| `COMPLETED` | `"completed"` | Reached `max_iterations` or finished naturally |
| `FAILED` | `"failed"` | Stopped by `--stop-on-error` after a failed/timed-out iteration, or crashed with an unhandled exception |

---

## `StopReason`

A `Literal` type indicating why a run stopped. Used in the `RUN_STOPPED` event's `reason` field.

| Value | Description |
|---|---|
| `"completed"` | Reached `max_iterations` or finished naturally |
| `"error"` | Crashed with an unhandled exception |
| `"user_requested"` | Stopped via `request_stop()` or `Ctrl+C` |

```python
from ralphify import StopReason
```

---

## Event system

The loop emits structured events at each step. Implement the `EventEmitter` protocol (a single `emit(event)` method) to listen.

### Custom emitter

```python
from pathlib import Path
from ralphify import Event, EventType, RunConfig, RunState, run_loop


class MyEmitter:
    def emit(self, event: Event) -> None:
        if event.type == EventType.ITERATION_COMPLETED:
            print(f"Iteration {event.data['iteration']} done in {event.data['duration_formatted']}")


config = RunConfig(
    agent="claude -p", ralph_dir=Path("my-ralph"),
    ralph_file=Path("my-ralph/RALPH.md"), commands=[], max_iterations=3,
)
state = RunState(run_id="observed-run")
run_loop(config, state, emitter=MyEmitter())
```

### `Event`

Each event carries:

| Field | Type | Description |
|---|---|---|
| `type` | `EventType` | What happened |
| `run_id` | `str` | Which run produced this event |
| `data` | `dict` | Event-specific payload |
| `timestamp` | `datetime` | UTC timestamp |

Use `event.to_dict()` to serialize to a JSON-compatible dict.

### `EventType` reference

#### Run lifecycle

| Event | Data fields |
|---|---|
| `RUN_STARTED` | `commands` (int count), `max_iterations`, `timeout`, `delay` |
| `RUN_STOPPED` | `reason` (`StopReason`), `total`, `completed`, `failed`, `timed_out` |
| `RUN_PAUSED` | -- |
| `RUN_RESUMED` | -- |

#### Iteration lifecycle

| Event | Data fields |
|---|---|
| `ITERATION_STARTED` | `iteration` |
| `ITERATION_COMPLETED` | `iteration`, `returncode`, `duration`, `duration_formatted`, `detail`, `log_file`, `result_text` |
| `ITERATION_FAILED` | same as `ITERATION_COMPLETED` |
| `ITERATION_TIMED_OUT` | same as `ITERATION_COMPLETED` (`returncode` is `None`) |

#### Commands

| Event | Data fields |
|---|---|
| `COMMANDS_STARTED` | `iteration`, `count` |
| `COMMANDS_COMPLETED` | `iteration`, `count` |

#### Prompt assembly

| Event | Data fields |
|---|---|
| `PROMPT_ASSEMBLED` | `iteration`, `prompt_length` |

#### Other

| Event | Data fields |
|---|---|
| `AGENT_ACTIVITY` | `iteration`, `raw` (dict — one stream-json line from the agent) |
| `LOG_MESSAGE` | `message`, `level` (`"info"` / `"error"`), `traceback` (optional) |

### Built-in emitters

| Emitter | Description |
|---|---|
| `NullEmitter` | Discards all events silently. Default when no emitter is passed. |
| `QueueEmitter` | Pushes events into a `queue.Queue` for async consumption. |
| `FanoutEmitter` | Broadcasts each event to multiple emitters. |
| `BoundEmitter` | Wraps any emitter with a fixed `run_id` so you don't have to construct `Event` objects manually. |

```python
from ralphify import QueueEmitter, FanoutEmitter, BoundEmitter

# Consume events from a queue
q_emitter = QueueEmitter()
run_loop(config, state, emitter=q_emitter)
while not q_emitter.queue.empty():
    event = q_emitter.queue.get()
    print(event.to_dict())

# Broadcast to multiple listeners
fanout = FanoutEmitter([q_emitter, MyEmitter()])
run_loop(config, state, emitter=fanout)

# Emit events without constructing Event objects
bound = BoundEmitter(q_emitter, run_id="my-run")
bound(EventType.LOG_MESSAGE, {"message": "hello", "level": "info"})
```

---

## Concurrent runs with `RunManager`

`RunManager` is a thread-safe registry for launching and controlling multiple ralph loops concurrently. Each run gets its own daemon thread and event queue.

```python
from pathlib import Path
from ralphify import RunManager, RunConfig, Command

manager = RunManager()

docs_config = RunConfig(
    agent="claude -p", ralph_dir=Path("docs-ralph"),
    ralph_file=Path("docs-ralph/RALPH.md"),
    commands=[Command(name="build", run="mkdocs build --strict")],
    max_iterations=5,
)
tests_config = RunConfig(
    agent="claude -p", ralph_dir=Path("tests-ralph"),
    ralph_file=Path("tests-ralph/RALPH.md"),
    commands=[Command(name="tests", run="uv run pytest -x")],
    max_iterations=3,
)

docs_run = manager.create_run(docs_config)
tests_run = manager.create_run(tests_config)

manager.start_run(docs_run.state.run_id)
manager.start_run(tests_run.state.run_id)

# Check progress
for run in manager.list_runs():
    print(f"{run.state.run_id}: {run.state.status.value} — {run.state.completed} done")

# Control a run
manager.pause_run(docs_run.state.run_id)
manager.resume_run(docs_run.state.run_id)
manager.stop_run(docs_run.state.run_id)
```

### `ManagedRun`

Each run created by `RunManager` is wrapped in a `ManagedRun` — a bundle of config, state, and event queue.

| Field | Type | Description |
|---|---|---|
| `config` | `RunConfig` | The run's configuration |
| `state` | `RunState` | Observable state — inspect progress or call control methods |
| `emitter` | `QueueEmitter` | Event queue — drain `emitter.queue` to consume events |

#### Adding custom listeners

Register additional emitters to receive events from a run. Add listeners **before** calling `start_run()`:

```python
from ralphify import RunManager, RunConfig, ManagedRun

class SlackNotifier:
    def emit(self, event):
        if event.type == EventType.RUN_STOPPED:
            notify_slack(f"Run {event.run_id} finished")

manager = RunManager()
run = manager.create_run(config)
run.add_listener(SlackNotifier())  # receives all events alongside the queue
manager.start_run(run.state.run_id)
```

When extra listeners are registered, events are broadcast to both the built-in queue and all custom listeners via a `FanoutEmitter`.

### `RunManager` methods

| Method | Description |
|---|---|
| `create_run(config)` | Create a `ManagedRun` from a `RunConfig`. Does not start it. |
| `start_run(run_id)` | Start the run in a daemon thread. |
| `stop_run(run_id)` | Signal the run to stop after the current iteration. |
| `pause_run(run_id)` | Pause the run between iterations. |
| `resume_run(run_id)` | Resume a paused run. |
| `list_runs()` | Return a snapshot of all registered runs. |
| `get_run(run_id)` | Look up a run by ID. |
