"""Tests for the Codex CLI adapter."""

from __future__ import annotations

import json

import pytest

from ralphify.adapters import select_adapter
from ralphify.adapters.codex import CodexAdapter


def test_matches_codex_binary_stem() -> None:
    adapter = CodexAdapter()
    assert adapter.matches(["codex"]) is True
    assert adapter.matches(["/usr/local/bin/codex"]) is True
    assert adapter.matches(["codex", "exec", "--sandbox"]) is True
    assert adapter.matches(["claude"]) is False
    assert adapter.matches([]) is False


def test_build_command_appends_json_flag() -> None:
    adapter = CodexAdapter()
    assert adapter.build_command(["codex"]) == ["codex", "--json"]


def test_build_command_is_idempotent() -> None:
    adapter = CodexAdapter()
    once = adapter.build_command(["codex"])
    twice = adapter.build_command(once)
    assert once == twice


def test_parse_tool_call_events() -> None:
    adapter = CodexAdapter()
    for event_type, expected_name in [
        ("CollabToolCall", "Edit"),
        ("McpToolCall", "Edit"),
        ("CommandExecution", "Edit"),
    ]:
        line = json.dumps({"type": event_type, "name": "Edit"})
        event = adapter.parse_event(line)
        assert event is not None
        assert event.kind == "tool_use"
        assert event.name == expected_name


def test_parse_turn_events() -> None:
    adapter = CodexAdapter()
    for event_type in ("TurnStarted", "TurnCompleted"):
        # TurnCompleted is a result *and* turn event; result wins.
        line = json.dumps({"type": event_type})
        event = adapter.parse_event(line)
        assert event is not None
        if event_type == "TurnCompleted":
            assert event.kind == "result"
        else:
            assert event.kind == "turn"


def test_parse_unknown_events_become_message() -> None:
    adapter = CodexAdapter()
    event = adapter.parse_event(json.dumps({"type": "SomethingNew"}))
    assert event is not None
    assert event.kind == "message"


def test_parse_malformed_returns_none() -> None:
    adapter = CodexAdapter()
    assert adapter.parse_event("not json") is None
    assert adapter.parse_event("") is None
    assert adapter.parse_event("42") is None


def test_parse_tool_call_nested_under_msg() -> None:
    """Some Codex builds wrap event data under a ``msg`` key."""
    adapter = CodexAdapter()
    line = json.dumps({"msg": {"type": "CommandExecution", "command": "git status"}})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "tool_use"
    assert event.name == "git status"


def test_parse_falls_back_to_event_type_for_name() -> None:
    adapter = CodexAdapter()
    line = json.dumps({"type": "CollabToolCall"})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.name == "CollabToolCall"


def test_extract_completion_signal_from_stream() -> None:
    adapter = CodexAdapter()
    stream = "\n".join(
        [
            json.dumps({"type": "TurnStarted"}),
            json.dumps({"type": "CommandExecution", "command": "ls"}),
            json.dumps({"type": "TaskComplete", "text": "<promise>DONE</promise>"}),
        ]
    )
    assert (
        adapter.extract_completion_signal(
            result_text=None, stdout=stream, user_signal="DONE"
        )
        is True
    )
    assert (
        adapter.extract_completion_signal(
            result_text=None, stdout=stream, user_signal="OTHER"
        )
        is False
    )


def test_extract_completion_signal_scans_plain_output() -> None:
    adapter = CodexAdapter()
    assert (
        adapter.extract_completion_signal(
            result_text=None,
            stdout="some <promise>HI</promise> text",
            user_signal="HI",
        )
        is True
    )


def test_extract_completion_signal_returns_false_when_stdout_missing() -> None:
    """When the engine elects not to capture stdout, Codex cannot detect
    completion — the streaming reader does not populate ``result_text``
    for Codex's ``TaskComplete`` event shape."""
    adapter = CodexAdapter()
    assert (
        adapter.extract_completion_signal(
            result_text=None, stdout=None, user_signal="DONE"
        )
        is False
    )


def test_install_wind_down_hook_raises_not_implemented(tmp_path) -> None:
    adapter = CodexAdapter()
    with pytest.raises(NotImplementedError):
        adapter.install_wind_down_hook(tmp_path, tmp_path / "counter", 10, 2)


def test_capability_flags() -> None:
    adapter = CodexAdapter()
    assert adapter.name == "codex"
    assert adapter.counts_what == "tool_use"
    assert adapter.supports_streaming is True
    assert adapter.renders_structured_peek is False
    assert adapter.supports_soft_wind_down is True
    assert adapter.requires_full_stdout_for_completion is True
    assert adapter.supports_prompt_caching is True


def test_extract_cache_stats_responses_api_shape() -> None:
    """Responses API emits input_tokens_details.cached_tokens."""
    adapter = CodexAdapter()
    raw = {
        "type": "TokenCount",
        "usage": {
            "input_tokens": 10_000,
            "output_tokens": 300,
            "input_tokens_details": {"cached_tokens": 7500},
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 7500
    assert stats.write_tokens == 0  # OpenAI does not split write vs miss
    assert stats.uncached_tokens == 2500


def test_extract_cache_stats_legacy_chat_shape() -> None:
    """Older Codex builds emit prompt_tokens + prompt_tokens_details."""
    adapter = CodexAdapter()
    raw = {
        "usage": {
            "prompt_tokens": 1000,
            "prompt_tokens_details": {"cached_tokens": 400},
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 400
    assert stats.uncached_tokens == 600


def test_extract_cache_stats_usage_nested_under_msg() -> None:
    """Some Codex events wrap usage under ``msg.usage``."""
    adapter = CodexAdapter()
    raw = {
        "type": "TurnCompleted",
        "msg": {
            "usage": {
                "input_tokens": 500,
                "input_tokens_details": {"cached_tokens": 500},
            },
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 500
    assert stats.uncached_tokens == 0


def test_extract_cache_stats_returns_none_when_no_usage() -> None:
    adapter = CodexAdapter()
    assert adapter.extract_cache_stats({"type": "TurnStarted"}) is None
    assert (
        adapter.extract_cache_stats({"type": "CommandExecution", "command": "ls"})
        is None
    )


def test_extract_cache_stats_returns_none_on_empty_usage() -> None:
    adapter = CodexAdapter()
    assert adapter.extract_cache_stats({"usage": {}}) is None
    assert adapter.extract_cache_stats({"usage": {"input_tokens": 0}}) is None


def test_extract_cache_stats_clamps_negative_uncached_to_zero() -> None:
    """If cached_tokens exceeds input_tokens (shouldn't happen but defensive)."""
    adapter = CodexAdapter()
    raw = {
        "usage": {
            "input_tokens": 100,
            "input_tokens_details": {"cached_tokens": 500},
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.uncached_tokens == 0


def test_extract_cache_stats_defensive_on_malformed_shapes() -> None:
    adapter = CodexAdapter()
    assert adapter.extract_cache_stats({"usage": "not a dict"}) is None
    assert adapter.extract_cache_stats({"msg": "not a dict"}) is None
    assert (
        adapter.extract_cache_stats({"usage": {"input_tokens_details": "not dict"}})
        is None
    )


def test_registered_in_adapters_registry() -> None:
    selected = select_adapter(["codex"])
    assert isinstance(selected, CodexAdapter)
