"""Tests for the Codex CLI adapter."""

from __future__ import annotations

import json
import sys

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


def test_parse_unknown_events_return_none() -> None:
    """Unknown Codex event types must NOT inflate the turn cap."""
    adapter = CodexAdapter()
    assert adapter.parse_event(json.dumps({"type": "SomethingNew"})) is None


def test_parse_result_event_carries_text() -> None:
    adapter = CodexAdapter()
    line = json.dumps({"type": "TaskComplete", "text": "finished"})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "result"
    assert event.text == "finished"


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


def test_parse_command_at_top_level() -> None:
    """``CommandExecution`` events carry the command at the top level too."""
    adapter = CodexAdapter()
    line = json.dumps({"type": "CommandExecution", "command": "ls -la"})
    event = adapter.parse_event(line)
    assert event is not None
    assert event.kind == "tool_use"
    assert event.name == "ls -la"


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
    assert adapter.extract_completion_signal(stream, "DONE") is True
    assert adapter.extract_completion_signal(stream, "OTHER") is False


def test_extract_completion_signal_scans_plain_output() -> None:
    adapter = CodexAdapter()
    assert (
        adapter.extract_completion_signal("some <promise>HI</promise> text", "HI")
        is True
    )


def test_install_wind_down_hook_writes_hooks_config_and_returns_env(tmp_path) -> None:
    adapter = CodexAdapter()
    counter_path = tmp_path / "counter"
    env = adapter.install_wind_down_hook(tmp_path, counter_path, 8, 3)

    assert env == {"CODEX_HOME": str(tmp_path)}

    hooks_payload = json.loads((tmp_path / "hooks.json").read_text(encoding="utf-8"))
    post_tool_use = hooks_payload["PostToolUse"]
    assert len(post_tool_use) == 1
    matcher_group = post_tool_use[0]
    assert matcher_group["matcher"] == "Bash"
    inner_hook = matcher_group["hooks"][0]
    assert inner_hook["type"] == "command"
    command = inner_hook["command"]
    assert sys.executable in command
    assert "ralphify._wind_down_shim" in command
    assert str(counter_path) in command
    assert " 8 3 codex" in command

    config_text = (tmp_path / "config.toml").read_text(encoding="utf-8")
    assert "[features]" in config_text
    assert "codex_hooks = true" in config_text


def test_capability_flags() -> None:
    adapter = CodexAdapter()
    assert adapter.name == "codex"
    assert adapter.counts_what == "tool_use"
    assert adapter.renders_structured is True
    assert adapter.supports_soft_wind_down is True


def test_registered_in_adapters_registry() -> None:
    selected = select_adapter(["codex"])
    assert isinstance(selected, CodexAdapter)
