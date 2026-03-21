"""CLI commands for ralphify — run and scaffold ralphs.

The ``run`` command delegates to the engine module for the core autonomous
loop.  Terminal rendering of events is handled by
:class:`~ralphify._console_emitter.ConsoleEmitter`.
"""

import os
import shlex
import shutil
import sys
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console

from ralphify import __version__
from ralphify._console_emitter import ConsoleEmitter
from ralphify._frontmatter import RALPH_MARKER, parse_frontmatter
from ralphify._run_types import Command, DEFAULT_COMMAND_TIMEOUT, RunConfig, RunState, generate_run_id
from ralphify.engine import run_loop

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

_console = Console(highlight=False)
rprint = _console.print

app = typer.Typer()


def _exit_error(msg: str) -> NoReturn:
    """Print an error in red and exit with code 1."""
    rprint(f"[red]{msg}[/red]")
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


def _print_banner() -> None:
    width = shutil.get_terminal_size().columns
    art_width = max(len(line) for line, _ in BANNER)
    pad = max(0, (width - art_width) // 2)
    prefix = " " * pad

    rprint()
    for line, color in BANNER:
        rprint(f"[bold {color}]{prefix}{line}[/bold {color}]")
    rprint()
    rprint(f"[italic #A78BF5]{TAGLINE:^{width}}[/italic #A78BF5]")
    rprint()
    help_text = "Run 'ralph --help' for usage information"
    rprint(f"[dim]{help_text:^{width}}[/dim]")
    star_text = "⭐ Star us on GitHub: https://github.com/computerlovetech/ralphify"
    rprint(f"[dim]{star_text:^{width}}[/dim]")
    rprint()


def _version_callback(value: bool) -> None:
    if value:
        rprint(f"ralphify {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version and exit.", callback=_version_callback, is_eager=True),
) -> None:
    """Stop stressing over not having an agent running. Ralph is always running."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        rprint(ctx.get_help())
        raise typer.Exit()


@app.command()
def new(
    name: str | None = typer.Argument(None, help="Name for the new ralph. If omitted, the agent will help you choose."),
) -> None:
    """Create a new ralph with AI-guided setup."""
    from ralphify._skills import build_agent_command, detect_agent, install_skill

    try:
        agent = detect_agent()
    except RuntimeError as e:
        _exit_error(str(e))

    try:
        install_skill("new-ralph", agent.name)
    except RuntimeError as e:
        _exit_error(str(e))

    cmd = build_agent_command(agent.name, "new-ralph", name)
    os.execvp(cmd[0], cmd)


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
    i = 0
    while i < len(raw_args):
        token = raw_args[i]
        if token.startswith("--"):
            name = token[2:]
            if i + 1 >= len(raw_args):
                raise typer.BadParameter(f"Flag '--{name}' requires a value.")
            result[name] = raw_args[i + 1]
            i += 2
        else:
            if not declared_names:
                raise typer.BadParameter(
                    f"Positional argument '{token}' requires args declared in RALPH.md frontmatter. "
                    f"Use --name value syntax or add 'args: [...]' to your RALPH.md."
                )
            if positional_index >= len(declared_names):
                raise typer.BadParameter(
                    f"Too many positional arguments. Expected at most {len(declared_names)} "
                    f"({', '.join(declared_names)})."
                )
            result[declared_names[positional_index]] = token
            positional_index += 1
            i += 1
    return result


def _parse_commands(raw_commands: list) -> list[Command]:
    """Validate and parse raw command dicts from frontmatter into Command objects."""
    commands: list[Command] = []
    seen_names: set[str] = set()
    for cmd_def in raw_commands:
        if not isinstance(cmd_def, dict) or "name" not in cmd_def or "run" not in cmd_def:
            _exit_error("Each command must have 'name' and 'run' fields.")
        for field in ("name", "run"):
            if not cmd_def[field] or not isinstance(cmd_def[field], str):
                _exit_error(f"Command '{field}' must be a non-empty string.")
        cmd_name = cmd_def["name"]
        if cmd_name in seen_names:
            _exit_error(f"Duplicate command name '{cmd_name}'.")
        seen_names.add(cmd_name)
        commands.append(Command(
            name=cmd_def["name"],
            run=cmd_def["run"],
            timeout=cmd_def.get("timeout", DEFAULT_COMMAND_TIMEOUT),
        ))
    return commands


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
    path = Path(ralph_path)

    # Resolve ralph directory and RALPH.md file
    if path.is_dir():
        ralph_dir = path
        ralph_file = path / RALPH_MARKER
    elif path.is_file() and path.name == RALPH_MARKER:
        ralph_dir = path.parent
        ralph_file = path
    else:
        _exit_error(f"'{ralph_path}' is not a directory or RALPH.md file.")

    if not ralph_file.exists():
        _exit_error(f"RALPH.md not found at '{ralph_file}'.")

    ralph_text = ralph_file.read_text()
    fm, _ = parse_frontmatter(ralph_text)

    # Validate required agent field
    agent = fm.get("agent")
    if not agent:
        _exit_error("Missing 'agent' field in RALPH.md frontmatter.")

    # Validate agent command exists
    try:
        agent_binary = shlex.split(agent)[0]
    except ValueError as exc:
        _exit_error(f"Malformed 'agent' field in RALPH.md frontmatter: {exc}")
    if not shutil.which(agent_binary):
        _exit_error(f"Agent command '{agent_binary}' not found on PATH.")

    # Parse commands from frontmatter
    raw_commands = fm.get("commands", [])
    if raw_commands and not isinstance(raw_commands, list):
        _exit_error("'commands' must be a list of {name, run} mappings.")
    commands = _parse_commands(raw_commands)

    # Parse user args
    declared_names = fm.get("args")
    ralph_args: dict[str, str] = {}
    if extra_args:
        ralph_args = _parse_user_args(extra_args, declared_names)

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
        log_dir=log_dir,
        project_root=Path.cwd(),
    )


@app.command(context_settings={"allow_extra_args": True, "allow_interspersed_args": True, "ignore_unknown_options": True})
def run(
    ctx: typer.Context,
    path: str = typer.Argument(..., help="Path to the ralph directory (containing RALPH.md)."),
    n: int | None = typer.Option(None, "-n", help="Max number of iterations. Infinite if not set."),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", "-s", help="Stop if the agent exits with non-zero."),
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
        rprint(f"[dim]Logging output to {log_dir}/[/dim]")

    state = RunState(run_id=generate_run_id())
    emitter = ConsoleEmitter(_console)

    run_loop(config, state, emitter)
