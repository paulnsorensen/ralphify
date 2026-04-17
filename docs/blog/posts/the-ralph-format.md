---
date: 2026-04-04
categories:
  - Standards
authors:
  - kasper
description: A short manifest defining the ralph format — a single-file, skill-like spec for autonomous agent loops.
keywords: ralph format, ralph spec, RALPH.md, autonomous agent loop format, agent harness spec, ralph standard
---

# The Ralph Format

A **ralph** is a directory with a `RALPH.md` file in it. `RALPH.md` defines an autonomous agent loop: the agent to run, the commands to run between iterations, and the prompt to pipe in.

That's the whole format.

<!-- more -->

## Minimal example

```markdown
---
agent: claude -p
commands:
  - name: tests
    run: uv run pytest -x
---

Fix the failing tests.

{{ commands.tests }}
```

Each iteration: run the commands, fill the `{{ commands.<name> }}` placeholders with their output, pipe the assembled prompt to the agent, repeat.

## The spec

`RALPH.md` is a markdown file with YAML frontmatter and a prompt body.

**Frontmatter fields:**

| Field | Required | Description |
|---|---|---|
| `agent` | yes | Command to run. Anything that reads a prompt on stdin. |
| `commands` | no | List of `{name, run}` (plus optional `timeout`). Output fills `{{ commands.<name> }}` placeholders. |
| `args` | no | List of argument names. Values fill `{{ args.<name> }}` placeholders and become CLI flags. |

**Body:** markdown with `{{ placeholders }}`. Unmatched placeholders resolve to empty strings.

**Placeholders:**

- `{{ commands.<name> }}` — output of a command (stdout + stderr, regardless of exit code)
- `{{ args.<name> }}` — value of a CLI argument
- `{{ ralph.name }}`, `{{ ralph.iteration }}`, `{{ ralph.max_iterations }}` — runtime metadata

## Directory form

`RALPH.md` on its own is enough. But a ralph is a directory so it can bundle anything the loop needs:

```
bug-hunter/
├── RALPH.md              # required
├── check-coverage.sh     # command script (optional)
├── coding-guidelines.md  # context for the agent (optional)
└── test-data.json        # supporting file (optional)
```

Commands whose `run` starts with `./` resolve relative to the ralph directory, so bundled scripts just work. The directory is the unit of sharing.

## A realistic example

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: lint
    run: uv run ruff check .
  - name: git-log
    run: git log --oneline -10
args:
  - focus
---

You are an autonomous bug-hunting agent running in a loop.
Each iteration starts with fresh context.

## Tests
{{ commands.tests }}

## Lint
{{ commands.lint }}

## Recent commits
{{ commands.git-log }}

## Task

Find and fix one real bug in this codebase. {{ args.focus }}

Rules:
- One bug per iteration
- Write a failing regression test before fixing
- Do not change unrelated code
- Commit with `fix: resolve <description>`
```

## The runtime

The format is the spec. A runtime executes it. [Ralphify](https://github.com/computerlovetech/ralphify) is the reference runtime:

```bash
uv tool install ralphify
ralph run ./bug-hunter --focus "authentication"
```

Anything that implements the loop — read `RALPH.md`, resolve placeholders, pipe to the agent, repeat — is a conforming runtime.

## Why a format

Everyone writing ralph loops ends up with the same scaffolding: a markdown prompt, a few shell commands that surface state between iterations, a while-loop that ties them together. A format turns that scaffolding into something you can share, version, and install.

Ralphs are to the outer loop what [skills](https://agentskills.io/) are to the inner loop. A skill guides an agent inside a session. A ralph defines what runs *between* sessions.

See also: [RALPH.md — a markdown format for autonomous agent loops](the-ralph-standard.md) — the longer thinking piece behind the format.
