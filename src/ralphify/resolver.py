"""Template placeholder resolution for commands and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific value's content.

Items not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

from __future__ import annotations

import re

from ralphify._frontmatter import FIELD_ARGS, FIELD_COMMANDS

# Shared pattern for Mustache-style placeholders: {{ kind.name }}
# The *kind* varies (commands, args) but the structure is identical.
_NAME_CHARS = r"[a-zA-Z0-9_-]+"


def _placeholder_pattern(kind: str) -> re.Pattern[str]:
    """Compile a regex matching ``{{ <kind>.<name> }}`` placeholders."""
    return re.compile(rf"\{{\{{\s*{kind}\.({_NAME_CHARS})\s*\}}\}}")


_COMMANDS_PATTERN = _placeholder_pattern(FIELD_COMMANDS)
_ARGS_PATTERN = _placeholder_pattern(FIELD_ARGS)


def _resolve_kind(prompt: str, available: dict[str, str], pattern: re.Pattern[str]) -> str:
    """Resolve placeholders matching *pattern*, clearing them when *available* is empty.

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    - When *available* is empty, all placeholders of this kind are cleared
    """

    if not available:
        return pattern.sub("", prompt)

    def _replace_named(match: re.Match) -> str:
        name = match.group(1)
        return available.get(name, "")

    return pattern.sub(_replace_named, prompt)


def resolve_commands(prompt: str, command_outputs: dict[str, str]) -> str:
    """Replace ``{{ commands.name }}`` placeholders with command outputs.

    When *command_outputs* is empty, clears any remaining
    ``{{ commands.* }}`` placeholders so they don't leak into the
    assembled prompt.
    """
    return _resolve_kind(prompt, command_outputs, _COMMANDS_PATTERN)


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    return _resolve_kind(prompt, user_args, _ARGS_PATTERN)
