---
description: ralph.toml configuration format, all CLI commands (init, run, status, new), and every option with defaults and examples.
---

# Configuration & CLI Reference

## `ralph.toml`

The `ralph.toml` file configures how ralphify runs your agent. It's created by `ralph init` and lives in your project root.

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```

### Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `command` | string | yes | The agent CLI executable to run |
| `args` | list of strings | no | Arguments passed to the command |
| `ralph` | string | yes | Path to a ralph file, or a [named ralph](primitives.md#ralphs) name |

The assembled prompt is piped to the agent command as **stdin**. The full command executed each iteration is:

```
<command> <args...> < assembled_prompt
```

See [Using with Different Agents](agents.md) for setup guides for other agents.

---

## CLI Commands

### `ralph`

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

### `ralph init`

Initialize a project with `ralph.toml` and `RALPH.md`.

```bash
ralph init
ralph init --force   # Overwrite existing files
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--force` | `-f` | off | Overwrite existing `ralph.toml` and `RALPH.md` |

During init, ralphify detects your project type by looking for manifest files (`package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`). The detected type is displayed but doesn't currently change the generated configuration — all project types get the same defaults.

### `ralph run`

Start the autonomous coding loop.

```bash
ralph run                          # Run forever (Ctrl+C to stop)
ralph run docs                     # Use the "docs" named ralph
ralph run -n 5                     # Run 5 iterations
ralph run "Fix the login bug"      # Ad-hoc inline prompt
ralph run path/to/prompt.md        # Use a specific prompt file
ralph run --stop-on-error          # Stop if agent exits non-zero
ralph run --delay 10               # Wait 10s between iterations
ralph run --timeout 300            # Kill agent after 5 minutes per iteration
ralph run --log-dir ralph_logs     # Save output to log files
```

| Argument / Option | Short | Default | Description |
|---|---|---|---|
| `[PROMPT]` | | none | Ralph name, file path, or inline prompt text (see resolution below) |
| `-n` | | unlimited | Max number of iterations |
| `--stop-on-error` | `-s` | off | Stop loop if agent exits non-zero or times out |
| `--delay` | `-d` | `0` | Seconds to wait between iterations |
| `--timeout` | `-t` | none | Max seconds per iteration |
| `--log-dir` | `-l` | none | Directory for iteration log files |

The `[PROMPT]` argument is smart — it resolves in order:

1. If it matches a named ralph in `.ralphify/ralphs/` → use that ralph
2. If it's an existing file path → use as prompt file
3. Otherwise → treat as inline prompt text
4. If omitted → fall back to `ralph.toml` `agent.ralph`

Inline prompts still resolve context placeholders. When inline text is provided, `RALPH.md` doesn't need to exist.

### `ralph status`

Show current configuration, validate setup, and list all discovered primitives.

```bash
ralph status
```

This command checks:

- Whether the prompt file exists
- Whether the agent command is on PATH
- All discovered checks, contexts, and named ralphs (with enabled/disabled status)

If everything is configured correctly, it prints "Ready to run." If not, it tells you exactly what's wrong.

### `ralph new`

Create a new ralph with AI-guided setup. Installs a skill into your agent (Claude Code, Codex) and launches an interactive session where the agent guides you through creating a complete ralph — prompt, checks, and contexts — via conversation.

```bash
ralph new              # Agent helps you choose a name and build everything
ralph new my-task      # Start with a name already chosen
```

| Argument | Default | Description |
|---|---|---|
| `[NAME]` | none | Name for the new ralph. If omitted, the agent will help you choose |

The command detects your agent from `ralph.toml` `[agent].command`, or auto-detects `claude` / `codex` on PATH. The skill is installed at `.claude/skills/new-ralph/SKILL.md` (or `.agents/skills/` for Codex) and kept in sync with your installed ralphify version.

See [Primitives](primitives.md) for the full reference on checks, contexts, and ralphs.
