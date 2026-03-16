"""Skill installation and agent detection for ``ralph new``."""

from __future__ import annotations

import importlib.resources
import shutil
import tomllib
from pathlib import Path

from ralphify._frontmatter import CONFIG_FILENAME

# Maps agent binary names to the directory where skills are installed.
_AGENT_SKILL_DIRS: dict[str, str] = {
    "claude": ".claude/skills",
    "codex": ".agents/skills",
}

# Maps agent binary names to their skill invocation prefix.
_AGENT_SKILL_PREFIX: dict[str, str] = {
    "claude": "/",
    "codex": "$",
}


def read_bundled_skill(skill_name: str) -> str:
    """Read a bundled SKILL.md from the ``ralphify.skills`` package.

    Raises ``FileNotFoundError`` if the skill does not exist.
    """
    pkg = importlib.resources.files("ralphify.skills").joinpath(skill_name, "SKILL.md")
    return pkg.read_text(encoding="utf-8")


def detect_agent() -> tuple[str, str]:
    """Detect the agent binary to use.

    Resolution order:
    1. ``ralph.toml`` ``[agent].command``
    2. Auto-detect on PATH: ``claude``, then ``codex``

    Returns ``(agent_name, agent_path)`` where *agent_name* is the
    basename (e.g. ``"claude"``) and *agent_path* is the resolved path.

    Raises ``RuntimeError`` when no agent can be found.
    """
    config_path = Path(CONFIG_FILENAME)
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
        command = config.get("agent", {}).get("command")
        if command:
            resolved = shutil.which(command)
            if resolved:
                return command, resolved

    for name in ("claude", "codex"):
        resolved = shutil.which(name)
        if resolved:
            return name, resolved

    raise RuntimeError(
        "No agent found. Install Claude Code or Codex, or set [agent].command in ralph.toml."
    )


def install_skill(skill_name: str, agent_name: str) -> Path:
    """Install a bundled skill into the agent's skill directory.

    Always overwrites so the skill stays in sync with the installed
    ralphify version.

    Returns the path to the installed SKILL.md.

    Raises ``RuntimeError`` for unknown agent names.
    """
    skill_dir_name = _AGENT_SKILL_DIRS.get(agent_name)
    if skill_dir_name is None:
        raise RuntimeError(f"Unknown agent: {agent_name!r}. Supported: {', '.join(_AGENT_SKILL_DIRS)}")

    content = read_bundled_skill(skill_name)
    dest = Path(skill_dir_name) / skill_name / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def build_agent_command(agent_name: str, skill_name: str, ralph_name: str | None) -> list[str]:
    """Build the command to launch the agent with the skill invoked.

    Returns a list suitable for ``os.execvp``.
    """
    prefix = _AGENT_SKILL_PREFIX.get(agent_name, "/")
    invocation = f"{prefix}{skill_name}"
    if ralph_name:
        invocation = f"{invocation} {ralph_name}"
    return [agent_name, invocation]
