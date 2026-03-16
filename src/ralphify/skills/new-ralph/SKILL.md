---
name: new-ralph
description: Create a new ralph with prompt, checks, and contexts via guided conversation
argument-hint: "[name]"
disable-model-invocation: true
---

You are helping the user create a new **ralph** — a reusable task-focused prompt with checks and contexts for autonomous AI coding loops powered by [ralphify](https://github.com/computerlovetech/ralphify).

## Ralphify primitives reference

A ralph lives at `.ralphify/ralphs/<name>/RALPH.md` and consists of:

### RALPH.md

```markdown
---
description: What this ralph does (one line)
enabled: true
---

Your prompt content here. This is piped to the agent as stdin each iteration.
```

### Checks

Checks validate the agent's work **after each iteration**. If a check fails, its output and failure instruction are appended to the next iteration's prompt.

Location: `.ralphify/ralphs/<name>/checks/<check-name>/CHECK.md`

```markdown
---
command: pytest -x
timeout: 120
enabled: true
---
Fix all failing tests. Do not skip or delete tests.
```

- `command`: parsed with `shlex.split()` — no shell features (pipes, `&&`, redirections)
- `timeout`: seconds before the check is killed (default: 60)
- `enabled`: set to `false` to skip without deleting
- Body text = failure instruction shown to the agent when the check fails
- If you need shell features, create a `run.sh` or `run.py` script in the check directory instead of using `command`

### Contexts

Contexts inject **dynamic data** into the prompt **before each iteration** — git history, coverage reports, file listings, etc.

Location: `.ralphify/ralphs/<name>/contexts/<context-name>/CONTEXT.md`

```markdown
---
command: git log --oneline -10
timeout: 30
enabled: true
---
## Recent commits
```

- Body text appears as a label above the command output
- Contexts run regardless of command exit code
- Place contexts in the prompt with `{{ contexts.context-name }}` — each context must be referenced by name

### Scripts

For commands needing shell features (pipes, redirects, `&&`), create a `run.sh` or `run.py` in the primitive directory. If both a `command` and a `run.*` script exist, the script takes precedence. Remember to `chmod +x` scripts.

### Execution order

Primitives run in alphabetical order by directory name. Use number prefixes to control order: `01-lint/`, `02-tests/`.

### Output truncation

All primitive output is truncated to 5000 characters.

## Your workflow

1. **Get the ralph name.** If `$ARGUMENTS` was provided, use it as the ralph name (convert to kebab-case if needed). Otherwise, ask the user what task they want to automate and derive a short kebab-case name.

2. **Ask clarifying questions.** Understand the task well enough to write a good prompt:
   - What does the agent need to accomplish each iteration?
   - What codebase, language, or tools are involved?
   - What validation matters? (tests, linting, type checking, builds, etc.)
   - Are there existing patterns or conventions to follow?

3. **Create the RALPH.md** at `.ralphify/ralphs/<name>/RALPH.md` with:
   - Frontmatter with a clear `description`
   - A well-structured prompt that tells the agent:
     - What it is and what it's doing
     - That each iteration starts fresh (progress lives in code and git)
     - Specific rules and constraints
     - Where to place context output (use named placeholders like `{{ contexts.name }}`)
   - Follow these prompt patterns:
     - Start with role and loop awareness: "You are an autonomous X agent running in a loop."
     - Include "Each iteration starts with a fresh context. Your progress lives in the code and git."
     - Be specific about what "one iteration" means
     - Include rules as a bulleted list
     - End with commit message conventions

4. **Create checks** at `.ralphify/ralphs/<name>/checks/<check-name>/CHECK.md`:
   - Always include relevant validation (tests, linting, type checking, builds)
   - Write clear failure instructions that tell the agent HOW to fix the problem
   - Use scripts (`run.sh`) when shell features are needed

5. **Create contexts** at `.ralphify/ralphs/<name>/contexts/<context-name>/CONTEXT.md` if useful:
   - Git log for tracking progress across iterations
   - Coverage reports for test-writing tasks
   - File listings for navigation
   - Use scripts for commands needing shell features

6. **Set permissions** — run `chmod +x` on any `run.sh` or `run.py` scripts you create.

7. **Show a summary** of everything you created (file tree with paths).

8. **Suggest testing** with: `ralph run <name> -n 1`
