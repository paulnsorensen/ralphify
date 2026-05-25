"""Turn-cap enforcement and soft wind-down across adapters.

Covers the behaviours that distinguish how each adapter participates in
``max_turns``:

- Streaming adapters that count tool uses (claude / codex / opencode) are
  preempted at the cap.
- Adapters that count nothing (crush) treat ``max_turns`` as a no-op.
- Adapters with no hook system (copilot / crush / opencode / generic)
  downgrade soft wind-down to hard-cap-only via ``NotImplementedError``.
- The engine emits ``ITERATION_TURN_CAPPED`` and fans the signal to hooks.
"""

from __future__ import annotations

import io
from unittest.mock import patch

from helpers import drain_events, event_types, make_config, make_state

from ralphify._agent import (
    AgentResult,
    _count_tool_uses_post_hoc,
    _read_agent_stream,
    _setup_wind_down,
)
from ralphify._events import EventType, QueueEmitter
from ralphify.adapters import select_adapter
from ralphify.adapters.claude import ClaudeAdapter
from ralphify.adapters.codex import CodexAdapter
from ralphify.adapters.copilot import CopilotAdapter
from ralphify.adapters.crush import CrushAdapter
from ralphify.adapters.opencode import OpenCodeAdapter
from ralphify.engine import run_loop
from ralphify.hooks import NoOpAgentHook


class _RecordingHook(NoOpAgentHook):
    """Hook that records the turn-cap callbacks it receives."""

    def __init__(self) -> None:
        self.capped: list[int] = []
        self.tool_uses: list[tuple[str, int]] = []

    def on_turn_capped(self, *, iteration: int, count: int) -> None:
        self.capped.append(count)

    def on_tool_use(self, *, iteration: int, tool_name: str, count: int) -> None:
        self.tool_uses.append((tool_name, count))


# ── opencode: counts_what == "tool_use" feeds the cap ──────────────────


def test_opencode_tool_use_events_count_toward_cap() -> None:
    """opencode tool_use events are counted and preempt at the cap."""
    adapter = OpenCodeAdapter()
    stream = io.StringIO(
        '{"type":"tool_use","name":"read"}\n'
        '{"type":"text","part":{"text":"thinking"}}\n'
        '{"type":"tool_use","name":"edit"}\n'
        '{"type":"tool_use","name":"bash"}\n'
    )
    seen: list[tuple[str, int]] = []

    result = _read_agent_stream(
        stream,
        deadline=None,
        on_activity=None,
        adapter=adapter,
        max_turns=2,
        on_tool_use=lambda name, count: seen.append((name, count)),
    )

    # The third tool_use is never reached: the cap fires at 2.
    assert result.turn_capped is True
    assert result.tool_use_count == 2
    assert seen == [("read", 1), ("edit", 2)]


def test_opencode_counts_without_cap_do_not_trip() -> None:
    """With no cap, opencode counts every tool use and never caps."""
    adapter = OpenCodeAdapter()
    stream = io.StringIO(
        '{"type":"tool_use","name":"read"}\n'
        '{"type":"tool_use","name":"edit"}\n'
        '{"type":"tool_use","name":"bash"}\n'
    )

    result = _read_agent_stream(
        stream, deadline=None, on_activity=None, adapter=adapter, max_turns=None
    )

    assert result.turn_capped is False
    assert result.tool_use_count == 3


# ── crush: counts_what == "none" makes max_turns a no-op ───────────────


def test_crush_max_turns_is_graceful_noop() -> None:
    """crush emits no countable events, so the cap can never fire."""
    adapter = CrushAdapter()
    stdout_lines = [
        "Did some work.\n",
        "<promise>COMPLETE</promise>\n",
    ]

    count, capped = _count_tool_uses_post_hoc(
        adapter=adapter,
        stdout_lines=stdout_lines,
        max_turns=1,
        on_tool_use=lambda name, c: None,
    )

    assert count == 0
    assert capped is False


# ── soft wind-down downgrade to hard-cap-only ──────────────────────────


def test_wind_down_downgrades_for_adapters_without_hooks(tmp_path) -> None:
    """copilot / crush / opencode / generic have no hook system → no setup."""
    for adapter in (
        CopilotAdapter(),
        CrushAdapter(),
        OpenCodeAdapter(),
        select_adapter(["echo"]),  # GenericAdapter fallback
    ):
        ctx = _setup_wind_down(
            adapter=adapter,
            max_turns=5,
            max_turns_grace=2,
            log_dir=None,
            iteration=1,
        )
        assert ctx is None, f"{adapter.name} should not set up wind-down"


def test_wind_down_setup_for_supporting_adapters() -> None:
    """claude / codex write hook config and return an env override."""
    for adapter in (ClaudeAdapter(), CodexAdapter()):
        ctx = _setup_wind_down(
            adapter=adapter,
            max_turns=5,
            max_turns_grace=2,
            log_dir=None,
            iteration=1,
        )
        assert ctx is not None, f"{adapter.name} should set up wind-down"
        try:
            assert ctx.counter_path.read_text(encoding="utf-8") == "0"
            assert ctx.env_overrides  # non-empty config-dir override
        finally:
            ctx.cleanup()
        assert not ctx.tempdir.exists()


def test_wind_down_skipped_when_grace_zero() -> None:
    """Grace of 0 opts out of the warning window even for claude."""
    ctx = _setup_wind_down(
        adapter=ClaudeAdapter(),
        max_turns=5,
        max_turns_grace=0,
        log_dir=None,
        iteration=1,
    )
    assert ctx is None


# ── engine surfaces the cap as an event + hook callback ────────────────


def test_engine_emits_turn_capped_event_and_fans_to_hook(tmp_path) -> None:
    """A capped iteration emits ITERATION_TURN_CAPPED and notifies the hook."""
    hook = _RecordingHook()
    config = make_config(tmp_path, max_turns=3, max_iterations=1, hooks=[hook])
    state = make_state()
    emitter = QueueEmitter()

    with patch("ralphify.engine.execute_agent") as mock_execute:
        mock_execute.return_value = AgentResult(
            returncode=0,
            elapsed=0.01,
            tool_use_count=3,
            turn_capped=True,
        )
        run_loop(config, state, emitter)

    types = event_types(drain_events(emitter))
    assert EventType.ITERATION_TURN_CAPPED in types
    assert hook.capped == [3]
    # A capped iteration counts as completed, not failed.
    assert state.completed == 1
    assert state.failed == 0
