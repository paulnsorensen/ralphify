"""Combine and truncate subprocess output for prompt injection.

Output from checks and contexts is capped at :data:`MAX_OUTPUT_LEN`
characters (5 000) to avoid blowing up the agent's context window.
"""

from __future__ import annotations

MAX_OUTPUT_LEN = 5000


def collect_output(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> str:
    """Combine stdout and stderr into a single string.

    Handles both str and bytes (as returned by subprocess.TimeoutExpired),
    decoding bytes as UTF-8 with replacement for non-decodable characters.
    """
    parts: list[str] = []
    for stream in (stdout, stderr):
        if stream:
            parts.append(stream if isinstance(stream, str) else stream.decode("utf-8", errors="replace"))
    return "".join(parts)


def truncate_output(text: str, max_len: int = MAX_OUTPUT_LEN) -> str:
    """Truncate *text* to *max_len* characters, appending an indicator if trimmed."""
    if len(text) > max_len:
        return text[:max_len] + "\n... (truncated)"
    return text
