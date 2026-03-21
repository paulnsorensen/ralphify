<p align="center">
  <img src="cli-graphic.png" alt="ralphify" />
</p>

<p align="center">
  <a href="https://pypi.org/project/ralphify/"><img src="https://img.shields.io/pypi/v/ralphify?color=blue" alt="PyPI version"></a>
  <a href="https://pypi.org/project/ralphify/"><img src="https://img.shields.io/pypi/pyversions/ralphify" alt="Python versions"></a>
  <a href="https://github.com/computerlovetech/ralphify/blob/main/LICENSE"><img src="https://img.shields.io/github/license/computerlovetech/ralphify" alt="License"></a>
  <a href="https://ralphify.co/docs/"><img src="https://img.shields.io/badge/docs-ralphify.co%2Fdocs-blue" alt="Documentation"></a>
</p>

Put your AI coding agent in a `while True` loop and let it ship.

Ralphify is a minimal harness for running autonomous AI coding loops, inspired by the [Ralph Wiggum technique](https://ghuntley.com/ralph/). The idea is simple: pipe a prompt to an AI coding agent, let it do one thing, commit, and repeat. Forever. Until you hit Ctrl+C.

```
while :; do cat RALPH.md | claude -p ; done
```

Ralphify wraps this pattern into a proper tool with commands, iteration tracking, and clean shutdown.

## Install

```bash
uv tool install ralphify    # recommended
```

Or if you don't have `uv`:

```bash
pipx install ralphify       # isolated install via pipx
pip install ralphify         # plain pip (use a virtualenv or --user)
```

Any of these gives you the `ralph` command.

## Quickstart

A ralph is a directory with a `RALPH.md` file. Scaffold one:

```bash
ralph init my-ralph
```

Then edit `my-ralph/RALPH.md`:

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest
---

You are an autonomous coding agent working in a loop.

## Test results

{{ commands.tests }}

If any tests are failing, fix them before continuing.

## Task

Implement the next feature from the TODO list.
```

Run it:

```bash
ralph run my-ralph           # Starts the loop (Ctrl+C to stop)
ralph run my-ralph -n 5      # Run 5 iterations then stop
```

### What `ralph run` does

Each iteration:
1. **Runs commands** — executes all commands, captures output
2. **Assembles prompt** — reads RALPH.md body, replaces `{{ commands.<name> }}` placeholders with output
3. **Pipes to agent** — executes the agent command with the assembled prompt on stdin
4. **Repeats** — goes back to step 1

### What it looks like

```
$ ralph run my-ralph -n 3

── Iteration 1 ──
  Commands: 1 ran
✓ Iteration 1 completed (52.3s)

── Iteration 2 ──
  Commands: 1 ran
✗ Iteration 2 failed with exit code 1 (23.1s)

── Iteration 3 ──
  Commands: 1 ran
✓ Iteration 3 completed (41.7s)

Done: 3 iteration(s) — 2 succeeded, 1 failed
```

## The technique

The Ralph Wiggum technique works because:

- **One thing per loop.** The agent picks the most important task, implements it, tests it, and commits. Then the next iteration starts fresh.
- **Fresh context every time.** No context window bloat. Each loop starts clean and reads the current state of the codebase.
- **Progress lives in git.** Code, commits, and a plan file are the only state that persists between iterations. If something goes wrong, `git reset --hard` and run more loops.
- **The prompt is a tuning knob.** When the agent does something dumb, you add a sign. Like telling Ralph not to jump off the slide — you add "SLIDE DOWN, DON'T JUMP" to the prompt.

Read the full writeup: [Ralph Wiggum as a "software engineer"](https://ghuntley.com/ralph/)

## Core concepts

A **ralph** is a directory containing a `RALPH.md` file. That's it. Everything the ralph needs lives in that directory.

```
my-ralph/
├── RALPH.md              # the prompt (required)
├── check-coverage.sh     # script (optional)
├── style-guide.md        # reference doc (optional)
└── test-data.json        # any supporting file (optional)
```

**RALPH.md** is the only file the framework reads. It has YAML frontmatter for configuration and a body that becomes the prompt:

| Frontmatter field | Required | Description |
|---|---|---|
| `agent` | Yes | The agent command to run |
| `commands` | No | List of commands (name + run) whose output fills `{{ commands.<name> }}` placeholders |
| `args` | No | Declared argument names for `{{ args.<name> }}` placeholders |
| `credit` | No | Append co-author trailer instruction to prompt (default: `true`) |

**Commands** run before each iteration. Their output replaces `{{ commands.<name> }}` placeholders in the prompt. Use them for test results, git history, lint output — anything that changes between iterations.

**No project-level configuration.** No `ralph.toml`. No `.ralphify/` directory. A ralph is fully self-contained.

## AI-guided setup

```bash
ralph new my-task
```

Launches an interactive agent conversation to scaffold a new ralph with the right commands and prompt for your project.

## Documentation

Full documentation at **[ralphify.co/docs](https://ralphify.co/docs/)** — getting started tutorial, prompt writing guide, cookbook, and troubleshooting.

## Requirements

- Python 3.11+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (or any agent CLI that accepts piped input)

## License

MIT
