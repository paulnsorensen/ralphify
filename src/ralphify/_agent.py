"""Run agent subprocesses with output capture and timeout enforcement.

This module handles the mechanics of executing agent commands — spawning
processes, enforcing timeouts, capturing output, and writing log files.
The engine module uses these functions but owns the orchestration: state
updates, event emission, and loop control.

Two execution modes are supported:

- **Streaming** (``_run_agent_streaming``) — line-by-line stdout reading
  via ``Popen``, used for agents that emit JSON streams (e.g. Claude Code).
- **Blocking** (``_run_agent_blocking``) — ``subprocess.run`` with optional
  output capture, used for all other agents.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import IO, NamedTuple

from ralphify._output import collect_output


@dataclass
class AgentResult:
    """Result of running the agent subprocess.

    *returncode* is the process exit code, or ``None`` when the process
    timed out.  *timed_out* makes the timeout condition explicit — prefer
    checking ``timed_out`` over ``returncode is None``.
    """

    returncode: int | None
    elapsed: float
    log_file: Path | None
    result_text: str | None = None
    timed_out: bool = False


class _StreamResult(NamedTuple):
    """Accumulated output from reading the agent's JSON stream."""

    stdout_lines: list[str]
    result_text: str | None
    timed_out: bool


def _write_log(
    log_path_dir: Path,
    iteration: int,
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> Path:
    """Write iteration output to a timestamped log file and return the path."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = log_path_dir / f"{iteration:03d}_{timestamp}.log"
    log_file.write_text(collect_output(stdout, stderr))
    return log_file


def _supports_stream_json(cmd: list[str]) -> bool:
    """Return True if the agent command supports ``--output-format stream-json``.

    Currently only Claude Code supports this protocol.  To add streaming
    support for another agent, extend the check here — no other changes
    needed since :func:`_run_agent_streaming` handles the protocol generically.
    """
    if not cmd:
        return False
    binary = Path(cmd[0]).name
    return binary == "claude"


def _read_agent_stream(
    stdout: IO[str],
    deadline: float | None,
    on_activity: Callable[[dict], None] | None,
) -> _StreamResult:
    """Read the agent's JSON stream line-by-line until EOF or timeout.

    Parses each non-empty line as JSON.  Valid JSON objects are forwarded
    to *on_activity* (if provided).  The ``result`` field from
    ``{"type": "result"}`` events is captured as *result_text*.

    Lines that aren't valid JSON are silently collected for logging but
    not forwarded — this keeps the caller working even if the agent
    emits non-JSON diagnostics to stdout.

    Returns early with ``timed_out=True`` when the deadline is exceeded,
    leaving the caller responsible for killing the subprocess.
    """
    stdout_lines: list[str] = []
    result_text: str | None = None

    for line in stdout:
        if deadline and time.monotonic() > deadline:
            return _StreamResult(stdout_lines, result_text, timed_out=True)

        stdout_lines.append(line)
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if parsed.get("type") == "result" and "result" in parsed:
            result_text = parsed["result"]
        if on_activity is not None:
            on_activity(parsed)

    return _StreamResult(stdout_lines, result_text, timed_out=False)


def _run_agent_streaming(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_activity: Callable[[dict], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess with line-by-line streaming of JSON output.

    Used for agents that support ``--output-format stream-json`` (e.g. Claude
    Code).  Stream processing is delegated to :func:`_read_agent_stream`;
    this function owns the subprocess lifecycle (spawn, stdin delivery,
    timeout kill, and cleanup via ``try/finally``).
    """
    stream_cmd = cmd + ["--output-format", "stream-json", "--verbose"]
    start = time.monotonic()
    deadline = (start + timeout) if timeout else None

    proc = subprocess.Popen(
        stream_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # Popen with PIPE guarantees non-None streams; guard explicitly
        # so the type checker narrows and -O mode cannot skip the check.
        if proc.stdin is None or proc.stdout is None or proc.stderr is None:
            raise RuntimeError("subprocess.Popen failed to create PIPE streams")

        proc.stdin.write(prompt)
        proc.stdin.close()

        stream = _read_agent_stream(proc.stdout, deadline, on_activity)

        if stream.timed_out:
            proc.kill()
        proc.wait()

        stderr_data = proc.stderr.read()
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()

    log_file: Path | None = None
    if log_path_dir:
        log_file = _write_log(log_path_dir, iteration, "".join(stream.stdout_lines), stderr_data)

    return AgentResult(
        returncode=None if stream.timed_out else proc.returncode,
        elapsed=time.monotonic() - start,
        log_file=log_file,
        result_text=stream.result_text,
        timed_out=stream.timed_out,
    )


def _run_agent_blocking(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
) -> AgentResult:
    """Run the agent subprocess, optionally write logs, and return the result.

    When *log_path_dir* is set, output is captured, written to a log file,
    then echoed to stdout/stderr so the user still sees it live.  When unset,
    output streams directly to the terminal (no capture overhead).

    Returns ``returncode=None`` when the process times out.
    Raises ``FileNotFoundError`` if the command binary does not exist.
    """
    start = time.monotonic()

    try:
        result = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            timeout=timeout,
            capture_output=bool(log_path_dir),
        )
    except subprocess.TimeoutExpired as e:
        log_file = None
        if log_path_dir:
            log_file = _write_log(log_path_dir, iteration, e.stdout, e.stderr)
        return AgentResult(
            returncode=None,
            elapsed=time.monotonic() - start,
            log_file=log_file,
            timed_out=True,
        )

    log_file: Path | None = None
    if log_path_dir:
        log_file = _write_log(log_path_dir, iteration, result.stdout, result.stderr)
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)

    return AgentResult(
        returncode=result.returncode,
        elapsed=time.monotonic() - start,
        log_file=log_file,
    )


def execute_agent(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_activity: Callable[[dict], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess, auto-selecting streaming or blocking mode.

    Uses streaming mode for agents that support ``--output-format stream-json``
    (e.g. Claude Code); all other agents use the blocking ``subprocess.run``
    path.  The *on_activity* callback is only invoked in streaming mode.

    This is the single entry point the engine should use — callers don't need
    to know which execution mode is selected.
    """
    if _supports_stream_json(cmd):
        return _run_agent_streaming(
            cmd, prompt, timeout, log_path_dir, iteration,
            on_activity=on_activity,
        )
    return _run_agent_blocking(cmd, prompt, timeout, log_path_dir, iteration)
