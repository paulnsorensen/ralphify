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

Pick one improvement per iteration from the categories below (or discover your own). Research the code before changing anything.

## Improvement categories

### Code Quality
- Remove dead code, unused imports, and unreachable branches
- Eliminate code duplication by extracting shared logic into reusable functions
- Replace magic numbers and hardcoded strings with named constants
- Simplify overly complex conditionals and nested logic

### Structure & Organization
- Break up large files or functions that are doing too many things
- Move code to more logical locations (wrong file, wrong module, wrong layer)
- Standardize inconsistent naming conventions across the codebase
- Group related functionality that is scattered across unrelated files

### Robustness
- Add missing error handling and edge case coverage
- Replace silent failures with meaningful errors or logs
- Harden functions that assume inputs are always valid

### Readability
- Add or improve inline comments for non-obvious logic
- Improve variable and function names that are vague or misleading
- Normalize inconsistent formatting, spacing, or style

### Tests
- Increase test coverage for untested or undertested modules
- Remove flaky, redundant, or low-value tests
- Improve test naming so failures are self-explanatory

### Dependencies & Config
- Remove unused dependencies
- Consolidate duplicated configuration
- Replace deprecated library usage with modern equivalents

This is not an exhaustive list. If you discover opportunities for improving the codebase while not changing functionality, go for it!

## Rules

- One improvement per iteration
- Research code before creating anything new
- No placeholder code — full, working implementations only
- Fix all test failures, type errors, and lint violations before committing
- Commit with a descriptive message and push
