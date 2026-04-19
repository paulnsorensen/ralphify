"""Fallback adapter for CLIs with no dedicated implementation.

Returned by :func:`ralphify.adapters.select_adapter` when no specific
adapter's ``matches`` returns True.  All capability flags are False, so
the core loop treats sessions as blocking, untyped, and uncappable.
"""

from __future__ import annotations

from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters import AdapterEvent, CountsWhat


class GenericAdapter:
    """No-op adapter: pass commands through unchanged, parse nothing."""

    name: str = "generic"
    counts_what: CountsWhat = "none"
    supports_streaming: bool = False
    renders_structured_peek: bool = False
    supports_soft_wind_down: bool = False

    def matches(self, cmd: list[str]) -> bool:
        return False

    def build_command(self, cmd: list[str]) -> list[str]:
        return list(cmd)

    def parse_event(self, line: str) -> AdapterEvent | None:
        return None

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Scan the full stdout for the promise tag.

        Unknown CLIs have no event schema to parse, so the whole-stdout
        regex scan is the only reliable path.  Matches the current
        engine-side behavior so switching to adapter-owned detection does
        not regress promise completion for untyped agents.
        """
        return has_promise_completion(stdout, user_signal)

    def install_wind_down_hook(
        self,
        tempdir: Path,
        counter_path: Path,
        cap: int,
        grace: int,
    ) -> dict[str, str]:
        raise NotImplementedError(
            "GenericAdapter does not support soft wind-down; max_turns will hard-kill."
        )
