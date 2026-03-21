"""CLI commands for ralphify — run and scaffold ralphs.

The ``run`` command delegates to the engine module for the core autonomous
loop.  Terminal rendering of events is handled by
:class:`~ralphify._console_emitter.ConsoleEmitter`.
"""

from __future__ import annotations

import math
import os
import re
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any, NoReturn

import typer
from rich.console import Console

from ralphify import __version__
from ralphify._console_emitter import ConsoleEmitter
from ralphify._frontmatter import (
    CMD_FIELD_NAME,
    CMD_FIELD_RUN,
    CMD_FIELD_TIMEOUT,
    FIELD_AGENT,
    FIELD_ARGS,
    FIELD_COMMANDS,
    FIELD_CREDIT,
    RALPH_MARKER,
    parse_frontmatter,
)
from ralphify._run_types import Command, DEFAULT_COMMAND_TIMEOUT, RunConfig, RunState, generate_run_id
from ralphify.engine import run_loop

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_console = Console(highlight=False)

app = typer.Typer()


def _exit_error(msg: str) -> NoReturn:
    """Print an error in red and exit with code 1."""
    _console.print(f"[red]{msg}[/red]")
    raise typer.Exit(1)


BANNER = [
    ("██████╗░░█████╗░██╗░░░░░██████╗░██╗░░██╗██╗███████╗██╗░░░██╗", "#8B6CF0"),
    ("██╔══██╗██╔══██╗██║░░░░░██╔══██╗██║░░██║██║██╔════╝╚██╗░██╔╝", "#A78BF5"),
    ("██████╔╝███████║██║░░░░░██████╔╝███████║██║█████╗░░░╚████╔╝░", "#D4A0E0"),
    ("██╔══██╗██╔══██║██║░░░░░██╔═══╝░██╔══██║██║██╔══╝░░░░╚██╔╝░░", "#E8956B"),
    ("██║░░██║██║░░██║███████╗██║░░░░░██║░░██║██║██║░░░░░░░░██║░░░", "#E87B4A"),
    ("╚═╝░░╚═╝╚═╝░░╚═╝╚══════╝╚═╝░░░░░╚═╝░░╚═╝╚═╝╚═╝░░░░░░░░╚═╝░░░", "#E06030"),
]

TAGLINE = "Stop stressing over not having an agent running. Ralph is always running"

_INIT_TEMPLATE = """\
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: git-log
    run: git log --oneline -5
args:
  - focus
---

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Recent changes

{{ commands.git-log }}

## Focus

{{ args.focus }}

## Task

<!-- Replace this section with your task description -->

- Implement one thing per iteration
- Run tests and fix failures before committing
- Commit with a descriptive message and push
"""


def _print_banner() -> None:
    width = shutil.get_terminal_size().columns
    art_width = max(len(line) for line, _ in BANNER)
    pad = max(0, (width - art_width) // 2)
    prefix = " " * pad

    _console.print()
    for line, color in BANNER:
        _console.print(f"[bold {color}]{prefix}{line}[/bold {color}]")
    _console.print()
    _console.print(f"[italic #A78BF5]{TAGLINE:^{width}}[/italic #A78BF5]")
    _console.print()
    help_text = "Run 'ralph --help' for usage information"
    _console.print(f"[dim]{help_text:^{width}}[/dim]")
    star_text = "⭐ Star us on GitHub: https://github.com/computerlovetech/ralphify"
    _console.print(f"[dim]{star_text:^{width}}[/dim]")
    _console.print()


def _version_callback(value: bool) -> None:
    if value:
        _console.print(f"ralphify {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit.", callback=_version_callback, is_eager=True),
) -> None:
    """Stop stressing over not having an agent running. Ralph is always running."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        _console.print(ctx.get_help())
        raise typer.Exit()


@app.command()
def new(
    name: str | None = typer.Argument(None, help="Name for the new ralph. If omitted, the agent will help you choose."),
) -> None:
    """Create a new ralph with AI-guided setup."""
    from ralphify._skills import build_agent_command, detect_agent, install_skill

    try:
        agent = detect_agent()
    except RuntimeError as exc:
        _exit_error(str(exc))

    try:
        install_skill("new-ralph", agent.name)
    except RuntimeError as exc:
        _exit_error(str(exc))

    cmd = build_agent_command(agent.name, "new-ralph", name)
    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        _exit_error(f"Agent command '{cmd[0]}' not found on PATH.")


@app.command()
def init(
    name: str | None = typer.Argument(None, help="Directory name. If omitted, creates RALPH.md in the current directory."),
) -> None:
    """Scaffold a new ralph with a ready-to-customize template."""
    if name:
        target_dir = Path.cwd() / name
        target_dir.mkdir(exist_ok=True)
    else:
        target_dir = Path.cwd()

    ralph_file = target_dir / RALPH_MARKER
    if ralph_file.exists():
        _exit_error(f"{RALPH_MARKER} already exists at '{ralph_file}'.")

    ralph_file.write_text(_INIT_TEMPLATE, encoding="utf-8")
    rel = ralph_file.relative_to(Path.cwd())
    _console.print(f"[green]Created[/green] {rel}")
    _console.print(f"[dim]Edit the file, then run:[/dim] ralph run {name or '.'}")


def _parse_user_args(
    raw_args: list[str],
    declared_names: list[str] | None,
) -> dict[str, str]:
    """Parse extra CLI args into a dict of user arguments.

    Supports ``--name value`` (named) and positional args mapped to
    *declared_names* from frontmatter ``args: [...]``.
    """
    result: dict[str, str] = {}
    positional_index = 0
    it = iter(raw_args)
    for token in it:
        if token.startswith("--"):
            name = token[2:]
            try:
                value = next(it)
            except StopIteration:
                raise typer.BadParameter(f"Flag '--{name}' requires a value.") from None
            result[name] = value
        else:
            if not declared_names:
                raise typer.BadParameter(
                    f"Positional argument '{token}' requires args declared in {RALPH_MARKER} frontmatter. "
                    f"Use --name value syntax or add 'args: [...]' to your {RALPH_MARKER}."
                )
            if positional_index >= len(declared_names):
                raise typer.BadParameter(
                    f"Too many positional arguments. Expected at most {len(declared_names)} "
                    f"({', '.join(declared_names)})."
                )
            result[declared_names[positional_index]] = token
            positional_index += 1
    return result


def _parse_commands(raw_commands: list[dict[str, Any]]) -> list[Command]:
    """Validate and parse raw command dicts from frontmatter into Command objects."""
    commands: list[Command] = []
    seen_names: set[str] = set()
    for cmd_def in raw_commands:
        if not isinstance(cmd_def, dict) or CMD_FIELD_NAME not in cmd_def or CMD_FIELD_RUN not in cmd_def:
            _exit_error(f"Each command must have '{CMD_FIELD_NAME}' and '{CMD_FIELD_RUN}' fields.")
        for key in (CMD_FIELD_NAME, CMD_FIELD_RUN):
            if not isinstance(cmd_def[key], str) or not cmd_def[key].strip():
                _exit_error(f"Command '{key}' must be a non-empty string.")
        cmd_name = cmd_def[CMD_FIELD_NAME]
        cmd_run = cmd_def[CMD_FIELD_RUN]
        if not re.fullmatch(r"[a-zA-Z0-9_-]+", cmd_name):
            _exit_error(
                f"Command name '{cmd_name}' contains invalid characters. "
                f"Names may only contain letters, digits, hyphens, and underscores."
            )
        if cmd_name in seen_names:
            _exit_error(f"Duplicate command name '{cmd_name}'.")
        seen_names.add(cmd_name)
        timeout = cmd_def.get(CMD_FIELD_TIMEOUT, DEFAULT_COMMAND_TIMEOUT)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            _exit_error(
                f"Command '{cmd_name}' has invalid timeout: {timeout!r}. "
                f"Must be a positive number."
            )
        commands.append(Command(
            name=cmd_name,
            run=cmd_run,
            timeout=timeout,
        ))
    return commands


def _resolve_ralph_paths(ralph_path: str) -> tuple[Path, Path]:
    """Resolve the ralph directory and RALPH.md file from a user-provided path.

    Accepts a directory containing RALPH.md or a direct path to RALPH.md.
    Returns ``(ralph_dir, ralph_file)``.  Exits with an error message when
    the path is invalid or RALPH.md is not found.
    """
    path = Path(ralph_path)
    if path.is_dir():
        ralph_dir = path
        ralph_file = path / RALPH_MARKER
    elif path.is_file() and path.name == RALPH_MARKER:
        ralph_dir = path.parent
        ralph_file = path
    else:
        _exit_error(f"'{ralph_path}' is not a directory or {RALPH_MARKER} file.")

    if not ralph_file.exists():
        _exit_error(f"{RALPH_MARKER} not found at '{ralph_file}'.")

    return ralph_dir, ralph_file


def _build_run_config(
    ralph_path: str,
    max_iterations: int | None,
    stop_on_error: bool,
    delay: float,
    log_dir: str | None,
    timeout: float | None,
    extra_args: list[str] | None = None,
) -> RunConfig:
    """Read RALPH.md from the given path, validate, and build a RunConfig."""
    ralph_dir, ralph_file = _resolve_ralph_paths(ralph_path)

    ralph_text = ralph_file.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(ralph_text)

    # Validate required agent field
    agent = fm.get(FIELD_AGENT)
    if not isinstance(agent, str) or not agent.strip():
        _exit_error(f"Missing or empty '{FIELD_AGENT}' field in {RALPH_MARKER} frontmatter.")

    # Validate agent command exists
    try:
        agent_binary = shlex.split(agent)[0]
    except ValueError as exc:
        _exit_error(f"Malformed '{FIELD_AGENT}' field in {RALPH_MARKER} frontmatter: {exc}")
    if not shutil.which(agent_binary):
        _exit_error(f"Agent command '{agent_binary}' not found on PATH.")

    # Parse commands from frontmatter
    raw_commands = fm.get(FIELD_COMMANDS, [])
    if not isinstance(raw_commands, list):
        _exit_error(f"'{FIELD_COMMANDS}' must be a list of {{name, run}} mappings.")
    commands = _parse_commands(raw_commands)

    # Parse user args
    declared_names = fm.get(FIELD_ARGS)
    if declared_names is not None and not isinstance(declared_names, list):
        _exit_error(f"'{FIELD_ARGS}' must be a list of strings.")
    if declared_names is not None and not all(isinstance(a, str) for a in declared_names):
        _exit_error(f"'{FIELD_ARGS}' items must be strings, got non-string value.")
    ralph_args: dict[str, str] = {}
    if extra_args:
        ralph_args = _parse_user_args(extra_args, declared_names)

    # Parse credit field (default: True)
    credit = fm.get(FIELD_CREDIT, True)
    if not isinstance(credit, bool):
        _exit_error(f"'{FIELD_CREDIT}' must be true or false, got {credit!r}.")

    # Validate numeric options
    if max_iterations is not None and max_iterations < 1:
        _exit_error(f"'-n' must be a positive integer, got {max_iterations}.")
    if not math.isfinite(delay) or delay < 0:
        _exit_error(f"'--delay' must be non-negative, got {delay}.")
    if timeout is not None and (not math.isfinite(timeout) or timeout <= 0):
        _exit_error(f"'--timeout' must be a positive number, got {timeout}.")

    return RunConfig(
        agent=agent,
        ralph_dir=ralph_dir.resolve(),
        ralph_file=ralph_file.resolve(),
        commands=commands,
        args=ralph_args,
        max_iterations=max_iterations,
        delay=delay,
        timeout=timeout,
        stop_on_error=stop_on_error,
        log_dir=Path(log_dir) if log_dir else None,
        project_root=Path.cwd(),
        credit=credit,
    )


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Path to the ralph directory (containing RALPH.md)."),
    n: int | None = typer.Option(None, "-n", help="Max number of iterations. Infinite if not set."),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", "-s", help="Stop if the agent exits non-zero or times out."),
    delay: float = typer.Option(0, "--delay", "-d", help="Seconds to wait between iterations."),
    log_dir: str | None = typer.Option(None, "--log-dir", "-l", help="Save iteration output to log files in this directory."),
    timeout: float | None = typer.Option(None, "--timeout", "-t", help="Max seconds per iteration. Kill agent if exceeded."),
) -> None:
    """Run the autonomous coding loop.

    Each iteration: run commands, assemble prompt with command output,
    pipe to agent, repeat until *n* iterations or Ctrl+C.

    Extra flags (--name value) and positional args after the path are
    passed as user arguments.  Use {{ args.name }} placeholders in
    RALPH.md to reference them.
    """
    extra = list(ctx.args)

    config = _build_run_config(
        path, n, stop_on_error, delay, log_dir, timeout,
        extra_args=extra or None,
    )

    if log_dir:
        _console.print(f"[dim]Logging output to {log_dir}/[/dim]")

    state = RunState(run_id=generate_run_id())
    emitter = ConsoleEmitter(_console)

    run_loop(config, state, emitter)
