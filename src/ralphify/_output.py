"""Combine and format subprocess output."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Any

# Platform flag used by _agent.py and cli.py to guard Windows-specific code
# paths (process-group handling, console encoding).  Centralised here next to
# SUBPROCESS_TEXT_KWARGS so platform-aware modules import from one place.
IS_WINDOWS = sys.platform == "win32"

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

    *returncode* is the process exit code, or ``None`` when the process
    timed out.  *timed_out* makes the timeout condition explicit — prefer
    checking ``timed_out`` over ``returncode is None``.
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
            text = ensure_str(stream)
            if parts and not parts[-1].endswith("\n"):
                parts.append("\n")
            parts.append(text)
    return "".join(parts)


_SECONDS_PER_MINUTE = 60
_MINUTES_PER_HOUR = 60


def format_duration(seconds: float) -> str:
    """Format *seconds* as a compact human-readable duration string.

    Returns ``"12.3s"`` for sub-minute, ``"2m 30s"`` for sub-hour,
    and ``"1h 15m"`` for longer durations.  Used in CLI output and
    event data for iteration timing.
    """
    if round(seconds, 1) < _SECONDS_PER_MINUTE:
        return f"{seconds:.1f}s"
    # Use rounded total to avoid edge cases like 59.95 → "0m 60s"
    total = round(seconds)
    minutes = total // _SECONDS_PER_MINUTE
    secs = total % _SECONDS_PER_MINUTE
    if minutes < _MINUTES_PER_HOUR:
        return f"{minutes}m {secs}s"
    hours = minutes // _MINUTES_PER_HOUR
    mins = minutes % _MINUTES_PER_HOUR
    return f"{hours}h {mins}m"
