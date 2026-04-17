# Live peek code review — task list

Tasks generated from a competitive review of the uncommitted live-peek feature (the `p` toggle for agent output streaming). Each task is self-contained so a fresh agent context can pick one up without needing the others.

**Pick them up in order.** Some later tasks build on earlier ones (e.g. `medium-01` depends on the capability signal introduced in `critical-01`).

## Critical — must fix before merge

| # | Task | Original IDs |
|---|---|---|
| 1 | [Capture strategy three-way branch](critical-01-capture-strategy-three-way-branch.md) | C1 + M1 |
| 2 | [`_pump_stream` exception containment](critical-02-pump-stream-exception-handling.md) | C2 + M9 |
| 3 | [`stdin.write` timeout enforcement](critical-03-stdin-write-timeout.md) | C3 |
| 4 | [Bounded reader-thread joins in `finally`](critical-04-bounded-reader-thread-joins.md) | C4 + C5 + M3 |

## High

| # | Task | Original IDs |
|---|---|---|
| 5 | [Echo output + Live spinner coordination](high-01-echo-output-live-spinner-coordination.md) | H1 + M8 |
| 6 | [`_read_agent_stream` deadline + readahead](high-02-read-agent-stream-deadline-and-buffering.md) | H2 + H3 |
| 7 | [Test helpers pid=12345 hazard](high-03-test-helpers-pid-hazard.md) | H4 |
| 8 | [Peek discoverability (`--help`, startup hint)](high-04-peek-discoverability.md) | H5 |

## Medium

| # | Task | Original IDs |
|---|---|---|
| 9 | [Filter `AGENT_OUTPUT_LINE` events when no subscriber](medium-01-agent-output-line-event-filtering.md) | M2 |
| 10 | [`returncode=None` semantic change — document](medium-02-returncode-semantic-change-docs.md) | M4 |
| 11 | [Keypress listener: EINTR / SIGTSTP / SIGCONT](medium-03-keypress-signal-handling.md) | M5 |
| 12 | [Peek lock discipline](medium-04-peek-lock-discipline.md) | M6 + M7 |
| 13 | [Console emitter handler interleaving](medium-05-console-emitter-handler-interleaving.md) | M10 |

## How to use

Each task file contains:
- **Problem** — what's wrong and where (file:line)
- **Why it matters** — concrete failure mode
- **Fix direction** — not a prescription, but the shape the fix should take
- **Done when** — checklist for completion
- **Context** — code snippets / surrounding gotchas the agent will need

Run `uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run ty check` after every task. Any new behavior needs a regression test.

## Out of scope

Low-severity / nit findings (`.gitignore` `.ralphify/`, CHANGELOG wording, `docs/llms-full.txt` stale copy, dumb-terminal check, import ordering, case-sensitive `p`, slow test markers, free-threaded Python compatibility) are tracked in the review transcript but not in individual task files — they can be swept up in a single follow-up PR.
