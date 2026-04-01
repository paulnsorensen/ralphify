"""Skill installation and agent detection for ``ralph new``."""

from __future__ import annotations

import importlib.resources
import shutil
from dataclasses import dataclass
from pathlib import Path


SKILL_MARKER = "SKILL.md"
"""Filename used for skill definition files inside agent skill directories."""


@dataclass(frozen=True)
class DetectedAgent:
    """Result of agent auto-detection."""

    name: str
    path: str


@dataclass(frozen=True)
class _AgentConfig:
    """Skill integration settings for a supported agent."""

    skill_dir: str
    skill_prefix: str
    extra_flags: tuple[str, ...] = ()


_AGENTS: dict[str, _AgentConfig] = {
    "claude": _AgentConfig(
        skill_dir=".claude/skills",
        skill_prefix="/",
        extra_flags=("--dangerously-skip-permissions",),
    ),
    "codex": _AgentConfig(skill_dir=".agents/skills", skill_prefix="$"),
}


def _get_agent_config(agent_name: str) -> _AgentConfig:
    """Look up agent-specific skill settings by name."""
    config = _AGENTS.get(agent_name)
    if config is None:
        raise RuntimeError(
            f"Unknown agent: {agent_name!r}. Supported: {', '.join(_AGENTS)}"
        )
    return config


def read_bundled_skill(skill_name: str) -> str:
    """Read a bundled SKILL.md from the ``ralphify.skills`` package."""
    pkg = importlib.resources.files("ralphify.skills").joinpath(
        skill_name, SKILL_MARKER
    )
    return pkg.read_text(encoding="utf-8")


def detect_agent() -> DetectedAgent:
    """Detect the agent binary to use.

    Auto-detects on PATH: ``claude``, then ``codex``.

    Returns a :class:`DetectedAgent` with the binary name and resolved path.
    Raises ``RuntimeError`` when no agent can be found.
    """
    for name in _AGENTS:
        resolved = shutil.which(name)
        if resolved:
            return DetectedAgent(name=name, path=resolved)

    raise RuntimeError("No agent found. Install Claude Code or Codex.")


def install_skill(skill_name: str, agent_name: str) -> Path:
    """Install a bundled skill into the agent's skill directory."""
    agent_config = _get_agent_config(agent_name)
    content = read_bundled_skill(skill_name)
    dest = Path(agent_config.skill_dir) / skill_name / SKILL_MARKER
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest


def build_agent_command(
    agent_name: str, skill_name: str, ralph_name: str | None
) -> list[str]:
    """Build the command to launch the agent with the skill invoked."""
    agent_config = _get_agent_config(agent_name)
    invocation = f"{agent_config.skill_prefix}{skill_name}"
    if ralph_name:
        invocation = f"{invocation} {ralph_name}"
    return [agent_name, *agent_config.extra_flags, invocation]
