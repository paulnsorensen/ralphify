"""Template placeholder resolution for commands and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific value's content.

Items not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

import re

_COMMANDS_PATTERN = re.compile(r"\{\{\s*commands\.([a-zA-Z0-9_-]+)\s*\}\}")
_ARGS_PATTERN = re.compile(r"\{\{\s*args\.([a-zA-Z0-9_-]+)\s*\}\}")

_PATTERNS: dict[str, re.Pattern[str]] = {
    "commands": _COMMANDS_PATTERN,
    "args": _ARGS_PATTERN,
}


def _resolve_kind(prompt: str, available: dict[str, str], kind: str) -> str:
    """Resolve placeholders of a given *kind*, clearing them when *available* is empty.

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    - When *available* is empty, all placeholders of this kind are cleared
    """
    pattern = _PATTERNS[kind]

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
    return _resolve_kind(prompt, command_outputs, "commands")


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    return _resolve_kind(prompt, user_args, "args")
