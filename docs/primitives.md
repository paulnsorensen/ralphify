---
description: Full reference for ralphify's three primitives — checks (post-iteration validation), contexts (dynamic data injection), and ralphs (named task-focused ralphs).
---

# Primitives

Primitives are reusable building blocks that extend your loop. They live in the `.ralphify/` directory and are automatically discovered by ralphify.

| Primitive | Purpose | Runs when |
|---|---|---|
| [Checks](#checks) | Validate the agent's work (tests, linters) | After each iteration |
| [Contexts](#contexts) | Inject dynamic or static data into the prompt | Before each iteration |
| [Ralphs](#ralphs) | Reusable task-focused ralphs you can switch between | At run start |

## Checks

Checks run **after** each iteration to validate what the agent did. If a check fails, its output (and optional failure instructions) are appended to the next iteration's prompt so the agent can fix the problem.

### Creating a check

The easiest way is `ralph new`, which guides you through creating a complete ralph with checks and contexts. To create a check manually:

Create `.ralphify/checks/my-tests/CHECK.md`:

```markdown
---
command: pytest -x
timeout: 120
enabled: true
---
Fix all failing tests. Do not skip or delete tests.
```

The body text below the frontmatter is the **failure instruction** — it gets included in the prompt alongside the check output when the check fails.

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `command` | string | — | Command to run (see [command parsing](#command-parsing) below) |
| `timeout` | int | `60` | Max seconds before the check is killed |
| `enabled` | bool | `true` | Set to `false` to skip without deleting |

A check must have either a `command` in its frontmatter or an executable `run.*` script in its directory. Checks that have neither are skipped with a warning.

### Command parsing

Commands are split with Python's `shlex.split()` and executed **directly** — not through a shell. This means:

- Simple commands work: `uv run pytest -x`, `npm test`, `ruff check .`
- Shell features like pipes (`|`), redirections (`>`), chaining (`&&`), and variable expansion (`$VAR`) do **not** work

If you need shell features, use a script instead.

### Using a script instead of a command

Place an executable script named `run.*` (e.g. `run.sh`, `run.py`) in the check directory. If both a `command` and a `run.*` script exist, the script takes precedence. Scripts run with the **project root** as the working directory.

### How check failures appear in the prompt

When a check fails, ralphify appends this to the next iteration's prompt:

````markdown
## Check Failures

The following checks failed after the last iteration. Fix these issues:

### my-tests
**Exit code:** 1

```
FAILED tests/test_foo.py::test_bar - AssertionError
```

Fix all failing tests. Do not skip or delete tests.
````

## Contexts

Contexts inject **dynamic data** into the prompt before each iteration — recent git history, test status, file listings, etc.

### Creating a context

To create a context manually:

Create `.ralphify/contexts/git-log/CONTEXT.md`:

```markdown
---
command: git log --oneline -10
timeout: 30
enabled: true
---
## Recent commits
```

The command runs each iteration and its stdout is injected into the prompt. The body text appears above the command output as a label. A context can also be purely static (no command) — just omit the `command` field.

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `command` | string | — | Command whose stdout is captured |
| `timeout` | int | `30` | Max seconds before the command is killed |
| `enabled` | bool | `true` | Set to `false` to skip without deleting |

Scripts work the same way as checks — place a `run.*` script in the context directory.

Context output is injected **regardless of the command's exit code**. Commands like `pytest --tb=line -q` exit non-zero but produce exactly the output you want.

### Placement in the prompt

Use named placeholders in your `RALPH.md` to place specific contexts:

```markdown
{{ contexts.git-log }}

Work on the next task.

{{ contexts.test-status }}
```

Each context must be referenced by name with `{{ contexts.name }}`. Contexts not referenced by a placeholder are excluded from the prompt.

## Ralphs

Named ralphs let you switch between different tasks without editing your root `RALPH.md`. Create a `docs` ralph, a `refactor` ralph, and a `bug-fix` ralph — select the one you need at run time.

### Creating a ralph

```bash
ralph new docs
```

This launches an AI-guided session that helps you create the ralph, its checks, and contexts. To create one manually, create `.ralphify/ralphs/docs/RALPH.md`:

```markdown
---
description: Improve project documentation
enabled: true
checks: [docs-build]
contexts: [git-log]
---

You are a documentation agent. Each iteration starts fresh.

Read the codebase and existing docs. Find the biggest gap and improve one page per iteration.

{{ contexts.git-log }}
```

### Frontmatter fields

| Field | Type | Default | Description |
|---|---|---|---|
| `description` | string | `""` | Short description of what this ralph does |
| `enabled` | bool | `true` | Set to `false` to disable without deleting |
| `checks` | list | — | Global checks to include (see [declaring dependencies](#declaring-global-primitive-dependencies) below) |
| `contexts` | list | — | Global contexts to include (see [declaring dependencies](#declaring-global-primitive-dependencies) below) |

### Running a named ralph

```bash
ralph run docs           # Use the "docs" ralph
ralph run refactor -n 5  # Use "refactor" for 5 iterations
```

You can also set a default in `ralph.toml`:

```toml
[agent]
ralph = "docs"   # Name of a ralph in .ralphify/ralphs/
```

### Prompt resolution

The positional `[PROMPT]` argument accepts a named ralph:

```bash
ralph run docs       # Looks up "docs" in .ralphify/ralphs/
```

If omitted, ralphify falls back to `ralph.toml`'s `agent.ralph` field, which can be either a ralph name or a file path (e.g. `RALPH.md`).

## Declaring global primitive dependencies

By default, **global primitives are not included** when running a named ralph. You must explicitly declare which global checks and contexts the ralph needs using `checks` and `contexts` in the ralph's frontmatter:

```markdown
---
description: Improve project documentation
checks: [lint, tests]
contexts: [git-log]
---
```

This tells ralphify to include the global `lint` and `tests` checks from `.ralphify/checks/` and the global `git-log` context from `.ralphify/contexts/`. Any global primitive not listed is excluded.

If you omit the `checks` or `contexts` field entirely, no global primitives of that type are included — only ralph-scoped (local) ones apply.

!!! tip "Why explicit dependencies?"
    Explicit dependencies keep ralphs self-contained and predictable. A `docs` ralph shouldn't run your test suite unless you say so. When you create a ralph with `ralph new`, the AI guide helps you declare the right dependencies.

## Ralph-scoped primitives

Named ralphs can also have their own checks and contexts that only apply when running that ralph. When you use `ralph new`, the AI guide creates ralph-scoped primitives automatically. To create them manually, place them inside the ralph's directory:

```
.ralphify/ralphs/docs/
├── RALPH.md
├── checks/docs-build/CHECK.md
└── contexts/doc-coverage/CONTEXT.md
```

Ralph-scoped primitives are always included — they don't need to be declared in the frontmatter.

### How global and local primitives merge

When you run `ralph run docs`:

1. Global checks/contexts listed in the ralph's `checks`/`contexts` frontmatter are selected
2. Ralph-scoped (local) primitives from the ralph's directory are discovered
3. The two sets are merged — if a local primitive has the same name as a global one, the **local version wins**
4. A disabled local primitive suppresses a global one with the same name

## Behavior notes

### Script execution environment

When a check or context command (or `run.*` script) runs, ralphify sets up the following environment:

**Working directory:** Always the **project root** (where `ralph.toml` lives), regardless of where the primitive directory is located.

**Environment variables:** Scripts inherit the full parent process environment (`PATH`, `HOME`, etc.). When running a named ralph, ralphify also sets:

| Variable | Value | When set |
|---|---|---|
| `RALPH_NAME` | Name of the current ralph (e.g. `docs`) | Only when running a named ralph via `ralph run docs` |

This lets a single script adapt its behavior based on which ralph is running:

```bash
#!/bin/bash
# .ralphify/checks/tests/run.sh
if [ "$RALPH_NAME" = "docs" ]; then
    uv run pytest tests/test_docs.py -x
else
    uv run pytest -x
fi
```

`RALPH_NAME` is not set when running the root `RALPH.md` directly (i.e. `ralph run` without a named ralph).

### Execution order

Primitives run in **alphabetical order by directory name**. To control order, use number prefixes: `01-lint/`, `02-typecheck/`, `03-tests/`. All checks run regardless of whether earlier checks pass or fail.

### What's re-read each iteration

Everything is re-read every iteration, so you can edit files on disk and the changes take effect on the next cycle — no restart needed.

| What | When loaded |
|---|---|
| `RALPH.md` prompt | Every iteration |
| Context command output | Every iteration |
| Primitive config (checks, contexts) | Every iteration |
