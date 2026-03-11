# CLI Reference

## `ralph`

With no subcommand, prints the banner and help text.

```bash
ralph --version   # Show version
ralph --help      # Show help
```

## `ralph init`

Initialize a project with `ralph.toml` and `PROMPT.md`.

```bash
ralph init
ralph init --force   # Overwrite existing files
```

## `ralph run`

Start the autonomous coding loop.

```bash
ralph run                          # Run forever (Ctrl+C to stop)
ralph run -n 5                     # Run 5 iterations
ralph run --stop-on-error          # Stop if agent exits non-zero
ralph run --delay 10               # Wait 10s between iterations
ralph run --timeout 300            # Kill agent after 5 minutes per iteration
ralph run --log-dir ralph_logs     # Save output to log files
```

| Option | Short | Default | Description |
|---|---|---|---|
| `--n` | `-n` | unlimited | Max number of iterations |
| `--stop-on-error` | `-s` | off | Stop loop if agent exits non-zero |
| `--delay` | `-d` | `0` | Seconds to wait between iterations |
| `--timeout` | `-t` | none | Max seconds per iteration |
| `--log-dir` | `-l` | none | Directory for iteration log files |

## `ralph status`

Show current configuration, validate setup, and list all discovered primitives.

```bash
ralph status
```

## `ralph new`

Scaffold new primitives. Each command creates a directory under `.ralph/` with a template file.

```bash
ralph new check <name>         # Create .ralph/checks/<name>/CHECK.md
ralph new instruction <name>   # Create .ralph/instructions/<name>/INSTRUCTION.md
ralph new context <name>       # Create .ralph/contexts/<name>/CONTEXT.md
```
