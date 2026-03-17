---
description: Copy-pasteable ralphify setups for Python, TypeScript, Rust, Go, codebase migrations, documentation, test coverage, and bug fixing loops.
---

# Cookbook

Copy-pasteable setups for common autonomous coding workflows. Each recipe includes the prompt, checks, and contexts you need — create the files, run `ralph run`, and go.

All recipes use the same `ralph.toml` (created by `ralph init`):

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```

!!! tip "Use named ralphs for multiple workflows"
    Instead of editing `RALPH.md` each time, save recipes as named ralphs in `.ralphify/ralphs/` and switch between them:

    ```bash
    ralph run docs           # Documentation loop
    ralph run tests          # Test coverage loop
    ralph run bugfix         # Bug fixing loop
    ```

    See [Named ralphs](primitives.md#ralphs) for details.

---

## Python project

A general-purpose loop for a Python project using pytest and ruff.

**`RALPH.md`**

```markdown
---
checks: [tests, lint]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Fix all failing tests. Do not skip or delete tests.
Do not add `# type: ignore` or `# noqa` comments.
```

**`.ralphify/checks/lint/CHECK.md`**

```markdown
---
command: uv run ruff check .
timeout: 60
---
Fix all lint errors. Do not suppress warnings with noqa comments.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/lint .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests, lint]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous coding agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    Read TODO.md for the current task list. Pick the top uncompleted task,
    implement it fully, then mark it done.

    ## Rules

    - One task per iteration
    - No placeholder code — full, working implementations only
    - Run tests before committing
    - Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
    - Mark the completed task in TODO.md
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: uv run pytest -x
    timeout: 120
    ---
    Fix all failing tests. Do not skip or delete tests.
    Do not add `# type: ignore` or `# noqa` comments.
    EOF

    cat > .ralphify/checks/lint/CHECK.md << 'EOF'
    ---
    command: uv run ruff check .
    timeout: 60
    ---
    Fix all lint errors. Do not suppress warnings with noqa comments.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## TypeScript / Node.js project

Loop for a Node.js or TypeScript project using npm scripts.

**`RALPH.md`**

```markdown
---
checks: [tests, lint]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run `npm test` before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: npm test
timeout: 120
---
Fix all failing tests. Do not skip or delete tests.
```

**`.ralphify/checks/lint/CHECK.md`**

```markdown
---
command: npx eslint .
timeout: 60
---
Fix all lint errors. Do not disable rules with eslint-disable comments.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/lint .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests, lint]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous coding agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    Read TODO.md for the current task list. Pick the top uncompleted task,
    implement it fully, then mark it done.

    ## Rules

    - One task per iteration
    - No placeholder code — full, working implementations only
    - Run `npm test` before committing
    - Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
    - Mark the completed task in TODO.md
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: npm test
    timeout: 120
    ---
    Fix all failing tests. Do not skip or delete tests.
    EOF

    cat > .ralphify/checks/lint/CHECK.md << 'EOF'
    ---
    command: npx eslint .
    timeout: 60
    ---
    Fix all lint errors. Do not disable rules with eslint-disable comments.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## Rust project

Loop for a Rust project using cargo's built-in toolchain.

**`RALPH.md`**

```markdown
---
checks: [tests, clippy, fmt]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- All code must pass `cargo test`, `cargo clippy`, and `cargo fmt --check`
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: cargo test
timeout: 180
---
Fix all failing tests. Do not ignore or delete tests.
```

**`.ralphify/checks/clippy/CHECK.md`**

```markdown
---
command: cargo clippy -- -D warnings
timeout: 60
---
Fix all clippy warnings. Do not add `#[allow(...)]` attributes to suppress them.
```

**`.ralphify/checks/fmt/CHECK.md`**

```markdown
---
command: cargo fmt --check
timeout: 30
---
Code is not formatted. Run `cargo fmt` to fix formatting.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/clippy .ralphify/checks/fmt .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests, clippy, fmt]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous coding agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    Read TODO.md for the current task list. Pick the top uncompleted task,
    implement it fully, then mark it done.

    ## Rules

    - One task per iteration
    - No placeholder code — full, working implementations only
    - All code must pass `cargo test`, `cargo clippy`, and `cargo fmt --check`
    - Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
    - Mark the completed task in TODO.md
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: cargo test
    timeout: 180
    ---
    Fix all failing tests. Do not ignore or delete tests.
    EOF

    cat > .ralphify/checks/clippy/CHECK.md << 'EOF'
    ---
    command: cargo clippy -- -D warnings
    timeout: 60
    ---
    Fix all clippy warnings. Do not add `#[allow(...)]` attributes to suppress them.
    EOF

    cat > .ralphify/checks/fmt/CHECK.md << 'EOF'
    ---
    command: cargo fmt --check
    timeout: 30
    ---
    Code is not formatted. Run `cargo fmt` to fix formatting.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## Go project

Loop for a Go project using standard tooling.

**`RALPH.md`**

```markdown
---
checks: [tests, vet]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- All code must pass `go test ./...` and `go vet ./...`
- Use `gofmt` conventions — do not fight the formatter
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: go test ./...
timeout: 180
---
Fix all failing tests. Do not skip or delete tests.
```

**`.ralphify/checks/vet/CHECK.md`**

```markdown
---
command: go vet ./...
timeout: 60
---
Fix all issues reported by `go vet`.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/vet .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests, vet]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous coding agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    Read TODO.md for the current task list. Pick the top uncompleted task,
    implement it fully, then mark it done.

    ## Rules

    - One task per iteration
    - No placeholder code — full, working implementations only
    - All code must pass `go test ./...` and `go vet ./...`
    - Use `gofmt` conventions — do not fight the formatter
    - Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
    - Mark the completed task in TODO.md
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: go test ./...
    timeout: 180
    ---
    Fix all failing tests. Do not skip or delete tests.
    EOF

    cat > .ralphify/checks/vet/CHECK.md << 'EOF'
    ---
    command: go vet ./...
    timeout: 60
    ---
    Fix all issues reported by `go vet`.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## Bug fixing

Fix bugs from failing tests. The agent sees which tests are broken and focuses on fixing them one at a time.

**`RALPH.md`**

```markdown
---
checks: [tests]
contexts: [git-log, failing-tests]
---

# Prompt

You are an autonomous bug-fixing agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

{{ contexts.failing-tests }}

Review the failing tests above. Pick the most important failure, trace it
to the root cause in the source code, and fix it. Write a regression test
if one doesn't already exist.

## Rules

- One bug fix per iteration
- Fix the source code, not the tests — unless the test itself is wrong
- Do not skip, delete, or mark tests as expected failures
- Run the full test suite before committing to check for regressions
- Commit with `fix: resolve X that caused Y`
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Tests are still failing. Fix the root cause — do not skip or delete tests.
```

**`.ralphify/contexts/failing-tests/run.sh`** (script-based — needs shell pipes):

```bash
#!/bin/bash
uv run pytest --tb=short -q 2>&1 || true
```

**`.ralphify/contexts/failing-tests/CONTEXT.md`**

```markdown
---
timeout: 120
---
## Current test results
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

Make the script executable: `chmod +x .ralphify/contexts/failing-tests/run.sh`

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/contexts/failing-tests .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests]
    contexts: [git-log, failing-tests]
    ---

    # Prompt

    You are an autonomous bug-fixing agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    {{ contexts.failing-tests }}

    Review the failing tests above. Pick the most important failure, trace it
    to the root cause in the source code, and fix it. Write a regression test
    if one doesn't already exist.

    ## Rules

    - One bug fix per iteration
    - Fix the source code, not the tests — unless the test itself is wrong
    - Do not skip, delete, or mark tests as expected failures
    - Run the full test suite before committing to check for regressions
    - Commit with `fix: resolve X that caused Y`
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: uv run pytest -x
    timeout: 120
    ---
    Tests are still failing. Fix the root cause — do not skip or delete tests.
    EOF

    cat > .ralphify/contexts/failing-tests/run.sh << 'EOF'
    #!/bin/bash
    uv run pytest --tb=short -q 2>&1 || true
    EOF
    chmod +x .ralphify/contexts/failing-tests/run.sh

    cat > .ralphify/contexts/failing-tests/CONTEXT.md << 'EOF'
    ---
    timeout: 120
    ---
    ## Current test results
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## Improve project docs

Improve project documentation one page at a time.

**`RALPH.md`**

```markdown
---
checks: [docs-build]
contexts: [git-log]
---

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
---
The docs build failed. Fix any warnings or errors in the markdown files.
Check for broken cross-links, missing pages in mkdocs.yml nav, and
invalid admonition syntax.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/docs-build .ralphify/contexts/git-log

    cat > RALPH.md << 'EOF'
    ---
    checks: [docs-build]
    contexts: [git-log]
    ---

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
    EOF

    cat > .ralphify/checks/docs-build/CHECK.md << 'EOF'
    ---
    command: uv run mkdocs build --strict
    timeout: 60
    ---
    The docs build failed. Fix any warnings or errors in the markdown files.
    Check for broken cross-links, missing pages in mkdocs.yml nav, and
    invalid admonition syntax.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF
    ```

---

## Increase test coverage

Uses script-based checks and contexts to track and enforce a coverage threshold.

**`RALPH.md`**

```markdown
---
checks: [tests, coverage-threshold]
contexts: [coverage]
---

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
---
## Current test coverage
```

Make scripts executable: `chmod +x .ralphify/checks/coverage-threshold/run.sh .ralphify/contexts/coverage/run.sh`

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/coverage-threshold .ralphify/contexts/coverage

    cat > RALPH.md << 'EOF'
    ---
    checks: [tests, coverage-threshold]
    contexts: [coverage]
    ---

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
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: uv run pytest -x
    timeout: 120
    ---
    Fix all failing tests. Do not skip or delete existing tests.
    If a new test is failing, the test is likely wrong — fix the test,
    not the source code.
    EOF

    cat > .ralphify/checks/coverage-threshold/run.sh << 'EOF'
    #!/bin/bash
    set -e
    uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
    EOF
    chmod +x .ralphify/checks/coverage-threshold/run.sh

    cat > .ralphify/checks/coverage-threshold/CHECK.md << 'EOF'
    ---
    timeout: 120
    ---
    Coverage has dropped below the minimum threshold. Check which tests
    are missing and add them. Do not lower the threshold.
    EOF

    cat > .ralphify/contexts/coverage/run.sh << 'EOF'
    #!/bin/bash
    uv run pytest --cov=src --cov-report=term-missing -q 2>/dev/null || true
    EOF
    chmod +x .ralphify/contexts/coverage/run.sh

    cat > .ralphify/contexts/coverage/CONTEXT.md << 'EOF'
    ---
    timeout: 60
    ---
    ## Current test coverage
    EOF
    ```

---

## Codebase migration

Systematically migrate a codebase one file at a time — JavaScript to TypeScript, Python 2 to 3, CommonJS to ESM, or any file-by-file conversion where the compiler validates correctness.

This example shows JS → TypeScript. See [adaptation tips](#adapting-for-other-migrations) below for other migration types.

**`RALPH.md`**

```markdown
---
checks: [typecheck, tests]
contexts: [migration-status]
---

# Prompt

You are an autonomous migration agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.migration-status }}

Review the migration status above. Pick the next unconverted `.js` file
(start with leaf modules that have no unconverted dependents), rename it
to `.ts` (or `.tsx` if it contains JSX), and add proper TypeScript types.

## Rules

- One file per iteration
- Rename `.js` → `.ts` (or `.jsx` → `.tsx`)
- Add proper TypeScript types — avoid `any` unless truly unavoidable
- Update imports in other files that reference the converted file
- Do not change runtime behavior — the migration is a pure type-safety improvement
- Run `npx tsc --noEmit` and fix all type errors before committing
- Run the test suite before committing
- Commit with `refactor: migrate <filename> to TypeScript`
```

**`.ralphify/checks/typecheck/CHECK.md`**

```markdown
---
command: npx tsc --noEmit
timeout: 120
---
TypeScript compilation failed. Fix all type errors in the migrated file.
Do not use `@ts-ignore` or `as any` to suppress errors — add proper types.
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: npm test
timeout: 120
---
Tests are failing after the migration. The migration should not change
runtime behavior — fix the issue without altering test expectations.
```

**`.ralphify/contexts/migration-status/run.sh`** (script-based — needs shell features):

```bash
#!/bin/bash
echo "### Files remaining (.js/.jsx)"
find src -name '*.js' -o -name '*.jsx' | sort
echo ""
echo "### Files converted (.ts/.tsx)"
find src -name '*.ts' -o -name '*.tsx' | grep -v '\.d\.ts$' | sort
echo ""
echo "Remaining: $(find src -name '*.js' -o -name '*.jsx' | wc -l | tr -d ' ') files"
echo "Converted: $(find src -name '*.ts' -o -name '*.tsx' | grep -v '\.d\.ts$' | wc -l | tr -d ' ') files"
```

**`.ralphify/contexts/migration-status/CONTEXT.md`**

```markdown
---
timeout: 30
---
## Migration status
```

Make the script executable: `chmod +x .ralphify/contexts/migration-status/run.sh`

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/typecheck .ralphify/checks/tests .ralphify/contexts/migration-status

    cat > RALPH.md << 'EOF'
    ---
    checks: [typecheck, tests]
    contexts: [migration-status]
    ---

    # Prompt

    You are an autonomous migration agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.migration-status }}

    Review the migration status above. Pick the next unconverted `.js` file
    (start with leaf modules that have no unconverted dependents), rename it
    to `.ts` (or `.tsx` if it contains JSX), and add proper TypeScript types.

    ## Rules

    - One file per iteration
    - Rename `.js` → `.ts` (or `.jsx` → `.tsx`)
    - Add proper TypeScript types — avoid `any` unless truly unavoidable
    - Update imports in other files that reference the converted file
    - Do not change runtime behavior — the migration is a pure type-safety improvement
    - Run `npx tsc --noEmit` and fix all type errors before committing
    - Run the test suite before committing
    - Commit with `refactor: migrate <filename> to TypeScript`
    EOF

    cat > .ralphify/checks/typecheck/CHECK.md << 'EOF'
    ---
    command: npx tsc --noEmit
    timeout: 120
    ---
    TypeScript compilation failed. Fix all type errors in the migrated file.
    Do not use `@ts-ignore` or `as any` to suppress errors — add proper types.
    EOF

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: npm test
    timeout: 120
    ---
    Tests are failing after the migration. The migration should not change
    runtime behavior — fix the issue without altering test expectations.
    EOF

    cat > .ralphify/contexts/migration-status/run.sh << 'SCRIPT'
    #!/bin/bash
    echo "### Files remaining (.js/.jsx)"
    find src -name '*.js' -o -name '*.jsx' | sort
    echo ""
    echo "### Files converted (.ts/.tsx)"
    find src -name '*.ts' -o -name '*.tsx' | grep -v '\.d\.ts$' | sort
    echo ""
    echo "Remaining: $(find src -name '*.js' -o -name '*.jsx' | wc -l | tr -d ' ') files"
    echo "Converted: $(find src -name '*.ts' -o -name '*.tsx' | grep -v '\.d\.ts$' | wc -l | tr -d ' ') files"
    SCRIPT
    chmod +x .ralphify/contexts/migration-status/run.sh

    cat > .ralphify/contexts/migration-status/CONTEXT.md << 'EOF'
    ---
    timeout: 30
    ---
    ## Migration status
    EOF
    ```

### Adapting for other migrations

The same pattern works for any file-by-file migration where you can validate correctness automatically:

**Python 2 → Python 3:**

- Change the context script to find `print ` statements, `except Exception, e:` patterns, or files without `from __future__ import` annotations
- Use checks: `python -m py_compile <file>` for syntax, `uv run pytest` for behavior
- Prompt rule: "Use `2to3` patterns — replace `print` statements, `dict.iteritems()`, `unicode()`, etc."

**CommonJS → ESM:**

- Change the context script to find files with `require()` or `module.exports`
- Use checks: `node --check <file>` for syntax, `npm test` for behavior
- Prompt rule: "Replace `require()` with `import`, `module.exports` with `export default`, and update `package.json` if needed"

**CSS → Tailwind:**

- Change the context script to list components with external CSS imports
- Use checks: `npm run build` for build validation, visual regression tests if available
- Prompt rule: "Replace CSS classes with Tailwind utilities, remove the old CSS file when all its classes are inlined"

The key to any migration recipe is a **context that shows progress** (what's done, what's left) and a **check that validates correctness** (compiler, test suite, linter). The agent handles the tedious file-by-file work while the checks prevent regressions.

---

## Multi-ralph project setup

Use multiple named ralphs with shared global primitives and ralph-scoped overrides. This is the setup for a mature project where different workflows share common checks (tests, lint) but each ralph also has its own validation.

### Directory structure

```
.ralphify/
├── checks/                              # Global checks — shared across ralphs
│   ├── lint/
│   │   └── CHECK.md
│   └── tests/
│       └── CHECK.md
│
├── contexts/                            # Global contexts — shared across ralphs
│   └── git-log/
│       └── CONTEXT.md
│
└── ralphs/
    ├── features/                        # Feature development ralph
    │   └── RALPH.md
    │
    ├── docs/                            # Documentation ralph
    │   ├── RALPH.md
    │   └── checks/                      # Ralph-scoped check (only runs with docs)
    │       └── docs-build/
    │           └── CHECK.md
    │
    └── tests/                           # Test coverage ralph
        ├── RALPH.md
        └── contexts/                    # Ralph-scoped context (only runs with tests)
            └── coverage/
                ├── CONTEXT.md
                └── run.sh
```

### Global primitives

These are shared across all ralphs — each ralph opts in by declaring them in its frontmatter.

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Fix all failing tests. Do not skip or delete tests.
```

**`.ralphify/checks/lint/CHECK.md`**

```markdown
---
command: uv run ruff check .
timeout: 60
---
Fix all lint errors. Do not suppress warnings with noqa comments.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

### Named ralphs

Each ralph declares which global primitives it needs. Ralph-scoped primitives are auto-included.

**`.ralphify/ralphs/features/RALPH.md`** — uses both global checks and the git-log context:

```markdown
---
description: Implement features from the task list
checks: [tests, lint]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/ralphs/docs/RALPH.md`** — uses only the lint check globally, plus its own ralph-scoped docs-build check:

```markdown
---
description: Improve project documentation
checks: [lint]
contexts: [git-log]
---

# Prompt

You are an autonomous documentation agent running in a loop. Each
iteration starts with a fresh context. Your progress lives in the code
and git.

{{ contexts.git-log }}

Read the codebase and existing docs. Find the biggest gap between what
the code can do and what the docs explain. Write or improve one page
per iteration.

## Rules

- Do one meaningful documentation improvement per iteration
- No placeholder content — full, accurate, useful writing only
- Verify any code examples actually run before committing
- Commit with `docs: explain X for users who want to Y`
```

**`.ralphify/ralphs/docs/checks/docs-build/CHECK.md`** — ralph-scoped check that only runs with the docs ralph:

```markdown
---
command: uv run mkdocs build --strict
timeout: 60
---
The docs build failed. Fix any warnings or errors in the markdown files.
Check for broken cross-links and invalid admonition syntax.
```

**`.ralphify/ralphs/tests/RALPH.md`** — uses the global tests check, plus a ralph-scoped coverage context:

```markdown
---
description: Increase test coverage
checks: [tests]
contexts: [coverage]
---

# Prompt

You are an autonomous test-writing agent running in a loop. Each
iteration starts with a fresh context. Your progress lives in the code
and git.

{{ contexts.coverage }}

Find the module with the lowest coverage that has meaningful logic
worth testing. Write thorough tests for that module.

## Rules

- One module per iteration
- Write tests that verify behavior, not implementation details
- Do NOT modify source code to make it easier to test
- Commit with `test: add tests for <module name>`
```

**`.ralphify/ralphs/tests/contexts/coverage/CONTEXT.md`**

```markdown
---
timeout: 60
---
## Current test coverage
```

**`.ralphify/ralphs/tests/contexts/coverage/run.sh`**

```bash
#!/bin/bash
uv run pytest --cov=src --cov-report=term-missing -q 2>/dev/null || true
```

Make the script executable: `chmod +x .ralphify/ralphs/tests/contexts/coverage/run.sh`

### Running

Switch between ralphs at the command line:

```bash
ralph run features          # Implement features from TODO.md
ralph run docs              # Improve documentation
ralph run tests -n 5        # Write tests for 5 modules
```

### How the primitives compose

When you run `ralph run docs`, here's what happens:

1. **Global checks selected:** `lint` (declared in docs ralph frontmatter). `tests` is NOT included — the docs ralph didn't declare it.
2. **Ralph-scoped checks discovered:** `docs-build` (inside `.ralphify/ralphs/docs/checks/`). Auto-included, no declaration needed.
3. **Merged check list:** `docs-build`, `lint` — both run after each iteration.
4. **Global contexts selected:** `git-log` (declared in frontmatter).
5. **No ralph-scoped contexts** for the docs ralph.
6. **Result:** The docs agent gets lint validation and a docs build check, but doesn't waste time running the test suite. The features ralph gets both lint and tests. Each ralph gets exactly the validation it needs.

??? example "One-command setup"

    ```bash
    ralph init
    mkdir -p .ralphify/checks/tests .ralphify/checks/lint .ralphify/contexts/git-log
    mkdir -p .ralphify/ralphs/features .ralphify/ralphs/docs/checks/docs-build
    mkdir -p .ralphify/ralphs/tests/contexts/coverage

    cat > .ralphify/checks/tests/CHECK.md << 'EOF'
    ---
    command: uv run pytest -x
    timeout: 120
    ---
    Fix all failing tests. Do not skip or delete tests.
    EOF

    cat > .ralphify/checks/lint/CHECK.md << 'EOF'
    ---
    command: uv run ruff check .
    timeout: 60
    ---
    Fix all lint errors. Do not suppress warnings with noqa comments.
    EOF

    cat > .ralphify/contexts/git-log/CONTEXT.md << 'EOF'
    ---
    command: git log --oneline -10
    ---
    ## Recent commits
    EOF

    cat > .ralphify/ralphs/features/RALPH.md << 'EOF'
    ---
    description: Implement features from the task list
    checks: [tests, lint]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous coding agent running in a loop. Each iteration
    starts with a fresh context. Your progress lives in the code and git.

    {{ contexts.git-log }}

    Read TODO.md for the current task list. Pick the top uncompleted task,
    implement it fully, then mark it done.

    ## Rules

    - One task per iteration
    - No placeholder code — full, working implementations only
    - Run tests before committing
    - Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
    - Mark the completed task in TODO.md
    EOF

    cat > .ralphify/ralphs/docs/RALPH.md << 'EOF'
    ---
    description: Improve project documentation
    checks: [lint]
    contexts: [git-log]
    ---

    # Prompt

    You are an autonomous documentation agent running in a loop. Each
    iteration starts with a fresh context. Your progress lives in the code
    and git.

    {{ contexts.git-log }}

    Read the codebase and existing docs. Find the biggest gap between what
    the code can do and what the docs explain. Write or improve one page
    per iteration.

    ## Rules

    - Do one meaningful documentation improvement per iteration
    - No placeholder content — full, accurate, useful writing only
    - Verify any code examples actually run before committing
    - Commit with `docs: explain X for users who want to Y`
    EOF

    cat > .ralphify/ralphs/docs/checks/docs-build/CHECK.md << 'EOF'
    ---
    command: uv run mkdocs build --strict
    timeout: 60
    ---
    The docs build failed. Fix any warnings or errors in the markdown files.
    Check for broken cross-links and invalid admonition syntax.
    EOF

    cat > .ralphify/ralphs/tests/RALPH.md << 'EOF'
    ---
    description: Increase test coverage
    checks: [tests]
    contexts: [coverage]
    ---

    # Prompt

    You are an autonomous test-writing agent running in a loop. Each
    iteration starts with a fresh context. Your progress lives in the code
    and git.

    {{ contexts.coverage }}

    Find the module with the lowest coverage that has meaningful logic
    worth testing. Write thorough tests for that module.

    ## Rules

    - One module per iteration
    - Write tests that verify behavior, not implementation details
    - Do NOT modify source code to make it easier to test
    - Commit with `test: add tests for <module name>`
    EOF

    cat > .ralphify/ralphs/tests/contexts/coverage/CONTEXT.md << 'EOF'
    ---
    timeout: 60
    ---
    ## Current test coverage
    EOF

    cat > .ralphify/ralphs/tests/contexts/coverage/run.sh << 'EOF'
    #!/bin/bash
    uv run pytest --cov=src --cov-report=term-missing -q 2>/dev/null || true
    EOF
    chmod +x .ralphify/ralphs/tests/contexts/coverage/run.sh
    ```
