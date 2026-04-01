"""Ralphify — a minimal harness for running autonomous AI coding loops.

Exposes the ``ralph`` CLI entry point, the package version, and the
public library API for programmatic use.

Quick start::

    from ralphify import run_loop, RunConfig, RunState, Command

    config = RunConfig(
        agent="claude -p --dangerously-skip-permissions",
        ralph_dir=Path("."),
        ralph_file=Path("RALPH.md"),
    )
    state = RunState(run_id="my-run")
    run_loop(config, state)
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("ralphify")
except PackageNotFoundError:
    __version__ = "0.0.0"

from ralphify.engine import run_loop
from ralphify._run_types import Command, RunConfig, RunState, RunStatus
from ralphify._events import (
    BoundEmitter,
    Event,
    EventEmitter,
    EventType,
    FanoutEmitter,
    NullEmitter,
    QueueEmitter,
    StopReason,
)
from ralphify.manager import ManagedRun, RunManager


def main() -> None:
    """Entry point for the ``ralph`` CLI (called by the console script)."""
    from ralphify.cli import app

    app()


__all__ = [
    "__version__",
    "run_loop",
    "BoundEmitter",
    "Command",
    "RunConfig",
    "RunState",
    "RunStatus",
    "Event",
    "EventEmitter",
    "EventType",
    "FanoutEmitter",
    "NullEmitter",
    "QueueEmitter",
    "StopReason",
    "ManagedRun",
    "RunManager",
]
