"""Pluggable CLI adapter layer.

Each supported agent CLI (Claude, Codex, Copilot, ...) implements the
:class:`CLIAdapter` protocol in its own module under this package.  The
engine dispatches on :func:`select_adapter` at run time, so adding a new
CLI means writing one file and registering it in :data:`ADAPTERS` — no
edits to the engine, emitter, or subprocess machinery.

Adapters translate the CLI's native output format to a common
:class:`AdapterEvent` stream and advertise capability flags so the core
loop can gracefully degrade when a CLI lacks structured output or hook
injection.  Process lifecycle (spawn, SIGTERM at cap, reap) stays in
``_agent.py``; adapters only observe.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, NamedTuple, Protocol, runtime_checkable


AdapterEventKind = Literal["tool_use", "turn", "message", "result"]
"""Categories of events an adapter can surface from a CLI's output stream."""

CountsWhat = Literal["tool_use", "turn", "none"]
"""What an adapter counts against ``max_turns`` — tool uses, turns, or nothing."""


class AdapterEvent(NamedTuple):
    """A single structured event parsed from a CLI's output stream.

    ``kind`` is the event category; ``name`` carries a tool name for
    ``tool_use`` events (``None`` otherwise); ``raw`` is the original
    parsed JSON object so callers can inspect extra fields when needed.
    """

    kind: AdapterEventKind
    name: str | None = None
    raw: dict | None = None


@runtime_checkable
class CLIAdapter(Protocol):
    """Protocol every CLI adapter must satisfy.

    Adapters are stateless singletons: the same instance is reused for
    every iteration of every run.  Any per-iteration state lives in the
    caller (``_agent.py``) — adapters only translate.
    """

    name: str
    counts_what: CountsWhat
    supports_streaming: bool
    renders_structured_peek: bool
    supports_soft_wind_down: bool

    def matches(self, cmd: list[str]) -> bool:
        """Return True if this adapter handles the given agent command."""
        ...

    def build_command(self, cmd: list[str]) -> list[str]:
        """Return the command with any adapter-required flags appended.

        Idempotent: calling twice returns the same command.
        """
        ...

    def parse_event(self, line: str) -> AdapterEvent | None:
        """Parse one line of stdout into an :class:`AdapterEvent`.

        Returns ``None`` for lines that are not recognised events.
        MUST NOT raise on malformed input (per FR-8).
        """
        ...

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Return True if the agent's final output contains the completion signal.

        The signal is wrapped in ``<promise>...</promise>`` markup; the
        inner text equals ``user_signal``.
        """
        ...

    def install_wind_down_hook(
        self,
        tempdir: Path,
        counter_path: Path,
        cap: int,
        grace: int,
    ) -> dict[str, str]:
        """Write hook config files into *tempdir* and return env-var overrides.

        Only called when ``supports_soft_wind_down`` is True.  Adapters that
        set the flag False may leave this unimplemented (a ``NotImplementedError``
        is acceptable and is treated as a runtime downgrade to hard-cap-only).
        """
        ...


ADAPTERS: list[CLIAdapter] = []
"""Adapter registry, populated at import time by concrete adapter modules.

Ordering matters: :func:`select_adapter` returns the first adapter whose
``matches`` method returns True, with :class:`GenericAdapter` as a final
catch-all.  Specific adapters go first, generic last.
"""


def select_adapter(cmd: list[str]) -> CLIAdapter:
    """Return the first registered adapter that claims *cmd*.

    Falls back to :class:`GenericAdapter` when nothing matches.  Never
    returns None — callers can always dispatch safely.
    """
    from ralphify.adapters._generic import GenericAdapter

    for adapter in ADAPTERS:
        if adapter.matches(cmd):
            return adapter
    return GenericAdapter()


def _register_builtin_adapters() -> None:
    """Import concrete adapter modules so their ``ADAPTERS.append`` runs.

    Keeps the registry populated without forcing callers to import every
    adapter module manually.  Imports are deferred to the bottom of this
    module (executed once at first package import) so cyclic-import risk
    is contained.
    """
    from ralphify.adapters import claude, codex, copilot  # noqa: F401


_register_builtin_adapters()


__all__ = [
    "ADAPTERS",
    "AdapterEvent",
    "AdapterEventKind",
    "CLIAdapter",
    "CountsWhat",
    "select_adapter",
]
