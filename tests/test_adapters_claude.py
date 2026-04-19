"""Tests for the Claude stream-json adapter."""

from __future__ import annotations

import json

import pytest

from ralphify.adapters import select_adapter
from ralphify.adapters.claude import ClaudeAdapter


def _assistant_event(*blocks: dict) -> str:
    """Build one JSON line matching Claude's assistant message schema."""
    return json.dumps(
        {
            "type": "assistant",
            "message": {"content": list(blocks)},
        }
    )


def _result_event(result_text: str) -> str:
    return json.dumps({"type": "result", "result": result_text})


def test_matches_claude_binary_stem() -> None:
    adapter = ClaudeAdapter()
    assert adapter.matches(["claude"]) is True
    assert adapter.matches(["/usr/local/bin/claude"]) is True
    assert adapter.matches(["claude", "--print"]) is True
    assert adapter.matches(["codex"]) is False
    assert adapter.matches([]) is False


def test_build_command_appends_stream_flags() -> None:
    adapter = ClaudeAdapter()
    result = adapter.build_command(["claude"])
    assert result == ["claude", "--output-format", "stream-json", "--verbose"]


def test_build_command_is_idempotent() -> None:
    adapter = ClaudeAdapter()
    once = adapter.build_command(["claude"])
    twice = adapter.build_command(once)
    assert once == twice


def test_build_command_preserves_user_flags() -> None:
    adapter = ClaudeAdapter()
    result = adapter.build_command(["claude", "--print", "-p"])
    assert result[:3] == ["claude", "--print", "-p"]
    assert "--output-format" in result
    assert "stream-json" in result


def test_parse_tool_use_event() -> None:
    adapter = ClaudeAdapter()
    line = _assistant_event({"type": "tool_use", "name": "Bash", "input": {}})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "tool_use"
    assert event.name == "Bash"


def test_parse_result_event() -> None:
    adapter = ClaudeAdapter()
    event = adapter.parse_event(_result_event("done"))
    assert event is not None
    assert event.kind == "result"


def test_parse_ignores_thinking_blocks() -> None:
    adapter = ClaudeAdapter()
    line = _assistant_event({"type": "thinking", "thinking": "planning..."})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "message"


def test_parse_malformed_json_returns_none() -> None:
    adapter = ClaudeAdapter()
    assert adapter.parse_event("not json") is None
    assert adapter.parse_event("") is None
    assert adapter.parse_event("   \n") is None


def test_parse_non_dict_json_returns_none() -> None:
    adapter = ClaudeAdapter()
    assert adapter.parse_event("[1, 2, 3]") is None
    assert adapter.parse_event('"just a string"') is None


def test_parse_tool_use_with_non_string_name() -> None:
    """Defensive: tool_use blocks with missing name must not raise."""
    adapter = ClaudeAdapter()
    line = _assistant_event({"type": "tool_use", "input": {}})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "tool_use"
    assert event.name is None


def test_parse_skips_first_non_tool_use_block() -> None:
    adapter = ClaudeAdapter()
    line = _assistant_event(
        {"type": "text", "text": "thinking out loud"},
        {"type": "tool_use", "name": "Edit", "input": {}},
    )
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "tool_use"
    assert event.name == "Edit"


def test_extract_completion_signal_from_result_text() -> None:
    adapter = ClaudeAdapter()
    result_text = "<promise>DONE</promise>"
    assert (
        adapter.extract_completion_signal(
            result_text=result_text, stdout=None, user_signal="DONE"
        )
        is True
    )
    assert (
        adapter.extract_completion_signal(
            result_text=result_text, stdout=None, user_signal="OTHER"
        )
        is False
    )


def test_extract_completion_signal_ignores_raw_stdout() -> None:
    """ClaudeAdapter only inspects ``result_text``; the streaming reader
    extracts the terminal assistant message there.  Promise tags embedded
    in raw stdout (e.g. ``status`` or ``assistant`` JSON) must not trigger
    completion."""
    adapter = ClaudeAdapter()
    stdout = "raw text <promise>MARKER</promise> trailing"
    assert (
        adapter.extract_completion_signal(
            result_text=None, stdout=stdout, user_signal="MARKER"
        )
        is False
    )


def test_extract_completion_signal_handles_missing_result_text() -> None:
    adapter = ClaudeAdapter()
    assert (
        adapter.extract_completion_signal(
            result_text=None, stdout=None, user_signal="DONE"
        )
        is False
    )
    assert (
        adapter.extract_completion_signal(
            result_text="", stdout=None, user_signal="DONE"
        )
        is False
    )


def test_install_wind_down_hook_raises_not_implemented(tmp_path) -> None:
    adapter = ClaudeAdapter()
    with pytest.raises(NotImplementedError):
        adapter.install_wind_down_hook(tmp_path, tmp_path / "counter", 10, 2)


def test_capability_flags() -> None:
    adapter = ClaudeAdapter()
    assert adapter.name == "claude"
    assert adapter.counts_what == "tool_use"
    assert adapter.supports_streaming is True
    assert adapter.renders_structured_peek is True
    assert adapter.supports_soft_wind_down is True
    assert adapter.requires_full_stdout_for_completion is False
    assert adapter.supports_prompt_caching is True


def test_extract_cache_stats_from_assistant_usage() -> None:
    adapter = ClaudeAdapter()
    raw = {
        "type": "assistant",
        "message": {
            "content": [],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_creation_input_tokens": 2000,
                "cache_read_input_tokens": 8000,
            },
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 8000
    assert stats.write_tokens == 2000
    assert stats.uncached_tokens == 100


def test_extract_cache_stats_from_result_event_top_level_usage() -> None:
    """Claude's terminal result event carries usage at the top level."""
    adapter = ClaudeAdapter()
    raw = {
        "type": "result",
        "result": "done",
        "usage": {
            "input_tokens": 5,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 12345,
        },
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 12345
    assert stats.write_tokens == 0
    assert stats.uncached_tokens == 5


def test_extract_cache_stats_returns_none_when_no_usage() -> None:
    adapter = ClaudeAdapter()
    assert adapter.extract_cache_stats({"type": "assistant"}) is None
    assert (
        adapter.extract_cache_stats({"type": "assistant", "message": {"content": []}})
        is None
    )


def test_extract_cache_stats_returns_none_when_all_counts_zero() -> None:
    """An empty usage object is indistinguishable from no-data; return None."""
    adapter = ClaudeAdapter()
    raw = {
        "type": "assistant",
        "message": {"usage": {"input_tokens": 0}},
    }
    assert adapter.extract_cache_stats(raw) is None


def test_extract_cache_stats_treats_missing_fields_as_zero() -> None:
    """Older Claude API responses may omit cache_* fields entirely."""
    adapter = ClaudeAdapter()
    raw = {
        "type": "assistant",
        "message": {"usage": {"input_tokens": 42}},
    }
    stats = adapter.extract_cache_stats(raw)
    assert stats is not None
    assert stats.read_tokens == 0
    assert stats.write_tokens == 0
    assert stats.uncached_tokens == 42


def test_extract_cache_stats_defensive_on_malformed_shapes() -> None:
    adapter = ClaudeAdapter()
    assert adapter.extract_cache_stats({"usage": "not a dict"}) is None
    assert adapter.extract_cache_stats({"message": "not a dict"}) is None
    assert (
        adapter.extract_cache_stats(
            {"usage": {"input_tokens": "twelve", "cache_read_input_tokens": None}}
        )
        is None
    )
    # Booleans must not leak through as 1/0 — they are not real counts.
    assert adapter.extract_cache_stats({"usage": {"input_tokens": True}}) is None


def test_registered_in_adapters_registry() -> None:
    """Import side-effect registration should hand back the Claude adapter."""
    selected = select_adapter(["claude"])
    assert isinstance(selected, ClaudeAdapter)
