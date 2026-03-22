---
description: Fix common ralphify issues — setup errors, agent hangs, command failures, and permission problems.
keywords: ralphify troubleshooting, agent hangs, command failures, setup errors, debug ralph loop
---

# Troubleshooting

Common issues and how to fix them. If your problem isn't listed here, run `ralph run my-ralph -n 1` — it validates your setup and shows clear errors.

## Setup issues

### "RALPH.md not found" or "No RALPH.md in directory"

The path you passed to `ralph run` doesn't contain a `RALPH.md` file. Make sure the directory exists and has a `RALPH.md`:

```bash
ls my-ralph/RALPH.md
```

### "agent field is required"

Your `RALPH.md` frontmatter is missing the `agent` field. Add it:

```markdown
---
agent: claude -p --dangerously-skip-permissions
---
```

### "Command 'claude' not found on PATH"

The agent CLI isn't installed or isn't in your shell's PATH. Verify by running `claude --version` directly. If it's installed but not found, check your PATH.

## Loop issues

### Agent produces no output or seems to hang

Try running the agent command directly to see if it works outside of ralphify:

```bash
echo "Say hello" | claude -p
```

If it hangs there too, the issue is with the agent CLI, not ralphify. If it works standalone but hangs via ralphify, try adding `--timeout` to kill stalled iterations:

```bash
ralph run my-ralph --timeout 300
```

### Agent exits non-zero every iteration

Check the agent's output to understand why. Use `--log-dir` to capture output:

```bash
ralph run my-ralph -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```

Common causes:

- The agent CLI requires authentication that hasn't been set up
- The prompt asks the agent to run a command that fails
- The agent's context window is being exceeded by a very large prompt

If you want the loop to stop on errors instead of continuing, use `--stop-on-error`:

```bash
ralph run my-ralph --stop-on-error --log-dir ralph_logs
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
ralph run my-ralph -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```

Common causes:

- The prompt is too vague ("improve the code" instead of "read TODO.md and implement the next task")
- There's no concrete task source (no TODO.md, PLAN.md, or failing tests to fix)
- The agent can't find what it's supposed to work on

## Frontmatter issues

### "Command name contains invalid characters" / "Arg name contains invalid characters"

Command names and arg names may only contain letters, digits, hyphens, and underscores (`a-z`, `A-Z`, `0-9`, `-`, `_`). Names with dots, spaces, or special characters are rejected because they can't be used in `{{ commands.<name> }}` or `{{ args.<name> }}` placeholders.

```yaml
# ✗ Wrong — dots and spaces aren't allowed
args: [my.focus, test subject]
commands:
  - name: my.tests
    run: uv run pytest -x
  - name: test suite
    run: uv run pytest -x

# ✓ Correct — use hyphens or underscores
args: [my-focus, test_subject]
commands:
  - name: my-tests
    run: uv run pytest -x
  - name: test_suite
    run: uv run pytest -x
```

### "Duplicate arg name" / "Duplicate command name"

Arg names and command names must be unique within a single `RALPH.md`. Duplicates are rejected at startup:

```yaml
# ✗ Wrong — "tests" appears twice
commands:
  - name: tests
    run: uv run pytest -x
  - name: tests
    run: uv run pytest tests/integration

# ✓ Correct — use distinct names
commands:
  - name: unit-tests
    run: uv run pytest -x
  - name: integration-tests
    run: uv run pytest tests/integration
```

The same applies to `args` — each name must appear only once.

### "'commands' must be a list" or "'args' must be a list of strings"

YAML scalars and lists look similar. A common mistake is writing a plain string where a list is expected:

```yaml
# ✗ Wrong — this is a string, not a list
args: focus
commands: uv run pytest -x

# ✓ Correct — use list syntax
args: [focus]
commands:
  - name: tests
    run: uv run pytest -x
```

`args` must be a list of strings (`[focus]` or `- focus`). `commands` must be a list of `{name, run}` mappings.

## Command issues

### Command with pipes or redirections not working

Commands in the `run` field are parsed with `shlex` and run **directly** — not through a shell. Shell features like pipes (`|`), redirections (`2>&1`), chaining (`&&`), and variable expansion (`$VAR`) silently fail or produce unexpected results.

**Won't work:**

```yaml
commands:
  - name: tests
    run: pytest --tb=line -q 2>&1 | tail -20
```

**Fix:** Point the command at a script instead:

```bash
#!/bin/bash
# scripts/run-tests.sh
pytest --tb=line -q 2>&1 | tail -20
```

```bash
chmod +x scripts/run-tests.sh
```

```yaml
commands:
  - name: tests
    run: ./scripts/run-tests.sh
```

### Command always failing

Run the command manually to see if it works:

```bash
uv run pytest -x
```

If the command fails manually, the issue isn't with ralphify — fix the underlying test/lint failures first.

Note that command output is included in the prompt **regardless of exit code**. A failing test command is often exactly what you want — the agent sees the failure and fixes it.

### Command output looks truncated

Each command has a default timeout of **60 seconds**. If your command takes longer (a large test suite, a slow build), it's killed at the timeout and only the output captured so far is used. The agent sees incomplete output without knowing it was cut short.

**Fix:** Increase the timeout for slow commands:

```yaml
commands:
  - name: tests
    run: uv run pytest -x
    timeout: 300  # 5 minutes
```

You can also speed up the command itself — for example, running a subset of tests or filtering output via a [wrapper script](#command-with-pipes-or-redirections-not-working).

### Command output missing from prompt

If a `{{ commands.my-command }}` placeholder produces nothing in the prompt:

1. Check the command name matches exactly: `{{ commands.my-command }}` requires a command with `name: my-command`
2. Verify the command produces output by running it manually
3. Must be `commands` (plural) — `{{ command.name }}` won't resolve

## Output issues

### No output visible during iteration

By default, agent output goes directly to the terminal. If you're using `--log-dir`, output is captured and then replayed — you'll still see it, but only after the iteration completes.

## Common questions

### Can I run multiple loops in parallel?

Yes, but they should work on **separate branches** to avoid git conflicts:

```bash
# Terminal 1
git checkout -b feature-a && ralph run feature-a-ralph

# Terminal 2
git checkout -b feature-b && ralph run feature-b-ralph
```

### What files should I commit?

| File / directory | Commit? | Why |
|---|---|---|
| `my-ralph/RALPH.md` | **Yes** | The ralph definition |
| `ralph_logs/` | **No** | Iteration logs — add to `.gitignore` |

### Can I edit RALPH.md while the loop runs?

Yes. The prompt body (everything below the frontmatter) is re-read every iteration — edit the prompt text and changes take effect on the next cycle. Frontmatter fields (`agent`, `commands`, `args`) are parsed once at startup, so changing those requires restarting the loop.

## Getting more help

1. Run `ralph run my-ralph -n 1` to validate your setup — it shows clear errors
2. Use `ralph run my-ralph -n 1 --log-dir ralph_logs` to capture a single iteration for debugging
3. Check the [CLI Reference](cli.md) for all available options
4. File an issue at [github.com/computerlovetech/ralphify](https://github.com/computerlovetech/ralphify/issues)
