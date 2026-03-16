"""Scaffold templates for ``ralph init``."""

RALPH_TOML_TEMPLATE = """\
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
"""

ROOT_RALPH_TEMPLATE = """\
# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

- Implement one thing per iteration
- Search before creating anything new
- No placeholder code — full implementations only
- Run tests and fix failures before committing
- Commit with a descriptive message

<!-- Add your project-specific instructions below -->
"""
