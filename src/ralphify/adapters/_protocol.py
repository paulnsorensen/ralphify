"""Adapter Protocol and registry — the dependency-free core of the layer.

Concrete adapter modules (:mod:`claude`, :mod:`codex`, :mod:`copilot`,
:mod:`_generic`) import from here, not from the package ``__init__``.
That prevents the circular-import risk a package-level Protocol would
create: the ``__init__`` imports concrete adapters to populate
:data:`ADAPTERS`, and those adapters need the Protocol *before* the
package ``__init__`` finishes executing.  Splitting the Protocol into a
leaf module keeps the import graph acyclic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, NamedTuple, Protocol, runtime_checkable


AdapterEventKind = Literal["tool_use", "turn", "message", "result"]
"""Categories of events an adapter can surface from a CLI's output stream.

Adapters return ``None`` from :meth:`CLIAdapter.parse_event` for lines
they cannot classify — ``"message"`` is reserved for lines the adapter
*did* classify as agent chatter but does not want counted (e.g. Codex
turn boundaries).  The distinction matters because emitters may render
``"message"`` events in the peek panel while always ignoring ``None``.
"""

CountsWhat = Literal["tool_use", "none"]
"""What an adapter counts against ``max_turns`` — tool uses, or nothing."""


class AdapterEvent(NamedTuple):
    """A single structured event parsed from a CLI's output stream.

    ``kind`` is the event category; ``name`` carries a tool name for
    ``tool_use`` events (``None`` otherwise); ``text`` carries the final
    assistant message for ``result`` events (``None`` otherwise); ``raw``
    is the original parsed JSON object so callers can inspect extra
    fields when needed.
    """

    kind: AdapterEventKind
    name: str | None = None
    text: str | None = None
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
    renders_structured: bool
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

Ordering matters: :func:`ralphify.adapters.select_adapter` returns the
first adapter whose ``matches`` method returns True, with
:class:`ralphify.adapters._generic.GenericAdapter` as a final catch-all.
Specific adapters go first, generic last.
"""
