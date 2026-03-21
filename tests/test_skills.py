"""Tests for skill installation and agent detection."""

from pathlib import Path
from unittest.mock import patch

import pytest

from ralphify._skills import (
    DetectedAgent,
    build_agent_command,
    detect_agent,
    install_skill,
    read_bundled_skill,
)


class TestReadBundledSkill:
    def test_reads_new_ralph_skill(self):
        content = read_bundled_skill("new-ralph")
        assert "name: new-ralph" in content
        assert "RALPH.md" in content

    def test_raises_for_nonexistent_skill(self):
        with pytest.raises(FileNotFoundError):
            read_bundled_skill("does-not-exist")


class TestDetectAgent:
    def test_from_path_claude(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def fake_which(cmd):
            if cmd == "claude":
                return "/usr/bin/claude"
            return None

        with patch("shutil.which", side_effect=fake_which):
            agent = detect_agent()
        assert agent.name == "claude"

    def test_prefers_codex_on_path_when_claude_missing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        def fake_which(cmd):
            if cmd == "codex":
                return "/usr/bin/codex"
            return None

        with patch("shutil.which", side_effect=fake_which):
            agent = detect_agent()
        assert agent.name == "codex"

    def test_raises_when_nothing_found(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with patch("shutil.which", return_value=None):
            with pytest.raises(RuntimeError, match="No agent found"):
                detect_agent()


class TestInstallSkill:
    def test_claude_skill_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = install_skill("new-ralph", "claude")
        assert dest == Path(".claude/skills/new-ralph/SKILL.md")
        assert (tmp_path / dest).exists()
        assert "new-ralph" in (tmp_path / dest).read_text()

    def test_codex_skill_path(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        dest = install_skill("new-ralph", "codex")
        assert dest == Path(".agents/skills/new-ralph/SKILL.md")
        assert (tmp_path / dest).exists()

    def test_raises_for_unknown_agent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(RuntimeError, match="Unknown agent"):
            install_skill("new-ralph", "unknown-agent")

    def test_overwrites_existing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        skill_dir = tmp_path / ".claude" / "skills" / "new-ralph"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("old version")

        install_skill("new-ralph", "claude")
        assert (skill_dir / "SKILL.md").read_text() != "old version"


class TestBuildAgentCommand:
    def test_claude_with_name(self):
        cmd = build_agent_command("claude", "new-ralph", "my-task")
        assert cmd == ["claude", "--dangerously-skip-permissions", "/new-ralph my-task"]

    def test_claude_without_name(self):
        cmd = build_agent_command("claude", "new-ralph", None)
        assert cmd == ["claude", "--dangerously-skip-permissions", "/new-ralph"]

    def test_codex_with_name(self):
        cmd = build_agent_command("codex", "new-ralph", "my-task")
        assert cmd == ["codex", "$new-ralph my-task"]

    def test_codex_without_name(self):
        cmd = build_agent_command("codex", "new-ralph", None)
        assert cmd == ["codex", "$new-ralph"]

    def test_raises_for_unknown_agent(self):
        with pytest.raises(RuntimeError, match="Unknown agent"):
            build_agent_command("unknown-agent", "new-ralph", None)
