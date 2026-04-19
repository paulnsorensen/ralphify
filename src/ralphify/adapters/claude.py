"""Claude Code adapter.

Claude is the only CLI shipping a stable ``--output-format stream-json``
protocol today; its structured events drive the peek panel and power
per-event tool-use counting.  Every Claude iteration emits:

1. A ``system`` init event with the model name.
2. Zero or more ``assistant`` messages whose ``content`` list may include
   ``tool_use``, ``thinking``, and ``text`` blocks.
3. Zero or more ``user`` messages (tool results echoed back).
4. A terminal ``result`` event carrying the final assistant text.

Tool-use counting is scoped to ``assistant`` messages; we ignore
``tool_use`` blocks echoed back by ``user`` events so each invocation is
counted exactly once.
"""

from __future__ import annotations

import json
from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters import ADAPTERS, AdapterEvent, CountsWhat


CLAUDE_BINARY_STEM = "claude"
"""Binary stem (``Path(cmd[0]).stem``) that identifies the Claude CLI."""

_STREAM_FLAGS: tuple[str, ...] = ("--output-format", "stream-json", "--verbose")
"""Flags appended to the Claude command to request structured streaming."""

_EVENT_TYPE_ASSISTANT = "assistant"
_EVENT_TYPE_RESULT = "result"
_BLOCK_TYPE_TOOL_USE = "tool_use"
_RESULT_FIELD = "result"


class ClaudeAdapter:
    """Parses Claude's stream-json output and supports soft wind-down."""

    name: str = "claude"
    counts_what: CountsWhat = "tool_use"
    renders_structured: bool = True
    supports_soft_windown: bool = True

    def matches(self, cmd: list[str]) -> bool:
        if not cmd:
            return False
        return Path(cmd[0]).stem == CLAUDE_BINARY_STEM

    def build_command(self, cmd: list[str]) -> list[str]:
        """Append stream-json flags, skipping any already present.

        Idempotent: running twice yields the same command.
        """
        result = list(cmd)
        for flag in _STREAM_FLAGS:
            if flag not in result:
                result.append(flag)
        return result

    def parse_event(self, line: str) -> AdapterEvent | None:
        """Return a ``tool_use`` event for each assistant-emitted tool call.

        Non-JSON lines, non-dict payloads, and events other than assistant
        tool-use blocks return ``None``.  Each ``assistant`` message may
        contain multiple tool_use blocks; callers receive the *first* one
        — Claude's stream-json format emits one block per newline-delimited
        message, so single-event dispatch matches the protocol.
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
        if event_type == _EVENT_TYPE_RESULT:
            return AdapterEvent(kind="result", raw=parsed)
        if event_type != _EVENT_TYPE_ASSISTANT:
            return AdapterEvent(kind="message", raw=parsed)

        for block in _iter_content_blocks(parsed):
            if block.get("type") == _BLOCK_TYPE_TOOL_USE:
                name = block.get("name")
                return AdapterEvent(
                    kind="tool_use",
                    name=name if isinstance(name, str) else None,
                    raw=parsed,
                )
        return AdapterEvent(kind="message", raw=parsed)

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Scan the final ``result`` event for ``<promise>{signal}</promise>``.

        Claude's terminal ``result`` event carries the last assistant
        message as a plain string; the promise tag may live anywhere in
        that text.  Only the ``result`` event is considered — raw JSON
        from ``status`` or ``assistant`` messages can legitimately echo
        ``<promise>...</promise>`` substrings that must not trigger
        completion.
        """
        for line in reversed(stdout.splitlines()):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(parsed, dict)
                and parsed.get("type") == _EVENT_TYPE_RESULT
                and isinstance(parsed.get(_RESULT_FIELD), str)
            ):
                return has_promise_completion(parsed[_RESULT_FIELD], user_signal)
        return False

    def install_wind_down_hook(
        self,
        tempdir: Path,
        counter_path: Path,
        cap: int,
        grace: int,
    ) -> dict[str, str]:
        raise NotImplementedError(
            "Claude soft wind-down (settings.json PreToolUse hook) is scheduled "
            "for Phase 3 of the CLI adapter layer spec."
        )


def _iter_content_blocks(raw: dict) -> list[dict]:
    """Return the ``message.content`` list, filtered to dict blocks only."""
    message = raw.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


ADAPTERS.append(ClaudeAdapter())
