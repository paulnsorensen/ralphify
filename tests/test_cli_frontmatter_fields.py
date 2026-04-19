"""Tests for the new max_turns / max_turns_grace / hooks frontmatter fields."""

from __future__ import annotations

from pathlib import Path

import pytest
import typer

from ralphify.cli import (
    _validate_hooks,
    _validate_max_turns,
    _validate_max_turns_grace,
    _build_run_config,
)
from ralphify.hooks import AgentHook, ShellAgentHook


class TestValidateMaxTurns:
    def test_absent_returns_none(self) -> None:
        assert _validate_max_turns(None) is None

    def test_positive_int_passes(self) -> None:
        assert _validate_max_turns(5) == 5
        assert _validate_max_turns(1) == 1

    def test_zero_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns(0)

    def test_negative_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns(-1)

    def test_bool_exits(self) -> None:
        # Booleans are ints in Python, but we reject them explicitly.
        with pytest.raises(typer.Exit):
            _validate_max_turns(True)

    def test_string_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns("5")


class TestValidateMaxTurnsGrace:
    def test_absent_defaults_to_two(self) -> None:
        assert _validate_max_turns_grace(None, None) == 2
        assert _validate_max_turns_grace(None, 10) == 2

    def test_zero_passes(self) -> None:
        assert _validate_max_turns_grace(0, 5) == 0

    def test_grace_equal_to_max_turns_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns_grace(5, 5)

    def test_grace_greater_than_max_turns_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns_grace(10, 5)

    def test_negative_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_max_turns_grace(-1, None)

    def test_no_cap_means_no_upper_bound(self) -> None:
        assert _validate_max_turns_grace(100, None) == 100


class TestValidateHooks:
    def test_absent_returns_empty(self) -> None:
        assert _validate_hooks(None) == []

    def test_valid_hook_returns_shell_hook(self) -> None:
        hooks = _validate_hooks([{"event": "on_iteration_started", "run": "echo hi"}])
        assert len(hooks) == 1
        assert isinstance(hooks[0], ShellAgentHook)
        # Protocol check — the validated object must satisfy AgentHook
        assert isinstance(hooks[0], AgentHook)

    def test_multiple_hooks_preserve_order(self) -> None:
        hooks = _validate_hooks(
            [
                {"event": "on_iteration_started", "run": "echo a"},
                {"event": "on_turn_capped", "run": "echo b"},
            ]
        )
        assert len(hooks) == 2

    def test_unknown_event_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_hooks([{"event": "on_bogus", "run": "echo x"}])

    def test_missing_event_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_hooks([{"run": "echo x"}])

    def test_missing_run_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_hooks([{"event": "on_iteration_started"}])

    def test_non_list_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_hooks({"event": "on_iteration_started", "run": "x"})

    def test_empty_command_exits(self) -> None:
        with pytest.raises(typer.Exit):
            _validate_hooks([{"event": "on_iteration_started", "run": ""}])


class TestBuildRunConfigIntegration:
    def _write_ralph(self, tmp_path: Path, frontmatter: str) -> Path:
        ralph = tmp_path / "RALPH.md"
        ralph.write_text(f"---\nagent: /bin/echo\n{frontmatter}\n---\nprompt\n")
        return ralph

    def test_max_turns_lands_on_run_config(self, tmp_path: Path) -> None:
        ralph = self._write_ralph(tmp_path, "max_turns: 15\nmax_turns_grace: 3")
        cfg = _build_run_config(str(ralph), None, False, 0.0, None, None)
        assert cfg.max_turns == 15
        assert cfg.max_turns_grace == 3

    def test_hooks_land_on_run_config(self, tmp_path: Path) -> None:
        ralph = self._write_ralph(
            tmp_path,
            "hooks:\n  - event: on_iteration_started\n    run: echo hi",
        )
        cfg = _build_run_config(str(ralph), None, False, 0.0, None, None)
        assert len(cfg.hooks) == 1
        assert isinstance(cfg.hooks[0], ShellAgentHook)

    def test_defaults_when_fields_absent(self, tmp_path: Path) -> None:
        ralph = self._write_ralph(tmp_path, "")
        cfg = _build_run_config(str(ralph), None, False, 0.0, None, None)
        assert cfg.max_turns is None
        assert cfg.max_turns_grace == 2
        assert cfg.hooks == []
