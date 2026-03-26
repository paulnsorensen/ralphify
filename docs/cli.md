---
title: Ralph CLI Reference
description: Full CLI reference for ralphify — ralph run, ralph init, ralph new, all options, user arguments, and RALPH.md frontmatter format.
keywords: ralph CLI, ralph run, ralph init, ralph new, CLI reference, RALPH.md format, frontmatter options, agent arguments
---

# CLI Reference

## `ralph`

With no subcommand, prints the banner and help text.

```bash
ralph            # Show banner and help
ralph --version  # Show version
ralph --help     # Show help
```

| Option | Short | Description |
|---|---|---|
| `--version` | `-V` | Show version and exit |
| `--install-completion` | | Install tab completion for your current shell |
| `--show-completion` | | Print the completion script (for manual setup) |
| `--help` | | Show help and exit |

### Shell completion

```bash
ralph --install-completion bash   # or zsh, fish
```

Restart your shell after installing. Use `--show-completion` to print the script for manual setup.

---

## `ralph run`

Start the autonomous coding loop.

```bash
ralph run my-ralph                         # Run forever (Ctrl+C to stop)
ralph run my-ralph -n 5                    # Run 5 iterations
ralph run my-ralph --stop-on-error         # Stop if agent exits non-zero or times out
ralph run my-ralph --delay 10              # Wait 10s between iterations
ralph run my-ralph --timeout 300           # Kill agent after 5 minutes per iteration
ralph run my-ralph --log-dir ralph_logs    # Save output to log files
ralph run my-ralph --dir ./src             # Pass user args to the ralph
```

| Argument / Option | Short | Default | Description |
|---|---|---|---|
| `PATH` | | (required) | Path to a ralph directory containing `RALPH.md`, or a direct path to a `RALPH.md` file |
| `-n` | | unlimited | Max number of iterations |
| `--stop-on-error` | `-s` | off | Stop loop if agent exits non-zero or times out |
| `--delay` | `-d` | `0` | Seconds to wait between iterations |
| `--timeout` | `-t` | none | Max seconds per iteration |
| `--log-dir` | `-l` | none | Directory for iteration log files |

### User arguments

User arguments are passed as named flags after the ralph path. Use `{{ args.<name> }}` placeholders in your RALPH.md to reference them.

User arguments must be declared in the `args` frontmatter field:

```markdown
---
agent: claude -p --dangerously-skip-permissions
args: [dir, focus]
---

Research the codebase at {{ args.dir }}.
Focus area: {{ args.focus }}
```

```bash
# Named flags
ralph run research --dir ./my-project --focus "performance"

# Equals syntax works too
ralph run research --dir=./my-project --focus="performance"

# Positional args (requires args: [dir, focus] in frontmatter)
ralph run research ./my-project "performance"

# Mixed — positional args skip names already provided via flags
ralph run research --focus "performance" ./my-project
# dir="./my-project", focus="performance"

# -- ends flag parsing — everything after is positional
ralph run research -- --verbose ./src
# dir="--verbose", focus="./src"
```

Use `--` when a positional value starts with `--` and would otherwise be parsed as a flag.

Missing args resolve to an empty string.

---

## `ralph init`

Scaffold a new ralph with a ready-to-customize template. No AI agent required.

```bash
ralph init my-task      # Creates my-task/RALPH.md with a generic template
ralph init              # Creates RALPH.md in the current directory
```

| Argument | Default | Description |
|---|---|---|
| `[NAME]` | none | Directory name. If omitted, creates RALPH.md in the current directory |

The generated template includes an example command (`git-log`), an example arg (`focus`), and a prompt body with placeholders for both. Edit it, then run `ralph run`.

Errors if `RALPH.md` already exists at the target location.

---

## `ralph new`

Create a new ralph with AI-guided setup. Launches an interactive session where the agent guides you through creating a complete ralph via conversation.

```bash
ralph new              # Agent helps you choose a name and build everything
ralph new my-task      # Start with a name already chosen
```

| Argument | Default | Description |
|---|---|---|
| `[NAME]` | none | Name for the new ralph. If omitted, the agent will help you choose |

The command detects your agent and installs a skill to guide the creation process.

---

## `ralph add`

Add a ralph from a GitHub repository. Installs it to `.ralphify/ralphs/<name>/` so you can run it by name.

```bash
ralph add owner/repo                    # Install repo as a ralph (or all ralphs in the repo)
ralph add owner/repo/ralph-name         # Install a specific ralph by name
ralph add https://github.com/owner/repo # Full GitHub URL also works
```

| Argument | Default | Description |
|---|---|---|
| `SOURCE` | required | GitHub source: `owner/repo` or `owner/repo/ralph-name` |

**How it resolves:**

- `owner/repo` — if the repo root contains `RALPH.md`, installs it as a single ralph named after the repo. Otherwise, finds and installs all ralphs in the repo.
- `owner/repo/ralph-name` — searches the repo for a directory named `ralph-name` containing `RALPH.md`. If multiple matches are found, prints the paths and asks you to use the full subpath to disambiguate.

After adding, run the ralph by name:

```bash
ralph run ralph-name
```

---

## RALPH.md format

The `RALPH.md` file is the single configuration and prompt file for a ralph. It uses YAML frontmatter for settings and the body for the prompt text.

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
args: [dir, focus]
---

# Prompt body

{{ commands.tests }}

{{ commands.git-log }}

Your instructions here. Reference args with {{ args.dir }}.
```

### Frontmatter fields

| Field | Type | Required | Description |
|---|---|---|---|
| `agent` | string | yes | The full agent command to pipe the prompt to |
| `commands` | list | no | Commands to run each iteration (each has `name` and `run`) |
| `args` | list of strings | no | Declared argument names for user arguments. Letters, digits, hyphens, and underscores only. |
| `credit` | bool | no | Append co-author trailer instruction to prompt (default: `true`) |

### Commands

Each command has these fields:

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | (required) | Identifier used in `{{ commands.<name> }}` placeholders. Letters, digits, hyphens, and underscores only. |
| `run` | string | (required) | Shell command to execute each iteration (supports `{{ args.<name> }}` placeholders). Commands starting with `./` run from the ralph directory; others run from the project root. |
| `timeout` | number | `60` | Max seconds before the command is killed |

Commands run in order. Output (stdout + stderr) is captured regardless of exit code. Commands are parsed with `shlex.split()` — no shell features (pipes, redirections, `&&`). For shell features, point the `run` field at a script.

If a command exceeds its timeout, the process is killed and the captured output up to that point is used.

### Placeholders

| Syntax | Resolves to |
|---|---|
| `{{ commands.<name> }}` | Output of the named command |
| `{{ args.<name> }}` | Value of the named user argument |
| `{{ ralph.name }}` | Ralph directory name (e.g. `my-ralph`) |
| `{{ ralph.iteration }}` | Current iteration number (1-based) |
| `{{ ralph.max_iterations }}` | Total iterations if `-n` was set, empty otherwise |

`ralph.*` placeholders are automatically available — no frontmatter configuration needed.

Unmatched placeholders resolve to an empty string.
