---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: remaining
    run: ./count-remaining.sh {{ args.old_pattern }}
  - name: types
    run: uv run ty check
  - name: lint
    run: uv run ruff check .
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

## Type checking

{{ commands.types }}

## Lint

{{ commands.lint }}

## Recent commits

{{ commands.git-log }}

If tests, types, or lint are failing, fix them before migrating more files.

## Rules

- Migrate 1-3 files per iteration — small batches that stay green
- Run tests after each change to catch breakage early
- Do not change behavior — only update the pattern
- Commit with `refactor: migrate <file> from old_pattern to new_pattern`
- If a file needs more than a mechanical replacement, note it in
  MIGRATION_NOTES.md and skip it
