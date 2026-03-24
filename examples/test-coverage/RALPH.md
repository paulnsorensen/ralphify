---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: coverage
    run: uv run pytest --cov=src --cov-report=term-missing -q
  - name: types
    run: uv run ty check
  - name: lint
    run: uv run ruff check .
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

## Lint

{{ commands.lint }}

## Recent commits

{{ commands.git-log }}

## Type checking

{{ commands.types }}

Fix any type errors or lint violations above before writing new tests.

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
