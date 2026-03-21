"""Shared pytest fixtures and helpers for ralphify tests."""

import subprocess
from pathlib import Path

import pytest

from ralphify._run_types import RunConfig, RunState


@pytest.fixture(autouse=True)
def _disable_streaming(monkeypatch):
    """Disable the Popen-based streaming path in all tests."""
    monkeypatch.setattr("ralphify._agent._supports_stream_json", lambda cmd: False)


# ── Shared constants ───────────────────────────────────────────────────

MOCK_SUBPROCESS = "ralphify._agent.subprocess.run"
"""Patch target for subprocess.run inside the agent module."""

MOCK_RUNNER_SUBPROCESS = "ralphify._runner.subprocess.run"
"""Patch target for subprocess.run inside the runner module."""


# ── Shared helpers ─────────────────────────────────────────────────────


def make_config(tmp_path, **overrides):
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


def make_state():
    """Create a RunState with a fixed test run ID."""
    return RunState(run_id="test-run-001")


def ok_result(*args, **kwargs):
    """Subprocess side_effect that returns exit code 0."""
    return subprocess.CompletedProcess(args=args, returncode=0)


def fail_result(*args, **kwargs):
    """Subprocess side_effect that returns exit code 1."""
    return subprocess.CompletedProcess(args=args, returncode=1)


def drain_events(emitter):
    """Drain all events from a QueueEmitter and return them as a list."""
    events = []
    while not emitter.queue.empty():
        events.append(emitter.queue.get())
    return events
