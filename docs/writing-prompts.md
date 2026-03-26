---
title: How to Write Prompts for Autonomous AI Coding Agents
description: Write RALPH.md prompts that make AI coding agents productive in autonomous loops — structure, self-healing patterns, anti-patterns, and copy-pasteable examples for Claude Code, Aider, and Codex.
keywords: prompt engineering AI coding agent, how to prompt autonomous agent, RALPH.md prompt guide, AI agent loop instructions, self-healing coding loop prompt, Claude Code prompt, Aider prompt, agent prompt patterns, autonomous coding prompt examples, coding agent anti-patterns
---

# Writing Prompts

!!! tldr "TL;DR"
    Every good RALPH.md has three parts: **orientation** (tell the agent it's in a loop with no memory), **task source** (point at something concrete like TODO.md), and **rules** (constraints matter more than instructions). Add commands for self-healing feedback. Edit the prompt while the loop runs to steer the agent.

Your `RALPH.md` is the single most important file in a ralph loop. A good prompt turns an AI coding agent into a productive autonomous worker. A bad one produces noise.

## The anatomy of a good RALPH.md

Every effective ralph has three parts in the prompt body:

### 1. Role and orientation

Tell the agent what it is, how it works, and where progress lives. This prevents the agent from trying to have a conversation, ask questions, or wait for input.

```markdown
You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.
```

This framing matters because the agent has **no memory between iterations**. Without it, the agent may try to pick up where it "left off" or reference work it can't see.

### 2. Task source

Point the agent at something concrete to work on. The most common mistake is being vague ("improve the codebase"). Instead, give the agent a **specific place to look** for work:

| Pattern | When to use |
|---|---|
| `Read TODO.md and pick the top uncompleted task` | When you maintain a task list |
| `Read PLAN.md and implement the next step` | For sequential multi-step work |
| `Find the module with the lowest test coverage` | For coverage-driven testing |
| `Read the codebase and find the biggest documentation gap` | For open-ended improvement |
| `Fix the failing tests shown above` | When commands feed failures back |

The key is that the agent can **find work without you telling it what to do each time**. The task source is what makes the loop autonomous.

### 3. Rules and constraints

Constraints are more important than instructions. The agent knows how to code — what it doesn't know is your project's conventions, what to avoid, and when to stop.

```markdown
## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Do not modify existing tests to make them pass
```

## Using commands for dynamic data

Commands are what make the loop self-healing. Instead of static instructions, you inject live data into every iteration.

### Test feedback loop

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
---

## Test results

{{ commands.tests }}

Fix any failing tests before starting new work.
Then read TODO.md and implement the next task.
```

The agent sees the current test results every iteration. If it broke something in the last iteration, the failure output is right there in the prompt.

### Multiple signals

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
  - name: coverage
    run: uv run pytest --cov=src --cov-report=term-missing -q
---

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

## Lint status

{{ commands.lint }}

## Coverage

{{ commands.coverage }}
```

Pick the 2-3 most useful signals. Don't dump everything — each command's output eats into the agent's context window.

### Shell features in commands

Commands are run directly, not through a shell — pipes (`|`), redirections (`2>&1`), and chaining (`&&`) don't work in the `run` field. If you need shell features, point the command at a script:

```yaml
commands:
  - name: status
    run: ./check-status.sh
```

Commands starting with `./` run relative to the ralph directory, so you can keep scripts alongside the `RALPH.md`. Other commands run from the project root. See [Troubleshooting](troubleshooting.md#command-with-pipes-or-redirections-not-working) if you hit quoting issues.

### Command timeouts

Each command has a 60-second timeout by default. If a command takes longer (slow test suites, builds, review agents), it gets killed and the output so far is used. Override it per command:

```yaml
commands:
  - name: tests
    run: uv run pytest
    timeout: 300  # 5 minutes
  - name: review
    run: ./review.sh
    timeout: 120
```

Set timeouts generously — a killed command means the agent sees truncated output. See the [command fields reference](quick-reference.md#command-fields) for all options.

## Patterns that work

### The TODO-driven loop

Maintain a `TODO.md` that the agent reads and updates each iteration.

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
---

{{ commands.tests }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If tests are failing, fix them before starting new work.

## Rules

- One task per iteration
- No placeholder code — full implementations only
- Commit with a descriptive message
- Mark the completed task in TODO.md
```

**Why it works:** The agent always knows what to do next. You control priority by reordering the list. You can add tasks while the loop runs.

### The self-healing loop

Rely on command output to define "done" and let failures guide the agent.

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: lint
    run: uv run ruff check .
  - name: typecheck
    run: uv run mypy src/
---

{{ commands.tests }}

{{ commands.lint }}

{{ commands.typecheck }}

Read PLAN.md and implement the next incomplete step. If any of the
commands above show failures, fix those first before moving on.

## Rules

- Fix command failures before starting new work
- One step per iteration
- Commit each completed step separately
```

**Why it works:** Failed commands automatically show their output. The agent sees exactly what broke and fixes it. You don't need to write error-handling instructions for every possible failure.

### The edit-while-running loop

The agent re-reads `RALPH.md` every iteration. You can steer the loop in real time.

```markdown
---
agent: claude -p --dangerously-skip-permissions
---

You are an autonomous agent improving this project's documentation.

## Current focus

<!-- Edit this section while the loop runs to steer the agent -->
Focus on the API reference docs. Each endpoint needs a working
curl example and a description of the response format.

## Rules

- One page per iteration
- Verify all code examples run correctly
- Commit with `docs: ...` prefix
```

**Why it works:** When the agent does something you don't want, you add a constraint. When you want it to shift focus, you edit the "Current focus" section. The next iteration picks up your changes immediately.

### Parameterized ralphs

Use user arguments to make a ralph reusable across different projects or configurations. Args work in both the prompt body and command `run` fields:

```markdown
---
agent: claude -p --dangerously-skip-permissions
args: [dir, focus]
commands:
  - name: git-log
    run: git log --oneline -10 -- {{ args.dir }}
  - name: research-so-far
    run: cat RESEARCH.md
---

## Recent changes in {{ args.dir }}

{{ commands.git-log }}

## Research so far

{{ commands.research-so-far }}

Research the codebase at {{ args.dir }}.

Focus area: {{ args.focus }}

## Rules

- Read the code before making claims
- Cite specific file paths and line numbers
- Summarize findings in RESEARCH.md
```

Run the same ralph against different targets:

```bash
ralph run research --dir ./api --focus "error handling"
ralph run research --dir ./frontend --focus "state management"
```

The `git-log` command uses `{{ args.dir }}` to show only commits touching the target directory — the same arg value is resolved in both command `run` strings and the prompt body.

### ralph context placeholders

Three `{{ ralph.* }}` placeholders are available automatically — no frontmatter needed:

| Placeholder | Value |
|---|---|
| `{{ ralph.name }}` | ralph directory name (e.g. `my-ralph`) |
| `{{ ralph.iteration }}` | Current iteration number (1-based) |
| `{{ ralph.max_iterations }}` | Total iterations if `-n` was set, empty otherwise |

Use these to change the agent's behavior based on where it is in the run, or to include the ralph name in output files and commit messages.

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
---

{{ commands.tests }}

This is iteration {{ ralph.iteration }} of {{ ralph.max_iterations }}.

If this is the last iteration, wrap up: clean up TODOs, run a final
check, and write a short summary of what was accomplished in PROGRESS.md.
Otherwise, read TODO.md and implement the next task.

## Rules

- One task per iteration
- Fix failing tests before starting new work
- Commit with a descriptive message
```

```bash
ralph run my-ralph -n 10
```

**Why it works:** Without this, the agent treats every iteration identically. With iteration awareness, you can tell it to be more exploratory early on and more conservative as the run winds down — or to write a summary on the final pass so you come back to a clean status report.

## Anti-patterns that waste iterations

### "Improve the codebase" — vague prompts with no task source

```markdown
<!-- DON'T -->
Improve the codebase. Make things better.
```

The agent doesn't know what "better" means to you. Always point at a concrete task source.

### "Do five things at once" — overloading a single iteration

```markdown
<!-- DON'T -->
Implement user authentication, add rate limiting, write tests for
both, update the API docs, and deploy to staging.
```

One iteration = one task. If the agent tries to do five things, it'll do all of them poorly.

### "Implement and commit" — no validation before committing

```markdown
<!-- DON'T -->
Read TODO.md, implement the next task, and commit.
```

Without "run tests before committing" or a test command, the agent will commit broken code. Always include validation, either in the prompt text or via commands.

### "Fix bugs" — no commit instructions

```markdown
<!-- DON'T -->
Fix bugs from the issue tracker.
```

Ralphify doesn't commit for the agent — the agent must do it. Without explicit commit instructions, some agents won't commit at all, and progress is lost when the next iteration starts fresh.

!!! tip "Co-author credit"
    By default, ralphify appends an instruction to each prompt asking the agent to include a `Co-authored-by: Ralphify <noreply@ralphify.co>` trailer in commit messages. This gives visibility into which commits came from a ralph loop. To disable it, set `credit: false` in frontmatter.

## Tuning a running loop

The most powerful feature of ralph loops is that you can edit `RALPH.md` while the loop is running. Here's how to use this effectively:

**When the agent does something dumb, add a sign.** This is the core insight from the [Ralph Wiggum technique](https://ghuntley.com/ralph/). If the agent keeps deleting tests instead of fixing them:

```markdown
## Rules
- Do NOT delete or skip failing tests — fix the code instead
```

**When the agent gets stuck in a loop,** it's usually because the prompt is ambiguous about what to do when something fails. Add explicit fallback instructions:

```markdown
- If you can't fix a failing test after one attempt, move on to the next task
  and leave a TODO comment explaining the issue
```

**When you want to shift focus,** edit the task source. Change "Read TODO.md" to "Focus only on the API module" and the next iteration follows the new direction.

**When the agent is too ambitious,** tighten the scope constraint:

```markdown
- Touch at most 3 files per iteration
- Do not refactor code that isn't directly related to the current task
```

### Annotate your prompt with HTML comments

??? note "HTML comments are stripped before the prompt reaches the agent"
    HTML comments in your RALPH.md are automatically stripped during prompt assembly — they never reach the agent and don't waste context window. Use them to annotate why rules were added, what to change next, or when to remove a temporary constraint:

    ```markdown
    <!-- Added 2025-01-20: agent kept deleting tests, so added the rule below -->

    ## Rules

    - Do NOT delete failing tests — fix the underlying code instead

    <!-- TODO: remove the coverage command once we hit 80% -->
    ```

    You can freely add and edit comments while the loop runs — they're stripped every iteration.

## How long should your prompt be?

Keep your prompt focused. A long prompt eats into the agent's context window, leaving less room for the actual codebase.

- **Core prompt:** 20-50 lines is the sweet spot
- **Commands:** 2-3 signals max — don't add commands whose output the agent doesn't need
- **Command output:** Can be long, but consider scripts that filter to the relevant lines if your commands produce verbose output

## Next steps

- [Getting Started](getting-started.md) — set up your first loop
- [Cookbook](cookbook.md) — copy-pasteable setups for common use cases
- [CLI Reference](cli.md) — all commands and options
