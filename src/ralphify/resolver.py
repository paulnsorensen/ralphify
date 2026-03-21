"""Template placeholder resolution for commands and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific value's content.

Items not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

import re

_ARGS_CLEANUP_RE = re.compile(r"\{\{\s*args\.[a-zA-Z0-9_-]+\s*\}\}")
_PATTERN_CACHE: dict[str, re.Pattern[str]] = {}


def _get_pattern(kind: str) -> re.Pattern[str]:
    """Return a compiled regex for the given placeholder kind, caching the result."""
    if kind not in _PATTERN_CACHE:
        _PATTERN_CACHE[kind] = re.compile(
            r"\{\{\s*" + re.escape(kind) + r"\.([a-zA-Z0-9_-]+)\s*\}\}"
        )
    return _PATTERN_CACHE[kind]


def resolve_placeholders(
    prompt: str,
    available: dict[str, str],
    kind: str,
) -> str:
    """Replace named template placeholders in a prompt string.

    *kind* is the placeholder category (e.g. "commands", "args").

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    """
    if not available:
        return prompt

    named_pattern = _get_pattern(kind)

    def _replace_named(match: re.Match) -> str:
        name = match.group(1)
        if name in available:
            return available[name]
        return ""

    return named_pattern.sub(_replace_named, prompt)


def resolve_commands(prompt: str, command_outputs: dict[str, str]) -> str:
    """Replace ``{{ commands.name }}`` placeholders with command outputs.

    Delegates to :func:`resolve_placeholders` with ``kind="commands"``.
    """
    return resolve_placeholders(prompt, command_outputs, "commands")


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    Delegates to :func:`resolve_placeholders` with ``kind="args"``.
    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    if not user_args:
        return _ARGS_CLEANUP_RE.sub("", prompt)
    return resolve_placeholders(prompt, user_args, "args")
