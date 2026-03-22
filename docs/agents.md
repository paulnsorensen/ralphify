---
title: Using Ralph Loops with Different Agents
description: Configure ralphify with Claude Code, Aider, Codex CLI, or any custom agent. Includes setup guides, agent comparison table, and wrapper script examples.
keywords: Claude Code agent, Aider agent, Codex CLI, AI coding agents, agent configuration, ralphify agents, custom agent wrapper
---

# Using with Different Agents

Ralphify works with **any CLI that reads a prompt from stdin and exits when done**. Claude Code is the default, but you can use any tool that follows this contract.

This page shows how to configure the `agent` field in your RALPH.md for popular agents and how to write your own wrapper.

## Agent comparison

| Agent | Stdin support | Streaming | `ralph new` support | Wrapper needed |
|---|---|---|---|---|
| [Claude Code](#claude-code) | Native (`-p`) | Yes — real-time activity tracking | Yes | No |
| [Aider](#aider) | Via bash wrapper | No | No | Yes (`bash -c`) |
| [Codex CLI](#codex-cli) | Native (`exec`) | No | Yes | No |
| [Custom](#custom-wrapper-script) | You implement it | No | No | Yes (script) |

If you're not sure which to pick: **start with Claude Code.** It has the deepest integration, the best autonomous coding capabilities, and is the default.

## What ralphify needs from an agent

Every iteration, ralphify runs your agent like this:

```
echo "<assembled prompt>" | <agent command>
```

Your agent must:

1. **Read a prompt from stdin** — the full assembled prompt is piped in
2. **Do work in the current directory** — edit files, run commands, make commits
3. **Exit when done** — exit code 0 means success, non-zero means failure

That's it. No special protocol, no API — just stdin in, work done, process exits.

## Claude Code

The default and recommended agent.

```markdown
---
agent: claude -p --dangerously-skip-permissions
---
```

| Flag | Purpose |
|---|---|
| `-p` | Non-interactive mode — reads prompt from stdin, prints output, exits |
| `--dangerously-skip-permissions` | Skips approval prompts so the agent can work autonomously |

Install Claude Code:

```bash
npm install -g @anthropic-ai/claude-code
```

!!! info "Why `--dangerously-skip-permissions`?"
    Without this flag, Claude Code pauses to ask for approval before editing files, running commands, or making commits. In an autonomous loop, nobody is there to approve — so the agent would hang forever. Commands in your RALPH.md act as your guardrails instead.

### Automatic streaming mode

When ralphify detects that the agent command starts with `claude`, it automatically adds `--output-format stream-json --verbose` to the command. You don't need to add these flags yourself.

This enables ralphify to:

- Parse Claude Code's structured JSON output line by line
- Track agent activity in real time
- Extract the final result text from the agent's response

## Aider

[Aider](https://aider.chat) is an AI pair-programming tool that works with multiple LLM providers.

```markdown
---
agent: bash -c 'aider --yes-always --no-auto-commits --message "$(cat -)"'
---
```

| Flag | Purpose |
|---|---|
| `--yes-always` | Auto-approve all changes (no interactive prompts) |
| `--no-auto-commits` | Let your prompt control when commits happen |
| `--message "..."` | Pass the prompt as a message instead of stdin |

!!! note "Why the bash wrapper?"
    Aider doesn't natively read prompts from stdin. The `bash -c` wrapper reads stdin with `cat -` and passes it as a `--message` argument.

### Aider with a specific model

```markdown
---
agent: bash -c 'aider --yes-always --no-auto-commits --model claude-sonnet-4-6 --message "$(cat -)"'
---
```

## Codex CLI

[OpenAI Codex CLI](https://github.com/openai/codex) supports non-interactive use natively via its `exec` subcommand.

```markdown
---
agent: codex exec --sandbox danger-full-access -
---
```

| Flag | Purpose |
|---|---|
| `exec` | Non-interactive mode — designed for piped/scripted use |
| `--sandbox danger-full-access` | Full filesystem access for autonomous operation |
| `-` | Read prompt from stdin |

## Custom wrapper script

For full control, write a wrapper script that reads stdin and calls your agent however it needs to be called.

**`ralph-agent.sh`**

```bash
#!/bin/bash
set -e

# Read the prompt from stdin
PROMPT=$(cat -)

# Call your agent however it works
my-custom-agent --input "$PROMPT" --auto-approve
```

```bash
chmod +x ralph-agent.sh
```

**`my-ralph/RALPH.md`**

```markdown
---
agent: ./ralph-agent.sh
---

Your prompt here.
```

## Testing your setup

Verify the agent works outside of ralphify first:

```bash
echo "Say hello" | <your-agent-command>
```

Then test through ralphify with a single iteration:

```bash
ralph run my-ralph -n 1 --log-dir ralph_logs
```

!!! tip "Non-Claude-Code agents"
    Disable auto-commits if your prompt handles commits — most agents have this feature, and it conflicts with prompt-driven commit instructions. Use `--timeout` as a safety net in case the agent enters an unexpected interactive mode.

## How agent output works

Ralphify uses two different execution modes depending on the agent:

### Streaming mode (Claude Code)

When the agent command starts with `claude`, ralphify spawns the process with `Popen` and reads its JSON output line by line. This enables:

- **Live activity tracking** — the terminal shows what the agent is doing in real time
- **Result text extraction** — the agent's final response is captured
- **Verbose logging** — with `--log-dir`, logs include the agent's internal tool calls and reasoning

### Blocking mode (all other agents)

For non-Claude agents, ralphify uses `subprocess.run` and waits for the process to exit. Output behavior depends on whether you're using `--log-dir`:

- **Without `--log-dir`** — agent output streams directly to your terminal in real time
- **With `--log-dir`** — output is captured, written to a log file, then replayed to the terminal after the iteration completes

Both modes support all ralphify features (commands, timeouts, iteration tracking). The difference is only in how output is handled during each iteration.

## Adapting other tools

Many AI coding tools don't read from stdin directly but can be adapted with a bash wrapper. The pattern is:

```bash
bash -c '<tool> <auto-approve-flag> --message "$(cat -)"'
```

The `cat -` reads the piped prompt from stdin and passes it as a command-line argument. This works for any tool that accepts a prompt via a flag (like `--message`, `--input`, `--prompt`).

If the tool has no way to accept a prompt non-interactively, a [custom wrapper script](#custom-wrapper-script) is the escape hatch — you can use the prompt text however the tool needs it.

## Next steps

- [Getting Started](getting-started.md) — set up your first loop with the agent you just configured
- [Writing Prompts](writing-prompts.md) — patterns for writing effective autonomous loop prompts
- [Troubleshooting](troubleshooting.md) — when the agent hangs, produces no output, or exits unexpectedly
