"""GitHub Copilot CLI adapter (alpha).

The standalone ``copilot`` binary (GA 2026-02-25) ships a
``--output-format json`` mode that is **only loosely documented**.  This
adapter does best-effort counting based on the empirical shapes seen in
the ralphify test corpus; unknown event types return ``None`` rather
than crashing.

Capability matrix:

- ``counts_what = "tool_use"`` with an alpha caveat — counting accuracy
  depends on ongoing schema discovery (see :file:`docs/agents.md`).
- ``renders_structured = False`` — peek panel stays in raw-line mode.
- ``supports_soft_wind_down = False`` — Copilot has no hook system as of
  2026-04, so ``install_wind_down_hook`` raises :class:`NotImplementedError`
  (which the engine downgrades to hard-cap-only).
"""

from __future__ import annotations

import json
from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters._protocol import ADAPTERS, AdapterEvent, CountsWhat


COPILOT_BINARY_STEM = "copilot"
"""Binary stem (``Path(cmd[0]).stem``) that identifies the standalone Copilot CLI.

Note: this is the GA ``copilot`` binary, NOT the ``gh copilot`` subcommand.
The ``gh`` stem is deliberately excluded because ``gh`` hosts many other
subcommands that have nothing to do with AI agents.
"""

_OUTPUT_FORMAT_FLAGS: tuple[str, ...] = ("--output-format", "json")

_TOOL_USE_EVENT_TYPES: frozenset[str] = frozenset(
    {"tool_use", "tool_call", "ToolCall", "ToolUse"}
)
_RESULT_EVENT_TYPES: frozenset[str] = frozenset(
    {"result", "response", "final", "Final", "Complete"}
)


class CopilotAdapter:
    """Best-effort adapter for the standalone Copilot CLI."""

    name: str = "copilot"
    counts_what: CountsWhat = "tool_use"
    renders_structured: bool = False
    supports_soft_wind_down: bool = False

    def matches(self, cmd: list[str]) -> bool:
        if not cmd:
            return False
        return Path(cmd[0]).stem == COPILOT_BINARY_STEM

    def build_command(self, cmd: list[str]) -> list[str]:
        """Append ``--output-format json``, replacing any conflicting value.

        Strips any existing ``--output-format <value>`` pair before
        appending the canonical JSON form, so
        ``copilot --output-format markdown`` becomes
        ``copilot --output-format json`` rather than a double-flag
        command that relies on last-wins parsing.  Idempotent.
        """
        result: list[str] = []
        skip_next = False
        for token in cmd:
            if skip_next:
                skip_next = False
                continue
            if token == "--output-format":
                skip_next = True
                continue
            result.append(token)
        result.extend(_OUTPUT_FORMAT_FLAGS)
        return result

    def parse_event(self, line: str) -> AdapterEvent | None:
        """Parse best-effort; return ``None`` for unknown shapes.

        The Copilot event schema is ``[unverified]`` in the spec — this
        method intentionally errs on the side of *not* inventing events
        so the turn cap is never inflated by false positives.  Only the
        canonical ``type`` key is accepted; ``event`` / ``kind`` are not
        recognised because they have not been seen in captured output
        and admitting them inflates the schema's surface area.
        """
        stripped = line.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None

        event_type = parsed.get("type")
        if not isinstance(event_type, str):
            return None

        if event_type in _TOOL_USE_EVENT_TYPES:
            name = parsed.get("name") or parsed.get("tool")
            return AdapterEvent(
                kind="tool_use",
                name=name if isinstance(name, str) else None,
                raw=parsed,
            )
        if event_type in _RESULT_EVENT_TYPES:
            text = None
            for key in ("result", "text", "content", "output", "message"):
                value = parsed.get(key)
                if isinstance(value, str):
                    text = value
                    break
            return AdapterEvent(kind="result", text=text, raw=parsed)
        return None

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Scan the entire stdout for the promise tag.

        Without a verified event schema there is no reliable per-event
        extraction path; the whole-stdout scan is the safest fallback.
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
            "Copilot CLI has no hook system as of 2026-04; max_turns "
            "will hard-kill without soft wind-down signal."
        )


ADAPTERS.append(CopilotAdapter())
