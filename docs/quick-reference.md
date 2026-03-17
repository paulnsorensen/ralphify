---
description: Condensed reference for ralphify commands, directory structure, frontmatter fields, and placeholder syntax — the page you bookmark and come back to.
---

# Quick Reference

Everything you need at a glance. Bookmark this page.

## CLI commands

```bash
ralph init                     # Create ralph.toml + RALPH.md
ralph init --force             # Overwrite existing ralph.toml

ralph run                      # Run loop forever (Ctrl+C to stop)
ralph run docs                 # Use named ralph from .ralphify/ralphs/docs/
ralph run -n 5                 # Run 5 iterations
ralph run -n 1 --log-dir logs  # Single iteration with output capture
ralph run --stop-on-error      # Stop if agent exits non-zero
ralph run --delay 10           # Wait 10s between iterations
ralph run --timeout 300        # Kill agent after 5 min per iteration

ralph new                      # AI-guided ralph creation
ralph new docs                 # AI-guided creation with name pre-filled

ralph --version                # Show version
```

## Directory structure

```
project-root/
├── ralph.toml                          # Agent configuration
├── RALPH.md                            # Root prompt (or use named ralphs)
└── .ralphify/
    ├── checks/                         # Global checks
    │   ├── lint/CHECK.md
    │   └── tests/CHECK.md
    ├── contexts/                       # Global contexts
    │   └── git-log/CONTEXT.md
    └── ralphs/                         # Named ralphs
        └── docs/
            ├── RALPH.md                # Ralph-specific prompt
            ├── checks/                 # Ralph-scoped checks (auto-included)
            │   └── docs-build/CHECK.md
            └── contexts/              # Ralph-scoped contexts (auto-included)
                └── doc-coverage/
                    ├── CONTEXT.md
                    └── run.sh          # Script for shell features
```

## Configuration

**`ralph.toml`**

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"              # File path or named ralph
```

## Primitive frontmatter

### CHECK.md

```markdown
---
command: uv run pytest -x       # Command to run (shlex-parsed, no shell features)
timeout: 120                    # Seconds before kill (default: 60)
enabled: true                   # Set false to skip (default: true)
---
Failure instruction text — included in prompt when check fails.
```

### CONTEXT.md

```markdown
---
command: git log --oneline -10  # Command whose stdout is captured
timeout: 30                     # Seconds before kill (default: 30)
enabled: true                   # Set false to skip (default: true)
---
Static header text — appears above command output in the prompt.
```

### RALPH.md (named ralph)

```markdown
---
description: What this ralph does
checks: [tests, lint]           # Global checks to include
contexts: [git-log]             # Global contexts to include
enabled: true                   # Set false to disable (default: true)
---
Prompt text here. Use {{ contexts.git-log }} for placement.
```

## Context placeholders

```markdown
{{ contexts.git-log }}          # Replaced with git-log context output
{{ contexts.test-status }}      # Replaced with test-status context output
```

- Each context must be referenced by name — unreferenced contexts are excluded
- Unmatched placeholders resolve to empty string (no raw `{{ }}` in output)
- Must be `contexts` (plural) — `{{ context.name }}` won't resolve

## Global vs. ralph-scoped primitives

| Type | Location | Inclusion rule |
|---|---|---|
| Global check | `.ralphify/checks/<name>/` | Must be declared in ralph frontmatter: `checks: [name]` |
| Global context | `.ralphify/contexts/<name>/` | Must be declared in ralph frontmatter: `contexts: [name]` |
| Ralph-scoped check | `.ralphify/ralphs/<ralph>/checks/<name>/` | Auto-included when that ralph runs |
| Ralph-scoped context | `.ralphify/ralphs/<ralph>/contexts/<name>/` | Auto-included when that ralph runs |

If a ralph-scoped primitive has the same name as a global one, the **local version wins**. A disabled local primitive suppresses the global one.

## Scripts vs. commands

Commands in frontmatter are parsed with `shlex.split()` — **no shell features** (pipes, redirections, `&&`, `$VAR`).

For shell features, use a script:

```bash
# .ralphify/checks/my-check/run.sh
#!/bin/bash
uv run pytest --tb=short -q 2>&1 | tail -20
```

```bash
chmod +x .ralphify/checks/my-check/run.sh
```

If both a `command` and a `run.*` script exist, the **script wins**. Any `run.*` filename works (`run.sh`, `run.py`, `run.rb`, etc.).

## Execution order

Primitives run in **alphabetical order** by directory name. Use number prefixes to control order:

```
.ralphify/checks/
├── 01-lint/CHECK.md        # First
├── 02-typecheck/CHECK.md   # Second
└── 03-tests/CHECK.md       # Third
```

## Environment variables

| Variable | Value | When set |
|---|---|---|
| `RALPH_NAME` | Name of the current ralph (e.g. `docs`) | Only when running a named ralph |

## Check failure injection

When checks fail, the next iteration's prompt gets this appended:

````markdown
## Check Failures

The following checks failed after the last iteration. Fix these issues:

### tests
**Exit code:** 1

```
FAILED tests/test_foo.py::test_bar - AssertionError
```

Your failure instruction text from CHECK.md body.
````

## Output limits

- Check and context output is truncated to **5,000 characters**
- The assembled prompt is the ralph body + resolved contexts + check failures
- Everything is re-read from disk every iteration — edit files while the loop runs

## Common patterns

### Minimal setup

```bash
ralph init && ralph run
```

### Full setup with checks

```bash
ralph init
mkdir -p .ralphify/checks/tests .ralphify/contexts/git-log
# Create CHECK.md and CONTEXT.md files
# Add frontmatter to RALPH.md: checks: [tests], contexts: [git-log]
ralph run
```

### Run on a branch

```bash
git checkout -b feature && ralph run
```

### Debug a single iteration

```bash
ralph run -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```
