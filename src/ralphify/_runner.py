"""Execute shell commands with timeout and output capture.

Used by the engine to run configured commands.  The working directory
is set by the caller — typically the project root or the ralph directory
for ``./`` commands.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ralphify._output import SUBPROCESS_TEXT_KWARGS, collect_output


@dataclass
class RunResult:
    """Result of running a command or script."""

    success: bool
    returncode: int | None
    output: str
    timed_out: bool = False


def run_command(
    *,
    command: str,
    cwd: Path,
    timeout: float,
    env: dict[str, str] | None = None,
) -> RunResult:
    """Run a shell command and return the result.

    The *command* string is split with :func:`shlex.split` and executed
    directly (no shell).  Pipes, redirections, and ``&&`` chaining are
    not supported — use a script for complex logic.

    When *env* is set, the given variables are merged on top of the
    current process environment so scripts keep ``PATH`` etc.  When
    ``None`` (default), ``subprocess.run`` inherits the parent env.

    On timeout, returns ``returncode=None`` and ``timed_out=True``.
    """
    cmd = shlex.split(command)
    if not cmd:
        raise ValueError(f"Command string produced no tokens after parsing: {command!r}")

    merged_env = {**os.environ, **env} if env else None

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            **SUBPROCESS_TEXT_KWARGS,
            cwd=cwd,
            timeout=timeout,
            env=merged_env,
        )
        return RunResult(
            success=result.returncode == 0,
            returncode=result.returncode,
            output=collect_output(result.stdout, result.stderr),
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            success=False,
            returncode=None,
            output=collect_output(e.stdout, e.stderr),
            timed_out=True,
        )
