---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: scan
    run: uv run bandit -r src/ -f json
  - name: open-issues
    run: cat SECURITY_FINDINGS.md
  - name: tests
    run: uv run pytest -x
  - name: types
    run: uv run ty check
  - name: lint
    run: uv run ruff check .
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

## Type checking

{{ commands.types }}

## Lint

{{ commands.lint }}

## Recent commits

{{ commands.git-log }}

If tests, types, or lint are failing, fix them before addressing security findings.

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
