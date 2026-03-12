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

### Extended Concept Load (hidden complexity)

Beyond the 10 listed concepts, users must also internalize:

11. **Directory convention** — `.ralphify/<kind>/<name>/<MARKER>.md>` pattern
12. **Placeholder resolution order** — named > bulk > implicit append (three modes)
13. **`run.*` scripts** — escape hatch from `shlex.split()` for complex commands
14. **Ralph-scoped primitives** — `.ralphify/ralphs/<name>/checks/` nesting
15. **Enabled/disabled filtering** — frontmatter flag that controls inclusion
16. **HTML comment stripping** — comments in markdown bodies are stripped from prompts

Effective concept count is **16**, not 10. Progressive disclosure should let users operate with 3–4 concepts for their first month (config file, prompt file, checks) and discover the rest as needed.

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

- **F29: `ralph.toml` has no comments or inline documentation** (VALIDATED). The generated `ralph.toml` (`_templates.py:3-8`) is 4 bare lines: `[agent]`, `command`, `args`, `ralph`. A new user has no idea what other options exist. There's no mention of `timeout`, `delay`, `log_dir`, or the `ralph` field's dual nature (file path or named ralph). Compare: a generated `.eslintrc` or `pyproject.toml` typically includes commented-out examples of common options. The user must read docs to discover any configuration beyond the defaults.

- **F36: `ralph init --force` overwrites both files without granularity** (VALIDATED). `cli.py:138-161`: `--force` overwrites both `ralph.toml` AND `RALPH.md`. A user who has carefully crafted their `RALPH.md` but wants to regenerate `ralph.toml` (e.g., to pick up a new default format) has no safe way to do this. They'd need to backup RALPH.md manually first.

### Job: Run (Launch the loop)

**Steps walked through:**

1. `ralph run` — uses ralph.toml defaults, works
2. `ralph run docs` — named ralph, works if it exists
3. `ralph run -n 3 --timeout 300 --log-dir logs` — full invocation

**Friction points identified:**

- **F6: Three ways to specify a prompt, unclear priority** (VALIDATED). Users can provide a prompt via: (a) positional `[RALPH_NAME]`, (b) `--prompt-file`/`-f`, (c) `--prompt`/`-p`, or (d) `ralph.toml`'s `ralph` field. The resolution chain in `ralphs.py:89-121` has a 4-level priority system. Using both `prompt_name` and `prompt_file` is an error (`cli.py:304-306`). This creates unnecessary cognitive load — "which one wins?" is a question users shouldn't have to answer.

- **F7: `--prompt-file` / `-f` is redundant** (VALIDATED). The `ralph.toml` already has a `ralph` field that can point to any file. Named ralphs live in `.ralphify/ralphs/`. Between the toml config and the positional argument, `--prompt-file` serves an edge case (one-off file that's not a named ralph and not the default). It adds a flag to learn and a conflict to handle (`cli.py:304-306`).

- **F8: Banner prints on every `ralph run`** (VALIDATED). The ASCII art banner (`cli.py:58-107`) prints every time the user runs `ralph run`. It's nice on first launch but wastes 8 lines of vertical space on subsequent runs. The "Star us on GitHub" line is promotional, not functional. During iteration, vertical space matters — users are scanning for check results and iteration status.

- **F9: No default for `-n` (iteration limit)** (VALIDATED). If the user omits `-n`, the loop runs infinitely until Ctrl+C. For new users, this is risky — J9 (prevent runaway costs) is a validated job. A sensible default (e.g., `-n 5` or `-n 10`) with an explicit `--no-limit` flag would protect new users while allowing power users to opt in.

- **F19: `ralph new ralph` reads awkwardly** (VALIDATED). To create a named ralph, the command is `ralph new ralph docs`. The word "ralph" appears twice: as the CLI tool name and as the primitive type. This is a consequence of using the product name ("ralph") as both the tool and a primitive type name. Compare: `git branch create` makes sense because "git" and "branch" are different words. A user may wonder "did I type that correctly?" Internally this is the `new_ralph` function at `cli.py:215-221`, which is even marked `hidden=True` — the `_DefaultRalphGroup` at `cli.py:46-52` auto-routes unknown subcommands to `ralph`, so `ralph new docs` works. But the hidden magic creates its own confusion: `ralph new --help` doesn't show how to create a ralph.

- **F20: No iteration progress when `-n` is set** (VALIDATED). When running `ralph run -n 10`, the iteration header shows `── Iteration 3 ──` but not `── Iteration 3/10 ──`. The user has no sense of progress toward the limit. The data is available in `RunConfig.max_iterations` but `ConsoleEmitter._on_iteration_started` doesn't use it (`_console_emitter.py:98-100`). For J6 (feel in control), knowing "3 of 10" vs "3 of ∞" is significant.

- **F21: `-p` inline prompt doesn't default to 1 iteration** (VALIDATED). When a user runs `ralph run -p "Fix the login bug"`, the inline prompt runs in an infinite loop, re-sending the same prompt every iteration. Inline prompts are almost always one-shot tasks. The engine at `cli.py:300-301` just uses the prompt_text with the default `n=None` (infinite). Users must remember to add `-n 1` for ad-hoc tasks or risk burning credits repeating the same prompt.

- **F33: `--stop-on-error` stops on agent failure but not check failure** (VALIDATED). From `engine.py:339-341`: `stop_on_error` only triggers when the agent process exits non-zero. Check failures do NOT trigger it — the loop continues and feeds the failure back. A user who sets `--stop-on-error` expecting the loop to stop when tests fail will be surprised. The flag name doesn't distinguish between "agent error" and "check error". There's no `--stop-on-check-failure` option. This is counterintuitive because checks ARE the error signal in ralphify's model — a check failure is the primary way users know something went wrong.

- **F38: No way to disable the banner via config or environment variable** (VALIDATED). Even users who know about the banner (F8) and find it annoying have no `RALPH_NO_BANNER=1` env var or `ralph.toml` option to suppress it. Power users running ralph in CI or scripts will be especially annoyed — the banner corrupts stdout parsing.

- **F42: No way to override ralph.toml settings from CLI** (VALIDATED). Many `ralph.toml` settings (like `command`, `args`) can only be changed by editing the file. If a user wants to quickly test with a different agent — `ralph run --command aider` — that doesn't exist. They have to edit the toml, run, then edit it back. This makes experimentation with different agents friction-heavy and error-prone (forgetting to revert the toml).

### Job: Monitor (Understand what happened)

**Steps walked through:**

1. During run: see iteration headers, spinner with elapsed time, check results
2. After run: summary line ("Done: 3 iteration(s) — 3 succeeded")
3. With `--log-dir`: per-iteration log files with full agent output

**Friction points identified:**

- **F10: No default log directory** (VALIDATED). Without `--log-dir`, all agent output is lost after the run. The user has to remember to add `--log-dir logs` every time. This contradicts J6 (feel in control even when autonomous) — you can't feel in control if you can't review what happened. Most users who care about quality will want logs. Should be on by default.

- **F11: Check failure output is truncated to 5,000 chars with no warning** (VALIDATED). `_output.py` truncates output to 5,000 characters with only `... (truncated)` appended to the text itself. This truncated text is injected into the next iteration's prompt. The CLI output (`_console_emitter.py`) shows no indication that truncation occurred. If a test suite produces verbose output, critical failure information may be cut off and the user never knows. For the agent, it sees `... (truncated)` but has no idea how much was lost (was it 5,001 chars or 50,000?).

- **F12: Iteration output is minimal during run** (VALIDATED). The console emitter (`_console_emitter.py`) shows: iteration header, spinner, completion status, check pass/fail summary. It does NOT show: which prompt was used, how many contexts/instructions were resolved, prompt length, or any preview of what the agent was told. For J6 (feel in control), users would benefit from knowing what went into each iteration.

- **F22: No indication of which check is currently running** (VALIDATED). During the checks phase, the console shows nothing until ALL checks complete. Checks run sequentially (`checks.py:125`: a list comprehension). If a user has 5 checks and the third one hangs, they see a blank screen with no indication of progress. The `CHECKS_STARTED` event fires before any checks run, and `CHECKS_COMPLETED` fires after all are done. The engine DOES emit `CHECK_PASSED`/`CHECK_FAILED` per check (`engine.py:286-289`), but `ConsoleEmitter` doesn't handle those events — only `CHECKS_COMPLETED`. The per-check event infrastructure exists but isn't rendered.

- **F23: Run summary doesn't include check statistics** (VALIDATED). The `_on_run_stopped` handler at `_console_emitter.py:138-151` shows iteration count and success/failure counts, but not check statistics. After a 10-iteration run, the user sees "Done: 10 iteration(s) — 7 succeeded, 3 failed" but not how many total checks passed/failed across all iterations. For J6 (feel in control), an aggregate like "Checks: 45/50 passed across 10 iterations" would be informative. The data exists in per-iteration `CHECKS_COMPLETED` events but isn't aggregated.

- **F31: No way to see what prompt was sent to the agent** (VALIDATED). The `PROMPT_ASSEMBLED` event at `engine.py:333` includes `prompt_length` but not the actual prompt text. `ConsoleEmitter._handlers` doesn't even include `PROMPT_ASSEMBLED` — the event is emitted but never rendered in CLI mode. Log files (`_agent.py:39-49`) only contain agent *output* (stdout/stderr), not the *input* prompt. If a user wants to debug "why did the agent do X?", they can't see what it was told. The only way is to read the source files manually and mentally resolve placeholders.

- **F32: Streaming mode only for Claude Code, silent fallback for others** (VALIDATED). `_agent.py:52-57`: `_is_claude_command` hardcodes a check for binary name "claude". Only Claude gets streaming mode with `--output-format stream-json --verbose`. All other agents get `subprocess.run` — blocking with no output until completion. There's no CLI flag or config to opt into streaming for custom agents. The dashboard's live activity feed (`AGENT_ACTIVITY` events) only works with Claude Code. Users of Aider, Codex, or custom wrappers see nothing in the dashboard during execution and get no terminal output during iteration (when logging is enabled — `_agent.py:174` sets `capture_output=bool(log_path_dir)`).

- **F41: The delay flag (`-d`) has no countdown or clear indication** (VALIDATED). When `ralph run -d 30` is used, the delay between iterations is printed as `[dim]Waiting 30s...[/dim]` (`engine.py:413`). This is a plain dim text message with no countdown, no progress bar, no indication of how long remains. For long delays (e.g., 60s to avoid rate limits), the user might think the tool has hung. The `time.sleep(config.delay)` at `engine.py:414` is a blocking call with no updates.

- **F43: Non-Claude agents show no output during iteration when logging is enabled** (VALIDATED). From `_agent.py:169-180`: when `log_path_dir` is set (including with the proposed default O2), `subprocess.run` is called with `capture_output=True`. This means ALL stdout/stderr is buffered until the process exits. For a 5-minute agent session, the terminal shows nothing but the spinner. After completion, the full output is echoed at once (`sys.stdout.write(result.stdout)`), but by then the user has been staring at a blank screen. This is the worst monitoring experience: the user sees nothing, then a wall of text. Claude Code avoids this via `run_agent_streaming` which reads line-by-line, but other agents have no equivalent.

### Job: Steer (Adjust behavior while running)

**Steps walked through:**

1. Edit RALPH.md in another terminal — re-read each iteration (works!)
2. Adding/removing checks, contexts, instructions — requires restart
3. Editing check commands — requires restart

**Friction points identified:**

- **F13: Primitive config is frozen at startup — not documented in CLI** (VALIDATED). The engine discovers primitives once at startup (`engine.py:379`). New checks, contexts, or instructions added while running are invisible until restart. The docs mention this, but the CLI gives zero indication. Users who add a check and expect it to run next iteration will be confused.

- **F14: No signal when RALPH.md changes are picked up** (VALIDATED). RALPH.md is re-read each iteration (`engine.py:184`), which is great for steering. But the console shows no indication that the prompt changed. Users editing RALPH.md while running have no confirmation their edits took effect.

- **F24: The reload mechanism exists but is invisible from CLI** (VALIDATED). The engine has `state.consume_reload_request()` at `engine.py:157` which triggers `_discover_enabled_primitives()` to re-scan all primitives. The `RunState` class has `request_reload()` (`_run_types.py:106`). But there's no CLI mechanism to trigger it — it's only accessible via the dashboard API. A user who adds a check and wants it picked up must restart the entire loop, losing their iteration count and any momentum. A signal handler (e.g., SIGUSR1) or a sentinel file could bridge this gap.

### Job: Trust (Know the output is good)

**Steps walked through:**

1. Checks run after each iteration
2. Failures feed back into next iteration's prompt
3. `ralph status` shows which checks are configured

**Friction points identified:**

- **F15: No guidance on WHAT checks to add** (VALIDATED). `ralph new check <name>` scaffolds an empty check. The template defaults to `ruff check .`. There's no "common checks" suggestion based on project type, no example library, and no indication of what good checks look like for the user's specific job.

- **F16: Silent context/instruction exclusion with named placeholders** (VALIDATED). From `resolver.py:43-55`: if you use `{{ contexts.git-log }}` without a `{{ contexts }}` bulk placeholder, ALL other contexts are silently dropped. There's no warning. This is documented in the docs but is a subtle, high-impact gotcha that violates the principle of least surprise.

- **F25: Check failure instructions are invisible until failure** (VALIDATED). The body text of CHECK.md (the failure instruction) is only ever shown to the agent, not the user. When a user creates a check, they write failure guidance in the markdown body, but there's no way to preview what the agent will actually see when the check fails. The `ralph status` command shows check names and commands but not failure instructions. For J2 (keep the agent from going off the rails), the quality of failure instructions is critical, yet users have no feedback loop on them.

- **F26: Checks always run sequentially, no early termination** (VALIDATED). `run_all_checks` at `checks.py:119-125` runs every check regardless of prior failures. If a fast lint check fails, the user still waits for a slow integration test to complete before the next iteration starts. There's no `--fail-fast` option for checks. For users with ordered checks (lint → typecheck → test), failing lint makes typecheck and test runs wasteful.

- **F30: Context command output injected regardless of exit code** (VALIDATED). From `contexts.py:85-107`: if a context command fails (non-zero exit code), the output is still injected into the prompt. This is documented as a feature ("useful for tests that fail but produce output") but is surprising. The `run_context` function returns `success=False` but `resolve_contexts` at `contexts.py:120-146` uses the output regardless of the `success` field. A user who adds `command: npm test` as a context and it fails will inject test failure output into every iteration's prompt — even though they might have intended it as a data source, not a test runner. There's no `required: true/false` frontmatter field to control whether a failed context should be injected.

- **F34: `ralph status` doesn't validate check commands will actually work** (VALIDATED). `cli.py:224-272`: `ralph status` checks if the agent command is on PATH and if the ralph file exists, but doesn't validate check or context commands. A user could have `command: ruff check .` in their check and `ruff` isn't installed — `ralph status` says "Ready to run." and the loop starts, only to have the check fail every iteration with a cryptic "command not found" error. The `status` command could parse each check's frontmatter and validate the command's first token is on PATH.

- **F37: Named placeholder for non-existent primitive silently produces empty string** (VALIDATED). From `resolver.py:35-41`: the `_replace_named` function checks `if name in available` — if the name isn't found, it returns `""`. A user who writes `{{ contexts.git-log }}` but named their context `gitlog` (no hyphen) gets an empty string with no warning. Combined with F16 (other contexts silently dropped when named placeholders are used), this can produce a prompt missing most of its intended context. The placeholder just vanishes.

- **F39: Check failure instruction text has no length guidance or limit** (VALIDATED). A check's failure instruction (body of CHECK.md) can be arbitrarily long. If a user writes a 10,000-character essay in CHECK.md, that full text gets appended to the prompt every time the check fails (`checks.py:152-153`). The check output is truncated to 5,000 chars, but the failure instruction is not. A verbose failure instruction could consume more of the agent's context window than the actual error output. The best practices docs say "write failure instructions that guide, not just complain" but the tool doesn't enforce or warn about excessive length.

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

- **F40: `ralph new` doesn't open the created file in `$EDITOR`** (VALIDATED). After `ralph new check tests`, the user sees "Created .ralphify/checks/tests/CHECK.md" and then has to manually navigate to and open the file. Many CLI tools (e.g., `git commit`, `crontab -e`) open the file automatically. Given that every scaffolded file needs editing (the templates contain generic placeholder content), this adds one extra step per primitive creation. A `--edit` flag (or auto-detect `$EDITOR`) would save time.

### Error Message Quality Audit (NEW)

This section walks through every error path in the codebase and evaluates whether the error message helps the user fix the problem. Grounded in: if a user triggers this error, can they immediately know what to do?

**Error: `ralph.toml not found. Run 'ralph init' first.`** (`cli.py:131`)
- Quality: GOOD. Clear problem, clear fix. Exit code 1.

**Error: `{CONFIG_FILENAME} already exists. Use --force to overwrite.`** (`cli.py:148`)
- Quality: GOOD. Tells user what to do.

**Error: `RALPH.md already exists. Use --force to overwrite.`** (`cli.py:155`)
- Quality: GOOD.

**Error: `Cannot use both a ralph name and --prompt-file.`** (`cli.py:305`)
- Quality: ADEQUATE. Says what's wrong but doesn't say which to prefer. Could add: "Use one or the other."

**Error: `Ralph '{name}' not found. Available: {list}`** (`ralphs.py:73-76`)
- Quality: GOOD. Shows what's available, suggests correction.

**Error: `Prompt file '{path}' not found.`** (`cli.py:319`)
- Quality: ADEQUATE. Says what's missing but doesn't suggest how to create it. Could add: "Run 'ralph init' to create RALPH.md."

**Error: `{Label} '{name}' already exists at {path}`** (`cli.py:181`)
- Quality: GOOD. Shows exact path.

**Error: `Check '{name}' has neither a run.* script nor a command — skipping`** (`checks.py:61`)
- Quality: POOR — this is a `warnings.warn()`, not a CLI error. It fires during discovery and might be lost in output. A user who creates a CHECK.md and forgets to add a command gets a warning they might never see. The check is silently excluded from the loop. For `ralph status`, this check would show up with `?` detail but no explanation of why.

- **F44: Check without command/script produces a warning, not a clear error** (NEW, VALIDATED). `checks.py:55-62`: when a CHECK.md has no `command` field and no `run.*` script, `_check_from_entry` returns `None` and the check is silently excluded from the list. A `warnings.warn()` fires but users may not see it. The `ralph status` command shows `?` for the detail but doesn't explain why. A user who creates a check and forgets to add the command sees the check in `ralph status` with `?`, runs the loop, and the check never executes. No error, no clear signal.

**Error: `Agent command not found: '{command}'. Check the [agent] command in ralph.toml.`** (`engine.py:224-227`)
- Quality: GOOD. Clear error, points to config file.

**Error: (Crash traceback) `Run crashed: {exc}`** (`engine.py:419-425`)
- Quality: ADEQUATE. Shows traceback in dim text but this is a catch-all. Unexpected errors get the same treatment as known errors.

- **F45: `ralph.toml` has no schema validation** (NEW, VALIDATED). `cli.py:127-134`: `_load_config()` loads the TOML file and returns a raw dict. The `run()` function at `cli.py:294-297` accesses `config["agent"]`, `agent["command"]`, etc. with no validation. If `ralph.toml` is missing the `[agent]` section, `command` field, or has typos (e.g., `comandd`), the user gets a raw Python `KeyError` traceback — not a helpful error message. Example: a user who writes `commnad = "claude"` (typo) gets `KeyError: 'command'` with no context about which key is missing or where.

- **F46: `resolve_ralph_source` has a confusing silent fallback** (NEW, VALIDATED). `ralphs.py:108-123`: when `ralph.toml` has `ralph = "docs"` (looks like a name) but no ralph named "docs" exists, the function silently falls back to treating "docs" as a file path. The user then hits "Prompt file 'docs' not found" — a confusing error because they intended "docs" as a ralph name, not a file path. The heuristic `is_ralph_name()` at `ralphs.py:79-88` checks for absence of `/` and `.` — but `"docs"` passes both checks. The fallback at line 121 (`return toml_ralph, None`) converts a "ralph not found" into a "file not found" without explaining the resolution chain.

- **F47: `ralph status` doesn't show which ralph will be used by `ralph run`** (NEW, VALIDATED). `cli.py:224-272`: the status command shows the `ralph` field from the config (e.g., `RALPH.md`), validates it exists, but doesn't indicate whether `ralph run` would use a named ralph, a root prompt file, or has a fallback chain. If `ralph.toml` has `ralph = "docs"`, status shows `Ralph: docs` and checks if the *file* "docs" exists — but it should check whether a ralph named "docs" exists under `.ralphify/ralphs/`. The status command doesn't mirror `resolve_ralph_source()`'s logic, so what status reports and what `run` uses can diverge.

- **F48: Context timeout defaults to 30s — silently fails for slow commands** (NEW, VALIDATED). `contexts.py:33`: the default context timeout is 30 seconds. If a user adds `command: npm test` as a context (to show test status) and the test suite takes >30s, the context silently times out. The output up to the timeout is still injected, but it's incomplete. There's no warning that a context timed out — the ContextResult has `timed_out=True` but `resolve_contexts` at `contexts.py:120-146` uses the output regardless. The user sees partial test output in their prompt with no indication that it was cut short by a timeout, not by the tests finishing.

- **F49: Log file naming is opaque** (NEW, VALIDATED). `_agent.py:46-48`: log files are named `{iteration:03d}_{timestamp}.log` (e.g., `001_20250312-143022.log`). This is useful for ordering but tells the user nothing about what happened. There's no way to quickly identify which iterations had failures vs successes from the filename alone. A naming convention like `001_20250312-143022_pass.log` or `001_20250312-143022_fail.log` would let users scan the log directory for problems.

- **F50: Non-Claude agent output dumped as wall of text after iteration** (NEW, VALIDATED). `_agent.py:176-181`: after `subprocess.run` completes with `capture_output=True`, the full stdout is dumped via `sys.stdout.write(result.stdout)`. This is a raw write — no paging, no truncation, no formatting. If the agent produced 10,000 lines of output, all 10,000 lines are printed at once between the iteration header and the check results. The user sees the spinner, then a massive wall of text, then the check results. The iteration status line (✓/✗ with duration) gets buried in the output.

### Configuration Surface Area Analysis (NEW)

The configuration story has three layers that interact in non-obvious ways:

**Layer 1: `ralph.toml` (project-level defaults)**
```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```
- Only 3 fields. No validation. No schema.
- `ralph` field has dual semantics: file path OR named ralph name. The distinction is made by `is_ralph_name()` checking for absence of `/` and `.`.
- No config for: timeout, delay, log_dir, stop_on_error. These are CLI-only.
- **Gap**: Users who always want `--log-dir logs --timeout 300` must type it every time. There's no way to set defaults in the config.

**Layer 2: CLI flags (per-invocation overrides)**
- 8 flags on `ralph run`, 1 on `ralph init`, 0 on `ralph status`.
- Cannot override `command` or `args` from CLI — must edit toml.
- Can set `--timeout` on CLI but not in toml. Can set `command` in toml but not on CLI. The two config surfaces are **non-overlapping** except for the `ralph` field.

**Layer 3: Frontmatter (per-primitive config)**
- `enabled`, `timeout`, `command`, `description` fields. Only `enabled` and `timeout` have type coercion.
- No schema or validation beyond type coercion. Unknown fields silently accepted as strings.
- `timeout` in frontmatter (per-check/context) vs `--timeout` on CLI (per-iteration) — same word, different scope. A user might think `--timeout 300` sets check timeouts.

**The interplay creates friction:**
- "How do I set the default timeout for all checks?" → Can't. Each check has its own frontmatter timeout, defaulting to 60s. No global check timeout.
- "How do I always log to a directory?" → Can't configure in toml. Must add `--log-dir` every time or use a shell alias.
- "How do I switch agents for one run?" → Can't use CLI. Must edit toml, run, edit back.
- "What does `ralph = "docs"` mean in my toml?" → Could be a file named "docs" or a ralph named "docs". `is_ralph_name()` decides, but the user has no visibility into this heuristic.

- **F51: CLI and toml config surfaces don't overlap** (NEW, VALIDATED). The CLI has `--timeout`, `--delay`, `--log-dir`, `--stop-on-error` that can't be set in toml. The toml has `command` and `args` that can't be overridden from CLI. Users who want consistent defaults for CLI-only settings have no config mechanism. Users who want to experiment with CLI-settable toml settings must edit the file. This creates a "worst of both worlds" situation where neither the config file nor the CLI is a complete control surface.

---

## Cross-Cutting Analysis

### The Invisible Infrastructure Problem

Several friction points share a root cause: things happen invisibly and the user has no way to observe them. This is the single biggest trust issue in ralphify's UX.

| What's invisible | Friction | Impact |
|---|---|---|
| Output truncation (5,000 chars) | F11 | User/agent don't know critical info was cut |
| Primitive config frozen at startup | F13 | User adds check, expects it to run, nothing happens |
| Prompt changes picked up silently | F14 | User edits RALPH.md, no confirmation it took effect |
| Context/instruction silent exclusion | F16 | Named placeholders silently drop other primitives |
| Per-check execution progress | F22 | User stares at blank screen during check phase |
| Full assembled prompt | F31 | User can't see what agent was told |
| Agent execution (non-Claude) | F43 | No output during iteration for non-Claude agents |
| Named placeholder resolution failure | F37 | Typo in placeholder name → silent empty string |
| Context timeout | F48 | Context times out silently, partial output injected |
| Ralph name/path resolution | F46 | Name falls back to path silently, confusing error |

**Root principle: Observability is trust.** Users can't trust what they can't see. Every invisible operation should have at least a dim/debug-level signal in the CLI output. The cost of one extra line of output is far lower than the cost of a user spending 20 minutes debugging why their context isn't being injected.

### The Two User Journeys

The friction analysis reveals two distinct user journeys with fundamentally different needs:

**Journey A: Quick Start** (Vibe Coder, Solo Founder)
- Wants: `ralph init && ralph run` to just work
- Blocked by: F1 (useless template), F2 (no checks), F3 (detection waste), F5 (12 steps), F9 (infinite default)
- Needs: smart defaults, auto-scaffolding, safe guardrails

**Journey B: Deep Customization** (Staff Engineer, Platform Engineer)
- Wants: fine-grained control over every aspect of the loop
- Blocked by: F31 (can't see prompt), F32 (Claude-only streaming), F42 (can't override config from CLI), F33 (stop-on-error semantics), F26 (no fail-fast), F51 (non-overlapping config surfaces)
- Needs: preview command, per-check events, CLI overrides, pluggable streaming, unified config

Current UX is stuck in the middle: too much ceremony for quick starters (12 steps), not enough power tools for power users. The simplification strategy should explicitly serve both — **reduce the floor** (fewer steps to first run) and **raise the ceiling** (more control for experts).

### The "Ralph" Naming Overload

The word "ralph" carries 5 meanings:
1. The CLI tool name (`ralph run`)
2. The root prompt file (`RALPH.md`)
3. A named prompt variant ("a ralph")
4. The `--ralph` scoping flag on `ralph new`
5. The `.ralphify/ralphs/` directory

This creates friction at F19, F22, F28 and any documentation that tries to distinguish between these uses. The `_DefaultRalphGroup` hidden routing (`cli.py:46-52`) is clever but adds a 6th layer of confusion: `ralph new docs` secretly becomes `ralph new ralph docs`, but this isn't shown in `--help`.

### The Configuration Identity Crisis (NEW)

Ralphify has three non-overlapping configuration surfaces (see F51):

1. **`ralph.toml`** controls: agent command, agent args, default prompt source
2. **CLI flags** control: iteration limit, timeout, delay, log dir, stop behavior
3. **Frontmatter** controls: per-primitive enabled, timeout, command

No single surface is authoritative. The mental model should be: "toml for project defaults, CLI for session overrides, frontmatter for per-primitive config." But the implementation doesn't follow this cleanly:
- `timeout` appears in both CLI (per-iteration) and frontmatter (per-check), with confusingly similar names but different scopes
- `ralph` (prompt source) appears in both toml and CLI (positional + `--prompt-file`)
- Common settings like log directory and iteration limit have no toml representation

**Opportunity: Unify the config model.** Allow `ralph.toml` to set defaults for ALL settings:
```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"

[run]
max_iterations = 5
timeout = 300
delay = 0
log_dir = "ralph_logs"
stop_on_error = false
```
CLI flags override toml defaults. This eliminates F42 and F51 simultaneously.

### The Error Diagnostic Gap (NEW)

The error path analysis reveals a pattern: errors are well-worded for expected cases (file not found, config not found) but fall through to raw Python exceptions for edge cases:
- Missing `[agent]` section in toml → `KeyError: 'agent'`
- Typo in toml field name → `KeyError` with no context
- Malformed frontmatter → depends on the parsing failure mode

The fix is lightweight: add a config validation step in `_load_config()` that checks for required keys and returns a typed object (or at minimum a clear error).

### The Agent Parity Problem (NEW)

Ralphify markets itself as "agent-agnostic" but the implementation is Claude-first:

| Feature | Claude Code | Other agents |
|---|---|---|
| Streaming output | Yes (JSON lines) | No |
| Dashboard activity feed | Yes | No (silent) |
| Live terminal output during iteration | Yes | Only without `--log-dir` |
| Result text extraction | Yes (`result` field from JSON) | No |
| Auto-added flags | `--output-format stream-json --verbose` | None |

This isn't necessarily wrong — Claude Code is the primary audience. But the marketing says "works with any agent CLI" while the experience diverges sharply. For non-Claude users, ralphify feels like a wrapper around `subprocess.run` with added complexity.

**Key insight:** The agent parity gap affects monitoring (J6) disproportionately. Non-Claude users can still SET UP and RUN loops fine. But they can't MONITOR effectively because the streaming/logging infrastructure assumes Claude's JSON output format. This makes the tool feel less trustworthy (J2) for non-Claude users.

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
**Risk:** Low. Disk space is cheap. Users who don't want logs can opt out. **But see F43** — enabling default logging for non-Claude agents means `capture_output=True`, which blocks all terminal output during iteration. O2 should be implemented together with a fix for F43 (e.g., use `tee`-style capture).

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

#### O24: Render per-check events in ConsoleEmitter
**What:** Add `CHECK_PASSED` and `CHECK_FAILED` to `ConsoleEmitter._handlers`. Show `  ⋯ running: tests` before each check and the pass/fail result immediately after.
**Why:** Addresses F22. The event infrastructure already exists (`engine.py:286-289` emits `CHECK_PASSED`/`CHECK_FAILED` per check). The `ConsoleEmitter` just doesn't handle them — it only renders `CHECKS_COMPLETED`. This is the lowest-effort monitoring improvement possible: the data is already flowing, it just needs a renderer.
**Job:** Monitor (J6)
**Effort:** XS — add two handlers to `_handlers` dict, ~10 lines of rendering code.
**Risk:** None.

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
**What:** Show `  ⋯ running: tests` in the console during each check.
**Why:** Addresses F22. Users with multiple checks (especially slow ones like integration tests) can see which check is currently running instead of staring at a blank screen.
**Job:** Monitor (J6)
**Effort:** S-M — the events already exist (CHECK_PASSED/CHECK_FAILED are emitted per-check). The gap is in `ConsoleEmitter` rendering (see O24) and potentially adding a CHECK_STARTED event to show the name before it runs.
**Risk:** Very low. More events = more information.

#### O25: Warn on unresolved named placeholders
**What:** When `{{ contexts.git-log }}` resolves to empty string because no context named "git-log" exists, emit a warning: `⚠ Placeholder {{ contexts.git-log }} not found — no context with that name exists. Available: gitlog, git-diff`.
**Why:** Addresses F37. Typos in placeholder names are currently silent and devastating — the user's prompt is missing critical context with no indication. The `_replace_named` function at `resolver.py:35-41` already knows the name isn't in `available`; it just needs to warn instead of silently returning `""`.
**Job:** Trust (J2, J6)
**Effort:** S — add a `warnings.warn()` call in `_replace_named` when `name not in available`. List available names in the warning message.
**Risk:** Very low. Warning only, no behavior change.

#### O26: Validate check/context commands in `ralph status`
**What:** Parse each check's and context's frontmatter `command` field, extract the first token (via `shlex.split`), and check if it's on PATH. Show a warning for each command that can't be found.
**Why:** Addresses F34. Users who run `ralph status` and see "Ready to run." should be able to trust that claim. Currently, a missing `ruff` binary will only surface as repeated check failures during the loop.
**Job:** Trust, Setup (J2, J5)
**Effort:** S — iterate over discovered checks/contexts in the `status` command, call `shutil.which()` on each command's first token.
**Risk:** Very low. Warnings only. Some commands might be scripts or PATH-dependent in ways that can't be validated statically, so frame as "warning" not "error".

#### O27: Clarify `--stop-on-error` semantics or add `--stop-on-check-failure`
**What:** Either: (a) rename `--stop-on-error` to `--stop-on-agent-error` to make the scope explicit, or (b) add a `--stop-on-check-failure` flag that stops the loop when any check fails, or (c) change `--stop-on-error` to also trigger on check failures (breaking change).
**Why:** Addresses F33. Check failures are the primary signal in ralphify — they're what makes the loop self-healing. A user who sets `--stop-on-error` expecting it to cover checks will be surprised when the loop continues after test failures. The current behavior makes sense for ralphify's model (self-healing loops should continue), but the flag name is misleading.
**Job:** Run, Trust (J2, J6)
**Effort:** S-M — option (a) is a rename, (b) is a new flag + one conditional in engine.py.
**Risk:** Low for (a) and (b). Higher for (c) since it changes default behavior.

#### O31: Validate `ralph.toml` schema on load (NEW)
**What:** Add validation in `_load_config()` that checks for required keys (`[agent]`, `command`) and provides clear error messages: "ralph.toml is missing the 'command' field under [agent]. Example: command = \"claude\"". Use a simple dict check, not a schema library.
**Why:** Addresses F45. Currently, a typo in ralph.toml produces a raw Python KeyError. Schema validation turns cryptic tracebacks into actionable error messages. This is a trust issue — if the tool crashes on a config typo, users lose confidence.
**Job:** Setup, Trust (J1, J5)
**Effort:** S — add ~15 lines of validation code in `_load_config()`.
**Risk:** None.

#### O32: Show context timeout warnings (NEW)
**What:** When a context command times out (`ContextResult.timed_out=True`), emit a warning in the CLI: `⚠ Context 'tests' timed out after 30s — output may be incomplete. Consider increasing timeout in CONTEXT.md frontmatter.` Also mark the injected output: `(timed out after 30s — output may be incomplete)`.
**Why:** Addresses F48. Context timeouts are currently invisible. The partial output is injected without any indication that it was cut short. This can cause the agent to act on incomplete information.
**Job:** Trust, Monitor (J2, J6)
**Effort:** S — add timeout check in the context resolution path, emit a warning event.
**Risk:** None.

#### O33: Unify config surfaces — add `[run]` section to `ralph.toml` (NEW)
**What:** Allow ralph.toml to set defaults for all `ralph run` flags:
```toml
[run]
max_iterations = 5
timeout = 300
delay = 0
log_dir = "ralph_logs"
stop_on_error = false
```
CLI flags override toml defaults. Existing behavior unchanged if `[run]` section is absent.
**Why:** Addresses F42 and F51. Users who always want the same settings don't have to type them every time. Makes the config file the single source of project-level defaults.
**Job:** Run, Setup (J1, J5, J6)
**Effort:** M — parse new section in `_load_config()`, merge with CLI args in `run()`.
**Risk:** Low. Purely additive — no breaking changes. CLI flags always win.

### Tier 3: Medium Impact, Medium Effort

#### O9: Hot-reload primitives
**What:** Re-discover checks, contexts, and instructions at the start of each iteration (not just startup).
**Why:** Addresses F13 and F24. Users can add/modify checks while the loop runs without restarting. Makes the steering experience consistent — if RALPH.md can change mid-run, why can't checks?
**Job:** Steer (J3, J6)
**Effort:** M — move `_discover_enabled_primitives()` call into the iteration loop. The `consume_reload_request()` mechanism exists in the engine (`engine.py:157`), so infrastructure is partially there. Could also use a lighter approach: compare file mtimes before rescanning.
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

#### O28: Fix non-Claude agent output during logging
**What:** For non-streaming agents (`run_agent` in `_agent.py`), use a `tee`-style approach: read output line-by-line and simultaneously display to terminal and buffer for log file, instead of the current all-or-nothing `capture_output`.
**Why:** Addresses F43 and F50. Currently, enabling `--log-dir` for non-Claude agents means zero terminal output during the entire iteration, followed by a wall of text. This is the worst possible monitoring experience and directly contradicts J6 (feel in control). With the proposed O2 (default logging), this would become the default experience for all non-Claude users — making O28 a prerequisite for O2.
**Job:** Monitor (J6)
**Effort:** M — change `subprocess.run` to `subprocess.Popen` with a line-by-line read loop similar to `run_agent_streaming`, but without JSON parsing.
**Risk:** Low. The streaming version for Claude already proves this approach works.

#### O29: Add inline comments to generated `ralph.toml`
**What:** Expand the `RALPH_TOML_TEMPLATE` to include commented-out examples of common config options: `# timeout = 300`, `# delay = 5`, `# log_dir = "ralph_logs/"`. Add a comment explaining the `args` line for Claude Code users.
**Why:** Addresses F29 and partially F17. The config file is the first thing a user reads after init. It should be self-documenting enough that the user doesn't need to open docs to understand what's configurable.
**Job:** Setup (J1, J5)
**Effort:** XS — just change the template string.
**Risk:** None.

#### O34: Improve `ralph status` to mirror `ralph run` resolution (NEW)
**What:** Make `ralph status` use the same `resolve_ralph_source()` logic as `ralph run`. Show the resolved prompt source: "Ralph: RALPH.md (from ralph.toml)" or "Ralph: .ralphify/ralphs/docs/RALPH.md (named ralph 'docs')". Warn if the `ralph` field in toml matches neither a file nor a named ralph.
**Why:** Addresses F46 and F47. Currently `ralph status` and `ralph run` can disagree about which prompt file to use. Status shows the raw toml value; run resolves it through a priority chain with fallbacks. If they diverge, the user trusts status and is surprised by run.
**Job:** Trust, Setup (J2, J6)
**Effort:** S-M — call `resolve_ralph_source()` from status and display the resolved path.
**Risk:** Very low.

#### O35: Include pass/fail suffix in log filenames (NEW)
**What:** Change log file naming from `001_20250312-143022.log` to `001_20250312-143022_pass.log` or `001_fail.log`. The suffix reflects the agent's exit code.
**Why:** Addresses F49. Users scanning a log directory can immediately identify failed iterations without opening each file. Essential for long runs (50+ iterations) where manual scanning is infeasible.
**Job:** Monitor (J6)
**Effort:** XS — pass return code to `_write_log()`, append suffix to filename.
**Risk:** Very low. Log file naming is internal, not a public API.

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
**Why:** Addresses F31 and F25 (partially) and aids debugging F16 (silent exclusion) and F37 (silent empty placeholder). Users can see exactly what the agent will receive. Contexts execute but the agent doesn't. Could also support `ralph preview --with-failures "check output here"` to simulate the failure feedback injection.
**Job:** Trust, Steer (J2, J6)
**Effort:** M — extract `_assemble_prompt()` into a standalone command, add context execution.
**Risk:** Low. New command, no behavior changes.

#### O30: Save assembled prompt to log directory
**What:** When `--log-dir` is set, write the assembled prompt to the log file alongside agent output. Format: `=== PROMPT ===\n{prompt}\n=== OUTPUT ===\n{output}`.
**Why:** Addresses F31 without adding a new CLI command. Users debugging "why did the agent do X?" can check the log file to see both the input and the output. This is simpler than O23 (preview command) and covers the most common debugging scenario.
**Job:** Monitor, Trust (J6)
**Effort:** S — pass the assembled prompt to `_execute_agent`, include it in the log write.
**Risk:** Very low. Log files get larger, but disk space is cheap and the prompt is the most important debugging artifact.

---

## Principles Applied

| Principle | Where Applied |
|---|---|
| **Sensible defaults** | O1 (auto-create checks), O2 (default logs), O3 (default iteration limit), O15 (inline prompt → 1 iteration), O17 (explain scary flag), O29 (documented config), O33 (toml defaults for run settings) |
| **Remove before you add** | O5 (remove --prompt-file), O10 (merge instructions) |
| **Fewer concepts** | O10 (merge instructions into prompt/checks), O22 (rename ralphs to reduce polysemy) |
| **Progressive disclosure** | O3 (safe default, opt into infinite), O4 (banner only when relevant), O21 (fail-fast checks opt-in) |
| **Convention over configuration** | O1 (detect project, create appropriate checks), O2 (default log dir), O15 (inline = one-shot), O17 (agent presets) |
| **Clear feedback** | O6 (warn on silent exclusion), O7 (prompt summary), O14 (progress N/M), O16 (truncation indicator), O18/O24 (per-check status), O19 (aggregate stats), O23/O30 (prompt visibility), O25 (warn on missing placeholder), O26 (validate commands), O31 (config validation), O32 (context timeout warning), O34 (status mirrors run), O35 (log file naming) |
| **Fewer steps** | O1 (init creates working setup), O8 (better template), O20 (reload without restart) |
| **Obvious naming** | O22 (rename ralphs to prompts/tasks), O27 (clarify stop-on-error scope) |
| **Observability is trust** | O7, O14, O16, O24, O25, O26, O28, O30, O32, O34, O35 (every invisible operation gets a signal) |
| **Single source of truth** | O31 (validated config), O33 (unified config surface), O34 (status mirrors run) |

---

## Recommended Implementation Order

Based on re-ranking with cross-cutting insights:

**Phase 1 — "Just Works" (all XS-S effort, highest combined impact):**
1. O4: Suppress banner on `ralph run` (XS)
2. O14: Show iteration progress N/M (XS)
3. O15: Default `-n 1` for inline prompts (XS)
4. O24: Render per-check events in ConsoleEmitter (XS — events already exist)
5. O29: Add inline comments to generated `ralph.toml` (XS)
6. O35: Include pass/fail suffix in log filenames (XS)
7. O7: Show prompt assembly summary per iteration (S)
8. O19: Aggregate check statistics in run summary (S)
9. O25: Warn on unresolved named placeholders (S)
10. O31: Validate `ralph.toml` schema on load (S)
11. O32: Show context timeout warnings (S)

**Phase 2 — "Smart Setup" (S-M effort, addresses the biggest setup gap):**
12. O1: Smart `ralph init` with auto-created checks (S)
13. O8: Better `ralph init` prompt template (S)
14. O17a: Add comment to `ralph.toml` explaining dangerous flag (S)
15. O3: Default iteration limit of 5 (S, needs careful migration comms)
16. O26: Validate check/context commands in `ralph status` (S)
17. O34: Improve `ralph status` to mirror `ralph run` resolution (S-M)
18. O6: Warn on silent context/instruction exclusion (S-M)

**Phase 3 — "Observable Loop" (M effort, addresses monitoring gaps):**
19. O28: Fix non-Claude agent output during logging (M — prerequisite for O2)
20. O2: Default log directory (S, but depends on O28)
21. O16: Show truncation details (S)
22. O30: Save assembled prompt to log directory (S)
23. O33: Unify config surfaces — add `[run]` section to toml (M)

**Phase 4 — "Power User Tools" (M-L effort, addresses expert needs):**
24. O23: Preview command (M)
25. O5: Remove `--prompt-file` flag (S-M)
26. O21: Fail-fast checks (S-M)
27. O27: Clarify stop-on-error semantics (S-M)
28. O9: Hot-reload primitives (M)

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

13. **Should O2 (default logging) be blocked on O28 (fix non-Claude output)?** Enabling default logging for non-Claude agents would cause F43 (zero terminal output during iteration) to become the default experience. This is a worse UX than no logging. Recommendation: implement O28 first, then O2.

14. **Is `context.success` field being ignored a bug or a feature?** `resolve_contexts` at `contexts.py:120-146` uses context output regardless of whether the command succeeded. The FAQ says "Context commands run regardless of exit code" — but users may not expect failed command output in their prompt. Should there be a `required: true` field that skips injection on failure?

15. **Should `--stop-on-error` cover check failures too?** The current behavior (only stops on agent process failure) makes sense for the self-healing loop model. But users from CI/CD backgrounds expect "stop on error" to mean "stop when anything fails." Options: rename to `--stop-on-agent-error`, add `--stop-on-check-failure`, or change the behavior with a deprecation warning.

16. **Should `ralph.toml` support a `[run]` section for default CLI settings?** (NEW) O33 proposes this but it changes the config surface. Questions: Should all CLI flags be representable in toml? What about flags that only make sense per-invocation (like `-p`)? Should there be a precedence doc?

17. **Should log files include the assembled prompt?** (NEW) O30 proposes this. The prompt can be large (5,000+ chars with contexts). Including it in every log file doubles the file size. Alternative: write a separate `001_prompt.md` file alongside the log. Or only write the prompt when a `--debug` flag is set.

18. **How should the dual-nature of `ralph.toml`'s `ralph` field be resolved?** (NEW) Currently `is_ralph_name()` checks for absence of `/` and `.`. This heuristic fails for values like `my-task` (could be either). Should the field be split into `ralph_file` and `ralph_name`? Or should named ralphs always be prefixed (e.g., `ralph = "@docs"`)? The current silent fallback (F46) is the biggest source of confusing errors.
