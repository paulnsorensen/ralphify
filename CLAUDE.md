# CLAUDE.md — ralphify

Ralphify is the open-source framework for ralph loop harness engineering, published on [PyPI](https://pypi.org/project/ralphify/). It's a CLI tool (`ralph`) that runs AI coding agents in autonomous loops — piping prompts to agents, running commands to capture dynamic data, and repeating with fresh context each iteration.

For full architecture details, see `docs/contributing/codebase-map.md`.

## Quick commands

```bash
uv run pytest              # Run tests (required before any commit)
uv run pytest -x           # Stop on first failure
uv run mkdocs build --strict  # Build docs (must pass with zero warnings)
uv run mkdocs serve        # Preview docs at http://127.0.0.1:8000
```

## Project layout

All source code is in `src/ralphify/`. The main file is `cli.py` — it contains the CLI commands and delegates to the engine for the core loop.

Key modules:
- `cli.py` — CLI commands (`run`, `new`, `init`); delegates to `_console_emitter.py` for terminal event rendering
- `engine.py` — Core run loop orchestration with structured event emission
- `manager.py` — Multi-run orchestration (concurrent runs via threads)
- `_frontmatter.py` — YAML frontmatter parsing (uses PyYAML) and the `RALPH_MARKER` constant
- `_run_types.py` — `RunConfig`, `RunState`, `RunStatus`, `Command` dataclasses
- `_resolver.py` — Template placeholder resolution (`{{ commands.name }}`, `{{ args.name }}`)
- `_agent.py` — Run agent subprocesses (streaming + blocking modes, log writing)
- `_runner.py` — Generic command execution with timeout
- `_events.py` — Event types, emitter protocol (NullEmitter, QueueEmitter, FanoutEmitter), and BoundEmitter convenience wrapper
- `_console_emitter.py` — Rich terminal rendering of events
- `_output.py` — `ProcessResult` base class, combine stdout+stderr, format durations
- `_source.py` — GitHub source parsing and git-based ralph fetching for `ralph add`
- `_skills.py` — Skill installation, agent detection, and command building for `ralph new`
- `skills/new-ralph/SKILL.md` — AI-guided ralph creation skill (bundled, installed into agent skill dir)

Tests are in `tests/` with one file per module. Docs are in `docs/` using MkDocs with Material theme.

## Core concepts

A **ralph** is a directory containing a `RALPH.md` file. That's it. No project-level config, no `.ralphify/` directory, no `ralph init`.

**RALPH.md** has YAML frontmatter + a prompt body:
- `agent` (required) — the agent command to run
- `commands` (optional) — list of `{name, run}` commands whose output fills `{{ commands.<name> }}` placeholders
- `args` (optional) — declared argument names for `{{ args.<name> }}` placeholders

**The loop**: run commands → assemble prompt (resolve placeholders) → pipe to agent → repeat.

## Conventions

- **Commit messages**: `docs: explain X for users who want to Y`, `feat: add X so users can Y`, `fix: resolve X that caused Y`
- **Dependencies**: Minimal by design. Runtime deps are `typer`, `rich`, and `pyyaml`. Prefer stdlib over new deps.
- **Tests**: No external services, no API keys. All tests use temporary directories.
- **Docs**: Every user-facing feature needs a docs page. Run `mkdocs build --strict` before committing doc changes.
- **Keeping docs surfaces in sync**: When making user-facing changes (new features, changed behavior, new CLI flags), update all relevant surfaces:
  - `docs/` (MkDocs) — user-facing docs: CLI reference, quick reference, writing prompts guide, cookbook. Only include what's relevant for users.
  - `docs/contributing/` — contributor/agent docs: codebase map, architecture. Only include what's relevant for contributors and coding agents.
  - `README.md` — keep short and high-level. Update only when the change affects the quickstart, install, or core concepts.
  - `src/ralphify/skills/new-ralph/SKILL.md` — the skill that powers `ralph new`. Update when new frontmatter fields or features are added.
  - `docs/changelog.md` — add an entry for every release.

## Traps

- The ralph marker filename (`RALPH.md`) is defined as `RALPH_MARKER` in `_frontmatter.py`. All modules import from there.
- Frontmatter parsing uses PyYAML (`yaml.safe_load`). The `commands` field is a list of dicts, `args` is a list of strings.
- Commands use `_runner.py:run_command()` with `shlex.split()` — no shell features (pipes, redirections, `&&`). Scripts are the escape hatch.
- Commands starting with `./` run relative to the ralph directory. Other commands run from the project root.
- The `agent` field in frontmatter is split with `shlex.split()` to build the command list.
- Placeholder resolution uses `_resolver.py` — `{{ commands.<name> }}` and `{{ args.<name> }}` are the two supported kinds.

The project has a website called ralphify.co and the docs live a ralphify.co/docs/