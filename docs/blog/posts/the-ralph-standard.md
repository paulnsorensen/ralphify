---
date: 2026-03-24
categories:
  - Standards
authors:
  - kasper
description: I've been obsessing over how to define autonomous agent loops in a single directory. Here's what I landed on.
---

# An agent skill-like standard for autonomous agent loops

I've spent the last few weeks messing around with [ralph loops](https://ghuntley.com/ralph/) — running an agent against a prompt in a while loop. The more I used them, the more I wanted a reusable format: deterministic scripts between iterations, their output optionally injected into the prompt, and a way to parametrize the whole thing so one loop definition works across projects.

So I designed one.

<!-- more -->

## The format

A ralph is a self-contained directory. The only required file is `RALPH.md` — everything else is optional context:

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

1. **Read code** — pick a module and read it carefully. Look for
   edge cases, off-by-one errors, missing validation, incorrect
   error handling, race conditions, or logic errors.
2. **Write a failing test** — prove the bug exists with a test
   that fails on the current code.
3. **Fix the bug** — make the test pass with a minimal fix.
4. **Verify** — all existing tests must still pass.

## Rules

- One bug per iteration
- The bug must be real — do not invent hypothetical issues
- Always write a regression test before fixing
- Do not change unrelated code
- Commit with `fix: resolve <description>`
```

## Four things

The whole format is four things:

1. **`agent`** — the command to run (anything that reads stdin)
2. **`commands`** — deterministic feedback commands that run between iterations
3. **`args`** — declared arguments to parametrize the ralph from the command line
4. **A prompt body** — with `{{ placeholders }}` for command output and arguments

Each iteration: run the commands, optionally inject their output into the prompt via `{{ commands.<name> }}`, resolve `{{ args.<name> }}` placeholders for ad-hoc steering, pipe the assembled prompt to the agent, agent does its thing, repeat. Fresh context every cycle. State, progress, strategy — it all lives in the project's filesystem. Git history, markdown docs, plan files, whatever makes sense. The format doesn't prescribe where state goes.

## Design decisions

**Why a directory, not just a file?** Same reason the [Agent Skills](https://agentskills.io/) format uses a directory. A `RALPH.md` on its own is enough for simple loops, but real-world loops often need a shell script for a custom check (`./check-coverage.sh`), reference docs for progressive disclosure (`coding-guidelines.md`, `architecture.md`), data files, templates. Commands starting with `./` run relative to the ralph directory, so bundled scripts just work. The directory is the unit of sharing — copy it, check it into a repo, and the whole loop travels together.

**Why not just make it a skill?** They look similar on the surface — both are directories with a markdown file and optional bundled resources. But a skill is loaded once when an agent decides it's relevant. It adds knowledge to a single session. A ralph is executed repeatedly — it's the outer loop that launches the agent, feeds it deterministic feedback, and kicks off the next iteration. Skills live inside an agent's context. Ralphs live outside, orchestrating from the outside in. You could use both together — a ralph that runs an agent which has skills installed. Complementary layers, not competing ones.

## What shaped the format

Two things influenced the design more than anything else. OpenAI's [harness engineering](https://openai.com/index/harness-engineering/) post — build deterministic infrastructure around the agent, keep progress as markdown in the codebase, don't try to make the agent smarter. And Karpathy's [autoresearch](https://github.com/karpathy/autoresearch) — one hard metric, ~700 experiments in two days, changes that don't improve the number get reverted.

`commands` in a ralph are the mechanism for all of this. They're not just ground truth — they're the control structure around the loop. Enforce file and directory conventions. Run checks. Inject dynamic context. Gate progress. The deterministic scaffolding that lets you trust the agent to operate autonomously.

The easy wins are tasks with hard metrics — test coverage, validation loss, a reference implementation to compare against. But I think ralph loops have the potential to take on much fuzzier, higher-level work. A PRD. A loose description of a desired outcome. A strategic goal. For that kind of work, how you frame the outcome matters more than how specifically you instruct the agent. Too specific and the agent overfits to your instructions. Too vague and it drifts. There's a weird golden balance, and I've been reaching for Jobs-to-be-Done as a prompting technique — express the outcome to optimize for, not the steps to take.

That's what I want to build towards — a format and a tool that enable increasingly ambitious and fuzzy things to be achieved with ralph loops. Because AI is truly powerful when it surprises you with solutions to problems you didn't anticipate when you kicked off the loop. True discovery. The iterative, fresh-context way of working makes that possible in a way that single-shot prompting doesn't. A good ralph engineer figures out how to get results with agents that are as autonomous as possible — because that means the strategy and outcome definition are good enough for the agent to make decisions you couldn't have predicted. That's the power of it. And honestly why I keep rabbit-holing on all of this.

## Try it

I'm building a tool called [Ralphify](https://github.com/computerlovetech/ralphify) to run ralphs in this format. Arguments declared in the frontmatter become flags on the command line, so a single ralph works across different contexts:

```bash
uv tool install ralphify

# point the bug hunter at a specific area
ralph run bug-hunter --focus "authentication and session handling"

# same ralph, different focus
ralph run bug-hunter --focus "edge cases in the payment flow"

# or run it without args — unmatched placeholders just resolve to empty
ralph run bug-hunter
```

Declare `args: [focus]` and you get `--focus` on the CLI. The value fills `{{ args.focus }}` in the prompt. One ralph, many use cases.

Ralphify is just one implementation though. The format itself is what I care about most — it's just YAML frontmatter and markdown. Any tool could read it and run the loop. I can't predict what will end up being useful here. But I built this, and maybe someone else finds the format interesting enough to build on or take in a direction I haven't thought of. The Agent Skills format started as one team's idea and ended up adopted by dozens of agents. I don't know if the same thing happens here, but the format is simple enough that it could.

## I'd love feedback

This is where my thinking landed, but I'm sure there are blind spots. If you're running agent loops — for coding, research, testing, or something I haven't thought of — I'd genuinely like to hear what you think.

- **Share a use case**: [open an issue](https://github.com/computerlovetech/ralphify/issues) describing how you'd use this, or how you already run agent loops. The weird, unexpected ones are the most useful.
- **Poke holes in the format**: if something feels wrong or missing, I want to know.
- **Write a ralph and share it**: if you try the format and build something interesting, I'd love to see it.

[GitHub](https://github.com/computerlovetech/ralphify) | [Docs](https://ralphify.co/docs/) | [PyPI](https://pypi.org/project/ralphify/)
