---
description: Copy-pasteable ralphify setups for autonomous coding, documentation, codebase improvement, deep research, bug fixing, and more.
keywords: ralphify cookbook, autonomous coding recipes, RALPH.md examples, documentation loop, bug fixing loop, codebase improvement, deep research agent
---

# Cookbook

Copy-pasteable setups for common autonomous workflows. Each recipe includes a complete `RALPH.md` — create a directory, drop the file in, and run.

---

## Python project

A general-purpose loop for a Python project using pytest and ruff.

**`python-dev/RALPH.md`**

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
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
- Do not add `# type: ignore` or `# noqa` comments
```

```bash
ralph run python-dev -n 5 --log-dir ralph_logs
```

---

## Codebase improvement

A loop that continuously improves code quality without changing functionality. It runs tests, type checking, and lint each iteration, then picks one improvement to make.

**`improve-codebase/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: types
    run: uv run ty check
  - name: lint
    run: uv run ruff check .
  - name: git-log
    run: git log --oneline -10
args:
  - focus
---

# Improve Codebase

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Recent changes

{{ commands.git-log }}

## Test results

{{ commands.tests }}

If any tests are failing above, fix them before doing anything else.

## Type checking

{{ commands.types }}

## Lint

{{ commands.lint }}

Fix any type errors or lint violations above before making new changes.

## Task

Make improvements to this codebase without changing any functionality.
{{ args.focus }}

Pick one improvement per iteration. Research the code before changing
anything.

## Improvement categories

- Remove dead code, unused imports, unreachable branches
- Eliminate duplication by extracting shared logic
- Simplify overly complex conditionals and nested logic
- Break up large files or functions doing too many things
- Add missing error handling and edge case coverage
- Improve variable and function names that are vague or misleading
- Increase test coverage for untested modules

## Rules

- One improvement per iteration
- Research code before creating anything new
- No placeholder code — full, working implementations only
- Fix all test failures, type errors, and lint violations before committing
- Commit with a descriptive message and push
```

```bash
ralph run improve-codebase -n 10 --log-dir ralph_logs
ralph run improve-codebase -n 5 -- --focus "focus on test coverage"
```

---

## Documentation loop

A loop focused on writing and improving documentation.

**`docs/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: docs-build
    run: uv run mkdocs build --strict
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Docs build

{{ commands.docs-build }}

You are an autonomous documentation agent running in a loop. Each
iteration starts with a fresh context.

Read PLAN.md for the documentation plan. Pick the next incomplete page,
write it fully, then mark it done.

If the docs build fails, fix the errors before moving on.

## Rules

- One page per iteration
- Include working code examples
- Commit with `docs: ...` prefix
- Mark the completed item in PLAN.md
```

```bash
ralph run docs --log-dir ralph_logs
```

---

## Bug hunter

A loop that discovers bugs and fixes them. The agent reads the codebase, finds a real bug (edge case, off-by-one, missing validation), writes a failing test to prove it, then fixes it.

**`bug-hunter/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
args:
  - focus
---

# Bug Hunter

You are an autonomous bug-hunting agent running in a loop. Each
iteration starts with a fresh context. Your progress lives in the
code and git.

## Test results

{{ commands.tests }}

## Recent commits

{{ commands.git-log }}

If tests are failing, fix them before hunting for new bugs.

## Task

Find and fix a real bug in this codebase.
{{ args.focus }}

Each iteration:

1. **Read code** — pick a module and read it carefully. Look for
   edge cases, off-by-one errors, missing validation, incorrect
   error handling, race conditions, or logic errors.
2. **Write a failing test** — prove the bug exists with a test that
   fails on the current code.
3. **Fix the bug** — make the test pass with a minimal fix.
4. **Verify** — all existing tests must still pass.

## Rules

- One bug per iteration
- The bug must be real — do not invent hypothetical issues
- Always write a regression test before fixing
- Do not change unrelated code
- Commit with `fix: resolve <description>`
```

```bash
ralph run bug-hunter -n 10 --log-dir ralph_logs
ralph run bug-hunter -n 5 -- --focus "focus on input validation"
```

---

## Deep research

A structured research loop that builds up a report over many iterations. Uses shell scripts as commands to track maturity, show the question tree, and even run an editorial review agent that gives feedback between iterations.

This is a more advanced ralph — it uses `args` for the research topic, helper scripts (run with `./` relative to the ralph directory), and a `timeout` on the review command.

**`research/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: git-log
    run: git log --oneline -15
  - name: last-diff
    run: git diff --stat HEAD~1
  - name: scratchpad
    run: ./show-focus.sh
  - name: questions
    run: ./show-questions.sh
  - name: outline
    run: ./show-outline.sh
  - name: maturity
    run: ./show-maturity.sh
  - name: review
    run: ./review.sh
    timeout: 120
args:
  - workspace
  - focus
---

# Deep Research

You are an autonomous research agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in files and git.

## Your mission

{{ args.focus }}

## Editorial review

{{ commands.review }}

Pay close attention to the review above. It's written by an editor who
can see your full body of work.

## State

{{ commands.git-log }}
{{ commands.last-diff }}
{{ commands.scratchpad }}
{{ commands.questions }}
{{ commands.outline }}
{{ commands.maturity }}

## Workspace

Work within `{{ args.workspace }}/`. Structure:

- `REPORT.md` — executive overview + chapter table of contents (<150 lines)
- `chapters/NN-slug.md` — deep-dive chapter files
- `notes/` — `questions.md`, `sources.md`, `insights.md`, `scratchpad.md`

## Each iteration

1. **Orient** — read the editorial review and state above
2. **Decide: research or refine?** Every 3-4 iterations, skip research
   and tighten prose, merge overlapping sections, restructure chapters
3. **Research** — pick ONE question. Go deep. Use web search. Log sources
4. **Capture** — update questions, insights, scratchpad
5. **Write** — findings go into the appropriate chapter
6. **Commit and push**

## Rules

- ONE focused thread per iteration. Depth over breadth.
- Every source gets logged with URL, author, and relevance rating
- Do not fabricate sources. Note contradictions when found.
```

The helper scripts (`show-focus.sh`, `show-questions.sh`, etc.) read from the workspace files and surface key state. The `review.sh` script pipes the full workspace to a separate Claude call that acts as an editorial reviewer — giving the research agent targeted feedback each iteration.

```bash
ralph run research -- --workspace ai-safety --focus "current approaches to AI alignment"
```

This recipe shows several advanced patterns: commands that call scripts relative to the ralph directory (`./show-focus.sh`), a command with a `timeout`, a command that itself calls an AI agent (`review.sh` pipes to `claude -p`), and `args` used in the prompt body via `{{ args.workspace }}` placeholders.

---

## Code migration

A loop for batch code transformations — migrating from one pattern to another across a codebase. The `remaining` command counts how many files still need migration, giving the agent a clear finish line.

**`migrate/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: remaining
    run: ./count-remaining.sh {{ args.old_pattern }}
  - name: git-log
    run: git log --oneline -10
args:
  - old_pattern
  - new_pattern
---

# Code Migration

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Migration spec

Migrate all usages of `{{ args.old_pattern }}` to `{{ args.new_pattern }}`.

## Remaining files

{{ commands.remaining }}

## Test results

{{ commands.tests }}

## Recent commits

{{ commands.git-log }}

If tests are failing, fix them before migrating more files.

## Rules

- Migrate 1-3 files per iteration — small batches that stay green
- Run tests after each change to catch breakage early
- Do not change behavior — only update the pattern
- Commit with `refactor: migrate <file> from old_pattern to new_pattern`
- If a file needs more than a mechanical replacement, note it in
  MIGRATION_NOTES.md and skip it
```

The `count-remaining.sh` script receives the pattern as an argument (resolved from `{{ args.old_pattern }}` in the `run` field) to find files that still need migration:

```bash
#!/bin/bash
pattern="$1"
files=$(grep -rl "$pattern" src/ 2>/dev/null)
count=$(echo "$files" | grep -c . 2>/dev/null || echo 0)
echo "$count files remaining"
echo "$files" | head -20
```

```bash
ralph run migrate -- --old_pattern "from utils import legacy_helper" \
                     --new_pattern "from core.helpers import modern_helper"
```

The `remaining` command gives the agent a shrinking counter and a list of files still needing attention, so it always knows where to focus next.

---

## Security scan

An iterative security review loop. The agent runs a scanner each iteration, picks one finding, fixes it, and verifies the fix. Good for systematically hardening a codebase.

**`security/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: scan
    run: uv run bandit -r src/ -f json
  - name: open-issues
    run: cat SECURITY_FINDINGS.md
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
---

# Security Scan

You are an autonomous security agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Scanner results

{{ commands.scan }}

## Open findings

{{ commands.open-issues }}

## Test results

{{ commands.tests }}

## Recent commits

{{ commands.git-log }}

If tests are failing, fix them before addressing security findings.

## Task

Review the scanner results above. Pick one finding and fix it. If a
finding is a false positive, document why in SECURITY_FINDINGS.md and
mark it as dismissed.

If no scanner findings remain, do a manual review: read one module,
look for injection risks, auth bypasses, or unsafe data handling, and
fix or document what you find.

## Rules

- One finding per iteration
- Always verify the fix doesn't break tests
- Log every finding (fixed or dismissed) in SECURITY_FINDINGS.md
  with: severity, location, description, resolution
- Do not suppress scanner warnings — fix the underlying issue
- Commit with `security: fix <description>`
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
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: coverage
    run: uv run pytest --cov=src --cov-report=term-missing -q
  - name: git-log
    run: git log --oneline -10
args:
  - target
---

# Test Coverage

You are an autonomous testing agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Current coverage

{{ commands.coverage }}

## Recent commits

{{ commands.git-log }}

## Task

Increase test coverage for this project.
{{ args.target }}

Pick the module with the most missing lines from the coverage report
above. Read the source code, understand what it does, and write
meaningful tests that exercise the uncovered paths.

## Rules

- One module per iteration
- Write tests that verify behavior, not just hit lines — assert
  return values, side effects, and error cases
- Do not mock things unnecessarily — prefer real objects when feasible
- Do not add `# pragma: no cover` comments
- All existing tests must still pass after your changes
- Commit with `test: add coverage for <module>`
```

```bash
ralph run test-coverage -n 10 --log-dir ralph_logs
ralph run test-coverage -n 5 -- --target "focus on error handling paths"
```

The coverage report gives the agent a clear metric to improve and shows exactly which lines are missing, so it always knows where to focus.
