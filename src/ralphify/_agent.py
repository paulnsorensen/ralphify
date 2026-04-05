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
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Any

from ralphify._events import OutputStream
from ralphify._output import (
    IS_WINDOWS,
    SESSION_KWARGS,
    SUBPROCESS_TEXT_KWARGS,
    ProcessResult,
    collect_output,
    ensure_str,
)

# Typed constants for the OutputStream literal so the type checker enforces
# that only "stdout" / "stderr" ever reach ``on_output_line``.
_STDOUT: OutputStream = "stdout"
_STDERR: OutputStream = "stderr"

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

# Seconds to wait for reader threads to drain during cleanup.
_THREAD_JOIN_TIMEOUT = 1.0


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


def _ensure_process_dead(proc: subprocess.Popen[Any]) -> None:
    """Kill the agent process if still running, then wait for exit.

    Safe to call multiple times — no-ops when the process has already
    exited.  Used in ``finally`` and exception-handler blocks to
    guarantee the child is reaped before we move on.
    """
    if proc.poll() is None:
        _kill_process_group(proc)
    proc.wait()


def _deliver_prompt(proc: subprocess.Popen[Any], prompt: str) -> None:
    """Write *prompt* to the agent's stdin and close the pipe.

    Silently handles ``BrokenPipeError`` — the agent may exit before
    consuming the full prompt, which is a normal (if uncommon) lifecycle
    event.
    """
    assert proc.stdin is not None
    try:
        proc.stdin.write(prompt)
    except BrokenPipeError:
        pass
    finally:
        try:
            proc.stdin.close()
        except BrokenPipeError:
            pass


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
    log_file = (
        log_path_dir / f"{iteration:0{_LOG_ITERATION_PAD_WIDTH}d}_{timestamp}.log"
    )
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
    on_output_line: Callable[[str, OutputStream], None] | None = None,
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
        if on_output_line is not None:
            on_output_line(line.rstrip("\r\n"), _STDOUT)

        stripped = line.strip()
        if stripped:
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, dict):
                if parsed.get("type") == _RESULT_EVENT_TYPE and isinstance(
                    parsed.get(_RESULT_FIELD), str
                ):
                    result_text = parsed[_RESULT_FIELD]
                if on_activity is not None:
                    on_activity(parsed)

        if deadline is not None and time.monotonic() > deadline:
            return _StreamResult(
                stdout_lines=stdout_lines, result_text=result_text, timed_out=True
            )

    return _StreamResult(
        stdout_lines=stdout_lines, result_text=result_text, timed_out=False
    )


def _run_agent_streaming(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_activity: Callable[[dict[str, Any]], None] | None = None,
    on_output_line: Callable[[str, OutputStream], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess with line-by-line streaming of JSON output.

    Used for agents that support ``--output-format stream-json`` (e.g. Claude
    Code).  Stream processing is delegated to :func:`_read_agent_stream`;
    this function owns the subprocess lifecycle (spawn, stdin delivery,
    timeout kill, and cleanup via ``try/finally``).

    stderr is drained concurrently on a background reader thread so large
    stderr volume can't deadlock the child on a full OS pipe buffer while
    the main thread is reading stdout.
    """
    stream_cmd = cmd + [_OUTPUT_FORMAT_FLAG, _STREAM_FORMAT, _VERBOSE_FLAG]
    start = time.monotonic()
    deadline = (start + timeout) if timeout is not None else None

    writer_thread: threading.Thread | None = None
    stderr_lines: list[str] = []
    stderr_thread: threading.Thread | None = None

    proc = subprocess.Popen(
        stream_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **SUBPROCESS_TEXT_KWARGS,
        **SESSION_KWARGS,
    )
    try:
        # Popen with PIPE guarantees non-None streams; guard explicitly
        # so the type checker narrows and -O mode cannot skip the check.
        if proc.stdin is None or proc.stdout is None or proc.stderr is None:
            raise RuntimeError("subprocess.Popen failed to create PIPE streams")

        # Start the stderr pump BEFORE writing stdin so large prompts can't
        # deadlock against an agent that writes substantial diagnostics to
        # stderr while still reading its stdin.
        stderr_thread = _start_pump_thread(
            proc.stderr, stderr_lines, _STDERR, on_output_line
        )

        # Deliver the prompt on a background thread so that a blocked write
        # (child not reading stdin, pipe buffer full) cannot prevent
        # proc.wait / deadline checks from firing.  Killing the process
        # group unblocks the write with BrokenPipeError, which
        # _deliver_prompt already swallows.
        writer_thread = threading.Thread(
            target=_deliver_prompt, args=(proc, prompt), daemon=True
        )
        writer_thread.start()

        stream = _read_agent_stream(proc.stdout, deadline, on_activity, on_output_line)

        if stream.timed_out:
            _kill_process_group(proc)
        proc.wait()
    finally:
        _ensure_process_dead(proc)
        _drain_readers(stderr_thread, writer_thread)

    log_file = _write_log(
        log_path_dir, iteration, "".join(stream.stdout_lines), "".join(stderr_lines)
    )

    return AgentResult(
        returncode=None if stream.timed_out else proc.returncode,
        elapsed=time.monotonic() - start,
        log_file=log_file,
        result_text=stream.result_text,
        timed_out=stream.timed_out,
    )


def _pump_stream(
    stream: IO[str],
    buffer: list[str] | None,
    stream_name: OutputStream,
    on_output_line: Callable[[str, OutputStream], None] | None,
) -> None:
    """Read *stream* line by line, optionally appending to *buffer* and forwarding to the callback.

    When *buffer* is ``None`` lines are forwarded to the callback without
    accumulating — this avoids unbounded memory growth when no log file
    will be written.

    Runs on a background thread so stdout and stderr can be drained
    concurrently without deadlocking the child subprocess.

    Exception handling:

    - **Callback exceptions** are caught per-line so that a raising
      callback never kills the drain loop.  The line is still buffered.
    - **``ValueError`` / ``OSError``** from ``readline`` (e.g. the pipe
      was closed concurrently) cause a clean exit so ``join()`` returns.
    """
    try:
        for line in iter(stream.readline, ""):
            if buffer is not None:
                buffer.append(line)
            if on_output_line is not None:
                try:
                    on_output_line(line.rstrip("\r\n"), stream_name)
                except Exception:
                    # Callback is best-effort; draining must not stop.
                    pass
    except (ValueError, OSError):
        # Pipe closed concurrently — exit cleanly so join() returns.
        pass


def _start_pump_thread(
    stream: IO[str],
    buffer: list[str] | None,
    stream_name: OutputStream,
    on_output_line: Callable[[str, OutputStream], None] | None,
) -> threading.Thread:
    """Create and start a daemon thread that drains *stream*.

    When *buffer* is not ``None``, lines are accumulated for later log
    writing.  When ``None``, lines are only forwarded to the callback.

    A thin wrapper around :func:`_pump_stream` that eliminates the repeated
    ``Thread(…, daemon=True) / .start()`` boilerplate in the streaming and
    blocking execution paths.
    """
    thread = threading.Thread(
        target=_pump_stream,
        args=(stream, buffer, stream_name, on_output_line),
        daemon=True,
    )
    thread.start()
    return thread


def _drain_readers(
    *threads: threading.Thread | None,
    timeout: float = _THREAD_JOIN_TIMEOUT,
) -> None:
    """Join reader threads, skipping any that are ``None``.

    Used in ``finally`` and ``except`` blocks to ensure background pump
    threads finish draining before the caller continues.
    """
    for thread in threads:
        if thread is not None:
            thread.join(timeout=timeout)


def _run_agent_blocking(
    cmd: list[str],
    prompt: str,
    timeout: float | None,
    log_path_dir: Path | None,
    iteration: int,
    on_output_line: Callable[[str, OutputStream], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess and return the result.

    Uses a three-way capture strategy:

    1. **Inherit** (``on_output_line is None and log_path_dir is None``) —
       stdout/stderr are not piped; the child writes directly to the
       parent's file descriptors.  No reader threads, no buffering.
    2. **Callback only** (``on_output_line`` set, no log dir) — reader
       threads forward lines to the callback without accumulating them,
       avoiding unbounded memory growth.
    3. **Log capture** (``log_path_dir`` set) — reader threads accumulate
       lines into lists for log writing; lines are also forwarded to the
       callback if provided.

    The subprocess is started in its own process group so that on
    ``KeyboardInterrupt`` or timeout the entire child tree can be killed
    via :func:`_kill_process_group`.

    Returns ``returncode=None`` when the process times out.
    Raises ``FileNotFoundError`` if the command binary does not exist.
    """
    start = time.monotonic()
    capture = log_path_dir is not None or on_output_line is not None

    if not capture:
        # ── Inherit path ─────────────────────────────────────────
        # No subscriber needs the bytes — let the child write directly
        # to the terminal.  Avoids silent output loss when the user
        # pipes ralph's output (e.g. ``ralph run | cat``).
        returncode: int | None = None
        timed_out = False
        writer_thread: threading.Thread | None = None

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            **SUBPROCESS_TEXT_KWARGS,
            **SESSION_KWARGS,
        )
        try:
            if proc.stdin is None:
                raise RuntimeError("subprocess.Popen failed to create PIPE stdin")

            writer_thread = threading.Thread(
                target=_deliver_prompt, args=(proc, prompt), daemon=True
            )
            writer_thread.start()

            try:
                returncode = proc.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                _ensure_process_dead(proc)
                timed_out = True
        except KeyboardInterrupt:
            _ensure_process_dead(proc)
            raise
        finally:
            _ensure_process_dead(proc)
            _drain_readers(writer_thread)

        return AgentResult(
            returncode=None if timed_out else returncode,
            elapsed=time.monotonic() - start,
            log_file=None,
            timed_out=timed_out,
        )

    # ── Capture path ─────────────────────────────────────────────
    # Reader threads drain stdout/stderr concurrently.  Lines are only
    # accumulated into buffers when a log file will be written; otherwise
    # the callback alone observes them, avoiding unbounded memory growth.
    returncode = None
    timed_out = False
    writer_thread: threading.Thread | None = None
    stdout_lines: list[str] | None = [] if log_path_dir is not None else None
    stderr_lines: list[str] | None = [] if log_path_dir is not None else None
    stdout_thread: threading.Thread | None = None
    stderr_thread: threading.Thread | None = None

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        **SUBPROCESS_TEXT_KWARGS,
        **SESSION_KWARGS,
    )
    try:
        if proc.stdin is None or proc.stdout is None or proc.stderr is None:
            raise RuntimeError("subprocess.Popen failed to create PIPE streams")

        stdout_thread = _start_pump_thread(
            proc.stdout, stdout_lines, _STDOUT, on_output_line
        )
        stderr_thread = _start_pump_thread(
            proc.stderr, stderr_lines, _STDERR, on_output_line
        )

        writer_thread = threading.Thread(
            target=_deliver_prompt, args=(proc, prompt), daemon=True
        )
        writer_thread.start()

        try:
            returncode = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _ensure_process_dead(proc)
            timed_out = True
    except KeyboardInterrupt:
        _ensure_process_dead(proc)
        raise
    finally:
        _ensure_process_dead(proc)
        _drain_readers(stdout_thread, stderr_thread, writer_thread)

    stdout = "".join(stdout_lines) if stdout_lines is not None else None
    stderr = "".join(stderr_lines) if stderr_lines is not None else None

    log_file = _write_log(log_path_dir, iteration, stdout, stderr)
    # When logging is enabled, output is diverted into the log file; echo it
    # so the user still sees what ran.  When logging is disabled, live peek
    # (if enabled) has already shown the lines as they arrived.
    if log_path_dir is not None:
        _echo_output(stdout, stderr)

    return AgentResult(
        returncode=None if timed_out else returncode,
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
    on_output_line: Callable[[str, OutputStream], None] | None = None,
) -> AgentResult:
    """Run the agent subprocess, auto-selecting streaming or blocking mode.

    Uses streaming mode for agents that support ``--output-format stream-json``
    (e.g. Claude Code); all other agents use the blocking path that drains
    stdout and stderr via reader threads.  The *on_activity* callback is
    only invoked in streaming mode; *on_output_line* fires for both modes
    as raw lines arrive.

    This is the single entry point the engine should use — callers don't need
    to know which execution mode is selected.
    """
    if _supports_stream_json(cmd):
        return _run_agent_streaming(
            cmd,
            prompt,
            timeout,
            log_path_dir,
            iteration,
            on_activity=on_activity,
            on_output_line=on_output_line,
        )
    return _run_agent_blocking(
        cmd,
        prompt,
        timeout,
        log_path_dir,
        iteration,
        on_output_line=on_output_line,
    )
