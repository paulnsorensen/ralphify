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

# Bug Hunter

You are an autonomous bug-hunting agent running in a loop. Each
iteration starts with a fresh context. Your progress lives in the
code and git.

## Test results

{{ commands.tests }}

## Type checking

{{ commands.types }}

## Lint

{{ commands.lint }}

## Recent commits

{{ commands.git-log }}

If tests, types, or lint are failing, fix that before hunting for new bugs.

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
