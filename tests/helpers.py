"""Shared constants and helpers for ralphify tests.

Import these directly: ``from helpers import MOCK_SUBPROCESS, ok_result``
Fixtures stay in conftest.py — pytest discovers them automatically.
"""

import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from ralphify._events import Event, QueueEmitter
from ralphify._frontmatter import serialize_frontmatter
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


def make_ralph(
    tmp_path: Path,
    prompt: str = "go",
    agent: str = "claude -p --dangerously-skip-permissions",
    commands: list[dict] | None = None,
    args: list[str] | None = None,
) -> Path:
    """Create a ralph directory with a proper RALPH.md for CLI-level tests.

    Returns the ralph directory path.  Uses :func:`serialize_frontmatter`
    to build the file, so the YAML is always well-formed.
    """
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    frontmatter: dict = {"agent": agent}
    if commands:
        frontmatter["commands"] = commands
    if args:
        frontmatter["args"] = args
    content = serialize_frontmatter(frontmatter, prompt)
    (ralph_dir / "RALPH.md").write_text(content)
    return ralph_dir


def make_config(tmp_path: Path, ralph_content: str = "test prompt", **overrides) -> RunConfig:
    """Create a RunConfig pointing at a temp ralph directory.

    *ralph_content* is written to the ``RALPH.md`` file every time, so
    tests can supply custom frontmatter + body without manually creating
    the ralph directory first.
    """
    ralph_dir = tmp_path / "my-ralph"
    ralph_dir.mkdir(exist_ok=True)
    ralph_file = ralph_dir / "RALPH.md"
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


def make_mock_popen(stdout_lines="", stderr_text="", returncode=0):
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
