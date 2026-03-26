---
title: Autonomous AI Coding Loops
description: Ralphify is a minimal CLI harness for autonomous AI coding loops. Run commands, assemble a prompt, pipe it to an AI agent, and repeat.
keywords: ralphify, AI coding agent, autonomous coding loop, CLI agent harness, while true loop, agent FOMO, agentic engineering
hide:
  - toc
---

<p align="center">
  <img src="assets/cli-banner.png" alt="Ralphify CLI banner" style="max-width: 500px;" />
</p>

<p align="center" style="font-size: 1.3em; margin-top: -0.5em;">
<strong>Put your AI coding agent in a <code>while True</code> loop and let it ship.</strong>
</p>

Ralphify is a minimal CLI harness for autonomous AI coding loops, inspired by the [Ralph Wiggum technique](https://ghuntley.com/ralph/). The core idea fits in one line:

```bash
while :; do cat RALPH.md | claude -p ; done
```

Ralphify wraps this into a proper tool — running commands that feed test results and context into each iteration, tracking progress, and handling clean shutdown.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[View Cookbook](cookbook.md){ .md-button }

---

## Install

=== "uv (recommended)"

    ```bash
    uv tool install ralphify
    ```

=== "pipx"

    ```bash
    pipx install ralphify
    ```

=== "pip"

    ```bash
    pip install ralphify
    ```

## Create a ralph and run it

```bash
ralph init my-ralph
```

This creates a directory with a `RALPH.md` template. Edit it to fit your project:

**`my-ralph/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

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

```bash
ralph run my-ralph         # Start the loop (Ctrl+C to stop)
ralph run my-ralph -n 3    # Run 3 iterations
```

### What it looks like

```text
$ ralph run my-ralph -n 3 --log-dir ralph_logs

▶ Running: my-ralph
  2 commands · max 3 iterations

── Iteration 1 ──
  Commands: 2 ran
✓ Iteration 1 completed (52.3s)
  → ralph_logs/001_20250115-142301.log

── Iteration 2 ──
  Commands: 2 ran
✗ Iteration 2 failed with exit code 1 (23.1s)
  → ralph_logs/002_20250115-142512.log

── Iteration 3 ──
  Commands: 2 ran
✓ Iteration 3 completed (41.7s)
  → ralph_logs/003_20250115-143012.log

──────────────────────
Done: 3 iterations — 2 succeeded, 1 failed
```

Edit `RALPH.md` while the loop is running — changes take effect on the next iteration.

## Or grab one from GitHub

Install a pre-built ralph from any GitHub repo and run it immediately:

```bash
ralph add owner/repo/my-ralph    # Install a ralph from GitHub
ralph run my-ralph               # Run it
```

`ralph add` fetches the ralph and installs it locally. You can install a single ralph by name, or all ralphs in a repo at once with `ralph add owner/repo`. See the [CLI reference](cli.md#ralph-add) for details.

---

## Why ralph loops?

A single agent conversation fills up its context window, slows down, and eventually loses the plot. Ralph loops solve this by resetting every iteration — the agent always starts fresh.

<div class="grid cards" markdown>

-   :material-refresh:{ .lg .middle } **Fresh context, no decay**

    ---

    Each iteration starts with a clean context window. No conversation bloat, no hallucinated memories, no degradation over time. The agent reads the current state of the codebase every loop.

-   :material-shield-check-outline:{ .lg .middle } **Commands as feedback**

    ---

    Commands run each iteration and their output feeds into the prompt. When tests fail, the agent sees the failure output and fixes it in the next iteration — a self-healing feedback loop.

-   :material-pencil-outline:{ .lg .middle } **Steer while it runs**

    ---

    The prompt is re-read every iteration. Edit `RALPH.md` while the loop runs and the agent follows your new rules on the next cycle. When it does something dumb, add a sign.

-   :material-git:{ .lg .middle } **Progress lives in git**

    ---

    Every iteration commits to git. If something goes wrong, `git log` shows exactly what happened and `git reset` rolls it back. No opaque internal state to debug or lose.

</div>

---

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (or [any agent CLI](agents.md) that accepts piped input)

---

## Next steps

- **[When to Use](when-to-use.md)** — figure out if a ralph loop fits your task
- **[Getting Started](getting-started.md)** — from install to a running loop in 10 minutes
- **[Writing Prompts](writing-prompts.md)** — patterns for effective autonomous loop prompts
- **[Cookbook](cookbook.md)** — copy-pasteable setups for coding, docs, research, and more
- **[Python API](api.md)** — embed the loop in your own automation
