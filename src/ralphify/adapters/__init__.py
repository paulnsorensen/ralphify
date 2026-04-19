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


class CacheStats(NamedTuple):
    """Prompt-cache token accounting for a single model call.

    Counts are input-side tokens only (caching does not apply to output):

    - ``read_tokens``    — input served from cache (the cheap tokens).
    - ``write_tokens``   — input newly written to cache this call.  Claude
      reports this as ``cache_creation_input_tokens``; APIs that do not
      distinguish creation from a regular miss (e.g. OpenAI Responses)
      report ``0`` here.
    - ``uncached_tokens`` — input that bypassed cache entirely.

    Total prompt tokens are ``read + write + uncached``.  A ratio of
    ``read_tokens / (read + write + uncached)`` gives the effective cache
    hit rate for that call.  Adapters return ``None`` from
    :meth:`CLIAdapter.extract_cache_stats` when an event carries no usage
    payload, so callers can distinguish "no data" from "zero cache hits".
    """

    read_tokens: int
    write_tokens: int
    uncached_tokens: int


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
    requires_full_stdout_for_completion: bool
    supports_prompt_caching: bool

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

    def extract_completion_signal(
        self,
        *,
        result_text: str | None,
        stdout: str | None,
        user_signal: str,
    ) -> bool:
        """Return True if the agent's final output contains the completion signal.

        The signal is wrapped in ``<promise>...</promise>`` markup; the
        inner text equals ``user_signal``.

        Adapters receive both the streaming-extracted *result_text* (the
        terminal assistant message, when the streaming path could parse one)
        and the full *stdout* buffer (only present when the engine chose to
        capture it).  Adapters with ``requires_full_stdout_for_completion``
        set False MUST be able to detect completion from *result_text* alone;
        engines may pass ``stdout=None`` to skip the memory cost.
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

    def extract_cache_stats(self, raw: dict) -> CacheStats | None:
        """Return prompt-cache token accounting for a single parsed event.

        Called once per :class:`AdapterEvent` the caller wants stats for —
        typically the terminal ``result`` event, but adapters that emit
        per-turn usage may surface stats on every turn boundary too.
        Returns ``None`` when *raw* has no usage payload (not every event
        carries one).

        Adapters with ``supports_prompt_caching`` set False MAY always
        return ``None``; the flag signals "this CLI has no observable
        caching story", whereas ``None`` from a capable adapter just means
        "this particular event had no usage data".
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
    "CacheStats",
    "CountsWhat",
    "select_adapter",
]
