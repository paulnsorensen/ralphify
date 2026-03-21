"""Multi-run orchestration for concurrent ralph loops.

Wraps run engine threads and provides a thread-safe registry for launching,
controlling, and inspecting multiple runs from external code.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from ralphify._events import EventEmitter, FanoutEmitter, QueueEmitter
from ralphify._run_types import RunConfig, RunState, generate_run_id
from ralphify.engine import run_loop


@dataclass
class ManagedRun:
    """A run bundled with its background thread and event queue.

    Created by :meth:`RunManager.create_run`.  Use ``state`` to inspect
    progress or call control methods (stop, pause, resume), and drain
    ``emitter.queue`` to consume events.  Register extra listeners with
    :meth:`add_listener` *before* calling :meth:`RunManager.start_run`.
    """

    config: RunConfig
    state: RunState
    emitter: QueueEmitter
    thread: threading.Thread | None = None
    _extra_emitters: list[EventEmitter] = field(default_factory=list)

    def add_listener(self, emitter: EventEmitter) -> None:
        """Register an additional emitter to receive events from this run."""
        self._extra_emitters.append(emitter)

    def build_emitter(self) -> EventEmitter:
        """Build the composite emitter for this run.

        Returns a :class:`FanoutEmitter` when extra listeners are registered,
        or the queue emitter directly when there are none.  This keeps the
        emitter composition logic inside ``ManagedRun`` so callers don't need
        to reach into private fields.
        """
        if self._extra_emitters:
            return FanoutEmitter([self.emitter, *self._extra_emitters])
        return self.emitter


class RunManager:
    """Thread-safe registry for managing concurrent background runs.

    Use this instead of calling :func:`run_loop` directly when you need to
    launch multiple runs, control them from another thread (e.g. a web
    server), or list/inspect all active runs.  Each run gets its own daemon
    thread and event queue.
    """

    def __init__(self) -> None:
        self._runs: dict[str, ManagedRun] = {}
        self._lock = threading.Lock()

    def _get_run(self, run_id: str) -> ManagedRun:
        """Look up a run by ID under the lock. Raises ``KeyError`` if missing."""
        with self._lock:
            try:
                return self._runs[run_id]
            except KeyError:
                raise KeyError(f"No run with ID '{run_id}'") from None

    def create_run(self, config: RunConfig) -> ManagedRun:
        """Create a new run from *config* and register it.

        Assigns a unique run ID and returns the :class:`ManagedRun`.
        The run is not started — call :meth:`start_run` to begin execution.
        """
        run_id = generate_run_id()
        state = RunState(run_id=run_id)
        emitter = QueueEmitter()
        managed = ManagedRun(config=config, state=state, emitter=emitter)
        with self._lock:
            self._runs[run_id] = managed
        return managed

    def start_run(self, run_id: str) -> None:
        """Start the run loop in a daemon thread.

        The thread calls :func:`engine.run_loop` with the emitter built
        by :meth:`ManagedRun.build_emitter`, which fans out to the queue
        and any extra listeners.

        The entire operation runs under the registry lock so that
        concurrent calls cannot race on the same run.

        Raises ``KeyError`` if the run ID is not registered.
        """
        with self._lock:
            try:
                managed = self._runs[run_id]
            except KeyError:
                raise KeyError(f"No run with ID '{run_id}'") from None
            emitter = managed.build_emitter()
            thread = threading.Thread(
                target=run_loop,
                args=(managed.config, managed.state, emitter),
                daemon=True,
                name=f"run-{run_id}",
            )
            managed.thread = thread
            thread.start()

    def stop_run(self, run_id: str) -> None:
        """Signal the run to stop after the current iteration finishes."""
        self._get_run(run_id).state.request_stop()

    def pause_run(self, run_id: str) -> None:
        """Pause the run between iterations until :meth:`resume_run` is called."""
        self._get_run(run_id).state.request_pause()

    def resume_run(self, run_id: str) -> None:
        """Resume a paused run."""
        self._get_run(run_id).state.request_resume()

    def list_runs(self) -> list[ManagedRun]:
        """Return a snapshot of all registered runs."""
        with self._lock:
            return list(self._runs.values())

    def get_run(self, run_id: str) -> ManagedRun | None:
        """Look up a run by ID, returning ``None`` if not found."""
        with self._lock:
            return self._runs.get(run_id)
