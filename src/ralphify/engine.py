"""Run loop with structured event emission.

The core ``run_loop`` function is the autonomous agent loop.  It accepts
a ``RunConfig``, ``RunState``, and ``EventEmitter``, making it reusable
from both CLI and UI contexts.

The v2 loop is simplified: run commands → assemble prompt → pipe to agent → repeat.
"""

from __future__ import annotations

import shlex
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ralphify._agent import execute_agent
from ralphify._events import Event, EventEmitter, EventType, NullEmitter
from ralphify._frontmatter import parse_frontmatter
from ralphify._output import format_duration
from ralphify._run_types import (
    Command,
    RunConfig,
    RunState,
    RunStatus,
)
from ralphify._runner import run_command
from ralphify.resolver import resolve_args, resolve_commands


_PAUSE_POLL_INTERVAL = 0.25  # seconds between pause/resume checks
_RELATIVE_CMD_PREFIX = "./"  # commands starting with this run from the ralph directory


class _BoundEmitter:
    """Wraps an EventEmitter with a fixed run_id for concise emission."""

    def __init__(self, emitter: EventEmitter, run_id: str) -> None:
        self._emitter = emitter
        self._run_id = run_id

    def __call__(
        self, event_type: EventType, data: dict[str, Any] | None = None,
    ) -> None:
        self._emitter.emit(Event(
            type=event_type, run_id=self._run_id, data=data if data is not None else {},
        ))


def _wait_for_resume(state: RunState, emit: _BoundEmitter) -> bool:
    """Block until the run is resumed or a stop is requested."""
    emit(EventType.RUN_PAUSED)
    while not state.wait_for_unpause(timeout=_PAUSE_POLL_INTERVAL):
        if state.stop_requested:
            break
    if state.stop_requested:
        state.status = RunStatus.STOPPED
        return False
    emit(EventType.RUN_RESUMED)
    return True


def _handle_control_signals(state: RunState, emit: _BoundEmitter) -> bool:
    """Handle stop and pause requests at the top of each iteration."""
    if state.stop_requested:
        state.status = RunStatus.STOPPED
        return False
    if state.paused:
        if not _wait_for_resume(state, emit):
            return False
    return True


def _run_commands(
    commands: list[Command],
    ralph_dir: Path,
    project_root: Path,
    user_args: dict[str, str],
) -> dict[str, str]:
    """Execute all commands and return a dict of name→output.

    Commands with paths starting with ``./`` run relative to the ralph
    directory.  Other commands run from the project root.
    """
    results: dict[str, str] = {}
    for cmd in commands:
        run_str = resolve_args(cmd.run, user_args)
        # Determine working directory: if the command starts with ./ it's
        # relative to the ralph directory, otherwise use project root.
        if run_str.startswith(_RELATIVE_CMD_PREFIX):
            cwd = ralph_dir
        else:
            cwd = project_root
        result = run_command(
            script=None,
            command=run_str,
            cwd=cwd,
            timeout=cmd.timeout,
        )
        results[cmd.name] = result.output
    return results


def _assemble_prompt(
    config: RunConfig,
    command_outputs: dict[str, str],
) -> str:
    """Build the full prompt for one iteration.

    Reads the RALPH.md body, resolves user args and command output
    placeholders.
    """
    raw = config.ralph_file.read_text(encoding="utf-8")
    _, prompt = parse_frontmatter(raw)
    prompt = resolve_args(prompt, config.args)
    prompt = resolve_commands(prompt, command_outputs)
    return prompt


def _run_agent_phase(
    prompt: str,
    config: RunConfig,
    state: RunState,
    log_path_dir: Path | None,
    emit: _BoundEmitter,
) -> bool:
    """Run the agent subprocess, update state counters, and emit the result event.

    Returns ``True`` when the agent exited successfully (code 0, no timeout).
    """
    try:
        cmd = shlex.split(config.agent)
    except ValueError as exc:
        raise ValueError(
            f"Invalid agent command syntax: {config.agent!r}. "
            f"Check the 'agent' field in your RALPH.md frontmatter."
        ) from exc

    try:
        agent = execute_agent(
            cmd, prompt, config.timeout, log_path_dir, state.iteration,
            on_activity=lambda data: emit(EventType.AGENT_ACTIVITY, {"raw": data, "iteration": state.iteration}),
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Agent command not found: {config.agent!r}. "
            f"Check the 'agent' field in your RALPH.md frontmatter."
        ) from exc

    duration = format_duration(agent.elapsed)

    if agent.timed_out:
        state.mark_timed_out()
        event_type = EventType.ITERATION_TIMED_OUT
        state_detail = f"timed out after {duration}"
    elif agent.success:
        state.mark_completed()
        event_type = EventType.ITERATION_COMPLETED
        state_detail = f"completed ({duration})"
    else:
        state.mark_failed()
        event_type = EventType.ITERATION_FAILED
        state_detail = f"failed with exit code {agent.returncode} ({duration})"

    emit(event_type, {
        "iteration": state.iteration,
        "returncode": agent.returncode,
        "duration": agent.elapsed,
        "duration_formatted": duration,
        "detail": state_detail,
        "log_file": str(agent.log_file) if agent.log_file else None,
        "result_text": agent.result_text,
    })
    return agent.success


def _run_iteration(
    config: RunConfig,
    state: RunState,
    log_path_dir: Path | None,
    emit: _BoundEmitter,
) -> bool:
    """Execute one iteration of the agent loop.

    Returns ``True`` if the loop should continue, ``False`` when
    ``--stop-on-error`` triggers.
    """
    iteration = state.iteration

    emit(EventType.ITERATION_STARTED, {"iteration": iteration})

    # Run commands and collect outputs for placeholder resolution
    command_outputs: dict[str, str] = {}
    if config.commands:
        emit(EventType.COMMANDS_STARTED, {"iteration": iteration, "count": len(config.commands)})
        command_outputs = _run_commands(
            config.commands, config.ralph_dir, config.project_root, config.args,
        )
        emit(EventType.COMMANDS_COMPLETED, {
            "iteration": iteration,
            "count": len(command_outputs),
        })

    # Assemble prompt
    prompt = _assemble_prompt(config, command_outputs)
    emit(EventType.PROMPT_ASSEMBLED, {"iteration": iteration, "prompt_length": len(prompt)})

    # Run agent
    agent_succeeded = _run_agent_phase(prompt, config, state, log_path_dir, emit)

    if not agent_succeeded and config.stop_on_error:
        emit(EventType.LOG_MESSAGE, {"message": "Stopping due to --stop-on-error.", "level": "error"})
        return False

    return True


def _delay_if_needed(config: RunConfig, state: RunState, emit: _BoundEmitter) -> None:
    """Sleep between iterations when a delay is configured."""
    if config.delay > 0 and (
        config.max_iterations is None or state.iteration < config.max_iterations
    ):
        emit(EventType.LOG_MESSAGE, {"message": f"Waiting {config.delay}s...", "level": "info"})
        time.sleep(config.delay)


def run_loop(
    config: RunConfig,
    state: RunState,
    emitter: EventEmitter | None = None,
) -> None:
    """Execute the autonomous agent loop.

    Each iteration: run commands → assemble prompt → pipe to agent → repeat.
    """
    if emitter is None:
        emitter = NullEmitter()

    emit = _BoundEmitter(emitter, state.run_id)
    state.status = RunStatus.RUNNING
    state.started_at = datetime.now(timezone.utc)

    log_path_dir: Path | None = None
    if config.log_dir:
        log_path_dir = Path(config.log_dir)
        log_path_dir.mkdir(parents=True, exist_ok=True)

    emit(EventType.RUN_STARTED, {
        "commands": len(config.commands),
        "max_iterations": config.max_iterations,
        "timeout": config.timeout,
        "delay": config.delay,
    })

    try:
        while True:
            if not _handle_control_signals(state, emit):
                break

            state.iteration += 1
            if config.max_iterations is not None and state.iteration > config.max_iterations:
                break

            should_continue = _run_iteration(config, state, log_path_dir, emit)
            if not should_continue:
                break

            _delay_if_needed(config, state, emit)

    except KeyboardInterrupt:
        state.status = RunStatus.STOPPED
    except Exception as exc:
        state.status = RunStatus.FAILED
        tb = traceback.format_exc()
        emit(EventType.LOG_MESSAGE, {
            "message": f"Run crashed: {exc}",
            "level": "error",
            "traceback": tb,
        })

    if state.status == RunStatus.RUNNING:
        state.status = RunStatus.COMPLETED

    reason = state.status.reason
    emit(EventType.RUN_STOPPED, {
        "reason": reason,
        "total": state.total,
        "completed": state.completed,
        "failed": state.failed,
        "timed_out": state.timed_out,
    })
