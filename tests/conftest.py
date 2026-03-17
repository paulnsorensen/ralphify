"""Shared pytest fixtures and helpers for ralphify tests."""

import subprocess
from dataclasses import replace

import pytest

from ralphify._events import QueueEmitter
from ralphify._run_types import RunConfig, RunState


@pytest.fixture(autouse=True)
def _disable_streaming(monkeypatch):
    """Disable the Popen-based streaming path in all tests.

    Tests mock ``subprocess.run`` to avoid real process execution.  The
    streaming code path uses ``subprocess.Popen`` instead, which would
    bypass those mocks.  Forcing ``_is_claude_command`` to return ``False``
    ensures all tests go through the ``subprocess.run`` path.
    """
    monkeypatch.setattr("ralphify._agent._is_claude_command", lambda cmd: False)


# ── Shared constants ───────────────────────────────────────────────────

MOCK_SUBPROCESS = "ralphify._agent.subprocess.run"
"""Patch target for subprocess.run inside the agent module."""


# ── Shared helpers ─────────────────────────────────────────────────────


def make_config(tmp_path, **overrides):
    """Create a RunConfig pointing at a temp directory with RALPH.md."""
    prompt_path = tmp_path / "RALPH.md"
    if not prompt_path.exists():
        prompt_path.write_text("test prompt")
    config = RunConfig(
        command="echo",
        args=[],
        ralph_file=str(prompt_path),
        max_iterations=1,
        project_root=tmp_path,
    )
    return replace(config, **overrides) if overrides else config


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
