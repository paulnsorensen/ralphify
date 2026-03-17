---
description: Use ralphify as a Python library — run loops programmatically, manage concurrent runs, listen to events, and discover primitives without the CLI.
---

# Python API

Ralphify can be used as a Python library. This is useful when you want to embed the loop in a larger automation pipeline, react to events programmatically, manage concurrent runs, or script runs with more control than the CLI provides.

All public API is available from the top-level `ralphify` package.

## Quick start

```python
from ralphify import run_loop, RunConfig, RunState

config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    ralph_file="RALPH.md",
    max_iterations=3,
)
state = RunState(run_id="my-run")
run_loop(config, state)
```

This runs the same loop as `ralph run -n 3`. When the loop finishes, `state` contains the results.

---

## `run_loop(config, state, emitter=None)`

The main loop. Discovers primitives, assembles prompts, pipes them to the agent, runs checks, and repeats. **Blocks until the loop finishes.**

| Parameter | Type | Description |
|---|---|---|
| `config` | `RunConfig` | All settings for the run |
| `state` | `RunState` | Observable state — counters, status, control methods |
| `emitter` | `EventEmitter | None` | Event listener. `None` uses `NullEmitter` (silent) |

---

## `RunConfig`

All settings for a single run. Fields match the CLI options.

```python
config = RunConfig(
    command="claude",
    args=["-p", "--dangerously-skip-permissions"],
    ralph_file="RALPH.md",
    prompt_text=None,          # Pass prompt text directly instead of reading from file
    ralph_name=None,           # Named ralph from .ralphify/ralphs/
    max_iterations=10,
    delay=2.0,
    timeout=300,
    stop_on_error=True,
    log_dir="ralph_logs",
    project_root=Path("."),
    global_checks=None,        # e.g. ["lint", "tests"]
    global_contexts=None,      # e.g. ["git-log"]
)
```

| Field | Type | Default | Description |
|---|---|---|---|
| `command` | `str` | — | Agent CLI executable |
| `args` | `list[str]` | — | Arguments passed to the command |
| `ralph_file` | `str` | — | Path to the ralph file (ignored when `prompt_text` is set) |
| `prompt_text` | `str | None` | `None` | Pass prompt text directly instead of reading from `ralph_file` |
| `ralph_name` | `str | None` | `None` | Named ralph from `.ralphify/ralphs/` |
| `max_iterations` | `int | None` | `None` | Max iterations (`None` = unlimited) |
| `delay` | `float` | `0` | Seconds to wait between iterations |
| `timeout` | `float | None` | `None` | Max seconds per iteration |
| `stop_on_error` | `bool` | `False` | Stop loop if agent exits non-zero |
| `log_dir` | `str | None` | `None` | Directory for iteration log files |
| `project_root` | `Path` | `Path(".")` | Project root directory |
| `global_checks` | `list[str] | None` | `None` | Global check names to include |
| `global_contexts` | `list[str] | None` | `None` | Global context names to include |

`RunConfig` is mutable — you can change fields mid-run, and the loop picks up changes at the next iteration boundary.

!!! tip "Dynamic prompts with `prompt_text`"
    Use `prompt_text` when you want to generate prompts programmatically instead of reading from a file. When set, `ralph_file` is still required but its contents are ignored — the loop uses `prompt_text` as the prompt body. Context placeholders (`{{ contexts.name }}`) and check failure injection still work normally on the provided text.

    ```python
    tasks = ["Add input validation to the login endpoint", "Write tests for the user model"]

    for task in tasks:
        config = RunConfig(
            command="claude",
            args=["-p", "--dangerously-skip-permissions"],
            ralph_file="RALPH.md",  # required but ignored when prompt_text is set
            prompt_text=f"You are an autonomous coding agent.\n\nTask: {task}\n\nCommit when done.",
            max_iterations=1,
        )
        state = RunState(run_id=f"task-{tasks.index(task)}")
        run_loop(config, state)
    ```

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
    `timed_out` is a **subset** of `failed`, not an independent category. A timed-out iteration increments both `timed_out` and `failed`. Therefore `completed + failed == total` — do not add `timed_out` separately.

### Control methods

Thread-safe methods for controlling the loop from another thread:

```python
state.request_stop()      # Stop after current iteration
state.request_pause()     # Pause between iterations
state.request_resume()    # Resume a paused loop
state.request_reload()    # Re-discover primitives before next iteration
```

---

## `RunStatus`

Lifecycle status of a run. Transitions follow: `PENDING` → `RUNNING` → terminal state.

| Status | Value | Description |
|---|---|---|
| `PENDING` | `"pending"` | Created but not yet started |
| `RUNNING` | `"running"` | Loop is executing iterations |
| `PAUSED` | `"paused"` | Paused between iterations, waiting for resume |
| `STOPPED` | `"stopped"` | Stopped by user via `request_stop()` |
| `COMPLETED` | `"completed"` | Reached `max_iterations` or finished naturally |
| `FAILED` | `"failed"` | Crashed with an unhandled exception |

```python
from ralphify import RunStatus

if state.status == RunStatus.COMPLETED:
    print(f"Finished: {state.completed} iterations succeeded")
elif state.status == RunStatus.FAILED:
    print(f"Crashed after {state.total} iterations")
```

---

## Event system

The loop emits structured events at each step. Implement the `EventEmitter` protocol (a single `emit(event)` method) to listen.

### Custom emitter

```python
from ralphify import Event, EventType, RunConfig, RunState, run_loop


class MyEmitter:
    def emit(self, event: Event) -> None:
        if event.type == EventType.ITERATION_COMPLETED:
            print(f"Iteration {event.data['iteration']} done in {event.data['duration_formatted']}")
        elif event.type == EventType.CHECK_FAILED:
            print(f"  Check '{event.data['name']}' failed (exit {event.data['exit_code']})")


config = RunConfig(command="claude", args=["-p"], ralph_file="RALPH.md", max_iterations=3)
state = RunState(run_id="observed-run")
run_loop(config, state, emitter=MyEmitter())
```

### `Event`

Each event carries:

| Field | Type | Description |
|---|---|---|
| `type` | `EventType` | What happened |
| `run_id` | `str` | Which run produced this event |
| `data` | `dict` | Event-specific payload (see table below) |
| `timestamp` | `datetime` | UTC timestamp |

Use `event.to_dict()` to serialize to a JSON-compatible dict.

### `EventType` reference

All event types emitted by the run loop, grouped by category.

#### Run lifecycle

| Event | Data fields |
|---|---|
| `RUN_STARTED` | `checks`, `contexts` (int counts), `max_iterations`, `timeout`, `delay`, `ralph_name` |
| `RUN_STOPPED` | `reason` (`"completed"` / `"user_requested"` / `"error"`), `total`, `completed`, `failed`, `timed_out` |
| `RUN_PAUSED` | — |
| `RUN_RESUMED` | — |

#### Iteration lifecycle

| Event | Data fields |
|---|---|
| `ITERATION_STARTED` | `iteration` |
| `ITERATION_COMPLETED` | `iteration`, `returncode`, `duration`, `duration_formatted`, `detail`, `log_file` |
| `ITERATION_FAILED` | same as `ITERATION_COMPLETED` |
| `ITERATION_TIMED_OUT` | same as `ITERATION_COMPLETED` (`returncode` is `None`) |

#### Checks

| Event | Data fields |
|---|---|
| `CHECKS_STARTED` | `iteration`, `count` |
| `CHECK_PASSED` | `iteration`, `name`, `passed` (`True`), `exit_code`, `timed_out` |
| `CHECK_FAILED` | `iteration`, `name`, `passed` (`False`), `exit_code`, `timed_out` |
| `CHECKS_COMPLETED` | `iteration`, `passed`, `failed`, `results` (list of per-check dicts) |

#### Prompt assembly

| Event | Data fields |
|---|---|
| `CONTEXTS_RESOLVED` | `iteration`, `count` |
| `PROMPT_ASSEMBLED` | `iteration`, `prompt_length` |

#### Other

| Event | Data fields |
|---|---|
| `AGENT_ACTIVITY` | `raw` (dict — one stream-json line from the agent) |
| `PRIMITIVES_RELOADED` | `checks`, `contexts` (int counts) |
| `LOG_MESSAGE` | `message`, `level` (`"info"` / `"error"`), `traceback` (optional) |

### Built-in emitters

| Emitter | Description |
|---|---|
| `NullEmitter` | Discards all events silently. Default when no emitter is passed. |
| `QueueEmitter` | Pushes events into a `queue.Queue` for async consumption. |
| `FanoutEmitter` | Broadcasts each event to multiple emitters. |

```python
from ralphify import QueueEmitter, FanoutEmitter, NullEmitter

# Consume events from a queue
q_emitter = QueueEmitter()
run_loop(config, state, emitter=q_emitter)
while not q_emitter.queue.empty():
    event = q_emitter.queue.get()
    print(event.to_dict())

# Broadcast to multiple listeners
fanout = FanoutEmitter([q_emitter, MyEmitter()])
run_loop(config, state, emitter=fanout)

# Pass your own queue
import queue
my_queue = queue.Queue()
q_emitter = QueueEmitter(q=my_queue)
```

---

## Concurrent runs with `RunManager`

`RunManager` is a thread-safe registry for launching and controlling multiple ralph loops concurrently. Each run gets its own daemon thread and event queue.

```python
from ralphify import RunManager, RunConfig

manager = RunManager()

# Create and start two concurrent runs
docs_config = RunConfig(
    command="claude", args=["-p"], ralph_file=".ralphify/ralphs/docs/RALPH.md",
    ralph_name="docs", max_iterations=5,
)
tests_config = RunConfig(
    command="claude", args=["-p"], ralph_file=".ralphify/ralphs/tests/RALPH.md",
    ralph_name="tests", max_iterations=3,
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

### `RunManager` methods

| Method | Description |
|---|---|
| `create_run(config)` | Create a `ManagedRun` from a `RunConfig`. Assigns a unique run ID. Does not start it. |
| `start_run(run_id)` | Start the run in a daemon thread. |
| `stop_run(run_id)` | Signal the run to stop after the current iteration. |
| `pause_run(run_id)` | Pause the run between iterations. |
| `resume_run(run_id)` | Resume a paused run. |
| `list_runs()` | Return a snapshot of all registered runs. |
| `get_run(run_id)` | Look up a run by ID (returns `None` if not found). |

### `ManagedRun`

Returned by `RunManager.create_run()`. Bundles a run's config, state, emitter, and thread.

| Field / Method | Type | Description |
|---|---|---|
| `config` | `RunConfig` | The run's configuration |
| `state` | `RunState` | Observable state and control methods |
| `emitter` | `QueueEmitter` | Event queue — drain `emitter.queue` to consume events |
| `thread` | `Thread | None` | The daemon thread (set after `start_run`) |
| `add_listener(emitter)` | method | Register an additional emitter to receive events |

Register extra listeners **before** calling `start_run`:

```python
managed = manager.create_run(config)
managed.add_listener(MyEmitter())  # receives events alongside the queue
manager.start_run(managed.state.run_id)
```

---

## Primitive discovery

Discover checks, contexts, and ralphs without running the loop.

### Checks

```python
from pathlib import Path
from ralphify import discover_checks, run_all_checks

root = Path(".")

# Discover all checks (enabled and disabled)
for check in discover_checks(root):
    print(f"{check.name}: command={check.command}, enabled={check.enabled}")

# Run enabled checks
enabled = [c for c in discover_checks(root) if c.enabled]
results = run_all_checks(enabled, root)
for r in results:
    status = "PASS" if r.passed else "FAIL"
    print(f"  {r.check.name}: {status} (exit {r.exit_code})")
```

### Contexts

```python
from ralphify import discover_contexts, run_all_contexts

for ctx in discover_contexts(root):
    print(f"{ctx.name}: command={ctx.command}, static={bool(ctx.static_content)}")

# Run enabled contexts
enabled = [c for c in discover_contexts(root) if c.enabled]
results = run_all_contexts(enabled, root)
for r in results:
    print(f"  {r.context.name}: {len(r.output)} chars, success={r.success}")
```

### Ralphs

```python
from ralphify import discover_ralphs, resolve_ralph_name

# List all named ralphs
for ralph in discover_ralphs(root):
    print(f"{ralph.name}: {ralph.description}")
    if ralph.checks:
        print(f"  checks: {ralph.checks}")
    if ralph.contexts:
        print(f"  contexts: {ralph.contexts}")

# Look up a specific ralph (raises ValueError if not found)
docs_ralph = resolve_ralph_name("docs", root)
print(docs_ralph.content)  # The full prompt text
```
