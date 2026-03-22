"""Combine and format subprocess output."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Shared subprocess kwargs for text-mode execution with UTF-8 decoding.
# Every subprocess.run / subprocess.Popen call that reads text output should
# unpack these to ensure consistent encoding behavior across the codebase.
SUBPROCESS_TEXT_KWARGS: dict[str, Any] = {
    "text": True,
    "encoding": "utf-8",
    "errors": "replace",
}


@dataclass
class ProcessResult:
    """Base result for any subprocess execution.

    Shared by :class:`~ralphify._runner.RunResult` and
    :class:`~ralphify._agent.AgentResult` so the common *success*
    logic lives in one place.
    """

    returncode: int | None
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """Whether the process exited successfully (code 0, no timeout)."""
        return self.returncode == 0 and not self.timed_out


def ensure_str(value: str | bytes) -> str:
    """Decode *value* to a string if it is bytes, passing strings through.

    Uses UTF-8 with replacement so non-decodable bytes never raise.
    """
    return value if isinstance(value, str) else value.decode("utf-8", errors="replace")


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
            parts.append(ensure_str(stream))
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
