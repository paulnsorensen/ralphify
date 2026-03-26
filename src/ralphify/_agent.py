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
import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any

from ralphify._output import IS_WINDOWS, SUBPROCESS_TEXT_KWARGS, ProcessResult, collect_output, ensure_str

# Agent binary name that supports --output-format stream-json.
_CLAUDE_BINARY = "claude"

# CLI flags appended when streaming mode is used.
_OUTPUT_FORMAT_FLAG = "--output-format"
_STREAM_FORMAT = "stream-json"
_VERBOSE_FLAG = "--verbose"

# JSON stream event types and fields for result extraction.
_RESULT_EVENT_TYPE = "result"
_RESULT_FIELD = "result"

# Log file naming — timestamp format and iteration zero-padding width.
_LOG_TIMESTAMP_FORMAT = "%Y%m%d-%H%M%S"
_LOG_ITERATION_PAD_WIDTH = 3

# Seconds to wait for graceful shutdown after SIGTERM before escalating to SIGKILL.
_SIGTERM_GRACE_PERIOD = 3

# Subprocess kwargs that isolate agent processes in their own session/group.
# On POSIX this uses start_new_session so the agent and all its children
# form a separate process group that can be killed together.
_SESSION_KWARGS: dict[str, Any] = (
    {} if IS_WINDOWS
    else {"start_new_session": True}
)


def _try_graceful_group_kill(proc: subprocess.Popen[Any]) -> bool:
    """Attempt to kill the process via its POSIX process group.

    Sends SIGTERM, waits briefly, then escalates to SIGKILL if needed.
    Only acts when the process is a session leader (pgid == pid) to avoid
    accidentally killing the caller's group in tests.

    Returns ``True`` if the group kill succeeded, ``False`` if the caller
    should fall back to ``proc.kill()``.
    """
    try:
        pgid = os.getpgid(proc.pid)
    except (OSError, ProcessLookupError):
        return False

    if pgid != proc.pid:
        return False

    try:
        os.killpg(pgid, signal.SIGTERM)
    except (OSError, ProcessLookupError):
        return False

    try:
        proc.wait(timeout=_SIGTERM_GRACE_PERIOD)
        return True
    except subprocess.TimeoutExpired:
        pass

    try:
        os.killpg(pgid, signal.SIGKILL)
        return True
    except (OSError, ProcessLookupError):
        return False


def _kill_process_group(proc: subprocess.Popen[Any]) -> None:
    """Kill the agent process and its entire process group.

    On POSIX, attempts a graceful group kill (SIGTERM → SIGKILL) via
    :func:`_try_graceful_group_kill`.  Falls back to ``proc.kill()``
    on Windows, when the process already exited, or if the group kill fails.
    """
    if not IS_WINDOWS and proc.poll() is None:
        if _try_graceful_group_kill(proc):
            return
    proc.kill()


@dataclass
class AgentResult(ProcessResult):
    """Result of running the agent subprocess."""

    elapsed: float = 0.0
    log_file: Path | None = None
    result_text: str | None = None


@dataclass(frozen=True)
class _StreamResult:
    """Accumulated output from reading the agent's JSON stream."""

    stdout_lines: list[str]
    result_text: str | None
    timed_out: bool


def _write_log(
    log_path_dir: Path | None,
    iteration: int,
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> Path | None:
    """Write iteration output to a timestamped log file if logging is configured.

    Returns the log file path, or ``None`` when *log_path_dir* is not set.
    """
    if log_path_dir is None:
        return None
    timestamp = datetime.now(timezone.utc).strftime(_LOG_TIMESTAMP_FORMAT)
    log_file = log_path_dir / f"{iteration:0{_LOG_ITERATION_PAD_WIDTH}d}_{timestamp}.log"
    log_file.write_text(collect_output(stdout, stderr), encoding="utf-8")
    return log_file


def _echo_output(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
) -> None:
    """Echo captured output to the terminal so the user still sees it.

    Called after output has been written to a log file — without this,
    captured output would be silently swallowed when logging is enabled.
    """
    if stdout:
        sys.stdout.write(ensure_str(stdout))
    if stderr:
        sys.stderr.write(ensure_str(stderr))


def _supports_stream_json(cmd: list[str]) -> bool:
    """Return True if the agent command supports ``--output-format stream-json``.

    Currently only Claude Code supports this protocol.  To add streaming
    support for another agent, extend the check here — no other changes
    needed since :func:`_run_agent_streaming` handles the protocol generically.
    """
    if not cmd:
        return False
    binary = Path(cmd[0]).stem
    return binary == _CLAUDE_BINARY


def _read_agent_stream(
    stdout: IO[str],
    deadline: float | None,
    on_activity: Callable[[dict[str, Any]], None] | None,
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
        stdout_lines.append(line)

        stripped = line.strip()
        if stripped:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                if parsed.get("type") == _RESULT_EVENT_TYPE and isinstance(parsed.get(_RESULT_FIELD), str):
                    result_text = parsed[_RESULT_FIELD]
                if on_activity is not None:
                    on_activity(parsed)

        if deadline is not None and time.monotonic() > deadline:
            return _StreamResult(stdout_lines=stdout_lines, result_text=result_text, timed_out=True)

    return _StreamResult(stdout_lines=stdout_lines, result_text=result_text, timed_out=False)


def _run_agent_streaming(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_activity: Callable[[dict[str, Any]], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess with line-by-line streaming of JSON output.

    Used for agents that support ``--output-format stream-json`` (e.g. Claude
    Code).  Stream processing is delegated to :func:`_read_agent_stream`;
    this function owns the subprocess lifecycle (spawn, stdin delivery,
    timeout kill, and cleanup via ``try/finally``).
    """
    stream_cmd = cmd + [_OUTPUT_FORMAT_FLAG, _STREAM_FORMAT, _VERBOSE_FLAG]
    start = time.monotonic()
    deadline = (start + timeout) if timeout is not None else None

    proc = subprocess.Popen(
        stream_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **SUBPROCESS_TEXT_KWARGS,
        **_SESSION_KWARGS,
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
            _kill_process_group(proc)
        proc.wait()

        stderr_data = proc.stderr.read()
    finally:
        if proc.poll() is None:
            _kill_process_group(proc)
            proc.wait()

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

    The subprocess is started in its own process group so that on
    ``KeyboardInterrupt`` or timeout the entire child tree can be killed
    via :func:`_kill_process_group`.

    Returns ``returncode=None`` when the process times out.
    Raises ``FileNotFoundError`` if the command binary does not exist.
    """
    start = time.monotonic()
    returncode: int | None = None
    timed_out = False
    stdout: str | bytes | None = None
    stderr: str | bytes | None = None
    capture = log_path_dir is not None

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        **SUBPROCESS_TEXT_KWARGS,
        **_SESSION_KWARGS,
    )
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        stdout, stderr = proc.communicate()
        timed_out = True
    except KeyboardInterrupt:
        _kill_process_group(proc)
        proc.wait()
        raise

    log_file = _write_log(log_path_dir, iteration, stdout, stderr)
    if log_path_dir:
        _echo_output(stdout, stderr)

    return AgentResult(
        returncode=returncode,
        elapsed=time.monotonic() - start,
        log_file=log_file,
        timed_out=timed_out,
    )


def execute_agent(
    cmd: list[str],
    prompt: str,
    *,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_activity: Callable[[dict[str, Any]], None] | None = None,
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
