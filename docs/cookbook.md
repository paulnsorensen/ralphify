---
description: Copy-pasteable ralphify setups for autonomous coding, documentation, codebase improvement, deep research, bug fixing, and more.
keywords: ralphify cookbook, autonomous coding recipes, RALPH.md examples, documentation loop, bug fixing loop, codebase improvement, deep research agent
---

# Cookbook

Copy-pasteable setups for common autonomous workflows. Each recipe is a real, runnable ralph from the [`cookbooks/`](https://github.com/computerlovetech/ralphify/tree/main/cookbooks) directory.

---

## Python project

A general-purpose loop for a Python project using pytest and ruff.

**`python-dev/RALPH.md`**

```markdown
--8<-- "cookbooks/python-dev/RALPH.md"
```

```bash
ralph run python-dev -n 5 --log-dir ralph_logs
```

---

## Codebase improvement

A loop that continuously improves code quality without changing functionality. It runs tests, type checking, and lint each iteration, then picks one improvement to make.

**`improve-codebase/RALPH.md`**

```markdown
--8<-- "cookbooks/improve-codebase/RALPH.md"
```

```bash
ralph run improve-codebase -n 10 --log-dir ralph_logs
ralph run improve-codebase -n 5 --focus "focus on test coverage"
```

---

## Documentation loop

A loop focused on writing and improving documentation.

**`docs/RALPH.md`**

```markdown
--8<-- "cookbooks/docs/RALPH.md"
```

```bash
ralph run docs --log-dir ralph_logs
ralph run docs --focus "focus on the API reference pages"
```

---

## Bug hunter

A loop that discovers bugs and fixes them. The agent reads the codebase, finds a real bug (edge case, off-by-one, missing validation), writes a failing test to prove it, then fixes it.

**`bug-hunter/RALPH.md`**

```markdown
--8<-- "cookbooks/bug-hunter/RALPH.md"
```

```bash
ralph run bug-hunter -n 10 --log-dir ralph_logs
ralph run bug-hunter -n 5 --focus "focus on input validation"
```

---

## Deep research

A structured research loop that builds up a report over many iterations. Uses shell scripts as commands to track maturity, show the question tree, and even run an editorial review agent that gives feedback between iterations.

This is a more advanced ralph — it uses `args` for the research topic, helper scripts (run with `./` relative to the ralph directory), and a `timeout` on the review command.

**`research/RALPH.md`**

```markdown
--8<-- "cookbooks/research/RALPH.md"
```

The helper scripts (`show-focus.sh`, `show-questions.sh`, etc.) read from the workspace files and surface key state. The `review.sh` script pipes the full workspace to a separate Claude call that acts as an editorial reviewer — giving the research agent targeted feedback each iteration.

```bash
ralph run research --workspace ai-safety --focus "current approaches to AI alignment"
```

This recipe shows several advanced patterns: commands that call scripts relative to the ralph directory (`./show-focus.sh`), a command with a `timeout`, a command that itself calls an AI agent (`review.sh` pipes to `claude -p`), and `args` used in the prompt body via `{{ args.workspace }}` placeholders.

---

## Code migration

A loop for batch code transformations — migrating from one pattern to another across a codebase. The `remaining` command counts how many files still need migration, giving the agent a clear finish line.

**`migrate/RALPH.md`**

```markdown
--8<-- "cookbooks/migrate/RALPH.md"
```

The `count-remaining.sh` script receives the pattern as an argument (resolved from `{{ args.old_pattern }}` in the `run` field) to find files that still need migration:

```bash
--8<-- "cookbooks/migrate/count-remaining.sh"
```

```bash
ralph run migrate --old_pattern "from utils import legacy_helper" \
                  --new_pattern "from core.helpers import modern_helper"
```

The `remaining` command gives the agent a shrinking counter and a list of files still needing attention, so it always knows where to focus next.

---

## Security scan

An iterative security review loop. The agent runs a scanner each iteration, picks one finding, fixes it, and verifies the fix. Good for systematically hardening a codebase.

**`security/RALPH.md`**

```markdown
--8<-- "cookbooks/security/RALPH.md"
```

```bash
ralph run security -n 10 --log-dir ralph_logs
```

Swap `bandit` for your scanner of choice — `semgrep`, `npm audit`, `cargo audit`, etc. The pattern works the same: scan, pick a finding, fix it, log it.

---

## Test coverage

A loop that systematically increases test coverage. The agent sees the current coverage percentage and a list of uncovered functions, then writes tests for one module per iteration.

**`test-coverage/RALPH.md`**

```markdown
--8<-- "cookbooks/test-coverage/RALPH.md"
```

```bash
ralph run test-coverage -n 10 --log-dir ralph_logs
ralph run test-coverage -n 5 --target "focus on error handling paths"
```

The coverage report gives the agent a clear metric to improve and shows exactly which lines are missing, so it always knows where to focus.
