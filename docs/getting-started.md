---
title: Getting Started with Ralph Loops
description: Install ralphify, create your first ralph with commands and placeholders, and run a productive autonomous AI coding loop in 10 minutes.
keywords: install ralphify, getting started, ralph new, ralph run, autonomous coding setup, AI agent quickstart
---

# Getting Started

This tutorial walks through setting up ralphify, creating a ralph with commands, and running a productive autonomous loop. By the end, you'll have a self-healing coding loop that validates its own work.

## Prerequisites

- **Python 3.11+**
- **An AI coding agent CLI** — this tutorial uses [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Install it with `npm install -g @anthropic-ai/claude-code`. Ralphify also works with [other agents](agents.md).
- **A project with a test suite** (we'll use this for the feedback loop)

## Step 1: Install ralphify

```bash
uv tool install ralphify
```

Verify it's working:

```bash
ralph --version
```

## Step 2: Create a ralph

The fastest way to scaffold a ralph is `ralph init`:

```bash
ralph init my-ralph
```

This creates `my-ralph/RALPH.md` with a ready-to-customize template including an example command, arg, and prompt. Edit the task section, [test it](#step-3-do-a-test-run), then follow [Step 4](#step-4-add-a-test-command) to add a test command — test feedback is what makes the loop self-healing.

Alternatively, use `ralph new` for AI-guided setup, or create the file manually as shown below.

!!! tip "Installing an existing ralph?"
    If someone has shared a ralph on GitHub, skip the manual setup and install it directly:

    ```bash
    ralph add owner/repo
    ```

    This installs to `.ralphify/ralphs/` so you can run it by name with `ralph run <name>`. See the [CLI reference](cli.md#ralph-add) for all source formats.

### Manual setup

Create a ralph directory and `RALPH.md` with the agent field — this is the only required frontmatter:

```markdown
---
agent: claude -p --dangerously-skip-permissions
---

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run `uv run pytest -x` before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

!!! info "What does `--dangerously-skip-permissions` do?"
    Claude Code normally asks for your approval before running shell commands, editing files, or making git commits. The `--dangerously-skip-permissions` flag disables these interactive prompts so the agent can work autonomously without waiting for input. The `-p` flag enables non-interactive ("print") mode, which reads the prompt from stdin instead of opening a chat session.

## Step 3: Do a test run

Run a single iteration to verify your setup works:

```bash
ralph run my-ralph -n 1 --log-dir ralph_logs
```

This runs a single iteration and saves the output to `ralph_logs/`. Review the log to see what the agent did:

```bash
ls ralph_logs/
cat ralph_logs/001_*.log
```

!!! tip "Add `ralph_logs/` to `.gitignore`"
    Log files are useful for debugging but shouldn't be committed:

    ```bash
    echo "ralph_logs/" >> .gitignore
    ```

If the agent produced useful work, you're ready to add test feedback.

!!! info "Something not working?"
    If the agent errored or didn't do anything useful, check [Troubleshooting](troubleshooting.md) for common issues — agent hangs, missing commands, and frontmatter mistakes are all covered there.

## Step 4: Add a test command

Commands run each iteration and their output is injected into the prompt via `{{ commands.<name> }}` placeholders. Add a test command and its placeholder:

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
---

# Prompt

## Test results

{{ commands.tests }}

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If tests are failing, fix them before starting new work.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

The `tests` command runs `uv run pytest -x` each iteration. Its output replaces `{{ commands.tests }}` in the prompt, so the agent always sees the current test results. If tests fail, the agent fixes them — that's the self-healing loop.

## Step 5: Add more commands

Add a lint command and a git log for context:

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
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

## Lint results

{{ commands.lint }}

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If tests or lint are failing, fix them before starting new work.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

## Step 6: Run the loop

Start with a few iterations to verify everything works:

```bash
ralph run my-ralph -n 3 --log-dir ralph_logs
```

Watch the output. Each iteration runs the commands, assembles the prompt with the command output, and pipes it to the agent:

```text
▶ Running: my-ralph
  3 commands · max 3 iterations

── Iteration 1 ──
  Commands: 3 ran
✓ Iteration 1 completed (45.2s)
  → ralph_logs/001_20250115-142301.log

── Iteration 2 ──
  Commands: 3 ran
✗ Iteration 2 failed with exit code 1 (23.1s)
  → ralph_logs/002_20250115-142512.log

── Iteration 3 ──
  Commands: 3 ran
✓ Iteration 3 completed (38.5s)
  → ralph_logs/003_20250115-142812.log

──────────────────────
Done: 3 iterations — 2 succeeded, 1 failed
```

If the agent breaks a test, the next iteration sees the failure output via `{{ commands.tests }}` and fixes it automatically.

Once you're confident the loop works, drop the `-n 3` to let it run indefinitely. Press `Ctrl+C` to stop.

## Step 7: Steer while it runs

The prompt body is re-read from disk every iteration. You can edit `RALPH.md` while the loop is running and the agent follows your changes on the next cycle.

When the agent does something you don't want, add a rule:

```markdown
## Rules

- Do NOT delete failing tests — fix the underlying code instead
```

When you want to shift focus, change the task:

```markdown
Read TODO.md and focus only on the API module.
```

This is the most powerful part of ralph loops — you're steering a running agent with a text file. See [Tuning a running loop](writing-prompts.md#tuning-a-running-loop) for more patterns.

!!! warning "Frontmatter changes need a restart"
    Only the **prompt body** is re-read each iteration. Frontmatter fields (`agent`, `commands`, `args`) are parsed once at startup. If you add a new command or change the agent, stop the loop with `Ctrl+C` and restart it.

## Next steps

- [Writing Prompts](writing-prompts.md) — patterns for writing effective autonomous loop prompts
- [Cookbook](cookbook.md) — copy-pasteable setups for coding, docs, research, and more
- [How it Works](how-it-works.md) — what happens inside each iteration
- [Troubleshooting](troubleshooting.md) — when things don't work as expected
- [CLI Reference](cli.md) — all commands and options
