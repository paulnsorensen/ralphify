---
title: Ralph Loop Recipes
description: Copy-pasteable ralph loop setups for autonomous ML research, test coverage, code migration, security scanning, deep research, documentation, bug fixing, and codebase improvement.
keywords: ralphify cookbook, autonomous coding recipes, RALPH.md examples, documentation loop, bug fixing loop, codebase improvement, deep research agent, code migration loop, security scanning agent, test coverage automation, autoresearch, autonomous ML research
---

# Cookbook

Copy-pasteable setups for common autonomous workflows. Each recipe is a real, runnable ralph from the [`examples/`](https://github.com/computerlovetech/ralphify/tree/main/examples) directory.

All recipes use **Claude Code** as the agent. To use a different agent, swap the `agent` field — see [Using with Different Agents](agents.md).

!!! tip "User arguments in recipes"
    Many recipes accept CLI arguments like `--focus` or `--target`. These aren't built-in flags — they're **user arguments** declared in each recipe's `args` field. When you pass `--focus "test coverage"`, the value replaces `{{ args.focus }}` in the prompt. See [User Arguments](cli.md#user-arguments) for details.

---

## Run autonomous ML experiments {: #autoresearch }

An autonomous ML research loop inspired by [Karpathy's autoresearch](https://github.com/karpathy/autoresearch). The agent runs experiments on a training script to minimize validation loss — modifying code, training for 5 minutes, keeping improvements and reverting failures.

**`autoresearch/RALPH.md`**

```markdown
--8<-- "examples/autoresearch/RALPH.md"
```

The helper scripts surface experiment state each iteration:

**`autoresearch/show-results.sh`**

```bash
--8<-- "examples/autoresearch/show-results.sh"
```

**`autoresearch/show-last-run.sh`**

```bash
--8<-- "examples/autoresearch/show-last-run.sh"
```

```bash
ralph run autoresearch --train_script train.py --prepare_script prepare.py
```

```text
▶ Running: autoresearch
  2 commands · unlimited iterations

── Iteration 1 ──
  Commands: 2 ran
✓ Iteration 1 completed (312.4s)

── Iteration 2 ──
  Commands: 2 ran
✓ Iteration 2 completed (287.1s)
```

The `train_script` and `prepare_script` args let you point the ralph at any autoresearch-style project. The agent handles everything autonomously: establishing a baseline on the first iteration, then running experiments indefinitely. Each iteration is one hypothesis tested — modify the train script, train, evaluate, keep or revert.

---

## Improve code quality continuously {: #codebase-improvement }

A loop that continuously improves code quality without changing functionality. It runs tests, type checking, and lint each iteration, then picks one improvement to make.

**`improve-codebase/RALPH.md`**

```markdown
--8<-- "examples/improve-codebase/RALPH.md"
```

```bash
ralph run improve-codebase -n 5 --focus "focus on test coverage" --log-dir ralph_logs
```

```text
▶ Running: improve-codebase
  3 commands · max 5 iterations

── Iteration 1 ──
  Commands: 3 ran
✓ Iteration 1 completed (48.2s)
  → ralph_logs/001_20250115-142301.log

── Iteration 2 ──
  Commands: 3 ran
✓ Iteration 2 completed (55.7s)
  → ralph_logs/002_20250115-143112.log
```

---

## Write and improve documentation automatically {: #documentation-loop }

A loop focused on writing and improving documentation.

**`docs/RALPH.md`**

```markdown
--8<-- "examples/docs/RALPH.md"
```

```bash
ralph run docs --focus "focus on the API reference pages" --log-dir ralph_logs
```

```text
▶ Running: docs
  1 command · unlimited iterations

── Iteration 1 ──
  Commands: 1 ran
✓ Iteration 1 completed (63.5s)
  → ralph_logs/001_20250120-091502.log
```

---

## Find and fix bugs automatically {: #bug-hunter }

A loop that discovers bugs and fixes them. The agent reads the codebase, finds a real bug (edge case, off-by-one, missing validation), writes a failing test to prove it, then fixes it.

**`bug-hunter/RALPH.md`**

```markdown
--8<-- "examples/bug-hunter/RALPH.md"
```

```bash
ralph run bug-hunter -n 5 --focus "focus on input validation" --log-dir ralph_logs
```

```text
▶ Running: bug-hunter
  1 command · max 5 iterations

── Iteration 1 ──
  Commands: 1 ran
✓ Iteration 1 completed (71.3s)
  → ralph_logs/001_20250118-103045.log
```

---

## Run structured AI research loops {: #deep-research }

A structured research loop that builds up a report over many iterations. Uses shell scripts as commands to track maturity, show the question tree, and even run an editorial review agent that gives feedback between iterations.

This is a more advanced ralph — it uses `args` for the research topic, helper scripts (run with `./` relative to the ralph directory), and a `timeout` on the review command.

**`research/RALPH.md`**

```markdown
--8<-- "examples/research/RALPH.md"
```

The helper scripts (`show-focus.sh`, `show-questions.sh`, etc.) read from the workspace files and surface key state. The `review.sh` script pipes the full workspace to a separate Claude call that acts as an editorial reviewer — giving the research agent targeted feedback each iteration.

```bash
ralph run research --workspace ai-safety --focus "current approaches to AI alignment"
```

```text
▶ Running: research
  4 commands · unlimited iterations

── Iteration 1 ──
  Commands: 4 ran
✓ Iteration 1 completed (185.6s)
```

This recipe shows several advanced patterns: commands that call scripts relative to the ralph directory (`./show-focus.sh`), a command with a `timeout`, a command that itself calls an AI agent (`review.sh` pipes to `claude -p`), and `args` used in the prompt body via `{{ args.workspace }}` placeholders.

---

## Migrate code patterns across a codebase {: #code-migration }

A loop for batch code transformations — migrating from one pattern to another across a codebase. The `remaining` command counts how many files still need migration, giving the agent a clear finish line.

**`migrate/RALPH.md`**

```markdown
--8<-- "examples/migrate/RALPH.md"
```

The `count-remaining.sh` script receives the pattern as an argument (resolved from `{{ args.old_pattern }}` in the `run` field) to find files that still need migration:

```bash
--8<-- "examples/migrate/count-remaining.sh"
```

```bash
ralph run migrate --old_pattern "from utils import legacy_helper" \
                  --new_pattern "from core.helpers import modern_helper"
```

```text
▶ Running: migrate
  1 command · unlimited iterations

── Iteration 1 ──
  Commands: 1 ran
✓ Iteration 1 completed (34.8s)
```

The `remaining` command gives the agent a shrinking counter and a list of files still needing attention, so it always knows where to focus next.

---

## Automate security scanning and fixes {: #security-scan }

An iterative security review loop. The agent runs a scanner each iteration, picks one finding, fixes it, and verifies the fix. Good for systematically hardening a codebase.

**`security/RALPH.md`**

```markdown
--8<-- "examples/security/RALPH.md"
```

```bash
ralph run security -n 10 --log-dir ralph_logs
```

```text
▶ Running: security
  1 command · max 10 iterations

── Iteration 1 ──
  Commands: 1 ran
✓ Iteration 1 completed (42.9s)
  → ralph_logs/001_20250122-160830.log
```

Swap `bandit` for your scanner of choice — `semgrep`, `npm audit`, `cargo audit`, etc. The pattern works the same: scan, pick a finding, fix it, log it.

---

## Increase test coverage automatically {: #test-coverage }

A loop that systematically increases test coverage. The agent sees the current coverage percentage and a list of uncovered functions, then writes tests for one module per iteration.

**`test-coverage/RALPH.md`**

```markdown
--8<-- "examples/test-coverage/RALPH.md"
```

```bash
ralph run test-coverage -n 5 --target "focus on error handling paths" --log-dir ralph_logs
```

```text
▶ Running: test-coverage
  2 commands · max 5 iterations

── Iteration 1 ──
  Commands: 2 ran
✓ Iteration 1 completed (56.1s)
  → ralph_logs/001_20250125-140210.log
```

The coverage report gives the agent a clear metric to improve and shows exactly which lines are missing, so it always knows where to focus.

---

## Next steps

- [Writing Prompts](writing-prompts.md) — customize your recipe's prompt with patterns for task sources, constraints, and live editing
- [CLI Reference](cli.md) — all `ralph run` options (`--timeout`, `--stop-on-error`, `--delay`, user args)
- [Troubleshooting](troubleshooting.md) — when the agent hangs, commands fail, or output looks wrong
