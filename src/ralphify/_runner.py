from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ralphify._output import collect_output


@dataclass
class RunResult:
    """Result of running a command or script."""

    success: bool
    exit_code: int
    output: str
    timed_out: bool = False


def run_command(
    *,
    script: Path | None,
    command: str | None,
    cwd: Path,
    timeout: int,
) -> RunResult:
    """Run a script or shell command and return the result.

    If *script* is set it takes precedence; otherwise *command* is
    split with ``shlex`` and executed.
    """
    if script:
        cmd = [str(script)]
    else:
        cmd = shlex.split(command)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
        )
        return RunResult(
            success=result.returncode == 0,
            exit_code=result.returncode,
            output=collect_output(result.stdout, result.stderr),
        )
    except subprocess.TimeoutExpired as e:
        return RunResult(
            success=False,
            exit_code=-1,
            output=collect_output(e.stdout, e.stderr),
            timed_out=True,
        )
