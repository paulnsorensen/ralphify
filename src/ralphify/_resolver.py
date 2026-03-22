"""Template placeholder resolution for commands and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific value's content.

Items not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

from __future__ import annotations

import re

from ralphify._frontmatter import CMD_NAME_RE, FIELD_ARGS, FIELD_COMMANDS


def _placeholder_pattern(kind: str) -> re.Pattern[str]:
    """Compile a regex matching ``{{ <kind>.<name> }}`` placeholders."""
    return re.compile(rf"\{{\{{\s*{kind}\.({CMD_NAME_RE.pattern})\s*\}}\}}")


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


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    return _resolve_kind(prompt, user_args, _ARGS_PATTERN)


# Single pattern matching both placeholder kinds for single-pass resolution.
_ALL_PATTERN = re.compile(
    rf"\{{\{{\s*({FIELD_COMMANDS}|{FIELD_ARGS})\.({CMD_NAME_RE.pattern})\s*\}}\}}"
)


def resolve_all(
    prompt: str,
    command_outputs: dict[str, str],
    user_args: dict[str, str],
) -> str:
    """Resolve all placeholders in a single pass to prevent cross-contamination.

    Resolves both ``{{ commands.name }}`` and ``{{ args.name }}`` in a
    single pass so values inserted by one kind of placeholder are not
    re-processed as the other kind.
    """
    lookups: dict[str, dict[str, str]] = {
        FIELD_COMMANDS: command_outputs,
        FIELD_ARGS: user_args,
    }

    def _replace(match: re.Match) -> str:
        kind = match.group(1)
        name = match.group(2)
        return lookups[kind].get(name, "")

    return _ALL_PATTERN.sub(_replace, prompt)
