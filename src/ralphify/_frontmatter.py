"""Parse YAML frontmatter from RALPH.md files.

A ralph is a directory containing a ``RALPH.md`` file.  The frontmatter
configures the agent command, commands to run, and accepted arguments.
The body is the prompt template.

HTML comments in the body are stripped so users can leave notes that
don't leak into the assembled prompt.
"""

import re

import yaml


# Single source of truth for the ralph marker filename.
RALPH_MARKER = "RALPH.md"

# YAML frontmatter delimiter line.
_FRONTMATTER_DELIMITER = "---"

# Pre-compiled pattern to strip HTML comments from body text.
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _extract_frontmatter_block(text: str) -> tuple[str, str]:
    """Split text into raw YAML frontmatter and body at ``---`` delimiters.

    The opening ``---`` must be the very first line (standard YAML
    frontmatter convention).  Returns ``("", text)`` when no valid
    frontmatter block is found.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != _FRONTMATTER_DELIMITER:
        return "", text

    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == _FRONTMATTER_DELIMITER:
            fm_raw = "\n".join(lines[1:i])
            body = "\n".join(lines[i + 1 :]).strip()
            return fm_raw, body
    return "", text


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a RALPH.md file with YAML frontmatter.

    Frontmatter is delimited by ``---`` lines at the start of the file.
    Full YAML is supported (nested lists, dicts).  HTML comments are
    stripped from the body so they don't leak into the assembled prompt.

    Returns ``(frontmatter_dict, body_text)``.
    """
    fm_raw, body = _extract_frontmatter_block(text)
    if fm_raw:
        try:
            frontmatter = yaml.safe_load(fm_raw) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in frontmatter: {exc}") from exc
        if not isinstance(frontmatter, dict):
            raise ValueError(
                f"Frontmatter must be a YAML mapping, got {type(frontmatter).__name__}"
            )
    else:
        frontmatter = {}
    body = _HTML_COMMENT_RE.sub("", body).strip()
    return frontmatter, body


def serialize_frontmatter(frontmatter: dict, body: str) -> str:
    """Serialize frontmatter and body back to a markdown string.

    This is the inverse of :func:`parse_frontmatter`.  If *frontmatter*
    is empty the body is returned as-is (no ``---`` delimiters).
    """
    parts: list[str] = []
    if frontmatter:
        parts.append(_FRONTMATTER_DELIMITER)
        fm_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()
        parts.append(fm_text)
        parts.append(_FRONTMATTER_DELIMITER)
        parts.append("")
    parts.append(body)
    return "\n".join(parts)
