"""Template placeholder resolution for contexts.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific primitive's content.

Contexts not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

import re


def resolve_placeholders(
    prompt: str,
    available: dict[str, str],
    kind: str,
) -> str:
    """Replace named template placeholders in a prompt string.

    *kind* is the placeholder category (e.g. "contexts").

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    """
    if not available:
        return prompt

    named_pattern = re.compile(r"\{\{\s*" + re.escape(kind) + r"\.([a-zA-Z0-9_-]+)\s*\}\}")

    def _replace_named(match: re.Match) -> str:
        name = match.group(1)
        if name in available:
            return available[name]
        return ""

    return named_pattern.sub(_replace_named, prompt)
