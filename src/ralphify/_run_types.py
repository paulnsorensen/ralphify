"""Data types for run configuration and state.

These are the core types shared across the engine, CLI, manager, and UI
modules.  They are intentionally separate from ``engine.py`` so modules
that only need the types don't pull in the engine's execution logic.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class RunStatus(Enum):
    """Lifecycle status of a run."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RunConfig:
    """All settings for a single run.  Mutable — fields can change mid-run."""

    command: str
    args: list[str]
    prompt_file: str
    prompt_text: str | None = None
    prompt_name: str | None = None
    max_iterations: int | None = None
    delay: float = 0
    timeout: float | None = None
    stop_on_error: bool = False
    log_dir: str | None = None
    project_root: Path = field(default_factory=lambda: Path("."))


@dataclass
class RunState:
    """Observable state for a run.

    Control methods (:meth:`request_stop`, :meth:`request_pause`,
    :meth:`request_resume`) use :class:`threading.Event` so the run loop
    can react at iteration boundaries without busy-waiting.

    **Threading model**: counters (``iteration``, ``completed``, etc.) are
    written only by the engine thread and read by API threads.  Under
    CPython's GIL this is safe — readers may see a briefly stale value,
    which is acceptable for dashboard display.
    """

    run_id: str
    status: RunStatus = RunStatus.PENDING
    iteration: int = 0
    completed: int = 0
    failed: int = 0
    timed_out: int = 0

    _stop_requested: bool = False
    _pause_event: threading.Event = field(default_factory=threading.Event)
    _reload_requested: bool = False

    def __post_init__(self) -> None:
        # Start un-paused
        self._pause_event.set()

    def request_stop(self) -> None:
        """Signal the loop to stop after the current iteration."""
        self._stop_requested = True
        # Unpause so the loop can exit
        self._pause_event.set()

    def request_pause(self) -> None:
        """Pause the loop between iterations until resumed."""
        self.status = RunStatus.PAUSED
        self._pause_event.clear()

    def request_resume(self) -> None:
        """Resume a paused loop."""
        self.status = RunStatus.RUNNING
        self._pause_event.set()

    def request_reload(self) -> None:
        """Request re-discovery of primitives before the next iteration."""
        self._reload_requested = True

    @property
    def stop_requested(self) -> bool:
        """Whether a stop has been requested."""
        return self._stop_requested

    @property
    def paused(self) -> bool:
        """Whether the run is currently paused."""
        return not self._pause_event.is_set()

    def wait_for_unpause(self, timeout: float | None = None) -> bool:
        """Block until unpaused or timeout. Returns True if unpaused."""
        return self._pause_event.wait(timeout=timeout)

    def consume_reload_request(self) -> bool:
        """If a reload was requested, clear the flag and return True."""
        if self._reload_requested:
            self._reload_requested = False
            return True
        return False
