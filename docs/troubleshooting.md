---
title: Troubleshooting Ralph Loops
description: Fix common ralphify issues — setup errors, agent hangs, command failures, ralph add problems, and permission issues.
keywords: ralphify troubleshooting, agent hangs, command failures, setup errors, debug ralph loop, ralph add issues
---

# Troubleshooting

!!! tldr "Quick checklist"
    1. Run `ralph run my-ralph -n 1` — it validates your setup and shows clear errors
    2. Test the agent outside ralphify: `echo "Say hello" | claude -p`
    3. Use `--log-dir ralph_logs` to capture output for debugging
    4. Commands don't support shell features (pipes, `&&`) — use a wrapper script instead

Common issues and how to fix them. If your problem isn't listed here, run [`ralph run`](cli.md#ralph-run) with `-n 1` — it validates your setup and shows clear errors.

## Setup issues

### "is not a directory, RALPH.md file, or installed ralph"

The path you passed to [`ralph run`](cli.md#ralph-run) doesn't resolve to a valid ralph. The command accepts a **directory** containing `RALPH.md`, a **direct path** to a `RALPH.md` file, or the **name of an installed ralph** (from [`ralph add`](cli.md#ralph-add)):

```bash
ralph run my-ralph              # directory containing RALPH.md
ralph run my-ralph/RALPH.md     # direct path to the file
ralph run my-ralph              # installed ralph in .ralphify/ralphs/my-ralph/
```

If you're getting this error, check that the path exists and points to the right place:

```bash
ls my-ralph/RALPH.md                       # local ralph
ls .ralphify/ralphs/my-ralph/RALPH.md      # installed ralph
```

### "Missing or empty 'agent' field in RALPH.md frontmatter"

Your `RALPH.md` [frontmatter](writing-prompts.md#the-anatomy-of-a-good-ralphmd) is missing the `agent` field or it's an empty string. Add it:

```markdown
---
agent: claude -p --dangerously-skip-permissions
---
```

### "Agent command 'claude' not found on PATH"

The agent CLI isn't installed or isn't in your shell's PATH. Verify by running `claude --version` directly. If it's installed but not found, check your PATH. See [supported agents](agents.md) for setup instructions.

## `ralph add` issues

### "Cannot parse source"

The source format wasn't recognized. [`ralph add`](cli.md#ralph-add) accepts these formats:

```bash
ralph add owner/repo                                        # shorthand
ralph add owner/repo/ralph-name                             # specific ralph
ralph add https://github.com/owner/repo                     # full URL
ralph add https://github.com/owner/repo/tree/main/my-ralph  # URL copied from GitHub
```

The easiest way to add a ralph from GitHub is to navigate to the directory in your browser and copy the URL — it works directly with `ralph add`.

### "git clone failed"

The repository couldn't be cloned. Common causes:

- The repository doesn't exist or has a typo in the owner/repo name
- The repository is **private** — `ralph add` uses `git clone` under the hood, so your local git credentials must have access. If you can `git clone https://github.com/owner/repo.git` manually, `ralph add` will work too.

### "No RALPH.md found" / "No ralph named '...' found"

The repository was cloned successfully but no ralphs were found. Either the repo doesn't contain any `RALPH.md` files, or the ralph name you specified doesn't match any directory in the repo.

### Re-running `ralph add` overwrites without warning

If you `ralph add` a ralph that's already installed in `.ralphify/ralphs/`, the existing copy is replaced silently. This is by design — it's how you update an installed ralph to the latest version. If you've made local edits to an installed ralph, copy them elsewhere before re-adding.

## Loop issues

### Agent produces no output or seems to hang

Try running the [agent command](agents.md) directly to see if it works outside of ralphify:

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

If iterations finish in seconds with no meaningful work, the agent may be exiting without taking action. Check the logs with [`--log-dir`](cli.md#ralph-run):

```bash
ralph run my-ralph -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```

Common causes:

- The prompt is too vague — see [anti-patterns that waste iterations](writing-prompts.md#anti-patterns-that-waste-iterations)
- There's no concrete task source (no TODO.md, PLAN.md, or failing tests to fix) — see [the TODO-driven loop](writing-prompts.md#the-todo-driven-loop)
- The agent can't find what it's supposed to work on

## Frontmatter issues

### "Invalid YAML in frontmatter"

Your YAML frontmatter has a syntax error — usually a missing colon, bad indentation, or an unquoted special character. The error message includes the YAML parser's details:

```text
Invalid YAML in frontmatter: while parsing a block mapping ...
```

Common fixes:

```yaml
# ✗ Wrong — missing colon, bad indentation
agent claude -p
commands:
- name: tests
run: uv run pytest

# ✓ Correct
agent: claude -p
commands:
  - name: tests
    run: uv run pytest
```

If your value contains special YAML characters (`:`, `#`, `{`, `[`), wrap it in quotes:

```yaml
agent: "claude -p --dangerously-skip-permissions"
```

### "Frontmatter must be a YAML mapping"

The frontmatter parsed as valid YAML but isn't a key-value mapping. This usually happens when the frontmatter is a plain string or a list instead of a mapping:

```yaml
# ✗ Wrong — this is a plain string, not a mapping
---
claude -p --dangerously-skip-permissions
---

# ✓ Correct — key: value pairs
---
agent: claude -p --dangerously-skip-permissions
---
```

### "Command name contains invalid characters" / "Arg name contains invalid characters"

Command names and arg names may only contain letters, digits, hyphens, and underscores (`a-z`, `A-Z`, `0-9`, `-`, `_`). Names with dots, spaces, or special characters are rejected because they can't be used in [`{{ commands.<name> }}` or `{{ args.<name> }}` placeholders](writing-prompts.md#ralph-context-placeholders).

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

### "Command '...' has invalid syntax"

A command's `run` string has malformed shell syntax — usually an unmatched quote. The error message tells you which command failed:

```text
Command 'tests' has invalid syntax: 'uv run pytest -x "unclosed'. Check the 'commands' field in your RALPH.md frontmatter.
```

Fix the quoting in the `run` value. If your command needs complex quoting, point it at a script instead — see [Command with pipes or redirections not working](#command-with-pipes-or-redirections-not-working).

### "Command '...' binary not found"

A command in your `commands` field references a binary that isn't installed or isn't on your PATH. The error message tells you which command failed:

```text
Command 'lint' binary not found: 'mypy src/'. Check the 'commands' field in your RALPH.md frontmatter.
```

Verify the binary exists by running it directly:

```bash
mypy --version
```

If it's installed in a virtual environment, prefix the command with `uv run` or the appropriate runner:

```yaml
commands:
  - name: lint
    run: uv run mypy src/
```

### Command with pipes or redirections not working

Commands in the `run` field are parsed with `shlex` and run **directly** — not through a shell. Shell features like pipes (`|`), redirections (`2>&1`), chaining (`&&`), and variable expansion (`$VAR`) silently fail or produce unexpected results. See [shell features in commands](writing-prompts.md#shell-features-in-commands) for background.

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
    run: scripts/run-tests.sh
```

Commands without a `./` prefix run from the project root, so `scripts/run-tests.sh` resolves to `<project-root>/scripts/run-tests.sh`. If you want to bundle the script next to your `RALPH.md`, use the `./` prefix instead — see [Working directory](how-it-works.md#2-run-commands) for details.

### Command always failing

Run the command manually to see if it works:

```bash
uv run pytest -x
```

If the command fails manually, the issue isn't with ralphify — fix the underlying test/lint failures first.

Note that command output is included in the prompt **regardless of exit code**. A failing test command is often exactly what you want — the agent sees the failure and fixes it.

### Command output looks truncated

Each command has a default timeout of **60 seconds** (see [command timeouts](writing-prompts.md#command-timeouts)). If your command takes longer (a large test suite, a slow build), it's killed at the timeout and only the output captured so far is used. The agent sees incomplete output without knowing it was cut short.

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

??? note "No output visible during iteration"
    By default, agent output goes directly to the terminal. If you're using `--log-dir`, output is captured and then replayed — you'll still see it, but only after the iteration completes.

??? note "CLI flag validation errors"
    ### "'-n' must be a positive integer"

    The `-n` flag sets how many iterations to run. It must be at least 1:

    ```bash
    # ✗ Wrong
    ralph run my-ralph -n 0

    # ✓ Correct
    ralph run my-ralph -n 1
    ```

    ### "'--delay' must be non-negative"

    The `--delay` flag sets seconds to wait between iterations. It can be zero but not negative:

    ```bash
    # ✗ Wrong
    ralph run my-ralph --delay -5

    # ✓ Correct
    ralph run my-ralph --delay 0
    ralph run my-ralph --delay 30
    ```

    ### "'--timeout' must be a positive number"

    The `--timeout` flag sets the per-iteration time limit in seconds. It must be greater than zero:

    ```bash
    # ✗ Wrong
    ralph run my-ralph --timeout 0

    # ✓ Correct
    ralph run my-ralph --timeout 300
    ```

## Common questions

### Can I run multiple loops in parallel?

Yes, but they should work on **separate branches** to avoid git conflicts:

```bash
# Terminal 1
git checkout -b feature-a && ralph run feature-a-ralph

# Terminal 2
git checkout -b feature-b && ralph run feature-b-ralph
```

For programmatic control over concurrent runs, use the [Python API's `RunManager`](api.md#concurrent-runs-with-runmanager).

### What files should I commit?

| File / directory | Commit? | Why |
|---|---|---|
| `my-ralph/RALPH.md` | **Yes** | The ralph definition |
| `my-ralph/*.sh` | **Yes** | Helper scripts referenced by commands |
| `ralph_logs/` | **No** | Iteration logs — add to `.gitignore` |

### Can I edit RALPH.md while the loop runs?

Yes. The prompt body (everything below the frontmatter) is re-read every iteration — edit the prompt text and changes take effect on the next cycle. Frontmatter fields (`agent`, `commands`, `args`) are parsed once at startup, so changing those requires restarting the loop.

### How do I disable the co-author credit in commits?

By default, ralphify appends an instruction asking the agent to add `Co-authored-by: Ralphify <noreply@ralphify.co>` to commit messages. To disable it, set `credit: false` in your RALPH.md frontmatter:

```yaml
---
agent: claude -p --dangerously-skip-permissions
credit: false
---
```

### How do I make a ralph reusable across projects?

Use `args` to parameterize your ralph instead of hardcoding project-specific values:

```markdown
---
agent: claude -p --dangerously-skip-permissions
args: [dir, focus]
commands:
  - name: tests
    run: uv run pytest {{ args.dir }}
---

Focus on {{ args.dir }}. Priority: {{ args.focus }}
```

```bash
ralph run my-ralph --dir ./api --focus "error handling"
ralph run my-ralph --dir ./frontend --focus "accessibility"
```

See [Parameterized ralphs](writing-prompts.md#parameterized-ralphs) for more patterns.

## Getting more help

1. Run `ralph run my-ralph -n 1` to validate your setup — it shows clear errors
2. Use `ralph run my-ralph -n 1 --log-dir ralph_logs` to capture a single iteration for debugging
3. Check the [CLI reference](cli.md) for all available options
4. File an issue at [github.com/computerlovetech/ralphify](https://github.com/computerlovetech/ralphify/issues)

## Next steps

- [How it works](how-it-works.md) — understand the iteration lifecycle to debug more effectively
- [Writing prompts](writing-prompts.md) — improve your RALPH.md to avoid common loop issues
- [Cookbook](cookbook.md) — working examples you can adapt for your project
