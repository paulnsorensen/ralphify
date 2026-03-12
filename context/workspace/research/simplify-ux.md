# UX/UI Simplification Analysis

## Users' Jobs to Be Done

Based on the JTBD research and codebase analysis, these are the core jobs users hire ralphify to do, ranked by frequency × intensity:

1. **Ship features while I'm not coding** (J1) — Set agent running autonomously, wake up to working code. VERY HIGH frequency/intensity.
2. **Keep the agent from going off the rails** (J2) — Automatic quality gates that catch bad work. VERY HIGH frequency/intensity.
3. **Stop babysitting the agent** (J3) — Step away and let the agent work independently. HIGH frequency/intensity.
4. **Have a reliable, repeatable workflow** (J5) — Replace fragile bash scripts with structured primitives. HIGH frequency/intensity.
5. **Feel in control even when autonomous** (J6) — See what happened each iteration without reviewing every line. HIGH frequency/intensity.

These jobs map to five user-facing workflows:
- **Setup**: Go from zero to a running loop
- **Run**: Launch and configure the loop
- **Monitor**: Watch progress and understand what happened
- **Steer**: Adjust the agent's behavior while running
- **Trust**: Know the output is good via checks

---

## Current UX Audit

### Surface Area Inventory

**CLI Commands (5):**
| Command | Purpose |
|---|---|
| `ralph init` | Create ralph.toml + RALPH.md |
| `ralph run [name]` | Start the autonomous loop |
| `ralph status` | Validate setup and list primitives |
| `ralph new <type> <name>` | Scaffold a new primitive |
| `ralph ui` | Launch web dashboard |

**`ralph run` Flags (8):**
| Flag | Short | Purpose |
|---|---|---|
| `[RALPH_NAME]` | positional | Named ralph to use |
| `--prompt` | `-p` | Inline prompt text |
| `--prompt-file` | `-f` | Path to prompt file |
| `-n` | | Max iterations |
| `--stop-on-error` | `-s` | Stop if agent fails |
| `--delay` | `-d` | Seconds between iterations |
| `--log-dir` | `-l` | Directory for logs |
| `--timeout` | `-t` | Max seconds per iteration |

**Concepts Users Must Learn (10):**
1. ralph.toml (config file)
2. RALPH.md (root prompt file)
3. .ralphify/ directory (primitives home)
4. Checks (validation scripts)
5. Contexts (dynamic data injection)
6. Instructions (static reusable rules)
7. Ralphs (named prompt variants)
8. Template placeholders (`{{ contexts.name }}`, `{{ instructions }}`)
9. Frontmatter (YAML config in markdown)
10. Failure instructions (body text in CHECK.md)

**Config Files:**
- `ralph.toml` — agent command, args, default ralph
- `RALPH.md` — root prompt (or named ralph)
- `.ralphify/checks/<name>/CHECK.md` — check config + failure instruction
- `.ralphify/contexts/<name>/CONTEXT.md` — context config + static header
- `.ralphify/instructions/<name>/INSTRUCTION.md` — instruction body
- `.ralphify/ralphs/<name>/RALPH.md` — named ralph prompt

---

## Friction Log

### Job: Setup (Go from zero to running loop)

**Steps walked through:**

1. `pip install ralphify` (or `uv tool install ralphify`) — fine
2. `ralph init` — creates ralph.toml + RALPH.md
3. User must edit RALPH.md manually — the template is generic ("Your prompt content here" equivalent)
4. User must know to run `ralph new check tests` to add quality gates
5. User must understand frontmatter syntax to configure the check command
6. User must edit ralph.toml if not using Claude Code (default is `claude` with `--dangerously-skip-permissions`)
7. `ralph status` to validate — good, but optional step users might skip
8. `ralph run -n 1` to test — must know to limit iterations for first try

**Friction points identified:**

- **F1: `ralph init` creates a useless prompt** (VALIDATED). The ROOT_RALPH_TEMPLATE at `_templates.py:61-74` is a generic skeleton. It says "Add your project-specific instructions below" but gives no guidance on what those should be. The user's very first edit is staring at a mostly-empty file. Compare: `git init` creates a working repo immediately.

- **F2: No checks created by default** (VALIDATED). After `ralph init`, running `ralph run` will start an agent loop with zero quality gates. The most important differentiator of ralphify (the self-healing feedback loop) is completely absent until the user manually discovers and runs `ralph new check`. This contradicts J2 (keep the agent from going off the rails), which is the #2 job.

- **F3: `detect_project()` does nothing with its result** (VALIDATED). The detector (`detector.py:11-27`) identifies Python/Node/Rust/Go projects, prints "Detected project type: python" during init, but takes no action. It doesn't create project-appropriate checks (e.g., `pytest` for Python, `npm test` for Node), doesn't customize the ralph.toml, and doesn't tailor the RALPH.md template. The user sees information but gets no benefit from it.

- **F4: Scaffolded templates are full of HTML comments explaining the format** (VALIDATED). The CHECK_MD_TEMPLATE, CONTEXT_MD_TEMPLATE, and INSTRUCTION_MD_TEMPLATE all contain multi-line HTML comments explaining the format rather than providing useful defaults. While comments are stripped from the assembled prompt (via `_HTML_COMMENT_RE` in `_frontmatter.py`), they create noise when the user opens the file to edit it. The check template defaults to `ruff check .` which may not be installed.

- **F5: 12-step getting started guide** (VALIDATED from docs). The documented onboarding flow is 12 steps. The minimum viable loop (init → edit prompt → add check → run) is 4 steps with manual editing. Could be fewer.

- **F17: `--dangerously-skip-permissions` in default config is alarming** (VALIDATED). The default `ralph.toml` template (`_templates.py:3-8`) includes `args = ["-p", "--dangerously-skip-permissions"]`. A new user sees the word "dangerously" in their config file on first run. This is a Claude Code flag that's necessary for autonomous operation, but: (a) it triggers anxiety about security, (b) it's meaningless for non-Claude-Code agents, (c) it violates the principle of trust — users are trying to trust the tool, and the default config contains a flag that sounds dangerous. The flag exists because Claude Code requires it, but the UX cost is real.

- **F18: No `.gitignore` guidance** (VALIDATED). After `ralph init`, there's no suggestion to add `ralph_logs/` or `.ralphify/` patterns to `.gitignore`. The `.ralphify/` directory should be committed (it's config), but log files shouldn't. New users may accidentally commit large log files or miss committing their primitive config. The init command could create/update `.gitignore` entries, or at minimum print guidance.

### Job: Run (Launch the loop)

**Steps walked through:**

1. `ralph run` — uses ralph.toml defaults, works
2. `ralph run docs` — named ralph, works if it exists
3. `ralph run -n 3 --timeout 300 --log-dir logs` — full invocation

**Friction points identified:**

- **F6: Three ways to specify a prompt, unclear priority** (VALIDATED). Users can provide a prompt via: (a) positional `[RALPH_NAME]`, (b) `--prompt-file`/`-f`, (c) `--prompt`/`-p`, or (d) `ralph.toml`'s `ralph` field. The resolution chain in `ralphs.py:89-121` has a 4-level priority system. Using both `prompt_name` and `prompt_file` is an error (`cli.py:304-306`). This creates unnecessary cognitive load — "which one wins?" is a question users shouldn't have to answer.

- **F7: `--prompt-file` / `-f` is redundant** (VALIDATED). The `ralph.toml` already has a `ralph` field that can point to any file. Named ralphs live in `.ralphify/ralphs/`. Between the toml config and the positional argument, `--prompt-file` serves an edge case (one-off file that's not a named ralph and not the default). It adds a flag to learn and a conflict to handle (`cli.py:304-306`).

- **F8: Banner prints on every `ralph run`** (VALIDATED). The ASCII art banner (`cli.py:58-107`) prints every time the user runs `ralph run`. It's nice on first launch but wastes 8 lines of vertical space on subsequent runs. The "Star us on GitHub" line is promotional, not functional. During iteration, vertical space matters — users are scanning for check results and iteration status.

- **F9: No default for `-n` (iteration limit)** (VALIDATED). If the user omits `-n`, the loop runs infinitely until Ctrl+C. For new users, this is risky — J9 (prevent runaway costs) is a validated job. A sensible default (e.g., `-n 5` or `-n 10`) with an explicit `--infinite` flag would protect new users while allowing power users to opt in.

- **F19: `ralph new ralph` reads awkwardly** (VALIDATED). To create a named ralph, the command is `ralph new ralph docs`. The word "ralph" appears twice: as the CLI tool name and as the primitive type. This is a consequence of using the product name ("ralph") as both the tool and a primitive type name. Compare: `git branch create` makes sense because "git" and "branch" are different words. A user may wonder "did I type that correctly?" Internally this is the `new_ralph` function at `cli.py:215-221`, which is even marked `hidden=True` — the `_DefaultRalphGroup` at `cli.py:46-52` auto-routes unknown subcommands to `ralph`, so `ralph new docs` works. But the hidden magic creates its own confusion: `ralph new --help` doesn't show how to create a ralph.

- **F20: No iteration progress when `-n` is set** (VALIDATED). When running `ralph run -n 10`, the iteration header shows `── Iteration 3 ──` but not `── Iteration 3/10 ──`. The user has no sense of progress toward the limit. The data is available in `RunConfig.max_iterations` but `ConsoleEmitter._on_iteration_started` doesn't use it (`_console_emitter.py:98-100`). For J6 (feel in control), knowing "3 of 10" vs "3 of ∞" is significant.

- **F21: `-p` inline prompt doesn't default to 1 iteration** (VALIDATED). When a user runs `ralph run -p "Fix the login bug"`, the inline prompt runs in an infinite loop, re-sending the same prompt every iteration. Inline prompts are almost always one-shot tasks. The engine at `cli.py:300-301` just uses the prompt_text with the default `n=None` (infinite). Users must remember to add `-n 1` for ad-hoc tasks or risk burning credits repeating the same prompt.

### Job: Monitor (Understand what happened)

**Steps walked through:**

1. During run: see iteration headers, spinner with elapsed time, check results
2. After run: summary line ("Done: 3 iteration(s) — 3 succeeded")
3. With `--log-dir`: per-iteration log files with full agent output

**Friction points identified:**

- **F10: No default log directory** (VALIDATED). Without `--log-dir`, all agent output is lost after the run. The user has to remember to add `--log-dir logs` every time. This contradicts J6 (feel in control even when autonomous) — you can't feel in control if you can't review what happened. Most users who care about quality will want logs. Should be on by default.

- **F11: Check failure output is truncated to 5,000 chars with no warning** (VALIDATED). `_output.py` truncates output to 5,000 characters with only `... (truncated)` appended to the text itself. This truncated text is injected into the next iteration's prompt. The CLI output (`_console_emitter.py`) shows no indication that truncation occurred. If a test suite produces verbose output, critical failure information may be cut off and the user never knows. For the agent, it sees `... (truncated)` but has no idea how much was lost (was it 5,001 chars or 50,000?).

- **F12: Iteration output is minimal during run** (VALIDATED). The console emitter (`_console_emitter.py`) shows: iteration header, spinner, completion status, check pass/fail summary. It does NOT show: which prompt was used, how many contexts/instructions were resolved, prompt length, or any preview of what the agent was told. For J6 (feel in control), users would benefit from knowing what went into each iteration.

- **F22: No indication of which check is currently running** (VALIDATED). During the checks phase, the console shows nothing until ALL checks complete. Checks run sequentially (`checks.py:130`: a simple list comprehension with no events between checks). If a user has 5 checks and the third one hangs, they see a blank screen with no indication of progress. The `CHECKS_STARTED` event fires before any checks run, and `CHECKS_COMPLETED` fires after all are done, but there's no `CHECK_RUNNING` event for individual checks. For long-running check suites (e.g., integration tests), this is a monitoring gap.

- **F23: Run summary doesn't include check statistics** (VALIDATED). The `_on_run_stopped` handler at `_console_emitter.py:138-151` shows iteration count and success/failure counts, but not check statistics. After a 10-iteration run, the user sees "Done: 10 iteration(s) — 7 succeeded, 3 failed" but not how many total checks passed/failed across all iterations. For J6 (feel in control), an aggregate like "Checks: 45/50 passed across 10 iterations" would be informative. The data exists in per-iteration `CHECKS_COMPLETED` events but isn't aggregated.

### Job: Steer (Adjust behavior while running)

**Steps walked through:**

1. Edit RALPH.md in another terminal — re-read each iteration (works!)
2. Adding/removing checks, contexts, instructions — requires restart
3. Editing check commands — requires restart

**Friction points identified:**

- **F13: Primitive config is frozen at startup — not documented in CLI** (VALIDATED). The engine discovers primitives once at startup (`engine.py:386`). New checks, contexts, or instructions added while running are invisible until restart. The docs mention this, but the CLI gives zero indication. Users who add a check and expect it to run next iteration will be confused.

- **F14: No signal when RALPH.md changes are picked up** (VALIDATED). RALPH.md is re-read each iteration (`engine.py:191`), which is great for steering. But the console shows no indication that the prompt changed. Users editing RALPH.md while running have no confirmation their edits took effect.

- **F24: The reload mechanism exists but is invisible from CLI** (VALIDATED). The engine has `state.consume_reload_request()` at `engine.py:164-170` which triggers `_discover_enabled_primitives()` to re-scan all primitives. The `RunState` class has `request_reload()` (`_run_types.py`). But there's no CLI mechanism to trigger it — it's only accessible via the dashboard API. A user who adds a check and wants it picked up must restart the entire loop, losing their iteration count and any momentum. A signal handler (e.g., SIGUSR1) or a sentinel file could bridge this gap.

### Job: Trust (Know the output is good)

**Steps walked through:**

1. Checks run after each iteration
2. Failures feed back into next iteration's prompt
3. `ralph status` shows which checks are configured

**Friction points identified:**

- **F15: No guidance on WHAT checks to add** (VALIDATED). `ralph new check <name>` scaffolds an empty check. The template defaults to `ruff check .`. There's no "common checks" suggestion based on project type, no example library, and no indication of what good checks look like for the user's specific job.

- **F16: Silent context/instruction exclusion with named placeholders** (VALIDATED). From `resolver.py:43-55`: if you use `{{ contexts.git-log }}` without a `{{ contexts }}` bulk placeholder, ALL other contexts are silently dropped. There's no warning. This is documented in the docs but is a subtle, high-impact gotcha that violates the principle of least surprise.

- **F25: Check failure instructions are invisible until failure** (VALIDATED). The body text of CHECK.md (the failure instruction) is only ever shown to the agent, not the user. When a user creates a check, they write failure guidance in the markdown body, but there's no way to preview what the agent will actually see when the check fails. The `ralph status` command shows check names and commands but not failure instructions. For J2 (keep the agent from going off the rails), the quality of failure instructions is critical, yet users have no feedback loop on them.

- **F26: Checks always run sequentially, no early termination** (VALIDATED). `run_all_checks` at `checks.py:130` runs every check regardless of prior failures. If a fast lint check fails, the user still waits for a slow integration test to complete before the next iteration starts. There's no `--fail-fast` option for checks. For users with ordered checks (lint → typecheck → test), failing lint makes typecheck and test runs wasteful.

### Job: Scaffold (Create new primitives)

**Steps walked through:**

1. `ralph new check tests` — creates `.ralphify/checks/tests/CHECK.md`
2. `ralph new context git-log` — creates `.ralphify/contexts/git-log/CONTEXT.md`
3. `ralph new instruction coding-standards` — creates `.ralphify/instructions/coding-standards/INSTRUCTION.md`
4. `ralph new docs` — creates `.ralphify/ralphs/docs/RALPH.md` (auto-routed via `_DefaultRalphGroup`)
5. `ralph new --ralph myralph check tests` — creates ralph-scoped check

**Friction points identified:**

- **F27: `ralph new` subcommand structure requires knowing primitive type names** (VALIDATED). A user who wants to "add something that runs tests after each iteration" must know that's called a "check". A user who wants to "inject the git log into the prompt" must know that's called a "context". The terminology is not self-evident from the domain. `ralph new` with no args shows help listing `check`, `context`, `instruction`, and (hidden) `ralph` — but the help descriptions are the only guide. There's no `ralph new --interactive` that asks "What do you want to add?" and guides them.

- **F28: `--ralph` flag on `ralph new` is confusing** (VALIDATED). To scope a check to a specific named ralph: `ralph new check tests --ralph my-task`. The flag name `--ralph` collides with the product name again. The semantics are "scope this primitive to the named ralph called my-task" but a new user might read it as "create a ralph called tests" or "use ralph to create something". The directory structure it creates (`.ralphify/ralphs/my-task/checks/tests/CHECK.md`) is deeply nested and non-obvious.

---

## Simplification Opportunities

Ranked by: (impact on user's job) × (frequency of the job) / (effort + risk)

### Tier 1: High Impact, Low Effort

#### O1: Smart `ralph init` — auto-create project-appropriate checks
**What:** When `ralph init` detects a Python project, auto-create `.ralphify/checks/tests/CHECK.md` with `command: uv run pytest -x` (or `npm test` for Node, `cargo test` for Rust, etc.). Similarly auto-create a lint check appropriate to the ecosystem.
**Why:** Removes F2 (no checks by default) and F3 (detect_project does nothing). The core value of ralphify — self-healing feedback loops — should be active from the first run, not after manual setup.
**Job:** Setup (J1, J2, J5)
**Effort:** S — `detect_project()` already identifies the ecosystem; just need to call `_scaffold_primitive` with appropriate templates per project type.
**Risk:** Low. Generated checks might not match the user's exact setup (e.g., they use `pytest` not `uv run pytest`). Mitigate by making generated checks obviously editable and running `ralph status` to validate.

#### O2: Default log directory (`ralph_logs/`)
**What:** Always log to `ralph_logs/` unless `--no-logs` is explicitly passed. Add `ralph_logs/` to `.gitignore` guidance.
**Why:** Removes F10. Every user running loops for real needs logs for J6 (feel in control). Requiring `--log-dir` every time is a footgun for new users.
**Job:** Monitor, Trust (J6)
**Effort:** S — one default value change in `cli.py:283`.
**Risk:** Very low. Disk space is cheap. Users who don't want logs can opt out.

#### O3: Default iteration limit (e.g., 5)
**What:** Change `-n` default from unlimited to 5. Add `--no-limit` or `-n 0` for infinite mode.
**Why:** Removes F9. Protects new users from runaway costs (J9). Power users can easily opt into infinite mode.
**Job:** Run, Trust (J1, J9)
**Effort:** S — one default value change.
**Risk:** Medium. Existing users who rely on infinite loops will need to add `--no-limit`. But this is the safer default — it's far worse to accidentally run an infinite loop than to have to type `--no-limit`.

#### O4: Suppress banner on `ralph run`
**What:** Only show banner on `ralph` (no subcommand). Don't print it on `ralph run`.
**Why:** Removes F8. Saves 8+ lines of vertical space every run. Users running `ralph run` repeatedly (the core workflow) don't need the logo each time.
**Job:** Monitor (J6)
**Effort:** S — remove `_print_banner()` call from `run()` at `cli.py:293`.
**Risk:** Very low. The banner still shows on bare `ralph` command.

#### O14: Show iteration progress as N/M when `-n` is set
**What:** Change the iteration header from `── Iteration 3 ──` to `── Iteration 3/10 ──` when max iterations is configured. Keep `── Iteration 3 ──` when running infinitely.
**Why:** Removes F20. Costs nothing, gives immediate sense of progress. Requires passing `max_iterations` from `RunConfig` into the `ITERATION_STARTED` event data and reading it in `ConsoleEmitter`.
**Job:** Monitor (J6)
**Effort:** XS — add one field to event data, one format string change in emitter.
**Risk:** None.

#### O15: Default `-n 1` for inline prompts (`-p`)
**What:** When `--prompt`/`-p` is used, automatically set `max_iterations=1` unless `-n` is explicitly provided.
**Why:** Removes F21. Inline prompts are almost always one-shot tasks. Running `ralph run -p "Fix the login bug"` in an infinite loop is a footgun — the same prompt re-sends every iteration.
**Job:** Run (J1, J9)
**Effort:** XS — one conditional in `cli.py:run()` before constructing `RunConfig`.
**Risk:** Very low. Users who genuinely want to repeat an inline prompt can add `-n 5`.

### Tier 2: High Impact, Medium Effort

#### O5: Remove `--prompt-file` / `-f` flag
**What:** Remove the `--prompt-file` flag entirely. Users who want a custom file put the path in `ralph.toml`'s `ralph` field.
**Why:** Removes F6 (three ways to specify prompt) and F7 (redundant flag). Simplifies the run command from 8 flags to 7. Eliminates the error case where both `prompt_name` and `--prompt-file` are used.
**Job:** Run (J1, J5)
**Effort:** S-M — remove flag from CLI, simplify `resolve_ralph_source()`, update docs.
**Risk:** Medium. Breaks any user currently using `--prompt-file`. But the toml config or named ralphs cover every use case.

#### O6: Warn on silent context/instruction exclusion
**What:** When named placeholders are used without a bulk placeholder, emit a warning listing which contexts/instructions were excluded.
**Why:** Removes F16. Prevents subtle prompt assembly bugs that undermine J2 (keep agent from going off the rails).
**Job:** Trust (J2, J6)
**Effort:** S-M — add a warning in `resolve_placeholders()` when `has_named` is true and no bulk placeholder exists and there are remaining items.
**Risk:** Low. Warnings are informational and non-breaking.

#### O7: Show prompt assembly summary per iteration
**What:** After prompt is assembled, print one line: `Prompt: 2,847 chars | Contexts: 3 | Instructions: 2 | Check failures: 1`.
**Why:** Addresses F12 and F14. Users can see at a glance what went into each iteration. If they edit RALPH.md and the char count changes, they know it took effect.
**Job:** Monitor, Steer (J6)
**Effort:** S — the data is already in `EventType.PROMPT_ASSEMBLED` event; just render it in `ConsoleEmitter`.
**Risk:** Very low. One extra line of output per iteration.

#### O8: Better `ralph init` prompt template with guided sections
**What:** Replace the generic ROOT_RALPH_TEMPLATE with a structured template that has labeled sections: Role, Task (with a pointer to a TODO.md pattern), Constraints, Process. Include a comment explaining each section.
**Why:** Addresses F1. The prompt is the most important file in the entire setup — it shouldn't be the one that gets the least guidance.
**Job:** Setup (J1, J5)
**Effort:** S — just change the template string.
**Risk:** Low. More opinionated template, but the current one is too minimal to be useful.

#### O16: Show truncation details in CLI output
**What:** When check output or context output is truncated (>5,000 chars), show `⚠ Output truncated: 12,847 → 5,000 chars` in the CLI. Also include the original length in the text injected into the prompt: `... (truncated from 12,847 to 5,000 chars)` instead of just `... (truncated)`.
**Why:** Addresses F11. Users and agents both know when they're seeing partial information. The agent can request full output from logs or ask the user for help. Currently `truncate_output()` at `_output.py:28-32` discards the original length entirely.
**Job:** Monitor, Trust (J6)
**Effort:** S — change return type of `truncate_output()` to include a flag or length, update `format_check_failures()` to include length info.
**Risk:** Very low.

#### O17: Soften the `--dangerously-skip-permissions` default
**What:** Three options, from least to most effort: (a) Add an inline comment in the generated ralph.toml explaining why it's there: `# Required for Claude Code autonomous mode — safe for local development`. (b) Move it to a preset system: `ralph init --agent claude` pre-configures the right args. (c) Auto-detect the agent and set appropriate defaults during init.
**Why:** Addresses F17. The word "dangerously" in a default config file undermines trust on first contact. Users who aren't using Claude Code are confused by it; users who are using Claude Code are alarmed by it.
**Job:** Setup, Trust (J1, J2)
**Effort:** S (option a) to M (option c).
**Risk:** Low. Adding a comment costs nothing. Agent presets are more work but future-proof.

#### O18: Emit per-check events during execution
**What:** Add a `CHECK_STARTED` or `CHECK_RUNNING` event emitted before each individual check runs. Show `  ⋯ running: tests` in the console during each check.
**Why:** Addresses F22. Users with multiple checks (especially slow ones like integration tests) can see which check is currently running instead of staring at a blank screen.
**Job:** Monitor (J6)
**Effort:** S-M — change `run_all_checks` from a list comprehension to a loop with event emission, or emit events from `_run_checks_phase` in the engine.
**Risk:** Very low. More events = more information.

### Tier 3: Medium Impact, Medium Effort

#### O9: Hot-reload primitives
**What:** Re-discover checks, contexts, and instructions at the start of each iteration (not just startup).
**Why:** Addresses F13 and F24. Users can add/modify checks while the loop runs without restarting. Makes the steering experience consistent — if RALPH.md can change mid-run, why can't checks?
**Job:** Steer (J3, J6)
**Effort:** M — move `_discover_enabled_primitives()` call into the iteration loop. The `consume_reload_request()` mechanism exists in the engine (`engine.py:164-170`), so infrastructure is partially there. Could also use a lighter approach: compare file mtimes before rescanning.
**Risk:** Medium. Discovery is filesystem I/O — adds latency per iteration. Also, adding a check mid-run that fails could surprise the agent if it wasn't prompted to address that check.

#### O10: Merge "instructions" into RALPH.md / checks
**What:** Eliminate the "instructions" primitive type. Static instructions belong in RALPH.md directly. Per-check instructions are already the CHECK.md body (failure instructions). The template placeholder `{{ instructions }}` can be replaced by just writing the content in the prompt.
**Why:** Reduces concept count from 10 to 9. Instructions are the least differentiated primitive — they're just static text. Contexts have commands (dynamic), checks have commands + failure feedback. Instructions have... nothing special. They're a text include mechanism.
**Job:** Setup, Steer (all jobs, indirectly)
**Effort:** L — breaking change, requires migration path for existing users with instructions.
**Risk:** High. Some users may have built workflows around instructions as a separate concept (e.g., shared instructions across multiple ralphs). The composability argument is valid. **Consider instead**: just deprioritize instructions in docs and scaffolding, so new users don't encounter them until needed.

#### O19: Aggregate check statistics in run summary
**What:** Track total checks passed/failed across all iterations and show in the final summary: `Done: 10 iteration(s) — 7 succeeded, 3 failed | Checks: 45/50 passed overall`.
**Why:** Addresses F23. After a long run, the user gets a snapshot of check health without scrolling through all iterations. The `ConsoleEmitter` already receives `CHECKS_COMPLETED` events per iteration — just needs a running counter.
**Job:** Monitor (J6)
**Effort:** S — add two counters to `ConsoleEmitter`, increment in `_on_checks_completed`, display in `_on_run_stopped`.
**Risk:** None.

#### O20: Expose reload trigger from CLI (via file or signal)
**What:** Watch for a sentinel file (e.g., `.ralphify/.reload`) or catch SIGUSR1 to trigger `state.request_reload()` during a running loop. Delete the sentinel after consuming it. This bridges the gap between the existing reload infrastructure and CLI users.
**Why:** Addresses F24. Users can `touch .ralphify/.reload` in another terminal to pick up new/changed primitives without restarting. Power users can script it. No UI needed.
**Job:** Steer (J3, J6)
**Effort:** S-M — add a file watcher or signal handler in the main loop. Could piggyback on the existing `_handle_loop_transitions()` function.
**Risk:** Low. Platform-dependent (SIGUSR1 not on Windows). File sentinel approach is cross-platform.

#### O21: `ralph run --fail-fast-checks`
**What:** Add an option to stop running remaining checks after the first failure. Useful when checks are ordered from fast (lint) to slow (integration tests).
**Why:** Addresses F26. Saves time and compute when early checks fail. The best practices docs already recommend ordering checks "from fast to strict", but the tool doesn't support short-circuiting.
**Job:** Run, Trust (J2, J3)
**Effort:** S-M — change `run_all_checks` to accept an `early_exit` flag and break on first failure.
**Risk:** Low. Opt-in flag, no behavior change for existing users. Agent still sees the specific failure that triggered the stop.

### Tier 4: Exploratory / Higher Risk

#### O12: `ralph init --interactive` wizard
**What:** Interactive setup that asks: What agent? (Claude/Aider/custom), What should it work on? (generates RALPH.md), What checks? (tests/lint/typecheck based on project). Falls back to current non-interactive behavior by default.
**Why:** Could reduce 12-step onboarding to 1 command. But adds complexity and interactive UX is harder to test.
**Job:** Setup (J1, J5)
**Effort:** L
**Risk:** Medium. Interactive prompts can be annoying in CI/automation. Must remain optional.

#### O13: Reduce `-p`/`--prompt` to just positional override
**What:** Instead of a separate `--prompt` flag for inline text, let `ralph run "Fix the login bug"` work as an inline prompt (detected by the string not matching any named ralph).
**Why:** More natural CLI UX. `ralph run "Fix the login bug"` vs `ralph run -p "Fix the login bug"`.
**Job:** Run (J1)
**Effort:** M — need to disambiguate between ralph names and inline prompts.
**Risk:** Medium. How do you distinguish `ralph run docs` (named ralph) from `ralph run "docs"` (inline prompt)? Could use quoting as the signal, but fragile.

#### O22: Rename "ralphs" primitive to "prompts" or "tasks"
**What:** Rename the primitive type from "ralphs" to "prompts" (or "tasks"). The directory would be `.ralphify/prompts/` instead of `.ralphify/ralphs/`. Commands become `ralph new prompt docs` instead of `ralph new ralph docs`.
**Why:** Addresses F19 and F28. The word "ralph" is currently overloaded to mean: (1) the CLI tool, (2) the root prompt file (RALPH.md), (3) a named prompt variant (a "ralph"), (4) the `--ralph` scoping flag, and (5) the `.ralphify/ralphs/` directory. This is five meanings for one word. "Prompt" or "task" would be clearer for meaning #3-5 while keeping "ralph" as the brand/tool name.
**Job:** All (reduces cognitive load across every job)
**Effort:** L — rename in all code, update docs, migration for existing `.ralphify/ralphs/` directories.
**Risk:** High. Breaking change. But the current naming is genuinely confusing for new users. Could be done as a major version bump with a compatibility shim that auto-discovers the old directory name.

#### O23: Preview the assembled prompt before sending to agent
**What:** Add `ralph preview [name]` command that assembles the full prompt (resolving contexts, instructions, etc.) and prints it to stdout without running the agent. Useful for debugging prompt assembly and checking placeholder resolution.
**Why:** Addresses F25 (partially) and aids debugging F16 (silent exclusion). Users can see exactly what the agent will receive. Contexts execute but the agent doesn't. Could also support `ralph preview --with-failures "check output here"` to simulate the failure feedback injection.
**Job:** Trust, Steer (J2, J6)
**Effort:** M — extract `_assemble_prompt()` into a standalone command, add context execution.
**Risk:** Low. New command, no behavior changes.

---

## Principles Applied

| Principle | Where Applied |
|---|---|
| **Sensible defaults** | O1 (auto-create checks), O2 (default logs), O3 (default iteration limit), O15 (inline prompt → 1 iteration), O17 (explain scary flag) |
| **Remove before you add** | O5 (remove --prompt-file), O10 (merge instructions) |
| **Fewer concepts** | O10 (merge instructions into prompt/checks), O22 (rename ralphs to reduce polysemy) |
| **Progressive disclosure** | O3 (safe default, opt into infinite), O4 (banner only when relevant), O21 (fail-fast checks opt-in) |
| **Convention over configuration** | O1 (detect project, create appropriate checks), O2 (default log dir), O15 (inline = one-shot), O17 (agent presets) |
| **Clear feedback** | O6 (warn on silent exclusion), O7 (prompt summary), O14 (progress N/M), O16 (truncation indicator), O18 (per-check status), O19 (aggregate stats), O23 (preview command) |
| **Fewer steps** | O1 (init creates working setup), O8 (better template), O20 (reload without restart) |
| **Obvious naming** | O22 (rename ralphs to prompts/tasks) |

---

## Open Questions

1. **How many users currently use `--prompt-file`?** If the answer is "almost none," removing it (O5) is safe. If some users depend on it, provide a migration period.

2. **What's the right default for `-n`?** Proposed: 5. But should it be 3? 10? Could also scale with project type or check count. Needs user testing.

3. **Should instructions be deprecated or just deprioritized?** O10 proposes merging them into other concepts. The composability argument (shared instructions across ralphs) is real. Alternative: keep them but don't scaffold them during init or mention them in getting-started docs.

4. **Would hot-reloading primitives (O9) confuse the agent?** If a new check appears mid-run, the agent hasn't been told about it. The failure feedback will mention it, but the agent might be confused by a check it wasn't originally instructed to satisfy.

5. **Is the banner (O4) important for brand recognition?** It uses vertical space but creates visual identity. Compromise: show it only on first run per session, or make it one line instead of six.

6. **What percentage of new users run `ralph status` before `ralph run`?** If most skip validation, the quality gates in `status` aren't providing value. Consider running status checks automatically as part of `ralph run` (emit warnings, not errors).

7. **Does `detect_project()` need to be more sophisticated?** It checks 4 manifest files. Many projects have multiple (e.g., Python + Node). Should it support multi-ecosystem projects? Or is the first-match heuristic good enough for auto-scaffolding checks?

8. **Should the `-p` inline prompt automatically set `-n 1`?** Inline prompts (`ralph run -p "quick task"`) are almost always one-off. Making them default to 1 iteration would remove a footgun without affecting named ralphs. (See O15 — this iteration validates this should be a **yes**.)

9. **Is "ralph" as a primitive name too confusing to keep?** The five-way overload (tool, file, primitive, flag, directory) is a real source of confusion. But renaming is a breaking change. Would a deprecation/migration period be worth it? Or is the confusion manageable because the hidden `_DefaultRalphGroup` routing means users rarely type `ralph new ralph`?

10. **Should `ralph init` auto-update `.gitignore`?** Precedent: tools like `cargo init` and `git init` manage `.gitignore`. Ralphify could add `ralph_logs/` and optionally `.ralphify/` patterns. Risk: modifying user files beyond the explicit scope of "init" may be surprising.

11. **Should `ralph status` run automatically before `ralph run` (first time only)?** If the setup isn't valid (missing prompt file, missing command), `ralph run` fails with an error at `cli.py:318-320`. Running status checks proactively would catch issues earlier and print more helpful diagnostics. But it adds latency to every run.

12. **Would a `ralph preview` command (O23) cannibalize `ralph run -n 1`?** Some users already use `-n 1` as a dry-run-ish workflow. A preview command would be more explicit ("show me the prompt but don't run it") vs. `-n 1` ("run one real iteration"). They serve different needs: preview is for debugging prompt assembly, `-n 1` is for testing the full loop.
