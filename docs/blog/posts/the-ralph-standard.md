---
date: 2026-03-24
categories:
  - Standards
authors:
  - kasper
description: I've been obsessing over how to define autonomous agent loops in a single directory. Here's what I landed on.
keywords: RALPH.md format, agent loop standard, autonomous coding format, ralph loop specification, YAML frontmatter prompt, AI agent harness design
---

# An agent skill-like standard for autonomous agent loops

I've spent the last few weeks messing around with [ralph loops](https://ghuntley.com/ralph/) - running an agent against a prompt in a while loop. The more I used them, the more I wanted a reusable format: deterministic scripts between iterations, their output optionally injected into the prompt, and a way to parametrize the whole thing so one loop definition works across projects.

So I designed one.

<!-- more -->

## The format

A ralph is a self-contained directory. The only required file is `RALPH.md` - everything else is optional context:

```
bug-hunter/
├── RALPH.md              # the loop definition (required)
├── check-coverage.sh     # script used by a command (optional)
├── coding-guidelines.md  # context the agent loads on demand (optional)
└── test-data.json        # whatever else the loop needs (optional)
```

The `RALPH.md` itself has YAML frontmatter that steers the loop, and a prompt body that gets assembled and piped to the agent each iteration:

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: types
    run: uv run ty check
  - name: lint
    run: uv run ruff check .
  - name: git-log
    run: git log --oneline -10
args:
  - focus
---

# Bug Hunter

You are an autonomous bug-hunting agent running in a loop.
Each iteration starts with fresh context.
Your progress lives in the code and git.

## Test results

{{ commands.tests }}

## Type checking

{{ commands.types }}

## Lint

{{ commands.lint }}

## Recent commits

{{ commands.git-log }}

If tests, types, or lint are failing, fix that before hunting
for new bugs.

## Task

Find and fix a real bug in this codebase.
{{ args.focus }}

Each iteration:

1. **Read code** - pick a module and read it carefully. Look for
   edge cases, off-by-one errors, missing validation, incorrect
   error handling, race conditions, or logic errors.
2. **Write a failing test** - prove the bug exists with a test
   that fails on the current code.
3. **Fix the bug** - make the test pass with a minimal fix.
4. **Verify** - all existing tests must still pass.

## Rules

- One bug per iteration
- The bug must be real - do not invent hypothetical issues
- Always write a regression test before fixing
- Do not change unrelated code
- Commit with `fix: resolve <description>`
```

## Four things

The whole format is four things:

1. **`agent`** - the command to run (anything that reads stdin)
2. **`commands`** - deterministic feedback commands that run between iterations
3. **`args`** - declared arguments to parametrize the ralph from the command line
4. **A prompt body** - with `{{ placeholders }}` for command output and arguments

Each iteration: run the commands, optionally inject their output into the prompt via `{{ commands.<name> }}`, resolve `{{ args.<name> }}` placeholders for ad-hoc steering, pipe the assembled prompt to the agent, agent does its thing, repeat. Fresh context every cycle.

## Design decisions

**Why a directory, not just a file?** Same reason the [Agent Skills](https://agentskills.io/) format uses a directory. A `RALPH.md` on its own is enough for simple loops, but ralph loops often benefit from being bundled with shell scripts for custom checks and context injection and reference docs for progressive disclosure (`coding-guidelines.md`, `architecture.md`). Commands starting with `./` run relative to the ralph directory, so bundled scripts just work. The directory then is the unit of sharing.

**Why not just make it a skill?** They look similar on the surface - both are directories with a markdown file and optional bundled resources. That similarity is intentional - the skill format has become familiar to a lot of people, and borrowing its shape makes ralphs easy to understand at a glance. But they serve different layers. A skill provides knowledge about reusable processes in the inner loop - the agent's session. A ralph steers the outer loop by running code between iterations to deterministically control the environment and optionally inject context into the inner loop before kicking off the next iteration. 

## Try it

I'm building a tool called [Ralphify](https://github.com/computerlovetech/ralphify) to run ralphs in this format. Arguments declared in the frontmatter become flags on the command line, so a single ralph works across different contexts:

```bash
uv tool install ralphify

# point it at a directory containing a RALPH.md
ralph run ./ralphs/bug-hunter --focus "authentication and session handling"

# same ralph, different focus
ralph run ./ralphs/bug-hunter --focus "edge cases in the payment flow"

# or run it without args - unmatched placeholders just resolve to empty
ralph run ./ralphs/bug-hunter
```

Declare `args: [focus]` and you get `--focus` on the CLI. The value fills `{{ args.focus }}` in the prompt. One ralph, many use cases.

Because ralphs are just directories in a git repo, anyone can share them. If a repo contains a directory with a `RALPH.md`, you can install it with `ralph add`:

```bash
# install a specific ralph from any GitHub repo
ralph add owner/repo/ralph-name

# install all ralphs in a repo
ralph add owner/repo
```

The [ralphify examples](https://github.com/computerlovetech/ralphify/tree/main/examples) are a good place to start — and the [cookbook](https://ralphify.co/docs/cookbook/) has more.

Ralphify is just one implementation though. The format itself is what I care about most - it's just YAML frontmatter and markdown. Any tool could read it and run the loop. I can't predict what will end up being useful here. But I built this, and maybe someone else finds the format interesting enough to build on or take in a direction I haven't thought of.

## I'd love feedback

This is where my thinking landed, but I'm sure there are blind spots. If you're running agent loops - for coding, research, testing, or something I haven't thought of - I'd genuinely like to hear what you think.

- **Share a use case**: [open an issue](https://github.com/computerlovetech/ralphify/issues) describing how you'd use this, or how you already run agent loops. The weird, unexpected ones are the most useful.
- **Poke holes in the format**: if something feels wrong or missing, I want to know.
- **Write a ralph and share it**: if you try the format and build something interesting, I'd love to see it.

[GitHub](https://github.com/computerlovetech/ralphify) | [Docs](https://ralphify.co/docs/) | [PyPI](https://pypi.org/project/ralphify/)
