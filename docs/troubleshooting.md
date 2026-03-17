---
description: Fix common ralphify issues — setup errors, agent hangs, check failures, missing contexts, output truncation, and permission problems.
---

# Troubleshooting

Common issues and how to fix them. If your problem isn't listed here, run `ralph run -n 1` — it validates your setup and shows clear errors.

## Setup issues

### "ralph.toml not found"

You haven't initialized the project yet. Run `ralph init` in your project directory to create `ralph.toml` and `RALPH.md`.

### "Command 'claude' not found on PATH"

The agent CLI isn't installed or isn't in your shell's PATH. Verify by running `claude --version` directly. If it's installed but not found, check your PATH.

### "Agent command not found on PATH"

`ralph run` checks that the agent command exists on PATH before starting the loop. If you see this error:

- Install the agent CLI or fix the `command` in `ralph.toml`

### "RALPH.md already exists"

`ralph init` won't overwrite existing files by default. If you want to start fresh:

```bash
ralph init --force
```

## Loop issues

### Agent produces no output or seems to hang

Try running the agent command directly to see if it works outside of ralphify:

```bash
echo "Say hello" | claude -p
```

If it hangs there too, the issue is with the agent CLI, not ralphify. If it works standalone but hangs via ralphify, try adding `--timeout` to kill stalled iterations:

```bash
ralph run --timeout 300
```

### Agent exits non-zero every iteration

Check the agent's output to understand why. Use `--log-dir` to capture output:

```bash
ralph run -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```

Common causes:
- The agent CLI requires authentication that hasn't been set up
- The prompt asks the agent to run a command that fails
- The agent's context window is being exceeded by a very large prompt

If you want the loop to stop on errors instead of continuing, use `--stop-on-error`:

```bash
ralph run --stop-on-error --log-dir ralph_logs
```

### Agent runs but doesn't commit

Ralphify doesn't commit for the agent — committing is the agent's responsibility. Make sure your prompt includes explicit commit instructions:

```markdown
## Process
- Run tests before committing
- Commit with a descriptive message like `feat: add X`
```

Also ensure the agent has permission to run git commands. With Claude Code, the `--dangerously-skip-permissions` flag handles this.

### Loop runs too fast / agent not doing anything useful

If iterations finish in seconds with no meaningful work, the agent may be exiting without taking action. Check the logs:

```bash
ralph run -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```

Common causes:
- The prompt is too vague ("improve the code" instead of "read TODO.md and implement the next task")
- There's no concrete task source (no TODO.md, PLAN.md, or failing tests to fix)
- The agent can't find what it's supposed to work on

### New check/context not being picked up

Primitives are re-discovered every iteration, so adding or editing a check or context on disk takes effect on the next cycle without restarting.

If a primitive still isn't running, check that it's **declared** in your ralph file's frontmatter. Global checks and contexts must be listed explicitly:

```markdown
---
checks: [tests, lint]
contexts: [git-log]
---
```

See [Declaring global primitive dependencies](primitives.md#declaring-global-primitive-dependencies) for details.

## Check issues

### Command with pipes or redirections not working

Commands in frontmatter are parsed with `shlex` and run **directly** — not through a shell. Shell features like pipes (`|`), redirections (`2>&1`), chaining (`&&`), and variable expansion (`$VAR`) silently fail or produce unexpected results.

**Won't work:**

```yaml
command: pytest --tb=line -q 2>&1 | tail -20
```

**Fix:** Use a `run.sh` script instead:

```bash
#!/bin/bash
# .ralphify/checks/my-check/run.sh
pytest --tb=line -q 2>&1 | tail -20
```

```bash
chmod +x .ralphify/checks/my-check/run.sh
```

See [command parsing](primitives.md#command-parsing) for details.

### Checks always failing

Run the check command manually to see if it works:

```bash
# Look up the command in your check file
cat .ralphify/checks/tests/CHECK.md

# Run it directly
uv run pytest -x
```

If the command fails manually, the issue isn't with ralphify — fix the underlying test/lint failures first.

### Check timed out

The check took longer than its configured timeout. Increase the `timeout` value in the check's frontmatter:

```markdown
---
command: uv run pytest
timeout: 300
enabled: true
---
```

The default is 60 seconds. Long test suites may need 300+ seconds.

### Script permission denied

If you're using a `run.sh` or `run.py` script instead of a frontmatter `command`, make sure it's executable:

```bash
chmod +x .ralphify/checks/my-check/run.sh
```

### Check has neither command nor script

If a check has neither a `run.*` script nor a `command`, add one of:

- A `command` field in the CHECK.md frontmatter
- An executable script named `run.sh`, `run.py`, etc. in the check directory

## Context issues

### Placeholder produces no output

If a `{{ contexts.my-context }}` placeholder silently disappears (the prompt has nothing where you expected content), the context name doesn't match any discovered context. Ralphify replaces unmatched named placeholders with an empty string — you won't see raw placeholder text. Check:

1. The directory name matches: `.ralphify/contexts/my-context/CONTEXT.md`
2. The placeholder uses the exact directory name: `{{ contexts.my-context }}`
3. The context is enabled (check the `enabled` field in its CONTEXT.md frontmatter)
4. If the context has a command, verify the command produces output by running it manually

!!! note "Raw placeholder text still visible?"
    If you see literal `{{ contexts.name }}` in the agent's output, the placeholder syntax wasn't recognized — usually a typo in the keyword (e.g. `{{ context.name }}` instead of `{{ contexts.name }}`). It must be `contexts` (plural).

### Context command failing

Run the context command manually to verify it produces output. Note that context output is injected **regardless of exit code** — commands like `pytest` exit non-zero but still produce useful output. If the command produces no output at all, check that it runs correctly outside of ralphify.

### Some contexts are missing from the prompt

Each context must be referenced by a named placeholder like `{{ contexts.git-log }}` to appear in the prompt. Contexts without a placeholder are excluded. Make sure every context you want included has a corresponding `{{ contexts.name }}` in your `RALPH.md`.

See [Placement in the prompt](primitives.md#placement-in-the-prompt) for full details.

## Output issues

### Output is truncated

Ralphify truncates check and context output to **5,000 characters** each. This prevents extremely long output from consuming the agent's context window. You'll see `... (truncated)` at the end of truncated output.

This is expected behavior. If you need the full output, check the log files:

```bash
ralph run --log-dir ralph_logs
cat ralph_logs/001_*.log
```

### No output visible during iteration

By default, agent output goes directly to the terminal. If you're using `--log-dir`, output is captured and then replayed — you'll still see it, but only after the iteration completes.

## Common questions

### Can I run multiple loops in parallel?

Yes, but they should work on **separate branches** to avoid git conflicts:

```bash
# Terminal 1
git checkout -b feature-a && ralph run

# Terminal 2
git checkout -b feature-b && ralph run
```

### What files should I commit?

| File / directory | Commit? | Why |
|---|---|---|
| `ralph.toml` | **Yes** | Loop configuration |
| `RALPH.md` | **Yes** | The prompt |
| `.ralphify/` | **Yes** | Checks, contexts, ralphs |
| `ralph_logs/` | **No** | Iteration logs — add to `.gitignore` |

## Getting more help

1. Run `ralph run -n 1` to validate your setup — it checks your config and shows clear errors
2. Use `ralph run -n 1 --log-dir ralph_logs` to capture a single iteration for debugging
3. Check the [Configuration & CLI](cli.md) for all available options
4. File an issue at [github.com/computerlovetech/ralphify](https://github.com/computerlovetech/ralphify/issues)
