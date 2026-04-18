"""Tests for the Copilot CLI adapter (alpha)."""

from __future__ import annotations

import json

import pytest

from ralphify.adapters import select_adapter
from ralphify.adapters.copilot import CopilotAdapter


def test_matches_copilot_binary_stem() -> None:
    adapter = CopilotAdapter()
    assert adapter.matches(["copilot"]) is True
    assert adapter.matches(["/opt/copilot/bin/copilot"]) is True
    # Deliberately does NOT match the gh subcommand
    assert adapter.matches(["gh"]) is False
    assert adapter.matches([]) is False


def test_build_command_appends_json_flags() -> None:
    adapter = CopilotAdapter()
    assert adapter.build_command(["copilot"]) == [
        "copilot",
        "--output-format",
        "json",
    ]


def test_build_command_is_idempotent() -> None:
    adapter = CopilotAdapter()
    once = adapter.build_command(["copilot"])
    twice = adapter.build_command(once)
    assert once == twice


def test_build_command_replaces_conflicting_format() -> None:
    """``--output-format markdown`` must be replaced, not duplicated."""
    adapter = CopilotAdapter()
    result = adapter.build_command(["copilot", "--output-format", "markdown"])
    assert result.count("--output-format") == 1
    assert "markdown" not in result
    assert "json" in result


def test_parse_tool_use_variants() -> None:
    adapter = CopilotAdapter()
    for event_type in ("tool_use", "tool_call", "ToolCall", "ToolUse"):
        line = json.dumps({"type": event_type, "name": "Edit"})
        event = adapter.parse_event(line)
        assert event is not None
        assert event.kind == "tool_use"
        assert event.name == "Edit"


def test_parse_result_variants() -> None:
    adapter = CopilotAdapter()
    for event_type in ("result", "response", "final", "Complete"):
        event = adapter.parse_event(json.dumps({"type": event_type}))
        assert event is not None
        assert event.kind == "result"


def test_parse_result_event_carries_text() -> None:
    adapter = CopilotAdapter()
    line = json.dumps({"type": "result", "result": "all done"})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "result"
    assert event.text == "all done"


def test_parse_unknown_returns_none() -> None:
    """Unknown event types must NOT count against the turn cap."""
    adapter = CopilotAdapter()
    assert adapter.parse_event(json.dumps({"type": "SomethingElse"})) is None
    assert adapter.parse_event(json.dumps({"type": "progress"})) is None


def test_parse_missing_type_returns_none() -> None:
    adapter = CopilotAdapter()
    assert adapter.parse_event(json.dumps({"name": "Edit"})) is None


def test_parse_malformed_returns_none() -> None:
    adapter = CopilotAdapter()
    assert adapter.parse_event("not json") is None
    assert adapter.parse_event("") is None


def test_parse_event_rejects_alternate_type_keys() -> None:
    """Only the canonical ``type`` key counts — ``event`` / ``kind`` do not.

    Admitting alternative keys widens the schema beyond what has been
    observed in captured output and risks double-counting if a future
    Copilot release emits both keys on the same event.
    """
    adapter = CopilotAdapter()
    assert (
        adapter.parse_event(json.dumps({"event": "tool_use", "name": "Bash"})) is None
    )
    assert adapter.parse_event(json.dumps({"kind": "tool_use", "name": "Bash"})) is None


def test_extract_completion_signal_scans_stdout() -> None:
    adapter = CopilotAdapter()
    assert (
        adapter.extract_completion_signal(
            "chat chatter <promise>MARKER</promise> more text", "MARKER"
        )
        is True
    )
    assert adapter.extract_completion_signal("no marker here", "MARKER") is False


def test_install_wind_down_hook_raises_not_implemented(tmp_path) -> None:
    adapter = CopilotAdapter()
    with pytest.raises(NotImplementedError, match="no hook system"):
        adapter.install_wind_down_hook(tmp_path, tmp_path / "counter", 10, 2)


def test_capability_flags() -> None:
    adapter = CopilotAdapter()
    assert adapter.name == "copilot"
    assert adapter.counts_what == "tool_use"
    assert adapter.renders_structured is False
    assert adapter.supports_soft_wind_down is False


def test_registered_in_adapters_registry() -> None:
    selected = select_adapter(["copilot"])
    assert isinstance(selected, CopilotAdapter)
