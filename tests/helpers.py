"""Shared constants and helpers for ralphify tests.

Import these directly: ``from helpers import MOCK_SUBPROCESS, ok_result``
Fixtures stay in conftest.py — pytest discovers them automatically.
"""

import subprocess
from pathlib import Path

from ralphify._events import Event, QueueEmitter
from ralphify._run_types import RunConfig, RunState


# ── Patch targets ─────────────────────────────────────────────────────

MOCK_SUBPROCESS = "ralphify._agent.subprocess.run"
"""Patch target for subprocess.run inside the agent module."""

MOCK_POPEN = "ralphify._agent.subprocess.Popen"
"""Patch target for subprocess.Popen inside the agent module (streaming path)."""

MOCK_RUNNER_SUBPROCESS = "ralphify._runner.subprocess.run"
"""Patch target for subprocess.run inside the runner module."""

MOCK_WHICH = "ralphify.cli.shutil.which"
"""Patch target for shutil.which inside the CLI module."""

MOCK_RUN_COMMAND = "ralphify.engine.run_command"
"""Patch target for run_command inside the engine module."""

MOCK_ENGINE_SLEEP = "ralphify.engine.time.sleep"
"""Patch target for time.sleep inside the engine module."""


# ── Factory helpers ───────────────────────────────────────────────────


def make_config(tmp_path: Path, **overrides) -> RunConfig:
    """Create a RunConfig pointing at a temp ralph directory."""
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    ralph_file = ralph_dir / "RALPH.md"
    if not ralph_file.exists():
        ralph_file.write_text("test prompt")

    defaults = dict(
        agent="echo",
        ralph_dir=ralph_dir,
        ralph_file=ralph_file,
        max_iterations=1,
        project_root=tmp_path,
    )
    defaults.update(overrides)
    return RunConfig(**defaults)


def make_state() -> RunState:
    """Create a RunState with a fixed test run ID."""
    return RunState(run_id="test-run-001")


def ok_result(*args, stdout="", stderr="", **kwargs) -> subprocess.CompletedProcess:
    """Subprocess side_effect that returns exit code 0.

    Works both as a ``side_effect`` callable (receives mock call args) and
    as a direct factory: ``ok_result(stdout="out\\n")``.
    """
    return subprocess.CompletedProcess(args=args, returncode=0, stdout=stdout, stderr=stderr)


def fail_result(*args, stdout="", stderr="", **kwargs) -> subprocess.CompletedProcess:
    """Subprocess side_effect that returns exit code 1.

    Works both as a ``side_effect`` callable (receives mock call args) and
    as a direct factory: ``fail_result(stderr="err\\n")``.
    """
    return subprocess.CompletedProcess(args=args, returncode=1, stdout=stdout, stderr=stderr)


def drain_events(emitter: QueueEmitter) -> list[Event]:
    """Drain all events from a QueueEmitter and return them as a list."""
    events = []
    while not emitter.queue.empty():
        events.append(emitter.queue.get())
    return events
