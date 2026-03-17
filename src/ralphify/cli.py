"""CLI commands for ralphify — init, run, and scaffold new primitives.

This is the main module.  The ``run`` command delegates to the engine module
for the core autonomous loop.  Terminal rendering of events is handled by
:class:`~ralphify._console_emitter.ConsoleEmitter`.
"""

import os
import shutil
import sys
import tomllib
import uuid
from pathlib import Path
from typing import NoReturn

import typer
from rich.console import Console

from ralphify import __version__
from ralphify._console_emitter import ConsoleEmitter
from ralphify._frontmatter import CONFIG_FILENAME, parse_frontmatter
from ralphify._run_types import RunConfig, RunState
from ralphify.engine import run_loop
from ralphify.ralphs import resolve_ralph_source
from ralphify.detector import detect_project
from ralphify._templates import (
    ROOT_RALPH_TEMPLATE,
    RALPH_TOML_TEMPLATE,
)

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


BANNER_LINES = [
    "██████╗░░█████╗░██╗░░░░░██████╗░██╗░░██╗██╗███████╗██╗░░░██╗",
    "██╔══██╗██╔══██╗██║░░░░░██╔══██╗██║░░██║██║██╔════╝╚██╗░██╔╝",
    "██████╔╝███████║██║░░░░░██████╔╝███████║██║█████╗░░░╚████╔╝░",
    "██╔══██╗██╔══██║██║░░░░░██╔═══╝░██╔══██║██║██╔══╝░░░░╚██╔╝░░",
    "██║░░██║██║░░██║███████╗██║░░░░░██║░░██║██║██║░░░░░░░░██║░░░",
    "╚═╝░░╚═╝╚═╝░░╚═╝╚══════╝╚═╝░░░░░╚═╝░░╚═╝╚═╝╚═╝░░░░░░░░╚═╝░░░",
]

TAGLINE = "Harness toolkit for autonomous AI coding loops"


BANNER_COLORS = [
    "#8B6CF0",  # light violet
    "#A78BF5",  # soft violet
    "#D4A0E0",  # pink-violet transition
    "#E8956B",  # warm transition
    "#E87B4A",  # orange accent
    "#E06030",  # deep orange
]


def _print_banner() -> None:
    width = shutil.get_terminal_size().columns
    art_width = max(len(line) for line in BANNER_LINES)
    pad = max(0, (width - art_width) // 2)
    prefix = " " * pad

    rprint()
    for line, color in zip(BANNER_LINES, BANNER_COLORS):
        rprint(f"[bold {color}]{prefix}{line}[/bold {color}]")
    rprint()
    rprint(f"[italic #A78BF5]{TAGLINE:^{width}}[/italic #A78BF5]")
    rprint(f"{'':^{width}}")
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
    """Harness toolkit for autonomous AI coding loops."""
    if ctx.invoked_subcommand is None:
        _print_banner()
        rprint(ctx.get_help())
        raise typer.Exit()

def _load_config() -> dict:
    """Load and return the ralph.toml config, exiting if not found."""
    config_path = Path(CONFIG_FILENAME)
    if not config_path.exists():
        _exit_error(f"{CONFIG_FILENAME} not found. Run 'ralph init' first.")
    with open(config_path, "rb") as f:
        return tomllib.load(f)


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing config."),
) -> None:
    """Initialize ralph config and prompt template."""
    config_path = Path(CONFIG_FILENAME)
    prompt_path = Path("RALPH.md")

    project_type = detect_project()

    if config_path.exists() and not force:
        rprint(f"[yellow]{CONFIG_FILENAME} already exists. Use --force to overwrite.[/yellow]")
        raise typer.Exit(1)

    config_path.write_text(RALPH_TOML_TEMPLATE)
    rprint(f"[green]Created {CONFIG_FILENAME}[/green]")

    if prompt_path.exists():
        rprint("[dim]RALPH.md already exists, skipping.[/dim]")
    else:
        prompt_path.write_text(ROOT_RALPH_TEMPLATE)
        rprint("[green]Created RALPH.md[/green]")

    rprint(f"\nDetected project type: [bold]{project_type}[/bold]")
    rprint("Edit RALPH.md to customize your agent's behavior.")


@app.command()
def new(
    name: str | None = typer.Argument(None, help="Name for the new ralph. If omitted, the agent will help you choose."),
) -> None:
    """Create a new ralph with AI-guided setup."""
    from ralphify._skills import build_agent_command, detect_agent, install_skill

    try:
        agent_name, agent_path = detect_agent()
    except RuntimeError as e:
        _exit_error(str(e))

    try:
        install_skill("new-ralph", agent_name)
    except RuntimeError as e:
        _exit_error(str(e))

    cmd = build_agent_command(agent_name, "new-ralph", name)
    os.execvp(cmd[0], cmd)


@app.command()
def run(
    prompt: str | None = typer.Argument(None, help="Named ralph from .ralphify/ralphs/."),
    n: int | None = typer.Option(None, "-n", help="Max number of iterations. Infinite if not set."),
    stop_on_error: bool = typer.Option(False, "--stop-on-error", "-s", help="Stop if the agent exits with non-zero."),
    delay: float = typer.Option(0, "--delay", "-d", help="Seconds to wait between iterations."),
    log_dir: str | None = typer.Option(None, "--log-dir", "-l", help="Save iteration output to log files in this directory."),
    timeout: float | None = typer.Option(None, "--timeout", "-t", help="Max seconds per iteration. Kill agent if exceeded."),
) -> None:
    """Run the autonomous coding loop.

    Each iteration: read RALPH.md, resolve context placeholders, append
    any check failures from the previous iteration, pipe the assembled
    prompt to the agent, then run checks.
    Repeat until *n* iterations or Ctrl+C.
    """
    toml_config = _load_config()
    agent = toml_config["agent"]
    command = agent["command"]
    args = agent.get("args", [])

    try:
        ralph_file_path, resolved_ralph_name = resolve_ralph_source(
            prompt=prompt,
            toml_ralph=agent.get("ralph", "RALPH.md"),
        )
    except ValueError as e:
        _exit_error(str(e))

    try:
        ralph_text = Path(ralph_file_path).read_text()
    except FileNotFoundError:
        _exit_error(f"Prompt file '{ralph_file_path}' not found.")

    if not shutil.which(command):
        _exit_error(f"Agent command '{command}' not found on PATH.")

    if log_dir:
        rprint(f"[dim]Logging output to {log_dir}/[/dim]")

    # Extract declared global primitive dependencies from ralph frontmatter
    ralph_fm, _ = parse_frontmatter(ralph_text)
    global_checks = ralph_fm.get("checks")
    global_contexts = ralph_fm.get("contexts")

    config = RunConfig(
        command=command,
        args=args,
        ralph_file=ralph_file_path,
        ralph_name=resolved_ralph_name,
        max_iterations=n,
        delay=delay,
        timeout=timeout,
        stop_on_error=stop_on_error,
        log_dir=log_dir,
        global_checks=global_checks,
        global_contexts=global_contexts,
    )
    state = RunState(run_id=uuid.uuid4().hex[:12])
    emitter = ConsoleEmitter(_console)

    run_loop(config, state, emitter)


