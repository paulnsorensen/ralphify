# CLAUDE.md — ralphify

Ralphify is the open-source framework for ralph loop harness engineering, published on [PyPI](https://pypi.org/project/ralphify/). It's a CLI tool (`ralph`) that runs AI coding agents in autonomous loops — piping prompts to agents, validating work with checks, and repeating with fresh context each iteration.

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
- `cli.py` — CLI commands; delegates to `_console_emitter.py` for terminal event rendering
- `engine.py` — Core run loop orchestration with structured event emission
- `manager.py` — Multi-run orchestration (concurrent runs via threads)
- `_templates.py` — Scaffold templates for `ralph init`
- `_skills.py` — Skill installation, agent detection, and command building for `ralph new`
- `skills/new-ralph/SKILL.md` — AI-guided ralph creation skill (bundled, installed into agent skill dir)
- `_frontmatter.py` — YAML frontmatter parsing and marker/config filename constants
- `_discovery.py` — Primitive directory scanning (`discover_primitives`, `find_run_script`)
- `resolver.py` — Template placeholder resolution (`{{ contexts.name }}`)
- `ralphs.py` — Named ralph discovery and resolution
- `checks.py`, `contexts.py` — Check and context primitive types
- `_events.py` — Event types and emitter protocol (NullEmitter, QueueEmitter, FanoutEmitter)
- `_agent.py` — Run agent subprocesses (streaming + blocking modes, log writing)
- `_output.py` — Combine/truncate stdout+stderr

Tests are in `tests/` with one file per module. Docs are in `docs/` using MkDocs with Material theme.

## Conventions

- **Commit messages**: `docs: explain X for users who want to Y`, `feat: add X so users can Y`, `fix: resolve X that caused Y`
- **Dependencies**: Minimal by design. Runtime deps are only `typer` and `rich`. Prefer stdlib over new deps.
- **Tests**: No external services, no API keys. All tests use temporary directories.
- **Docs**: Every user-facing feature needs a docs page. Run `mkdocs build --strict` before committing doc changes.
- **Keeping docs surfaces in sync**: When making user-facing changes (new features, changed behavior, new CLI flags), update all relevant surfaces:
  - `docs/` (MkDocs) — user-facing docs: primitives, CLI reference, quick reference, writing prompts guide, cookbook. Only include what's relevant for users.
  - `docs/contributing/` — contributor/agent docs: codebase map, architecture. Only include what's relevant for contributors and coding agents.
  - `README.md` — keep short and high-level. Update only when the change affects the quickstart, install, or core concepts.
  - `src/ralphify/skills/new-ralph/SKILL.md` — the skill that powers `ralph new`. Update when new primitives, frontmatter fields, or prompt features (like user arguments) are added, so the AI-guided setup can suggest them.
  - `docs/changelog.md` — add an entry for every release.

## Traps

- Primitive marker filenames (`CHECK.md`, `CONTEXT.md`, `RALPH.md`) are defined as constants in `_frontmatter.py` (`CHECK_MARKER`, `CONTEXT_MARKER`, `RALPH_MARKER`). The primitives directory name is `PRIMITIVES_DIR`. All modules import from there — change the constant to rename everywhere.
- `timeout` and `enabled` frontmatter fields have special type coercion via `_FIELD_COERCIONS` in `_frontmatter.py`. To add a new typed field, add an entry to that dict.
- Contexts use `resolver.py:resolve_placeholders()` for `{{ contexts.name }}` template substitution. User arguments use `{{ args.name }}` — both are resolved by the same resolver.
- Output is truncated to 5000 chars in `_output.py`. This is intentional.
- Commands in frontmatter run via `shlex.split()` — no shell features (pipes, redirections, `&&`). Scripts (`run.*`) are the escape hatch.
