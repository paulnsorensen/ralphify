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
``tool_use``, not ``turn``, for a unified metric — see spec Q13).
"""

from __future__ import annotations

import json
from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters import ADAPTERS, AdapterEvent, CacheStats, CountsWhat


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
    supports_streaming: bool = True
    # Codex emits structured JSON that the streaming execution path parses
    # for activity callbacks, but the console peek panel only understands
    # Claude's stream-json schema today. Keep peek in raw-line mode until
    # the emitter can render Codex events directly.
    renders_structured_peek: bool = False
    supports_soft_wind_down: bool = True
    # Codex's terminal text lives inside ``TaskComplete`` / ``TurnCompleted``
    # events, which the streaming reader does not extract into
    # ``agent.result_text``.  The full stdout buffer is currently the only
    # source for promise-tag scanning.
    requires_full_stdout_for_completion: bool = True
    # OpenAI's Responses API caches automatically; usage events carry a
    # ``cached_tokens`` field under ``input_tokens_details`` (Responses) or
    # ``prompt_tokens_details`` (older Chat shape).  We surface the count
    # as :class:`CacheStats`, with ``write_tokens=0`` because OpenAI does
    # not distinguish a cache write from a regular miss.  Caching is
    # fragile — routing stickiness across fresh ``codex exec`` invocations
    # is not guaranteed — but when hits occur, this is where we see them.
    supports_prompt_caching: bool = True

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
        """Classify one JSONL line as turn / tool_use / message / result.

        Unknown event types return ``AdapterEvent(kind="message", ...)`` so
        callers can still render them (e.g. peek panel) without counting
        them against the turn cap.  Malformed lines return ``None``.
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
            return AdapterEvent(kind="result", raw=parsed)
        if event_type in _TURN_EVENTS:
            return AdapterEvent(kind="turn", raw=parsed)
        return AdapterEvent(kind="message", raw=parsed)

    def extract_completion_signal(
        self,
        *,
        result_text: str | None,
        stdout: str | None,
        user_signal: str,
    ) -> bool:
        """Scan every ``TurnCompleted`` / ``TaskComplete`` event for the promise tag.

        Codex does not carry a single terminal ``result`` string the way
        Claude does; completion may be spread across assistant text in
        multiple events.  Falling back to a whole-stdout scan is safe
        because promise tags are explicit and non-ambiguous markup.

        *result_text* is unused — Codex never populates it through the
        streaming reader (no ``{"type":"result"}`` lines).  The engine
        opts into ``requires_full_stdout_for_completion`` to make sure
        *stdout* is supplied when promise detection is requested.
        """
        del result_text
        if stdout is None:
            return False
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

    def extract_cache_stats(self, raw: dict) -> CacheStats | None:
        """Extract :class:`CacheStats` from a Codex event's usage payload.

        Codex emits usage data either on a dedicated ``TokenCount`` event or
        nested inside a ``TurnCompleted`` event; both shapes surface the
        same ``usage`` dict.  We check ``usage.input_tokens_details.cached_tokens``
        first (the Responses API shape) and fall through to the older
        ``prompt_tokens_details.cached_tokens`` layout, mirroring what the
        Codex CLI has emitted across its 2025–2026 builds.

        OpenAI does not distinguish a cache write from a regular miss, so
        ``write_tokens`` is always ``0`` for this adapter — the total
        prompt cost splits cleanly between cached and uncached input.
        Returns ``None`` when no usage dict is present.
        """
        usage = _extract_usage_dict(raw)
        if usage is None:
            return None
        prompt_tokens = _int_or_zero(
            usage.get("input_tokens") or usage.get("prompt_tokens")
        )
        cached = _int_or_zero(_nested_cached_tokens(usage))
        if prompt_tokens == 0 and cached == 0:
            return None
        uncached = max(prompt_tokens - cached, 0)
        return CacheStats(read_tokens=cached, write_tokens=0, uncached_tokens=uncached)


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
    for key in ("name", "tool", "tool_name"):
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


def _extract_usage_dict(raw: dict) -> dict | None:
    """Return the ``usage`` dict from either top-level or nested ``msg.usage``."""
    usage = raw.get("usage")
    if isinstance(usage, dict):
        return usage
    msg = raw.get("msg")
    if isinstance(msg, dict):
        nested = msg.get("usage")
        if isinstance(nested, dict):
            return nested
    return None


def _nested_cached_tokens(usage: dict) -> object:
    """Return the cached-tokens value from either Responses or Chat usage shapes."""
    for container_key in ("input_tokens_details", "prompt_tokens_details"):
        container = usage.get(container_key)
        if isinstance(container, dict):
            cached = container.get("cached_tokens")
            if cached is not None:
                return cached
    return usage.get("cached_tokens")


def _int_or_zero(value: object) -> int:
    """Coerce a usage field to int; non-ints and booleans become zero."""
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


ADAPTERS.append(CodexAdapter())
