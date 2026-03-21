---
description: Full CLI reference for ralphify — ralph run, ralph new, all options, user arguments, and RALPH.md frontmatter format.
keywords: ralph CLI, ralph run, ralph new, CLI reference, RALPH.md format, frontmatter options, agent arguments
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
ralph run my-ralph --stop-on-error         # Stop if agent exits non-zero
ralph run my-ralph --delay 10              # Wait 10s between iterations
ralph run my-ralph --timeout 300           # Kill agent after 5 minutes per iteration
ralph run my-ralph --log-dir ralph_logs    # Save output to log files
ralph run my-ralph -- --dir ./src          # Pass user args to the ralph
```

| Argument / Option | Short | Default | Description |
|---|---|---|---|
| `PATH` | | (required) | Path to a ralph directory containing `RALPH.md` |
| `-n` | | unlimited | Max number of iterations |
| `--stop-on-error` | `-s` | off | Stop loop if agent exits non-zero or times out |
| `--delay` | `-d` | `0` | Seconds to wait between iterations |
| `--timeout` | `-t` | none | Max seconds per iteration |
| `--log-dir` | `-l` | none | Directory for iteration log files |
| `--` | | | Separator before user arguments |

### User arguments

Extra flags after `--` are passed as user arguments to the ralph template. Use `{{ args.<name> }}` placeholders in your RALPH.md to reference them.

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
ralph run research -- --dir ./my-project --focus "performance"

# Positional args (requires args: [dir, focus] in frontmatter)
ralph run research -- ./my-project "performance"

# Mixed
ralph run research -- ./my-project --focus "performance"
```

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
| `args` | list of strings | no | Declared argument names for user arguments |

### Commands

Each command has two fields:

| Field | Type | Description |
|---|---|---|
| `name` | string | Identifier used in `{{ commands.<name> }}` placeholders |
| `run` | string | Shell command to execute each iteration |

Commands run in order. Output (stdout + stderr) is captured regardless of exit code. Commands are parsed with `shlex.split()` — no shell features (pipes, redirections, `&&`). For shell features, point the `run` field at a script.

### Placeholders

| Syntax | Resolves to |
|---|---|
| `{{ commands.<name> }}` | Output of the named command |
| `{{ args.<name> }}` | Value of the named user argument |

Unmatched placeholders resolve to an empty string.
