"""Codex CLI adapter.

Codex emits newline-delimited JSON with explicit event types:

- ``TurnStarted`` / ``TurnCompleted`` — conversation turn boundaries.
- ``CollabToolCall`` / ``McpToolCall`` — tool invocations initiated by
  the agent.
- ``CommandExecution`` — shell commands run inside the sandbox.

We map every tool-call event to ``AdapterEvent(kind="tool_use", ...)``
so the turn-cap counter uses the same user-facing metric across CLIs.
Turn boundaries surface as ``kind="turn"`` events for adapters that want
them; they do not count against ``max_turns`` today (counts_what is
``tool_use`` for a unified metric — see spec Q13).

Event classification priority: ``TurnCompleted`` is a member of both
``_TURN_EVENTS`` and ``_RESULT_EVENTS``; the result branch fires first so
the terminal turn yields the final-assistant text the engine needs for
completion-signal extraction.  Treating it as a plain turn boundary
would drop that payload.
"""

from __future__ import annotations

import json
from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters._protocol import ADAPTERS, AdapterEvent, CountsWhat


CODEX_BINARY_STEM = "codex"
"""Binary stem (``Path(cmd[0]).stem``) that identifies the Codex CLI."""

_JSON_FLAG = "--json"
"""Flag appended to request newline-delimited JSON output."""

_TURN_EVENTS: frozenset[str] = frozenset({"TurnStarted", "TurnCompleted"})
_TOOL_CALL_EVENTS: frozenset[str] = frozenset(
    {"CollabToolCall", "McpToolCall", "CommandExecution"}
)
_RESULT_EVENTS: frozenset[str] = frozenset({"TaskComplete", "TurnCompleted"})


class CodexAdapter:
    """Parses Codex's ``--json`` event stream."""

    name: str = "codex"
    counts_what: CountsWhat = "tool_use"
    renders_structured: bool = True
    # Phase 3 will flip this to True once ``install_wind_down_hook``
    # actually writes a ``hooks.json`` PostToolUse entry.  Until then
    # the flag stays False so the engine downgrades to hard-cap-only.
    supports_soft_wind_down: bool = False

    def matches(self, cmd: list[str]) -> bool:
        if not cmd:
            return False
        return Path(cmd[0]).stem == CODEX_BINARY_STEM

    def build_command(self, cmd: list[str]) -> list[str]:
        """Append ``--json`` to request structured output.  Idempotent."""
        result = list(cmd)
        if _JSON_FLAG not in result:
            result.append(_JSON_FLAG)
        return result

    def parse_event(self, line: str) -> AdapterEvent | None:
        """Classify one JSONL line as tool_use / result / turn.

        Returns ``None`` for malformed lines, non-dict payloads, and
        unknown event types — the engine treats ``None`` as "ignore
        completely" so unclassified Codex events never count against
        the turn cap.  ``TurnCompleted`` hits the result branch before
        the turn branch (see module docstring) to preserve the final
        payload for completion-signal extraction.
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

        event_type = _event_type(parsed)
        if event_type in _TOOL_CALL_EVENTS:
            return AdapterEvent(
                kind="tool_use",
                name=_tool_name(parsed, event_type),
                raw=parsed,
            )
        if event_type in _RESULT_EVENTS:
            return AdapterEvent(
                kind="result",
                text=_event_text_payload(parsed),
                raw=parsed,
            )
        if event_type in _TURN_EVENTS:
            return AdapterEvent(kind="turn", raw=parsed)
        return None

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Scan every ``TurnCompleted`` / ``TaskComplete`` event for the promise tag.

        Codex does not carry a single terminal ``result`` string the way
        Claude does; completion may be spread across assistant text in
        multiple events.  Falling back to a whole-stdout scan is safe
        because promise tags are explicit and non-ambiguous markup.
        """
        if has_promise_completion(stdout, user_signal):
            return True
        for line in stdout.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and _event_type(parsed) in _RESULT_EVENTS:
                text = _event_text_payload(parsed)
                if text and has_promise_completion(text, user_signal):
                    return True
        return False

    def install_wind_down_hook(
        self,
        tempdir: Path,
        counter_path: Path,
        cap: int,
        grace: int,
    ) -> dict[str, str]:
        raise NotImplementedError(
            "Codex soft wind-down (hooks.json PostToolUse) is scheduled "
            "for Phase 3 of the CLI adapter layer spec."
        )


def _event_type(parsed: dict) -> str | None:
    """Return the Codex event type, whether top-level or nested under ``type``."""
    event_type = parsed.get("type") or parsed.get("kind")
    if isinstance(event_type, str):
        return event_type
    msg = parsed.get("msg")
    if isinstance(msg, dict):
        nested = msg.get("type") or msg.get("kind")
        if isinstance(nested, str):
            return nested
    return None


def _tool_name(parsed: dict, event_type: str | None) -> str | None:
    """Best-effort extraction of the tool name from a tool-call event.

    Codex event shapes vary by tool type — ``CommandExecution`` carries a
    command, ``CollabToolCall`` a tool name, ``McpToolCall`` a server +
    tool.  When no specific name is available, return the event type.
    """
    for key in ("name", "tool", "tool_name", "command"):
        value = parsed.get(key)
        if isinstance(value, str):
            return value
    msg = parsed.get("msg")
    if isinstance(msg, dict):
        for key in ("name", "tool", "tool_name", "command"):
            value = msg.get(key)
            if isinstance(value, str):
                return value
    return event_type


def _event_text_payload(parsed: dict) -> str | None:
    """Extract any final-assistant text from a Codex result event."""
    for key in ("result", "text", "content", "output"):
        value = parsed.get(key)
        if isinstance(value, str):
            return value
    msg = parsed.get("msg")
    if isinstance(msg, dict):
        for key in ("result", "text", "content", "output"):
            value = msg.get(key)
            if isinstance(value, str):
                return value
    return None


ADAPTERS.append(CodexAdapter())
