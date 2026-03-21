---
description: Copy-pasteable ralphify setups for Python, TypeScript, Rust, and Go autonomous coding loops — plus recipes for documentation, bug fixing, and parameterized research.
keywords: ralphify cookbook, autonomous coding recipes, Python AI agent, TypeScript AI agent, Rust AI agent, Go AI agent, RALPH.md examples, documentation loop, bug fixing loop
---

# Cookbook

Copy-pasteable setups for common autonomous coding workflows. Each recipe includes a complete `RALPH.md` — create a directory, drop the file in, and run.

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

## TypeScript / Node.js

A loop for a TypeScript project using vitest and eslint.

**`ts-dev/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: npx vitest run
  - name: lint
    run: npx eslint .
  - name: typecheck
    run: npx tsc --noEmit
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

## Lint

{{ commands.lint }}

## Type errors

{{ commands.typecheck }}

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If any checks above show failures, fix them before starting new work.

## Rules

- One task per iteration
- No `any` types — use proper TypeScript types
- No `@ts-ignore` or `eslint-disable` comments
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

```bash
ralph run ts-dev -n 5 --log-dir ralph_logs
```

---

## Rust

A loop for a Rust project using cargo.

**`rust-dev/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: cargo test
  - name: clippy
    run: cargo clippy -- -D warnings
  - name: fmt-check
    run: cargo fmt --check
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

## Clippy

{{ commands.clippy }}

## Format check

{{ commands.fmt-check }}

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If any checks above show failures, fix them before starting new work.
Run `cargo fmt` before committing if the format check fails.

## Rules

- One task per iteration
- No `#[allow(...)]` to suppress warnings — fix the underlying issue
- No `unsafe` unless absolutely required and documented
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

```bash
ralph run rust-dev -n 5 --log-dir ralph_logs
```

---

## Go

A loop for a Go project using standard tooling.

**`go-dev/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: go test ./...
  - name: vet
    run: go vet ./...
  - name: build
    run: go build ./...
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

## Vet

{{ commands.vet }}

## Build

{{ commands.build }}

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

If any checks above show failures, fix them before starting new work.

## Rules

- One task per iteration
- Run `go fmt ./...` before committing
- No `//nolint` comments — fix the underlying issue
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

```bash
ralph run go-dev -n 5 --log-dir ralph_logs
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

## Bug fixing loop

A targeted loop for fixing bugs from a list.

**`bugfix/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
---

# Prompt

## Recent commits

{{ commands.git-log }}

## Test results

{{ commands.tests }}

You are an autonomous bug-fixing agent running in a loop. Each
iteration starts with a fresh context.

Read BUGS.md for the bug list. Pick the top unfixed bug, fix it,
write a regression test, then mark it fixed.

## Rules

- One bug per iteration
- Always write a regression test that proves the fix
- Do not change unrelated code
- Commit with `fix: resolve <description>`
- Mark the fixed bug in BUGS.md
```

```bash
ralph run bugfix -n 10 --log-dir ralph_logs
```

---

## Parameterized research loop

A reusable ralph for researching any part of a codebase. Args work in both the prompt body and command `run` fields, so the same ralph adapts to any target.

**`research/RALPH.md`**

```markdown
---
agent: claude -p --dangerously-skip-permissions
args: [dir, focus]
commands:
  - name: git-log
    run: git log --oneline -10 -- {{ args.dir }}
  - name: research-so-far
    run: cat RESEARCH.md
---

## Recent changes in {{ args.dir }}

{{ commands.git-log }}

## Research so far

{{ commands.research-so-far }}

You are an autonomous research agent. Each iteration starts with
a fresh context.

Research the codebase at {{ args.dir }}.
Focus area: {{ args.focus }}

If RESEARCH.md already has findings, go deeper on areas that need
more detail rather than repeating what's there.

## Rules

- Read the code before making claims
- Cite specific file paths and line numbers
- Summarize findings in RESEARCH.md, appending to existing content
- Commit with `docs: research <topic>`
```

```bash
ralph run research -- --dir ./api --focus "error handling"
ralph run research -- --dir ./frontend --focus "state management"
```

The `git-log` command uses `{{ args.dir }}` in the `run` field to show only recent commits touching the target directory. The `research-so-far` command feeds previous findings back into the prompt so the agent builds on its earlier work instead of repeating it.
