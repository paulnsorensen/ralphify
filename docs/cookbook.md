---
description: Copy-pasteable ralphify setups for documentation and test coverage.
---

# Cookbook

Copy-pasteable setups for documentation and test coverage loops. Each recipe includes the prompt, checks, and contexts you need.

All recipes use the same `ralph.toml` (created by `ralph init`):

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```

---

## Improve project docs

Improve project documentation one page at a time.

**`RALPH.md`**

```markdown
# Prompt

You are an autonomous documentation agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read the codebase and existing docs. Identify the biggest gap between
what the code can do and what the docs explain. Write or improve one
page per iteration.

## Rules

- Do one meaningful documentation improvement per iteration
- Search before creating anything new
- No placeholder content — full, accurate, useful writing only
- Verify any code examples actually run before committing
- Commit with a descriptive message like `docs: explain X for users who want to Y`
```

**`.ralphify/checks/docs-build/CHECK.md`**

```markdown
---
command: uv run mkdocs build --strict
timeout: 60
enabled: true
---
The docs build failed. Fix any warnings or errors in the markdown files.
Check for broken cross-links, missing pages in mkdocs.yml nav, and
invalid admonition syntax.
```

```bash
ralph init
ralph new check docs-build
ralph new context git-log
```

---

## Increase test coverage

Uses script-based checks and contexts to track and enforce a coverage threshold.

**`RALPH.md`**

```markdown
# Prompt

You are an autonomous test-writing agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.coverage }}

Read the coverage report above. Find the module with the lowest coverage
that has meaningful logic worth testing. Write thorough tests for that
module — cover the happy path, edge cases, and error conditions.

## Rules

- One module per iteration — write all tests for it, then move on
- Write tests that verify behavior, not implementation details
- Do NOT modify source code to make it easier to test — test it as-is
- Run the full test suite before committing to check for regressions
- Commit with `test: add tests for <module name>`
- Skip modules that already have 90%+ coverage
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
enabled: true
---
Fix all failing tests. Do not skip or delete existing tests.
If a new test is failing, the test is likely wrong — fix the test,
not the source code.
```

**`.ralphify/checks/coverage-threshold/run.sh`** (script-based — needs shell features):

```bash
#!/bin/bash
set -e
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

**`.ralphify/checks/coverage-threshold/CHECK.md`**

```markdown
---
timeout: 120
enabled: true
---
Coverage has dropped below the minimum threshold. Check which tests
are missing and add them. Do not lower the threshold.
```

**`.ralphify/contexts/coverage/run.sh`**:

```bash
#!/bin/bash
uv run pytest --cov=src --cov-report=term-missing -q 2>/dev/null || true
```

**`.ralphify/contexts/coverage/CONTEXT.md`**

```markdown
---
timeout: 60
enabled: true
---
## Current test coverage
```

Make scripts executable: `chmod +x .ralphify/checks/coverage-threshold/run.sh .ralphify/contexts/coverage/run.sh`
