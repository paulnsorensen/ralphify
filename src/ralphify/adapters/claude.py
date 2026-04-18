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
import sys
from pathlib import Path

from ralphify._promise import has_promise_completion
from ralphify.adapters._protocol import ADAPTERS, AdapterEvent, CountsWhat


CLAUDE_BINARY_STEM = "claude"
"""Binary stem (``Path(cmd[0]).stem``) that identifies the Claude CLI."""

_STREAM_FLAGS: tuple[str, ...] = ("--output-format", "stream-json", "--verbose")
"""Flags appended to the Claude command to request structured streaming."""

_EVENT_TYPE_ASSISTANT = "assistant"
_EVENT_TYPE_RESULT = "result"
_BLOCK_TYPE_TOOL_USE = "tool_use"
_RESULT_FIELD = "result"

_SETTINGS_FILENAME = "settings.json"
"""File Claude reads for hook configuration when ``CLAUDE_CONFIG_DIR`` is set."""

_HOOK_EVENT = "PreToolUse"
"""Claude hook stage that fires before each tool invocation."""

_HOOK_MATCHER = "*"
"""Wildcard matcher — wind-down should fire regardless of which tool is about to run."""

_AGENT_KIND = "claude"
"""Argument passed to the wind-down shim so it picks the Claude payload shape."""


class ClaudeAdapter:
    """Parses Claude's stream-json output and supports soft wind-down."""

    name: str = "claude"
    counts_what: CountsWhat = "tool_use"
    renders_structured: bool = True
    supports_soft_wind_down: bool = True

    def matches(self, cmd: list[str]) -> bool:
        if not cmd:
            return False
        return Path(cmd[0]).stem == CLAUDE_BINARY_STEM

    def build_command(self, cmd: list[str]) -> list[str]:
        """Append stream-json flags, replacing any conflicting user values.

        Strips any existing ``--output-format <value>`` pair and bare
        ``--verbose`` token before appending the canonical flag set, so
        ``claude --output-format text`` becomes
        ``claude --output-format stream-json --verbose`` rather than a
        double-flag command that relies on "last wins" parsing.
        Idempotent: running twice yields the same command.
        """
        result = _strip_flag_pair(cmd, "--output-format")
        result = [tok for tok in result if tok != "--verbose"]
        result.extend(_STREAM_FLAGS)
        return result

    def parse_event(self, line: str) -> AdapterEvent | None:
        """Return a ``tool_use`` event for each assistant-emitted tool call.

        Returns ``None`` for any line the adapter cannot classify: non-JSON,
        non-dict payloads, non-assistant/non-result event types (``system``,
        ``user``, ...), and assistant messages whose content has no
        tool_use block.  The engine treats ``None`` as "ignore completely"
        — no counting, no peek-panel render — so false classifications
        never inflate the turn cap.
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
            result_value = parsed.get(_RESULT_FIELD)
            text = result_value if isinstance(result_value, str) else None
            return AdapterEvent(kind="result", text=text, raw=parsed)
        if event_type != _EVENT_TYPE_ASSISTANT:
            return None

        # Under-count rather than over-count: if an assistant message
        # ever carries multiple tool_use blocks (rare — stream-json emits
        # one block per message today), the first block wins and the
        # rest are ignored.  Over-counting would inflate the turn cap
        # and break FR-3's "hard cap" invariant; under-counting is a
        # leniency the user can recover from by re-running.
        for block in _iter_content_blocks(parsed):
            if block.get("type") == _BLOCK_TYPE_TOOL_USE:
                name = block.get("name")
                return AdapterEvent(
                    kind="tool_use",
                    name=name if isinstance(name, str) else None,
                    raw=parsed,
                )
        return None

    def extract_completion_signal(self, stdout: str, user_signal: str) -> bool:
        """Return True when ``<promise>{signal}</promise>`` appears in output.

        Scans the raw stdout first — the promise tag is unambiguous markup
        and a full-stream scan catches it whether it lives in a ``result``
        event, an assistant text block, or a truncated stream where the
        event order shifted.  Falls back to scanning the final ``result``
        event's ``result`` field only when the stdout scan fails, so
        adapters that share an escape-hatched promise format don't drift.
        """
        if has_promise_completion(stdout, user_signal):
            return True
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
        """Write Claude's ``settings.json`` and return a ``CLAUDE_CONFIG_DIR`` override.

        The settings file registers a ``PreToolUse`` hook that invokes
        :mod:`ralphify._wind_down_shim` with the per-iteration counter
        path.  Spawning Claude with ``CLAUDE_CONFIG_DIR=<tempdir>``
        isolates the hook from the user's real ``~/.claude`` config so a
        crash leaves no global side effects.
        """
        settings_path = tempdir / _SETTINGS_FILENAME
        command = _build_shim_command(counter_path, cap, grace)
        settings_path.write_text(
            json.dumps(_build_settings_payload(command), indent=2),
            encoding="utf-8",
        )
        return {"CLAUDE_CONFIG_DIR": str(tempdir)}


def _iter_content_blocks(raw: dict) -> list[dict]:
    """Return the ``message.content`` list, filtered to dict blocks only."""
    message = raw.get("message")
    if not isinstance(message, dict):
        return []
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _build_shim_command(counter_path: Path, cap: int, grace: int) -> str:
    """Return the shell command string Claude's hook runner will execute.

    Uses ``sys.executable`` so the shim runs under the same Python that
    spawned ralphify — avoids relying on a system ``python`` on PATH.
    Args are space-joined; counter paths with spaces are not supported,
    matching Claude's hook command convention (no shell interpolation).
    """
    return (
        f"{sys.executable} -m ralphify._wind_down_shim "
        f"{counter_path} {cap} {grace} {_AGENT_KIND}"
    )


def _build_settings_payload(command: str) -> dict:
    """Return the JSON dict written to ``settings.json``.

    The shape matches Claude Code's hook reference: the top-level
    ``hooks`` mapping keys event names to a list of matcher groups, each
    of which carries an inner ``hooks`` list of ``{type, command}``
    entries.
    """
    return {
        "hooks": {
            _HOOK_EVENT: [
                {
                    "matcher": _HOOK_MATCHER,
                    "hooks": [
                        {"type": "command", "command": command},
                    ],
                }
            ]
        }
    }


def _strip_flag_pair(cmd: list[str], flag: str) -> list[str]:
    """Return *cmd* with every ``flag <value>`` pair removed.

    The token immediately following ``flag`` is treated as its value and
    dropped along with ``flag``.  Used to sanitise user commands before
    the adapter appends its own canonical flag set.
    """
    result: list[str] = []
    skip_next = False
    for token in cmd:
        if skip_next:
            skip_next = False
            continue
        if token == flag:
            skip_next = True
            continue
        result.append(token)
    return result


ADAPTERS.append(ClaudeAdapter())
