"""Combine and format subprocess output."""

from __future__ import annotations


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


def format_duration(seconds: float) -> str:
    """Format *seconds* as a compact human-readable duration string.

    Returns ``"12.3s"`` for sub-minute, ``"2m 30s"`` for sub-hour,
    and ``"1h 15m"`` for longer durations.  Used in CLI output and
    event data for iteration timing.
    """
    if round(seconds, 1) < 60:
        return f"{seconds:.1f}s"
    # Use rounded total to avoid edge cases like 59.95 → "0m 60s"
    total = round(seconds)
    minutes = total // 60
    secs = total % 60
    if minutes < 60:
        return f"{minutes}m {secs}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"
