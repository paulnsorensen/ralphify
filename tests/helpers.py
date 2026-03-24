"""Shared constants and helpers for ralphify tests.

Import these directly: ``from helpers import MOCK_SUBPROCESS, ok_result``
Fixtures stay in conftest.py — pytest discovers them automatically.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from ralphify._events import Event, EventType, QueueEmitter
from ralphify._frontmatter import RALPH_MARKER, serialize_frontmatter
from ralphify._run_types import RunConfig, RunState
from ralphify._runner import RunResult


# ── Patch targets ─────────────────────────────────────────────────────

MOCK_SUBPROCESS = "ralphify._agent.subprocess.Popen"
"""Patch target for subprocess.Popen inside the agent module (blocking path)."""

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

MOCK_SKILLS_WHICH = "ralphify._skills.shutil.which"
"""Patch target for shutil.which inside the skills module."""


# ── Factory helpers ───────────────────────────────────────────────────


def make_ralph(
    tmp_path: Path,
    prompt: str = "go",
    agent: str = "claude -p --dangerously-skip-permissions",
    commands: list[dict[str, Any]] | None = None,
    args: list[str] | None = None,
) -> Path:
    """Create a ralph directory with a proper RALPH.md for CLI-level tests.

    Returns the ralph directory path.  Uses :func:`serialize_frontmatter`
    to build the file, so the YAML is always well-formed.
    """
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    frontmatter: dict[str, Any] = {"agent": agent}
    if commands:
        frontmatter["commands"] = commands
    if args:
        frontmatter["args"] = args
    content = serialize_frontmatter(frontmatter, prompt)
    (ralph_dir / RALPH_MARKER).write_text(content)
    return ralph_dir


def make_config(tmp_path: Path, ralph_content: str = "test prompt", **overrides) -> RunConfig:
    """Create a RunConfig pointing at a temp ralph directory.

    *ralph_content* is written to the ``RALPH.md`` file every time, so
    tests can supply custom frontmatter + body without manually creating
    the ralph directory first.
    """
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    ralph_file = ralph_dir / RALPH_MARKER
    ralph_file.write_text(ralph_content)

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


def _make_completed_process(
    returncode: int = 0, stdout: str = "", stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    """Build a CompletedProcess with the given values."""
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def ok_result(
    *_args: Any, stdout: str = "", stderr: str = "", **_kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Subprocess result with exit code 0.

    Works as a direct factory — ``ok_result(stdout="out\\n")`` — and as a
    ``side_effect`` callable where mock call args are silently absorbed.
    Used by runner tests that mock ``subprocess.run``.
    """
    return _make_completed_process(returncode=0, stdout=stdout, stderr=stderr)


def fail_result(
    *_args: Any, stdout: str = "", stderr: str = "", **_kwargs: Any,
) -> subprocess.CompletedProcess[str]:
    """Subprocess result with exit code 1.

    Works as a direct factory and as a ``side_effect`` callable (see
    :func:`ok_result`).
    """
    return _make_completed_process(returncode=1, stdout=stdout, stderr=stderr)


def _make_mock_proc(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    """Build a MagicMock that mimics Popen for the agent blocking path."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate.return_value = (stdout, stderr)
    proc.wait.return_value = returncode
    proc.poll.return_value = returncode
    proc.pid = 12345
    return proc


def ok_proc(*_args: Any, stdout: str = "", stderr: str = "", **_kwargs: Any) -> MagicMock:
    """Popen mock with exit code 0.  Works as a factory and ``side_effect``."""
    return _make_mock_proc(returncode=0, stdout=stdout, stderr=stderr)


def fail_proc(*_args: Any, stdout: str = "", stderr: str = "", **_kwargs: Any) -> MagicMock:
    """Popen mock with exit code 1."""
    return _make_mock_proc(returncode=1, stdout=stdout, stderr=stderr)


def timeout_proc(
    *_args: Any, timeout: float = 5, stdout: str = "", stderr: str = "", **_kwargs: Any,
) -> MagicMock:
    """Popen mock whose communicate() raises TimeoutExpired."""
    proc = _make_mock_proc(returncode=0)
    proc.communicate.side_effect = [
        subprocess.TimeoutExpired(cmd="agent", timeout=timeout),
        (stdout, stderr),
    ]
    proc.poll.return_value = None
    return proc


def ok_run_result(
    output: str = "",
) -> RunResult:
    """RunResult with exit code 0 (success).

    Mirrors :func:`ok_result` but for the runner module's return type.
    """
    return RunResult(returncode=0, output=output)


def make_mock_popen(
    stdout_lines: str = "", stderr_text: str = "", returncode: int = 0,
) -> MagicMock:
    """Create a MagicMock that mimics subprocess.Popen for the streaming path."""
    proc = MagicMock()
    proc.stdin = MagicMock()
    proc.stdout = io.StringIO(stdout_lines)
    proc.stderr = io.StringIO(stderr_text)
    proc.returncode = returncode
    proc.wait.return_value = returncode
    proc.poll.return_value = returncode  # not None → process finished
    return proc


def drain_events(emitter: QueueEmitter) -> list[Event]:
    """Drain all events from a QueueEmitter and return them as a list."""
    events = []
    while not emitter.queue.empty():
        events.append(emitter.queue.get())
    return events


def events_of_type(events: list[Event], event_type: EventType) -> list[Event]:
    """Filter a list of events to only those matching *event_type*."""
    return [e for e in events if e.type == event_type]


def event_types(events: list[Event]) -> list[EventType]:
    """Extract the ordered list of event types from a list of events."""
    return [e.type for e in events]
