# Architecture Opportunities — Jobs to Be Done

## User Jobs

Ranked by frequency × intensity (from JTBD research):

1. **J1: Ship features while I'm not coding** — Set agent running autonomously, wake up to working code. VERY HIGH.
2. **J2: Keep the agent from going off the rails** — Automatic quality gates with self-healing feedback. VERY HIGH.
3. **J3: Stop babysitting the agent** — Step away, let the agent work independently. HIGH.
4. **J5: Have a reliable, repeatable workflow** — Replace fragile bash scripts with structured primitives. HIGH.
5. **J6: Feel in control even when autonomous** — See what happened each iteration without reviewing every line. HIGH.
6. **J9: Prevent runaway costs** — Guardrails against cost blowouts. HIGH.
7. **J10: Encode expertise into guardrails** — Senior judgment encoded as reusable checks/instructions. MEDIUM-HIGH.
8. **J8: Standardize workflows across team** — Shared, version-controlled harness config. MEDIUM.

## System Jobs

These are the internal jobs the software must perform to fulfill user jobs. Each is mapped to its owning module(s) and the user jobs it serves.

### SJ1: Discover primitives on disk
**Owner:** `_discovery.py` (generic scanning), `checks.py`, `contexts.py`, `instructions.py`, `ralphs.py` (type-specific construction)
**Serves:** J1, J2, J5, J10
**Assessment:** Well-factored. The `Primitive` protocol in `_discovery.py:19-32` enables type-safe generic operations. `discover_primitives()` (line 82) handles directory scanning. Each primitive module has a `_xxx_from_entry()` constructor that converts `PrimitiveEntry` to its domain type. The `discover_enabled()` generic (line 119) captures the discover → merge → filter pattern.

**Issue: Repetitive boilerplate across primitive modules.** Each module repeats the same three-function chain:
- `discover_xxx(root)` → calls `discover_primitives(root, kind, marker)` + maps entries
- `discover_xxx_local(prompt_dir)` → calls `discover_local_primitives(prompt_dir, kind, marker)` + maps entries
- `discover_enabled_xxx(root, prompt_dir)` → calls `discover_enabled(root, prompt_dir, discover_xxx, discover_xxx_local)`

Compare `checks.py:94-118`, `contexts.py:66-91`, `instructions.py:41-65` — structurally identical. The entry-to-dataclass conversion (`_check_from_entry`, `_context_from_entry`, `_instruction_from_entry`) is the only unique part. This isn't a bug — the pattern is explicit and easy to follow — but it's a maintenance smell: adding a new primitive type requires copying ~30 lines of boilerplate.

### SJ2: Resolve templates and placeholders
**Owner:** `resolver.py` (core logic), `contexts.py:resolve_contexts()` (line 129), `instructions.py:resolve_instructions()` (line 68)
**Serves:** J1, J2, J5
**Assessment:** Clean. `resolver.py` is 57 lines with a single public function (`resolve_placeholders`). The three resolution strategies (named, bulk, implicit append) are well-documented. Both contexts and instructions delegate to the same function, which prevents drift.

**No significant issues.** The silent empty-string behavior for missing named placeholders (`resolver.py:38-40`) is documented as friction F37 in the UX research, but that's a feature/UX decision, not an architectural problem.

### SJ3: Orchestrate the iteration loop
**Owner:** `engine.py`
**Serves:** J1, J2, J3, J5, J6
**Assessment:** Well-structured. `engine.py` is ~407 lines decomposed into focused helpers:
- `_discover_enabled_primitives()` (line 56) — discovery layer
- `_handle_loop_transitions()` (line 114) — state machine (stop/pause/reload)
- `_assemble_prompt()` (line 146) — pure text assembly
- `_run_agent_phase()` (line 173) — agent execution + state updates
- `_run_checks_phase()` (line 229) — check execution + event emission
- `_run_iteration()` (line 267) — one full iteration
- `run_loop()` (line 316) — the outer loop

Each helper has a clear, documented responsibility. The `_BoundEmitter` (line 78) reduces boilerplate in event emission. State counter updates are localized in `_run_agent_phase` (lines 202-215) — explicitly called out as "one place for easy auditing."

**No significant architectural issues.** This is the strongest module in the codebase.

### SJ4: Execute subprocesses
**Owner:** `_agent.py` (agent execution), `_runner.py` (check/context execution)
**Serves:** J1, J2, J3
**Assessment:** Clean separation. `_agent.py` handles the complex agent case (streaming vs. blocking, log writing, result_text extraction). `_runner.py` handles the simple check/context case (run command, capture output, handle timeout). Different enough to justify two modules.

**Issue: Agent detection is hardcoded.** `_agent.py:52-57` — `_is_claude_command()` checks if the binary name is `"claude"`. This determines streaming vs. blocking mode. All other agents get the inferior blocking path with no output during execution (validated as friction F32, F43). This hardcoding couples the execution mode to a specific vendor rather than to a capability. A user running a custom wrapper that supports stream-json has no way to opt in.

**Issue: Blocking mode hides output when logging is enabled.** `_agent.py:170-176` — `subprocess.run(capture_output=bool(log_path_dir))`. When logging is on, ALL output is buffered until the process exits. For a 5-minute agent session, the terminal shows only a spinner. After completion, the full output is dumped via `sys.stdout.write(result.stdout)` (line 179-180). Validated as F43.

### SJ5: Emit events for rendering
**Owner:** `_events.py` (types + protocols), `_console_emitter.py` (CLI rendering)
**Serves:** J6, J3
**Assessment:** Well-designed protocol-based system. The `EventEmitter` protocol (line 129) is minimal (single `emit` method). Four implementations cover all use cases: `NullEmitter` (tests), `QueueEmitter` (async consumers), `FanoutEmitter` (multi-listener), `ConsoleEmitter` (CLI).

**Issue: ConsoleEmitter ignores several event types.** `_console_emitter.py:51-59` registers handlers for only 8 of 15 event types. Notably missing:
- `CHECK_PASSED` / `CHECK_FAILED` — per-check events exist (`engine.py:251-254`) but aren't rendered live; only the aggregate `CHECKS_COMPLETED` is shown (validated as F22)
- `PROMPT_ASSEMBLED` — emitted with `prompt_length` (`engine.py:298`) but never rendered (validated as F31)
- `CONTEXTS_RESOLVED` — emitted (`engine.py:292`) but never rendered (validated as F12)
- `AGENT_ACTIVITY` — only useful for Claude Code streaming; no fallback for other agents

The event infrastructure is ahead of the rendering layer. Events are emitted but not consumed — wasted work in every iteration.

### SJ6: Manage run state
**Owner:** `_run_types.py`
**Serves:** J1, J3, J6
**Assessment:** Clean. `RunConfig` (line 37) and `RunState` (line 62) are well-documented dataclasses. `RunState` uses `threading.Event` for pause/resume/stop — thread-safe by design. Counter invariants are documented in the class docstring (line 69-77).

**No significant issues.** The separation of types into `_run_types.py` (away from `engine.py`) prevents import cycles and keeps modules that only need types lightweight.

### SJ7: Parse configuration and frontmatter
**Owner:** `_frontmatter.py` (frontmatter parsing), `cli.py:_load_config()` (TOML loading)
**Serves:** J5, J1
**Assessment:** Frontmatter parsing is solid — `_frontmatter.py` is 107 lines with `_FIELD_COERCIONS` (line 31) for extensible type handling.

**Issue: No config validation.** `cli.py:133-140` — `_load_config()` returns a raw `dict` from `tomllib.load()`. The `run()` command accesses keys like `config["agent"]`, `agent["command"]` with no validation. A typo in `ralph.toml` (e.g., `comandd = "claude"`) produces a raw Python `KeyError` traceback with no context about what's missing or where. Validated as F45.

**Issue: Config schema is undocumented and non-extensible.** `ralph.toml` has only 3 fields (`command`, `args`, `ralph`) under `[agent]`. CLI-only settings (`timeout`, `delay`, `log_dir`, `stop_on_error`) have no config-file equivalent, forcing users to retype them every invocation. Validated as F42 — no config→CLI bridging.

### SJ8: Log agent output
**Owner:** `_agent.py:_write_log()` (line 39)
**Serves:** J6
**Assessment:** Simple — writes timestamped log files with combined stdout+stderr. Log naming is `{iteration:03d}_{timestamp}.log` (line 47).

**Issue: Logs capture output but not input.** Log files contain the agent's stdout/stderr but NOT the assembled prompt that was sent to the agent. When debugging "why did the agent do X?", the user can't see what it was told. Validated as F31.

**Issue: Log filenames don't indicate pass/fail.** Validated as F49 — users can't scan the log directory to find failures.

### SJ9: Multi-run management
**Owner:** `manager.py`
**Serves:** J4, J8 (team use), J1 (power users)
**Assessment:** Clean. `RunManager` (line 38) is a thread-safe registry wrapping run threads. `ManagedRun` (line 18) bundles config + state + emitter + thread. Uses `FanoutEmitter` for multi-listener broadcast.

**No significant issues.** This module is building-block quality — used by external orchestration layers (UI/dashboard). It doesn't try to do too much.

### SJ10: Scaffold project structure
**Owner:** `_templates.py` (template strings), `cli.py:init()` (line 143), `cli.py:_scaffold_primitive()` (line 170)
**Serves:** J5, J1 (setup)
**Assessment:** Functional but minimal.

**Issue: `init` creates a generic, minimally useful starting point.** The `ROOT_RALPH_TEMPLATE` (`_templates.py:61-74`) is a skeleton prompt. No checks are created by default — the core differentiator (self-healing feedback loop) is absent until the user manually discovers `ralph new check`. Validated as F1, F2.

**Issue: `detect_project()` result is unused.** `detector.py:11-27` detects Python/Node/Rust/Go but only prints the result. It doesn't create project-appropriate checks, customize the template, or tailor ralph.toml. Validated as F3.

### SJ11: Format and truncate output
**Owner:** `_output.py`
**Serves:** J2, J6
**Assessment:** Simple (51 lines) with three utility functions: `collect_output`, `truncate_output`, `format_duration`.

**Issue: Truncation is silent.** `truncate_output()` (line 28) appends `... (truncated)` to the text itself, but no metadata (original length, amount truncated) is communicated back to callers or through the event system. The CLI never indicates that truncation occurred. Validated as F11.

## Architecture Audit

### Module Dependency Graph

```
cli.py ──→ engine.py ──→ checks.py ──→ _discovery.py ──→ _frontmatter.py
  │            │          contexts.py ──→ _runner.py
  │            │          instructions.py ──→ resolver.py
  │            │          _agent.py ──→ _output.py
  │            │          _events.py
  │            │          _run_types.py
  │            │
  │            └──→ _output.py
  │
  ├──→ checks.py, contexts.py, instructions.py, ralphs.py (for status command)
  ├──→ _console_emitter.py ──→ _events.py, _output.py
  ├──→ _templates.py
  ├──→ detector.py
  └──→ _frontmatter.py

manager.py ──→ engine.py, _events.py, _run_types.py
```

**No circular dependencies.** Dependency direction is clean: CLI → engine → primitives → shared infrastructure. The `_` prefix convention clearly marks internal modules.

### Responsibility Map

| Module | Lines | System Jobs | Concerns |
|--------|-------|-------------|----------|
| `cli.py` | 349 | SJ7 (partial), SJ10 | CLI commands, config loading, banner, prompt resolution, status display, scaffolding |
| `engine.py` | 407 | SJ3, SJ1 (partial) | Loop orchestration, primitive discovery wiring, iteration execution |
| `checks.py` | 186 | SJ1, SJ4 (partial) | Check discovery, execution, failure formatting |
| `contexts.py` | 156 | SJ1, SJ2 (partial), SJ4 (partial) | Context discovery, execution, placeholder resolution |
| `instructions.py` | 81 | SJ1, SJ2 (partial) | Instruction discovery, placeholder resolution |
| `ralphs.py` | 124 | SJ1 | Ralph discovery, prompt source resolution |
| `resolver.py` | 57 | SJ2 | Placeholder resolution (shared) |
| `_agent.py` | 218 | SJ4, SJ8 | Agent subprocess execution, log writing |
| `_runner.py` | 69 | SJ4 | Check/context subprocess execution |
| `_events.py` | 186 | SJ5 | Event types, emitter protocol, queue/fanout implementations |
| `_console_emitter.py` | 153 | SJ5 | CLI terminal rendering of events |
| `_run_types.py` | 145 | SJ6 | RunConfig, RunState, RunStatus |
| `_frontmatter.py` | 107 | SJ7 | YAML frontmatter parsing, marker constants |
| `_discovery.py` | 137 | SJ1 | Primitive protocol, directory scanning, merge_by_name |
| `_output.py` | 51 | SJ11 | Output combination, truncation, duration formatting |
| `_templates.py` | 75 | SJ10 | Scaffold templates |
| `detector.py` | 28 | SJ10 (unused) | Project type detection |
| `manager.py` | 109 | SJ9 | Multi-run orchestration |
| `__init__.py` | 73 | — | Public API surface, version |

**Total:** ~2,896 lines across 18 modules. This is a well-sized codebase — small enough to understand fully, large enough to have real architecture.

## Job–Architecture Alignment

### Well-Aligned

| User Job | System Job | Architecture Quality |
|----------|------------|---------------------|
| J1 (Ship features) | SJ3 (Orchestrate) | Excellent — `engine.py` is clean, focused, well-decomposed |
| J2 (Guardrails) | SJ1 (Discover) + SJ4 (Execute) | Good — checks run after every iteration, failures feed back into prompt |
| J5 (Reliable workflow) | SJ7 (Parse config) + SJ1 (Discover) | Good — primitives, config, and discovery are structured and predictable |
| J3 (Stop babysitting) | SJ3 (Orchestrate) + SJ6 (Manage state) | Good — pause/resume/stop via RunState; reload mechanism exists |

### Misaligned

| User Job | Gap | Root Cause |
|----------|-----|-----------|
| J6 (Feel in control) | Events emitted but not rendered (F12, F22, F31) | ConsoleEmitter underuses the event system |
| J6 (Feel in control) | Prompt not logged (F31) | `_agent.py:_write_log()` captures output but not input |
| J6 (Feel in control) | Truncation is silent (F11) | `_output.py` has no feedback channel |
| J2 (Guardrails) | No checks created by default (F2) | `init` scaffolding doesn't use `detect_project()` result |
| J5 (Reliable workflow) | Config not validated (F45) | No validation layer between TOML loading and usage |
| J5 (Reliable workflow) | CLI-only settings can't be defaulted in config (F42) | `ralph.toml` schema is too narrow |
| J9 (Cost control) | No cost tracking or spend limits | No system job exists for cost management |
| J1 (Ship features) | Non-Claude agents get degraded experience (F32, F43) | Agent mode detection hardcoded to `"claude"` binary name |

## Opportunities

Ranked by: (impact on job fulfillment) × (frequency of the job) / (effort + risk)

### O1: Config Validation Layer [HIGH PRIORITY]
**What:** Add a validation function between `_load_config()` and config usage that checks required keys exist, validates types, and produces actionable error messages.
**Job:** SJ7 → J5 (reliable workflow)
**Why:** A typo in `ralph.toml` produces a raw `KeyError` traceback (`cli.py:294-297`). Every new user will encounter this. The fix is 20-30 lines — validate `[agent]` section exists, `command` is a string, `args` is a list, `ralph` is a string.
**Effort:** S (one function, ~30 lines)
**Risk:** Very low — additive change, no behavior modification

### O2: Render Existing Events in ConsoleEmitter [HIGH PRIORITY]
**What:** Add handlers in `ConsoleEmitter` for `CHECK_PASSED`/`CHECK_FAILED` (live per-check progress), `PROMPT_ASSEMBLED` (prompt length each iteration), `CONTEXTS_RESOLVED` (context count). The events already exist and are already emitted — the rendering is the only missing piece.
**Job:** SJ5 → J6 (feel in control)
**Why:** The engine emits 15 event types but the CLI renders only 8. Per-check progress (`engine.py:251-254`), prompt assembly info (`engine.py:298`), and context resolution (`engine.py:292`) are all emitted but silently discarded. Users see nothing during the check phase until all checks complete (F22). This is low-hanging fruit — the infrastructure is done.
**Effort:** S (add 3-4 handler methods to `_console_emitter.py`, ~20 lines each)
**Risk:** Very low — additive, no change to event emission or engine logic

### O3: Project-Aware Init with Default Checks [HIGH PRIORITY]
**What:** Make `ralph init` use `detect_project()` to create 1-2 project-appropriate checks automatically (e.g., `pytest` for Python, `npm test` for Node). Create the `.ralphify/checks/` directory during init.
**Job:** SJ10 → J2 (guardrails), J1 (ship features)
**Why:** Today, `ralph init` creates a loop with zero quality gates. The core differentiator (self-healing feedback loop) is absent until the user manually discovers `ralph new check`. `detector.py` already identifies project types but does nothing with the result (F2, F3). A Python project should get a `pytest` check out of the box.
**Effort:** S-M (extend `init` command, add check templates per project type)
**Risk:** Low — the check can be created as `enabled: true` with a reasonable default; users can disable or modify

### O4: Extend ralph.toml Schema for CLI Defaults [MEDIUM PRIORITY]
**What:** Allow `ralph.toml` to specify defaults for `timeout`, `delay`, `log_dir`, `stop_on_error`, `max_iterations` under a `[run]` section. CLI flags override these values.
**Job:** SJ7 → J5 (reliable workflow), J6 (feel in control)
**Why:** Users who always want `--log-dir logs --timeout 300` must type it every invocation (F42). The config file has only 3 fields. Adding a `[run]` section bridges the gap between "project defaults" and "per-invocation overrides."
**Effort:** S-M (add TOML section parsing, merge with CLI flags in `cli.py:run()`)
**Risk:** Low — additive schema extension; existing configs remain valid

### O5: Add Truncation Metadata to Events [MEDIUM PRIORITY]
**What:** Have `truncate_output()` return both the truncated text and metadata (original length, truncated bool). Propagate this through check result events so `ConsoleEmitter` can warn: "Check output truncated (12,847 → 5,000 chars)".
**Job:** SJ11 + SJ5 → J6 (feel in control), J2 (guardrails)
**Why:** Check failure output is silently truncated to 5,000 chars (F11). Users never know critical failure information was cut off. Agents see `... (truncated)` but don't know the magnitude. A small metadata addition makes truncation visible.
**Effort:** S (modify `truncate_output` signature, update callers in `checks.py` and `contexts.py`)
**Risk:** Very low — backwards-compatible if metadata is optional

### O6: Log Prompt Input Alongside Agent Output [MEDIUM PRIORITY]
**What:** Write the assembled prompt to the log file before agent output, or to a separate `{iteration}_prompt.md` file. This makes each log file a complete record of input + output.
**Job:** SJ8 → J6 (feel in control)
**Why:** Currently log files contain only agent stdout/stderr (`_agent.py:39-49`), not the prompt that was sent. When debugging "why did the agent do X?", users can't see what it was told (F31). The prompt is already available in `_run_agent_phase` — it just needs to be passed to the log writer.
**Effort:** S (pass prompt to `_write_log`, prepend to log file)
**Risk:** Very low — additive change to log content

### O7: Make Agent Execution Mode Configurable [MEDIUM PRIORITY]
**What:** Replace `_is_claude_command()` hardcheck with a configuration option (e.g., `streaming = true` in `ralph.toml` under `[agent]`). Auto-detect Claude as a default, but allow opt-in/opt-out.
**Job:** SJ4 → J1 (ship features), J6 (feel in control)
**Why:** `_agent.py:52-57` hardcodes `"claude"` as the only agent that gets streaming mode. All other agents get the inferior blocking path — no output during execution, wall-of-text dump after completion (F32, F43). Users of custom agents or wrappers around Claude Code (e.g., aliased or wrapped commands) get the wrong mode with no override.
**Effort:** S (add config field, replace hardcoded check)
**Risk:** Low — streaming mode already works; making it configurable just expands access

### O8: Context Timeout Awareness [LOW PRIORITY]
**What:** When a context times out, emit a warning event and/or mark the context result distinctly so `ConsoleEmitter` can show "Context 'npm-test' timed out after 30s (output may be incomplete)".
**Job:** SJ5 → J6 (feel in control), J2 (guardrails)
**Why:** Context timeouts are silent — the partial output is injected into the prompt with no indication it was cut short by a timeout (F48). `ContextResult.timed_out` exists (line 50) but is never checked during resolution.
**Effort:** S (add event emission in engine, add handler in ConsoleEmitter)
**Risk:** Very low

### O9: Reduce Primitive Discovery Boilerplate [LOW PRIORITY]
**What:** Create a generic discovery factory in `_discovery.py` that takes a constructor function and returns the discover/discover_local/discover_enabled trio. Each primitive module would call this factory instead of repeating the pattern.
**Job:** SJ1 → J5 (reliable workflow, indirectly — easier to add new primitives)
**Why:** The discover/discover_local/discover_enabled chain is structurally identical across `checks.py:94-118`, `contexts.py:66-91`, `instructions.py:41-65`. Adding a new primitive type requires copying ~30 lines. A factory would reduce this to ~3 lines per module.
**Effort:** M (refactor 4 modules, update tests)
**Risk:** Medium — the current explicit pattern is easy to read and debug; abstraction adds indirection. Only valuable if new primitive types are planned.
**Recommendation:** Only pursue if a 5th primitive type is on the roadmap. Three instances of a pattern is acceptable; five is not.

### O10: Parallel Check Execution [LOW PRIORITY]
**What:** Run checks concurrently using `concurrent.futures.ThreadPoolExecutor` instead of sequentially in `run_all_checks()` (`checks.py:143-154`).
**Job:** SJ4 → J1 (ship features — faster iterations), J2 (guardrails)
**Why:** Checks run sequentially. If a user has 5 checks and the slowest takes 60s, the check phase takes sum(all check durations) rather than max. For users with multiple slow checks (test suite + type checker + linter), this could cut the check phase significantly.
**Effort:** S-M (replace list comprehension with thread pool)
**Risk:** Medium — check ordering might matter for some use cases; need to ensure thread safety in output collection. Would need an opt-in flag or config option.

## Anti-Patterns Spotted

### 1. Dead Code: `detector.py`
`detector.py` is imported and called during `ralph init` (`cli.py:151`) but its return value is only printed — never used to influence behavior. This is either:
- An incomplete feature (intended to create project-specific checks/templates)
- Premature abstraction (built for a future need)

**Recommendation:** Either wire it into `init` to create project-appropriate checks (O3) or remove it. Dead code that looks intentional is worse than no code — it signals "someone thought about this" without delivering value.

### 2. Emit-But-Don't-Render
The engine emits 15 event types; the CLI renders 8. This means every iteration:
- `CONTEXTS_RESOLVED` is emitted and discarded
- `PROMPT_ASSEMBLED` is emitted and discarded
- `CHECK_PASSED` / `CHECK_FAILED` are emitted and discarded (individually)

The cost is minimal (Python function calls), but it creates a misleading architecture: a reader sees events being emitted and assumes they're being consumed somewhere. If these events are only meaningful for the web UI (which uses `QueueEmitter`), that should be documented. If they're valuable for CLI users too, render them (O2).

### 3. Silent Degradation for Non-Claude Agents
The codebase assumes Claude Code as the primary agent in three places:
- `_agent.py:52-57` — streaming mode only for `"claude"` binary
- `_templates.py:6` — default args include `--dangerously-skip-permissions` (Claude Code flag)
- `_agent.py:121-124` — `result_text` extraction from Claude's JSON stream

This creates a two-tier experience: Claude Code users get streaming output, live activity events, and result summaries. All other agents get blocking execution, no live output, and no result text. The fallback is silent — users don't know they're getting the inferior path.

### 4. Config→CLI Gap
`ralph.toml` has 3 fields. `ralph run` has 8 flags. The 5 missing config fields (`timeout`, `delay`, `log_dir`, `stop_on_error`, `max_iterations`) can only be set per-invocation. Users who want consistent behavior must type the same flags every time. This violates J5 (reliable, repeatable workflow) — if the config file exists to avoid repetition, it should cover the common options.

## Open Questions

1. **Is a 5th primitive type planned?** If yes, O9 (reduce discovery boilerplate) becomes higher priority. If no, the current explicit pattern is fine.

2. **Should `ralph init` be opinionated or minimal?** O3 proposes project-aware init with default checks. This makes the tool more opinionated (potentially alienating the Skeptical Senior persona) but dramatically improves time-to-first-useful-run (critical for Solo Founder and Vibe Coder personas). The right answer depends on which persona is the primary target.

3. **Is the web dashboard (`ralph ui`) still actively developed?** Several event types (AGENT_ACTIVITY, CONTEXTS_RESOLVED, PROMPT_ASSEMBLED) may be consumed by the UI layer even though the CLI ignores them. If the UI is active, the emit-but-don't-render pattern is justified for those events. If the UI is paused/abandoned, those events are dead code.

4. **Should non-Claude agents get first-class streaming support?** O7 proposes making streaming mode configurable. But streaming requires the agent to emit parseable output on stdout. If most non-Claude agents don't support this, the config option would be a trap (user enables streaming, agent doesn't support it, broken output). A middle ground: tee-based output capture that shows output live without requiring structured streaming.

5. **What's the relationship between `ralphify` and `alphify`?** Memory reference mentions alphify as a separate product for non-technical users. If alphify will wrap ralphify's library API, the public surface in `__init__.py` needs to be stable and well-documented. O4 (config schema extension) and O1 (config validation) become more important — library consumers need reliable, validated config handling.
