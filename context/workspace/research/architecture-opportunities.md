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

### Feedback Loop Data Flow (End-to-End Trace)

The self-healing feedback loop is ralphify's core differentiator. This trace documents every transformation data undergoes from check execution to the agent receiving feedback, and identifies where signal is lost.

#### Step-by-step data path

```
Iteration N: Check Phase
┌─────────────────────────────────────────────────────────────────────┐
│ 1. engine.py:308-311   _run_checks_phase() called                  │
│ 2. checks.py:143-154   run_all_checks() → run_check() per check    │
│ 3. _runner.py:49-56    subprocess.run(capture_output=True)          │
│ 4. _output.py:12-25    collect_output() → stdout+stderr merged      │
│    ⚠ SL1: stdout/stderr concatenated with no separator             │
│ 5. checks.py:134-140   RunResult → CheckResult(output, passed, ..) │
│ 6. engine.py:264       format_check_failures(check_results)        │
│ 7. checks.py:157-185   Filter failures, format as markdown:        │
│    - "## Check Failures" header                                    │
│    - Per failure: ### name, exit code, truncated output, instruction│
│ 8. _output.py:28-32    truncate_output(output, max_len=5000)       │
│    ⚠ SL2: Truncates to first 5000 chars (head, not tail)           │
│    ⚠ SL3: Test summaries are at the END — most useful info cut off │
└─────────────────────────────────────────────────────────────────────┘

Between Iterations
┌─────────────────────────────────────────────────────────────────────┐
│ 9. engine.py:368-370   check_failures_text returned from           │
│                        _run_iteration(), carried to next iteration  │
│    ⚠ SL4: Previous iteration's failures completely replaced        │
│           — no diff, no history of what improved/regressed         │
└─────────────────────────────────────────────────────────────────────┘

Iteration N+1: Prompt Assembly
┌─────────────────────────────────────────────────────────────────────┐
│ 10. engine.py:295-298  _assemble_prompt(config, primitives,        │
│                        context_results, check_failures_text)       │
│ 11. engine.py:159-163  Read base prompt (file or -p text)          │
│ 12. engine.py:164-165  Resolve contexts ({{ contexts.x }})         │
│     ⚠ SL5: Context failures unchecked — resolve_contexts() at     │
│            contexts.py:129 never inspects ContextResult.success    │
│ 13. engine.py:166-167  Resolve instructions                        │
│ 14. engine.py:168-169  Append: prompt + "\n\n" + failures_text     │
│     ⚠ SL6: All-passed = empty string = zero signal to agent       │
└─────────────────────────────────────────────────────────────────────┘

Agent Receives Prompt
┌─────────────────────────────────────────────────────────────────────┐
│ 15. _agent.py:103      (streaming) proc.stdin.write(prompt)        │
│     _agent.py:170-171  (blocking)  subprocess.run(input=prompt)    │
│     ⚠ SL7: Prompt not logged — _write_log() captures agent output │
│            but not the input that was sent (already in O6)         │
└─────────────────────────────────────────────────────────────────────┘
```

#### Signal loss analysis

**SL1: stdout/stderr conflation** (`_output.py:12-25`)
`collect_output()` concatenates stdout and stderr into one string with no separator or labels. If a test runner writes progress to stderr and results to stdout, they're interleaved. The agent can't distinguish between a compiler warning (stderr) and a test failure message (stdout). Impact: **medium** — signal is present but muddled.

**SL2+SL3: Head-biased truncation** (`_output.py:28-32`)
`truncate_output()` keeps `text[:5000]` — the **first** 5000 characters. But most test runners (pytest, jest, go test, cargo test) output individual test results in order, then print the **failure summary at the end**. This means truncation systematically cuts off the most useful information:
- **pytest:** "FAILURES" section with tracebacks, then "short test summary info" — both at the end
- **jest:** summary of failed tests, expected vs. received — at the end
- **go test:** "FAIL" lines with the failing test name — at the end
- **cargo test:** "failures:" section listing failed tests — at the end

The agent receives "PASSED test_a... PASSED test_b... PASSED test_c... (truncated)" instead of the actual failure details. **This is the single biggest signal loss point in the feedback loop.** The architecture inverts the information value: the highest-value content (failure details) is truncated while the lowest-value content (passing tests listed first) is preserved.

**SL4: No check history between iterations** (`engine.py:342,368`)
`check_failures_text` is a simple string variable that is completely overwritten each iteration. The agent receives the **current** failures but has no way to know:
- Which checks improved (failed → passed) — its fixes worked
- Which checks regressed (passed → failed) — its changes broke something
- Which failures persist (same failure across iterations) — the fix isn't working

On iteration 5, if the agent fixed 3 out of 5 failing checks but broke 1 new one, it sees "3 failures" with no indication that 3 others were fixed. It can't measure its own progress. Impact: **medium-high** — agents that can't track progress tend to thrash.

**SL5: Context failures silently enter prompt** (`contexts.py:94-116,129-155`)
When a context command fails (non-zero exit or timeout), `ContextResult.success` is set to `False` and `ContextResult.timed_out` may be `True`. But `resolve_contexts()` (line 129) never checks these fields. It processes every result identically — whether the context ran successfully or crashed. A failing `git log` context injects error output (or empty output) into the prompt with no warning. The engine emits `CONTEXTS_RESOLVED` with a count but no failure indicator. Impact: **medium** — the agent operates on corrupt or missing data without knowing it.

**SL6: Zero positive feedback** (`checks.py:162-164`, `engine.py:168-169`)
When all checks pass, `format_check_failures()` returns `""` and `_assemble_prompt()` skips appending. The agent receives an identical prompt to iteration 1 — no signal that its work in the previous iteration passed all quality gates. The agent can't distinguish between "first iteration, no checks have run yet" and "iteration 5, all checks pass, your work is good." Impact: **low-medium** — most agents infer success from the absence of failure feedback, but an explicit "all checks passed" signal would reduce unnecessary re-work.

### Named Ralph Resolution Trace

The `ralph run <name>` path is a key workflow that spans CLI → ralphs → discovery → engine. This traces the full resolution chain.

```
ralph run docs
┌─────────────────────────────────────────────────────────────────────┐
│ 1. cli.py:283         prompt_name="docs" (from positional arg)      │
│ 2. cli.py:315         resolve_ralph_source(prompt_name="docs", ...) │
│    → ralphs.py:108    prompt_name is truthy                         │
│    → ralphs.py:109    resolve_ralph_name("docs")                    │
│      → ralphs.py:68   discover_ralphs(root)                         │
│        → ralphs.py:54 discover_primitives(root, "ralphs", RALPH.md) │
│          → _discovery.py:91 _scan_dir(.ralphify/ralphs/, "RALPH.md")│
│      → ralphs.py:69-71 linear scan for name == "docs"               │
│      → returns Ralph(name="docs", path=.ralphify/ralphs/docs, ...)  │
│    → ralphs.py:110    return (".ralphify/ralphs/docs/RALPH.md",     │
│                               "docs")                               │
│ 3. cli.py:324         Path(prompt_file_path).exists() — validated   │
│ 4. cli.py:331-342     RunConfig(prompt_file=path, prompt_name=name) │
└─────────────────────────────────────────────────────────────────────┘

engine.py:run_loop()
┌─────────────────────────────────────────────────────────────────────┐
│ 5. engine.py:51-52    _resolve_prompt_dir(config):                   │
│    config.prompt_name="docs" and not config.prompt_text → True       │
│    prompt_dir = Path(".ralphify/ralphs/docs/RALPH.md").parent        │
│              = Path(".ralphify/ralphs/docs")                         │
│ 6. engine.py:72-75    _discover_enabled_primitives(root, prompt_dir):│
│    → discover_enabled_checks(root, prompt_dir=".ralphify/ralphs/docs")│
│      → discover_checks(root) — global checks                        │
│      → discover_checks_local(".ralphify/ralphs/docs")                │
│        → _scan_dir(".ralphify/ralphs/docs/checks/", "CHECK.md")     │
│      → merge_by_name(global, local) — local wins on name collision   │
│      → filter enabled                                                │
│    (same for contexts and instructions)                              │
│ 7. engine.py:162-163  _assemble_prompt():                            │
│    Path(".ralphify/ralphs/docs/RALPH.md").read_text()                │
│    → parse_frontmatter(raw) → prompt body                            │
│    → resolve_contexts, resolve_instructions, append failures         │
└─────────────────────────────────────────────────────────────────────┘
```

**Assessment:** Well-designed resolution chain. Key architectural properties:
- Named ralphs get their own prompt directory, enabling scoped primitives (checks/contexts/instructions specific to a task)
- `merge_by_name` allows local overrides of global primitives
- The `_resolve_prompt_dir` function cleanly derives the prompt directory from the prompt file path

**Issue: Ralph name fallback silently converts to file path.** `ralphs.py:116-121` — when `ralph.toml` contains `ralph = "myralph"` and `"myralph"` is not found as a named ralph, `resolve_ralph_source` silently falls back to treating `"myralph"` as a file path. This means the error the user sees is "Prompt file 'myralph' not found" (`cli.py:325`) rather than "Ralph 'myralph' not found." The user has no indication that name resolution was attempted and failed — the error looks like a missing file, not a missing ralph. This is confusing because the user intended a name, not a path.

**Issue: Ralph discovery scans on every resolution.** `resolve_ralph_name()` (`ralphs.py:68`) calls `discover_ralphs(root)` which scans the entire `.ralphify/ralphs/` directory for each lookup. During `ralph run`, this happens once at startup. But `resolve_ralph_source()` at `ralphs.py:117-118` can call `resolve_ralph_name()` even for the TOML fallback path, meaning a single invocation may scan the ralphs directory twice (once for name resolution, once if it falls back). Not a performance issue at current scale, but the pattern would become relevant if ralph counts grow.

### Error Propagation Audit

This section traces error handling across every module boundary in the codebase. The finding: **the codebase has no error boundary strategy — errors either crash the entire operation or are silently swallowed, with almost nothing in between.**

#### Layer 1: Config Loading (`cli.py:133-140`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| File missing | Clean exit with message | `cli.py:136-138` — **good** |
| Invalid TOML syntax | Unhandled `tomllib.TOMLDecodeError` → raw traceback | `cli.py:139-140` |
| Missing `[agent]` section | Unhandled `KeyError` → raw traceback | `cli.py:301` |
| Missing `command` key | Unhandled `KeyError` → raw traceback | `cli.py:302` |
| Extra/unknown keys | Silently ignored | No validation layer |

**Pattern:** Only the file-missing case has a user-friendly error. All other config errors produce raw Python tracebacks. (Covered by O1.)

#### Layer 2: Frontmatter Parsing (`_frontmatter.py`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| No frontmatter delimiters | Returns `({}, full_text)` — body is the entire file | `_frontmatter.py:85-86` — **good, intentional** |
| Malformed `key: value` lines | Silently skipped | `_frontmatter.py:42-45` — **good, lenient** |
| `timeout: abc` (non-integer) | **Unhandled `ValueError`** from `int("abc")` → crashes discovery | `_frontmatter.py:50` via `_FIELD_COERCIONS` |
| `enabled: maybe` (non-boolean) | Coerced to `False` (not in `"true", "yes", "1"`) | `_frontmatter.py:33` — **surprising but safe** |

**Pattern:** Frontmatter parsing is lenient for missing/malformed structure but crashes hard on type coercion failures. A single primitive with `timeout: slow` crashes the entire discovery phase for that primitive type. The `_FIELD_COERCIONS` dict at line 31 has no try/except — `int()` and the `enabled` lambda are called directly.

#### Layer 3: Primitive Discovery (`_discovery.py`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| `.ralphify/` directory missing | Silently yields nothing | `_discovery.py:66-67` — **good** |
| Marker file read fails (permissions) | **Unhandled exception** → crashes all discovery for that kind | `_discovery.py:77` |
| `run.*` script directory iteration fails | **Unhandled exception** → crashes discovery | `_discovery.py:52` |

**Pattern:** Discovery handles the normal "directory doesn't exist" case well, but has no error boundaries around individual primitive reads. One corrupted `CHECK.md` file (bad encoding, permission denied) crashes discovery for ALL checks, not just the broken one.

#### Layer 4: Check/Context Subprocess Execution (`_runner.py`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| Command timeout | Handled — returns `RunResult(success=False, timed_out=True)` | `_runner.py:62-68` — **good** |
| Command not found (FileNotFoundError) | **Unhandled** → crashes the entire check/context phase | `_runner.py:50` |
| Script not executable (PermissionError) | **Unhandled** → crashes the entire check/context phase | `_runner.py:50` |
| Script not found (FileNotFoundError) | **Unhandled** → crashes the entire check/context phase | `_runner.py:44-45` |
| Invalid command string (ValueError from shlex) | **Unhandled** → crashes the entire check/context phase | `_runner.py:47` |

**Impact amplified by sequential execution:** Checks run via `[run_check(check, project_root) for check in checks]` (`checks.py:154`). Contexts use the same pattern (`contexts.py:126`). A single `FileNotFoundError` or `PermissionError` in any check/context aborts the entire list comprehension — remaining checks/contexts never run. The agent receives no feedback at all, rather than feedback from the checks that did succeed.

#### Layer 5: Agent Execution (`_agent.py`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| Command not found | Re-raised as `FileNotFoundError` with helpful message | `engine.py:194-198` — **good** |
| Timeout (streaming) | Handled — process killed, returns `returncode=None` | `_agent.py:108-112` — **good** |
| Timeout (blocking) | Handled — returns `returncode=None` | `_agent.py:184-186` — **good** |
| `BrokenPipeError` on stdin write (streaming) | **Unhandled** → crashes iteration | `_agent.py:103` |
| JSON decode error (streaming) | Handled — line skipped | `_agent.py:119-120` — **good** |

**Pattern:** Agent execution is the best-handled layer. Most error cases are covered. The `BrokenPipeError` case is the main gap: if the agent process exits immediately after starting (e.g., invalid args), `proc.stdin.write(prompt)` raises `BrokenPipeError`. The `try/finally` at line 132-135 cleans up the process, but the exception propagates to `_run_iteration`, which is caught by the generic `except Exception` in `run_loop` — terminating the entire run.

#### Layer 6: Engine Loop (`engine.py:356-390`)

| Error | What happens | Code reference |
|-------|-------------|----------------|
| Prompt file missing/unreadable | **Caught by generic `except Exception`** → sets status FAILED, stops run | `engine.py:383-390` |
| Discovery crash (from Layer 3) | **Caught by generic `except Exception`** → sets status FAILED, stops run | `engine.py:383-390` |
| Check/context crash (from Layer 4) | **Caught by generic `except Exception`** → sets status FAILED, stops run | `engine.py:383-390` |
| `KeyboardInterrupt` | Handled — sets status STOPPED | `engine.py:381-382` — **good** |

**Pattern:** The generic `except Exception` at `engine.py:383` is the only error boundary in the system. It catches everything and terminates the run. This means any unhandled error in layers 2-5 escalates to "run crashed" with a traceback. There's no middle ground — no "skip this iteration and continue" or "skip this check and report the rest."

#### Summary: The Error Boundary Gap

```
Error severity:     FATAL ◄──────────────────────────► SILENT
                      │                                    │
Where errors land:    │    (nothing in between)             │
                      │                                    │
Config errors:    ────┤                                    │
Discovery crash:  ────┤                                    │
Subprocess crash: ────┤                                    │
                      │                                    │
Context failures: ────┼────────────────────────────────────┤
Missing placeholders: ┼────────────────────────────────────┤
Truncation:       ────┼────────────────────────────────────┤
                      │                                    │
                   run_loop()                        resolve_contexts()
                   except Exception                  (no check at all)
```

The codebase has exactly two error handling strategies:
1. **Crash the run** — any unhandled exception reaches `run_loop`'s `except Exception` and terminates everything
2. **Swallow silently** — context failures, missing placeholders, and truncation are invisible

What's missing is the middle tier: **graceful degradation**. Examples:
- A check script with bad permissions → skip that check, report the error, continue with remaining checks
- A context timeout → mark the context as degraded, warn the user, continue with partial data
- A corrupt frontmatter file → skip that primitive, warn, continue discovering others
- A TOML parse error → specific error message pointing to the syntax problem

This gap directly impacts **J2 (guardrails)** and **J5 (reliable workflow)**. A user who adds a new check with a typo in the command shouldn't have their entire run crash — they should see "Check 'my-check' failed to execute: command 'pytst' not found" alongside normal results from the other checks.

### CLI Prompt Resolution: All Paths to Running the Loop

The `run` command (`cli.py:281-346`) has 4 ways to specify what prompt to use. These paths converge on `RunConfig` but have subtly different semantics and error behavior. This trace maps all paths and identifies where they diverge.

#### Path 1: Inline prompt text (`-p/--prompt`)
```
ralph run -p "Fix the failing test"
┌─────────────────────────────────────────────────────────────────────┐
│ cli.py:306   prompt_text is truthy → skip file resolution entirely  │
│ cli.py:307   prompt_file_path = agent.get("ralph", "RALPH.md")     │
│              ⚠ PR1: prompt_file is set but NEVER READ by engine    │
│              (engine.py:159 checks config.prompt_text first)        │
│ cli.py:308   resolved_prompt_name = None                           │
│ cli.py:331   RunConfig(prompt_text="Fix the failing test",         │
│                        prompt_file=<from toml>, prompt_name=None)  │
│                                                                     │
│ engine.py:51  _resolve_prompt_dir: prompt_name=None → returns None │
│ engine.py:344 prompt_dir=None → only global primitives discovered  │
│ engine.py:159 prompt_text is truthy → prompt = config.prompt_text  │
│              ⚠ PR2: No frontmatter parsing for inline text         │
│              (file-based prompts go through parse_frontmatter)      │
└─────────────────────────────────────────────────────────────────────┘
```

**PR1: Dead `prompt_file` value on the `-p` path.** When `-p` is used, `prompt_file_path` is still set from `ralph.toml` (`cli.py:307`). This value is stored in `RunConfig.prompt_file` but never used — `engine.py:159-160` checks `config.prompt_text` first and skips the file read. The dead value is harmless but misleading: a reader might think the file is a fallback. More importantly, if the TOML file doesn't even have a `ralph` key, `agent.get("ralph", "RALPH.md")` silently defaults — masking a broken config. The `-p` user never discovers their `ralph.toml` is malformed.

**PR2: Inline text skips frontmatter parsing.** When a prompt file is used, `engine.py:162-163` calls `parse_frontmatter(raw)` to strip the `---` block. Inline text bypasses this. If a user copies a `RALPH.md` file's content into `-p "---\ntimeout: 300\n---\nFix the test"`, the frontmatter ends up in the agent prompt verbatim. This is arguably correct (inline text has no frontmatter), but the asymmetry is undocumented.

#### Path 2: Positional ralph name (`ralph run docs`)
```
ralph run docs
┌─────────────────────────────────────────────────────────────────────┐
│ cli.py:283   prompt_name="docs"                                     │
│ cli.py:314   resolve_ralph_source(prompt_name="docs", ...)          │
│  → ralphs.py:108-110  discover_ralphs() → find by name             │
│  → returns (".ralphify/ralphs/docs/RALPH.md", "docs")              │
│ cli.py:324   Path(prompt_file_path).exists() — validated            │
│ cli.py:331   RunConfig(prompt_file=path, prompt_name="docs")       │
│                                                                     │
│ engine.py:51  prompt_name="docs" and not prompt_text → True        │
│ engine.py:52  prompt_dir = Path(prompt_file).parent                │
│              = ".ralphify/ralphs/docs"                              │
│ engine.py:344 prompt_dir set → discovers LOCAL + GLOBAL primitives │
│              ⚠ PR3: This is the ONLY path that gets local prims    │
└─────────────────────────────────────────────────────────────────────┘
```

**PR3: Scoped primitives only activate for named ralphs.** `_resolve_prompt_dir()` (`engine.py:45-53`) returns a `prompt_dir` only when `config.prompt_name` is set AND `config.prompt_text` is not. This means scoped primitives (checks/contexts/instructions inside a ralph directory) only work with `ralph run <name>`. If a user specifies `--prompt-file .ralphify/ralphs/docs/RALPH.md` (Path 3), `prompt_name` is `None`, so `_resolve_prompt_dir()` returns `None`, and local primitives under `.ralphify/ralphs/docs/checks/` are silently ignored. The file is read, but the scoping is lost. A user who manually points to a ralph file instead of using its name gets a degraded experience with no warning.

#### Path 3: Explicit file (`--prompt-file`)
```
ralph run --prompt-file custom/my-prompt.md
┌─────────────────────────────────────────────────────────────────────┐
│ cli.py:286   prompt_file="custom/my-prompt.md"                      │
│ cli.py:314   resolve_ralph_source(prompt_file="custom/my-prompt.md")│
│  → ralphs.py:112-113  prompt_file is truthy → return (path, None)  │
│ cli.py:324   Path(prompt_file_path).exists() — validated            │
│ cli.py:331   RunConfig(prompt_file=path, prompt_name=None)         │
│                                                                     │
│ engine.py:51  prompt_name=None → _resolve_prompt_dir returns None  │
│ engine.py:344 prompt_dir=None → only global primitives             │
│              ⚠ PR3 applies here too                                │
└─────────────────────────────────────────────────────────────────────┘
```

#### Path 4: TOML default (no arguments)
```
ralph run
┌─────────────────────────────────────────────────────────────────────┐
│ cli.py:283   prompt_name=None                                       │
│ cli.py:314   resolve_ralph_source(prompt_name=None, prompt_file=None│
│              toml_ralph="RALPH.md")  [or toml_ralph="docs"]        │
│                                                                     │
│ Case A: toml_ralph="RALPH.md" (has ".")                            │
│  → ralphs.py:116  is_ralph_name("RALPH.md") → False ("." present) │
│  → ralphs.py:123  return ("RALPH.md", None)                       │
│  → RunConfig(prompt_file="RALPH.md", prompt_name=None)             │
│  → engine.py:51  prompt_name=None → no prompt_dir → global only   │
│                                                                     │
│ Case B: toml_ralph="docs" (no "." or "/")                          │
│  → ralphs.py:116  is_ralph_name("docs") → True                    │
│  → ralphs.py:117-119  resolve_ralph_name("docs")                  │
│    → Success: return (".ralphify/ralphs/docs/RALPH.md", "docs")    │
│    → Failure: ValueError caught at ralphs.py:120-121               │
│      ⚠ PR4: falls back to return ("docs", None)                   │
│      → cli.py:324 checks Path("docs").exists() → probably fails   │
│      → Error: "Prompt file 'docs' not found"                       │
│      → User sees FILE error, not NAME error (already in O18)       │
│                                                                     │
│ Case C: toml_ralph="ralphs/custom.md" (has "/")                    │
│  → ralphs.py:116  is_ralph_name("ralphs/custom.md") → False       │
│  → ralphs.py:123  return ("ralphs/custom.md", None)               │
│  → prompt_name=None → no local primitives                          │
│    ⚠ PR3 applies again                                             │
└─────────────────────────────────────────────────────────────────────┘
```

**PR4: `is_ralph_name` heuristic is brittle.** `ralphs.py:88` — `"/" not in value and "." not in value`. This means `ralph = "my.task"` in `ralph.toml` is treated as a file path (because of the `.`), even if the user intended it as a name. Similarly, `ralph = "add-tests"` is treated as a name, but `ralph = "tasks/add-tests"` is treated as a path. The heuristic is correct for the common cases but has no escape hatch. A user can't force name resolution for names that happen to contain `.` or `/`, and can't force file resolution for bare names.

#### Summary: Path Feature Matrix

| Feature | Path 1 (-p) | Path 2 (name) | Path 3 (--file) | Path 4a (toml file) | Path 4b (toml name) |
|---------|-------------|----------------|------------------|---------------------|---------------------|
| Frontmatter parsed | No | Yes | Yes | Yes | Yes |
| Local primitives | No | **Yes** | No | No | **Yes** |
| File existence check | No | Yes | Yes | Yes | Yes |
| Prompt source validated | N/A | At resolution | At cli.py:324 | At cli.py:324 | At resolution |
| Config errors masked | **Yes** (PR1) | No | No | No | Partially (PR4) |

**Architectural insight:** The scoped-primitives feature (local checks/contexts/instructions) only activates on 2 of 5 paths. This is by design (only named ralphs have a meaningful directory to scope to), but the asymmetry is invisible to users. A user who types `--prompt-file .ralphify/ralphs/docs/RALPH.md` might reasonably expect to get the same behavior as `ralph run docs`. The gap between these paths becomes a trap when the user moves from "named ralph that works" to "custom file path for more control" — they silently lose scoped primitives.

### RunState State Machine and Threading Model

The `RunState` class (`_run_types.py:61-144`) manages the lifecycle of a run through both status transitions and control events. This section validates the state machine and probes the threading model for correctness.

#### State Transition Diagram

```
                     ┌──────────┐
                     │ PENDING  │
                     └────┬─────┘
                          │ run_loop() sets status=RUNNING (engine.py:334)
                          ▼
              ┌───────────────────────────┐
              │                           │
         ┌────┤        RUNNING            ├────┐
         │    │                           │    │
         │    └─────┬───────────┬─────────┘    │
         │          │           │              │
    request_pause() │           │ stop_requested│
    (sets PAUSED,   │           │ (engine.py:  │
    clears event)   │           │ 128-129)     │
         │          │           │              │
         ▼          │           │              │
   ┌──────────┐     │           │              │
   │  PAUSED  │     │           │              │
   └────┬─────┘     │           │              │
        │           │           │              │
   request_resume() │           │              │
   (sets RUNNING,   │           │              │
    sets event)     │           │              │
        │           │           │              │
        └───────────┘           │              │
                                │              │
                     ┌──────────┘              │
                     │                         │
                     ▼                         ▼
              ┌──────────┐              ┌──────────┐
              │ STOPPED  │              │ COMPLETED│
              └──────────┘              └──────────┘
                     ▲
                     │ except Exception
                     │ (engine.py:383-384)
              ┌──────────┐
              │  FAILED  │
              └──────────┘
```

#### Validated Transitions

| From | To | Trigger | Code Reference | Correct? |
|------|----|---------|----------------|----------|
| PENDING | RUNNING | `run_loop` starts | `engine.py:334` | **Yes** |
| RUNNING | PAUSED | `request_pause()` | `_run_types.py:111-114` | **Yes** |
| PAUSED | RUNNING | `request_resume()` | `_run_types.py:116-119` | **Yes** |
| RUNNING | STOPPED | `request_stop()` detected | `engine.py:128-129` | **Yes** |
| PAUSED | STOPPED | `request_stop()` while paused | `engine.py:107-108` via `_wait_for_resume` | **Yes** |
| RUNNING | COMPLETED | Loop exits normally | `engine.py:392-393` | **Yes** |
| RUNNING | FAILED | Unhandled exception | `engine.py:383-384` | **Yes** |
| PAUSED | FAILED | Exception during pause handling | Theoretically via `engine.py:383` | **Yes** (covered by outer try/except) |

#### Issue: State inconsistency during `request_pause()` / `request_resume()`

**ST1: `request_pause()` sets `status` directly from any thread.**
`_run_types.py:113` — `self.status = RunStatus.PAUSED` is set by the calling thread (typically the API/UI thread), not by the engine thread. The engine thread may be mid-iteration when `status` changes to PAUSED. Any code that checks `state.status` from the engine thread during an iteration will see PAUSED even though the loop hasn't actually paused yet — it's still executing. The engine only checks for pause at the top of the next iteration (`_handle_loop_transitions`, `engine.py:131`).

In practice, this is benign: the engine thread doesn't check `state.status` during an iteration — it only reads the `_pause_event` flag at iteration boundaries. But any future code (or external observer like a dashboard) that reads `state.status` during an iteration will see a misleading PAUSED status while the agent is still running.

**ST2: `request_resume()` sets `status = RUNNING` before `_pause_event.set()`.**
`_run_types.py:117-119` — `status` transitions to RUNNING before the event is signaled. The engine thread is blocked in `_wait_for_resume` (`engine.py:104`) waiting on `_pause_event.wait()`. There's a brief window where `status` is RUNNING but the engine is still blocked. This is cosmetic — the engine unblocks on the next `wait` cycle (250ms timeout) — but a dashboard polling `state.status` would show RUNNING before the engine has actually resumed.

**ST3: No transition validation.** `request_stop()`, `request_pause()`, and `request_resume()` can be called in any state. Calling `request_resume()` on a RUNNING (non-paused) run silently does nothing harmful (it sets `_pause_event`, which is already set). Calling `request_pause()` on a COMPLETED run sets `status = PAUSED` — a logically invalid state. There are no guards, and the `RunStatus` enum doesn't enforce a transition table.

**Impact assessment:** ST1-ST3 are all **low severity**. The engine thread is the sole writer of counters and the sole consumer of control events. The control methods are only written by API threads. Under CPython's GIL, attribute writes are atomic. The status inconsistencies are cosmetic (250ms window at most) and only visible to external observers. However, if the codebase grows to include status-dependent behavior (e.g., "don't start a new run if one is RUNNING"), ST3 becomes a real bug.

#### Threading Boundary Analysis

```
Engine Thread (run_loop)         │  API/UI Thread (RunManager)
                                 │
Reads:                           │  Reads:
  state._stop_requested          │    state.status
  state._pause_event (wait)      │    state.iteration, completed, failed
  state._reload_requested        │    state.total
                                 │
Writes:                          │  Writes:
  state.status (Running/         │    state._stop_requested (via request_stop)
    Completed/Failed/Stopped)    │    state._pause_event (via request_pause/resume)
  state.iteration                │    state.status (via request_pause/resume)  ⚠
  state.completed, failed,       │    state._reload_requested (via request_reload)
    timed_out                    │
  state.started_at               │
```

**Conflict point:** `state.status` is written by both threads. The engine sets it to RUNNING/COMPLETED/FAILED/STOPPED; the API sets it to PAUSED/RUNNING. Under CPython's GIL, individual attribute writes are atomic, so this is safe — there's no torn read. But the lack of a single writer for status means ordering isn't guaranteed. If the API calls `request_pause()` (sets PAUSED) at the exact moment the engine finishes the loop and sets COMPLETED, the final status depends on timing. In practice, the engine's status write in the `finally` block at `engine.py:392-393` happens after the loop exits, and `request_pause()` is a no-op at that point. But the pattern is fragile.

**Recommendation:** If state machine correctness matters for the UI layer (dashboard showing accurate run status), consider making the engine the sole writer of `status` via a `_pause_requested` flag pattern (same as `_stop_requested`), where the engine transitions to PAUSED itself at the iteration boundary.

### Public API Surface Analysis (`__init__.py`)

`__init__.py` (lines 1-73) exports 15 symbols. This section evaluates whether the public surface forms a coherent library API, particularly for the alphify product that wraps ralphify.

#### Exported Surface

| Symbol | Module | Category | Library Use Case |
|--------|--------|----------|------------------|
| `run_loop` | `engine.py` | Core | Run the autonomous loop programmatically |
| `RunConfig` | `_run_types.py` | Core | Configure a run |
| `RunState` | `_run_types.py` | Core | Observe/control a running loop |
| `RunStatus` | `_run_types.py` | Core | Check lifecycle status |
| `Event` | `_events.py` | Events | Consume structured events |
| `EventEmitter` | `_events.py` | Events | Implement custom event handlers |
| `EventType` | `_events.py` | Events | Switch on event types |
| `FanoutEmitter` | `_events.py` | Events | Broadcast to multiple consumers |
| `NullEmitter` | `_events.py` | Events | Suppress events in tests/batch |
| `QueueEmitter` | `_events.py` | Events | Async event consumption (UI) |
| `ManagedRun` | `manager.py` | Multi-run | Inspect a managed run |
| `RunManager` | `manager.py` | Multi-run | Orchestrate multiple concurrent runs |
| `discover_checks` | `checks.py` | Discovery | List available checks |
| `run_all_checks` | `checks.py` | Discovery | Run checks programmatically |
| `discover_contexts` | `contexts.py` | Discovery | List available contexts |
| `run_all_contexts` | `contexts.py` | Discovery | Run contexts programmatically |
| `discover_instructions` | `instructions.py` | Discovery | List available instructions |
| `discover_ralphs` | `ralphs.py` | Discovery | List available ralphs |
| `resolve_ralph_name` | `ralphs.py` | Discovery | Look up a ralph by name |

#### API Coherence Issues

**API1: Missing `discover_enabled_*` functions.**
The public API exports `discover_checks`, `discover_contexts`, `discover_instructions`, `discover_ralphs` — these return ALL primitives (enabled + disabled). But the engine uses `discover_enabled_checks`, `discover_enabled_contexts`, `discover_enabled_instructions` — which merge local overrides and filter to enabled-only. A library consumer wanting to replicate what the engine does must either:
- Call `discover_enabled_*` directly from the submodule (bypassing `__init__.py`)
- Manually replicate the merge+filter logic from `_discovery.py:discover_enabled`

The public API exposes the building blocks but not the composed operation that the engine actually uses. For alphify, this means either importing from internal modules or re-implementing filtering.

**API2: `app` is exported.**
`__init__.py:23` — `from ralphify.cli import app` exports the Typer app object. This is the CLI entry point, not a library symbol. Importing `ralphify` triggers CLI module loading (all of `cli.py`'s imports: `typer`, `rich`, `shutil`, etc.). For a pure library consumer who only wants `run_loop`, this adds unnecessary import overhead and pulls in CLI dependencies. The `app` is used by the `main()` entry point (`__init__.py:41-43`) but doesn't need to be in the module namespace.

**API3: No `Check`, `Context`, `Instruction`, `Ralph` types exported.**
The discovery functions return typed objects (`list[Check]`, `list[Context]`, etc.), but these types aren't in `__all__`. A library consumer who calls `discover_checks()` gets back `Check` objects but can't type-hint their own code without importing from `ralphify.checks` directly. The types are publicly usable but not publicly documented.

**API4: No `ConsoleEmitter` exported.**
The three emitter implementations (`NullEmitter`, `QueueEmitter`, `FanoutEmitter`) are exported, but `ConsoleEmitter` is not. A library consumer who wants terminal output identical to the CLI must import from `ralphify._console_emitter` — a private module. This is arguably intentional (ConsoleEmitter is tied to Rich, which is a CLI concern), but it means there's no "batteries included" way to get human-readable output from the library API.

**API5: `run_all_checks` and `run_all_contexts` lack their counterpart resolution functions.**
The API exports `run_all_checks` and `run_all_contexts` (execution) but not `format_check_failures` (feedback formatting) or `resolve_contexts` (prompt injection). A library consumer who runs checks can't format the results without importing from `ralphify.checks.format_check_failures` directly. The execution half of the workflow is public; the formatting half is not.

#### Assessment

The public API is designed around two use cases: (1) running a loop from code (`run_loop` + `RunConfig` + emitters) and (2) inspecting primitives (`discover_*`). Use case 1 is complete — `run_loop` is a self-contained entry point. Use case 2 is partial — discovery works but the types and formatting functions needed to build on top of discovery are missing.

For alphify (non-technical user wrapper), the critical path is use case 1 via `RunManager`. This path is well-served: `RunManager.create_run()` → `start_run()` → drain `QueueEmitter.queue`. The gaps (API1-API5) matter more for a "power library consumer" building custom tooling around ralphify's primitives.

### CLI Bridge Layer Analysis (`cli.py`)

`cli.py` (349 lines) is the translation layer between user intent and engine configuration. It performs six distinct jobs: banner display, config loading, prompt resolution, primitive scaffolding, status reporting, and RunConfig construction. This section traces how each function operates and identifies where the bridge introduces friction, divergence, or silent misbehavior.

#### The `run()` Command: Intent-to-Config Translation

The `run()` function (`cli.py:281-346`) is the most complex CLI command. Its responsibility is:
1. Load TOML config (`_load_config()`)
2. Resolve which prompt source to use (4 paths — traced in the CLI Resolution section above)
3. Construct `RunConfig` with the merged result of TOML values + CLI flags
4. Create `RunState` and `ConsoleEmitter`
5. Call `run_loop(config, state, emitter)`

**CL1: No exit code propagation.** `run_loop()` returns `None` (`engine.py:316`). The `run()` CLI command at `cli.py:346` calls it and returns implicitly. After the loop, `state.status` contains `COMPLETED`, `FAILED`, or `STOPPED`, and `state.failed` contains the failure count — but the CLI never translates this to a process exit code. `ralph run -n 1` exits 0 **even if all checks failed** or the run crashed with an exception.

For CI/automation (J5, J8), the exit code is the primary interface. A shell script like `ralph run -n 3 && git push` will push even if every iteration failed. The fix is ~5 lines at the end of `run()`: check `state.status` and `raise typer.Exit(1)` on failure.

**CL2: Config loading is duplicated and unvalidated.** Both `run()` (`cli.py:300-303`) and `status()` (`cli.py:232-236`) independently access `config["agent"]`, `agent["command"]`, `agent["ralph"]` from the raw TOML dict. Neither validates the structure. If a user renames `[agent]` to `[agents]`, both commands crash with `KeyError: 'agent'` — but they crash independently, meaning fixing one command doesn't fix the other. The `_load_config()` function (`cli.py:133-140`) is the shared bottleneck, but it only checks for file existence, not content validity.

**CL3: `project_root` is never resolved to an absolute path.** `RunConfig.project_root` defaults to `Path(".")` (`_run_types.py:58`). The CLI never sets it — it relies on the default. All check and context execution uses `cwd=project_root` (`_runner.py:54`). This works for CLI usage (CWD is the project root) but breaks for library consumers who call `run_loop()` from a different directory. The default should be `Path(".").resolve()` or the CLI should explicitly set it.

**CL4: Banner adds friction for frequent users.** `run()` calls `_print_banner()` at `cli.py:299` — 10+ lines of ASCII art + tagline before any useful output. For a tool that's run frequently (J1), this pushes the actionable output (check counts, iteration results) below the fold. `status()` does not print the banner, creating inconsistency. The banner could be suppressed with a `--quiet` flag or limited to the first run.

#### The `status` Command: Divergent Discovery

The `status()` command (`cli.py:229-278`) shows a different view of the world than the engine uses.

**CL5: `status` discovers differently than `run`.** `status()` calls:
- `discover_checks()` — global only, enabled + disabled
- `discover_contexts()` — global only, enabled + disabled
- `discover_instructions()` — global only, enabled + disabled
- `discover_ralphs()` — global only, enabled + disabled

But the engine (`engine.py:71-75`) calls:
- `discover_enabled_checks(root, prompt_dir)` — global + local merged, enabled only
- `discover_enabled_contexts(root, prompt_dir)` — global + local merged, enabled only
- `discover_enabled_instructions(root, prompt_dir)` — global + local merged, enabled only

This means:
1. `ralph status` shows ALL primitives (enabled + disabled) globally — correct for a general overview
2. But it **can't** answer "what will `ralph run docs` actually use?" because it doesn't merge local primitives or know which ralph the user intends to run
3. If a check is disabled globally but enabled locally for a specific ralph, `status` shows it as disabled, but `ralph run <name>` uses it as enabled
4. Scoped primitives (under `.ralphify/ralphs/<name>/checks/`) don't appear at all in `status`

The gap: there's no way to preview the effective configuration for a specific named ralph before running it. A `ralph status --ralph docs` command would fill this gap by showing the merged, filtered view.

#### The `_DefaultRalphGroup` Implicit Routing

`_DefaultRalphGroup` (`cli.py:49-55`) silently transforms unknown `ralph new <arg>` subcommands into `ralph new ralph <arg>`. Combined with `hidden=True` on the `new_ralph` command (`cli.py:221`), this creates:

**CL6: Implicit routing with a collision trap.** `ralph new foo` creates a ralph named "foo" (because "foo" is not a known command, so it's routed to `ralph new ralph foo`). But `ralph new check` creates a check (because "check" IS a known command name). This means:
- `ralph new check` → creates a check (expected)
- `ralph new test-runner` → creates a **ralph** named "test-runner" (surprising — user might expect a check)
- `ralph new ralph check` → creates a ralph named "check" (the explicit path)
- A user who wants a ralph named "check" must use the explicit `ralph new ralph check` syntax, but the `ralph` subcommand is hidden

The implicit routing is clever but creates a learning trap: users who successfully use `ralph new docs` to create a ralph will be surprised when `ralph new check` creates a check instead of a ralph named "check". The heuristic (unknown = ralph) is invisible.

#### Prompt Re-Read: Undocumented Live Editing

**CL7: Prompt file is re-read from disk on every iteration.** `_assemble_prompt()` (`engine.py:162`) calls `Path(config.prompt_file).read_text()` each iteration. This is an **undocumented feature**: users can edit `RALPH.md` (or any prompt file) between iterations and the changes take effect immediately.

This creates an asymmetry:
- **Prompt content** is dynamic (re-read each iteration)
- **Prompt directory** (for scoped primitives) is fixed at startup (`engine.py:343-344` — `_resolve_prompt_dir` is called once)
- **Primitives** are fixed at startup unless explicitly reloaded via `request_reload()`

So a user can live-edit their prompt text, but they can't add/remove/edit checks mid-run without triggering a reload (which is only available via the API, not the CLI). This half-dynamic behavior is neither documented nor surfaced — users who discover it will expect the other half to be dynamic too.

**Risk:** If the user deletes or renames the prompt file between iterations, `Path(config.prompt_file).read_text()` raises `FileNotFoundError`, which propagates to `run_loop`'s `except Exception` and crashes the run. There's no retry or fallback.

#### Config-to-RunConfig Bridging Gap

**CL8: CLI flags that can't be defaulted in config.** The `run()` command exposes 8 flags. Only 3 have config-file equivalents:

| Setting | CLI Flag | Config Equivalent | Default |
|---------|----------|-------------------|---------|
| Command | — | `agent.command` | Required |
| Args | — | `agent.args` | `[]` |
| Ralph | `prompt_name` / `--prompt-file` | `agent.ralph` | `"RALPH.md"` |
| Iterations | `-n` | — | Infinite |
| Prompt text | `-p` | — | None |
| Stop on error | `-s` | — | `False` |
| Delay | `-d` | — | `0` |
| Log dir | `-l` | — | None |
| Timeout | `-t` | — | None |

5 of 8 runtime behaviors can only be set per-invocation. A user who always wants `--log-dir logs --timeout 300 -n 10` types it every time. Already documented as F42 and O4, but this trace shows the precise gap at the bridging layer: `cli.py:331-342` constructs `RunConfig` purely from CLI flags with no config-file merging for these fields.

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
| J2 (Guardrails) | Feedback loop systematically truncates most useful info (SL2, SL3) | `truncate_output()` keeps head, test runners put summaries at tail |
| J2 (Guardrails) | Context failures silently corrupt prompt data (SL5) | `resolve_contexts()` never checks `ContextResult.success` |
| J2 (Guardrails) | No check progress tracking between iterations (SL4) | `check_failures_text` completely replaced each iteration |
| J3 (Stop babysitting) | Agent can't tell if its fixes worked (SL4, SL6) | No positive feedback when checks pass; no diff of what changed |
| J5 (Reliable workflow) | One broken primitive crashes all of its type | No error boundaries in discovery (`_discovery.py:77`) or execution (`_runner.py:50`) |
| J5 (Reliable workflow) | Frontmatter type errors crash discovery | `_FIELD_COERCIONS` (`_frontmatter.py:50`) has no try/except |
| J5 (Reliable workflow) | Ralph name resolution error is misleading | `ralphs.py:120-121` silently falls back from name to path |
| J5 (Reliable workflow) | Scoped primitives silently lost on `--prompt-file` path | `_resolve_prompt_dir` only activates for named ralphs (PR3) |
| J10 (Encode expertise) | Scoped checks don't work with all invocation paths | Feature only works on 2 of 5 prompt paths |
| J8 (Team workflows) | Public API missing types returned by public functions | `Check`, `Context`, etc. not in `__all__` (API3) |
| J8 (Team workflows) | Library import pulls in CLI dependencies | `__init__.py` imports `app` from `cli.py` (API2) |
| J5 (Reliable workflow) | `ralph run` exits 0 even when all checks fail | `run_loop` returns None; CLI doesn't translate `RunState.status` to exit code (CL1) |
| J8 (Team workflows) | Can't use `ralph run` in CI pipelines reliably | No non-zero exit code on failure means `&&` chaining, CI steps don't detect failures (CL1) |
| J6 (Feel in control) | `ralph status` can't show what a specific ralph will use | `status` discovers globally; doesn't merge scoped primitives for a named ralph (CL5) |
| J5 (Reliable workflow) | `project_root` is relative, breaks library consumers | `RunConfig.project_root` defaults to `Path(".")` — never resolved to absolute (CL3) |
| J6 (Feel in control) | Prompt content is live-editable but primitives aren't | Prompt file re-read each iteration; primitives fixed at startup unless API reload (CL7) |

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

---

### Feedback Loop Opportunities (from data flow trace)

### O11: Tail-Biased Truncation [HIGH PRIORITY]
**What:** Change `truncate_output()` (`_output.py:28-32`) to keep the **last** N characters instead of the first N, or keep both head and tail with an elision in the middle (e.g., first 1000 + `\n... (N chars truncated) ...\n` + last 4000).
**Job:** SJ11 → J2 (guardrails — self-healing feedback quality)
**Why:** This is the single biggest signal loss point in the feedback loop. `text[:5000]` keeps the **head** of check output, but all major test runners (pytest, jest, go test, cargo test) put failure summaries and error details at the **end**. The agent systematically receives the least useful part of the output — a stream of "PASSED" lines — while the actual failure details (tracebacks, expected-vs-received, failure counts) are truncated away. An agent that can't see what failed can't fix it. The fix is ~10 lines.
**Effort:** S (change truncation logic in `_output.py:28-32`, ~10 lines)
**Risk:** Very low — same API surface, better content. Test runners universally put summaries at the end, so tail-biased truncation is strictly better for the feedback loop use case.
**Evidence:** `_output.py:30-31` — `text[:max_len]` with no consideration of content structure. Every test runner puts its summary at the end: pytest prints `=== FAILURES ===` then tracebacks then `short test summary info`; jest prints `Tests:` summary; go test prints `FAIL` lines.

### O12: Context Failure Surfacing [HIGH PRIORITY]
**What:** In `resolve_contexts()` (`contexts.py:129-155`), check `ContextResult.success` and `ContextResult.timed_out`. When a context fails, either: (a) skip it and emit a warning event, or (b) wrap the output in a warning block so the agent knows the data may be corrupt. Also emit a `CONTEXT_FAILED` event (new EventType) so the CLI can warn the user.
**Job:** SJ2 → J2 (guardrails), J6 (feel in control)
**Why:** When a context command fails (non-zero exit) or times out, `resolve_contexts()` silently injects whatever output was captured — which may be empty, partial, or error messages. The agent has no way to know it's operating on corrupt data. If a `git log` context fails, the agent might conclude there's no git history rather than that the context failed. `ContextResult.success` and `ContextResult.timed_out` fields already exist (line 49-50) but are never read by the resolution path.
**Effort:** S (add conditional check in `resolve_contexts`, add event type, add ConsoleEmitter handler)
**Risk:** Low — the context data is already potentially corrupt; surfacing this is strictly better

### O13: Check Progress Feedback [MEDIUM PRIORITY]
**What:** Include a brief summary of the previous iteration's check status in the failure feedback text. Modify `format_check_failures()` (`checks.py:157-185`) to accept the previous iteration's results and generate a diff: "Previously failing: X, Y, Z. Now passing: X, Y. Still failing: Z. New failure: W."
**Job:** SJ3 (orchestrate) → J2 (guardrails), J3 (stop babysitting)
**Why:** `check_failures_text` is completely overwritten each iteration (`engine.py:368`). The agent can't tell if it's making progress — it sees the current failures but not what changed. If it fixed 3 of 5 failing checks but broke 1 new one, it sees "3 failures" with no indication that 3 were fixed. Agents that can't measure their own progress tend to thrash — retrying fixes that already worked or abandoning approaches that were partially successful.
**Effort:** M (store previous `CheckResult` list in loop state, compare in `format_check_failures`)
**Risk:** Low — additive to the feedback text; the agent still sees current failures. The diff summary adds ~3-5 lines before the detailed failures.

### O14: Positive Check Feedback [LOW PRIORITY]
**What:** When all checks pass, `format_check_failures()` returns `""` and the prompt gets no feedback. Instead, return a brief positive signal: `"## Check Results\n\nAll N checks passed after the last iteration."` so the agent knows its work succeeded.
**Job:** SJ3 → J1 (ship features), J3 (stop babysitting)
**Why:** On iteration 2+ with all checks passing, the prompt is identical to iteration 1. The agent can't distinguish "first iteration, no checks run yet" from "iteration 5, all checks pass." Without positive feedback, some agents will redundantly re-verify their work or continue making unnecessary changes. An explicit "all passed" signal helps the agent focus on remaining work rather than re-checking.
**Effort:** S (3-5 lines in `format_check_failures`, update `_assemble_prompt` to always append)
**Risk:** Very low — adds a few tokens to the prompt; some agents may benefit more than others

### O15: Separate stdout/stderr in Check Output [LOW PRIORITY]
**What:** Change `collect_output()` (`_output.py:12-25`) to label stdout and stderr sections rather than blindly concatenating them. E.g., `"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"` when both are non-empty.
**Job:** SJ11 → J2 (guardrails)
**Why:** stdout and stderr from check commands are concatenated with no separator or labels. Compiler warnings (stderr) mix with test output (stdout). The agent can't distinguish between a test failure message and a deprecation warning. In practice, most check commands write to only one stream, so this matters mainly for linter/compiler checks that write diagnostics to stderr and results to stdout.
**Effort:** S (modify `collect_output` to add labels when both streams are non-empty)
**Risk:** Low — changes the format of output seen by the agent, which could affect agents that parse check output literally. Should only add labels when both streams are non-empty to avoid noise.

### O16: Error Boundaries for Check/Context Execution [HIGH PRIORITY]
**What:** Wrap individual check and context execution in try/except in `run_all_checks()` (`checks.py:154`) and `run_all_contexts()` (`contexts.py:126`). Catch `FileNotFoundError`, `PermissionError`, and `OSError`. When a check/context fails to execute, produce a synthetic `CheckResult`/`ContextResult` with the error message as output, rather than crashing the entire phase.
**Job:** SJ4 → J2 (guardrails), J5 (reliable workflow)
**Why:** A single check with a typo in its command (`pytst` instead of `pytest`) or a non-executable script crashes the entire check phase via unhandled `FileNotFoundError`. Because checks run in a list comprehension, remaining checks never execute. The agent receives no feedback at all — not even from the checks that would have succeeded. This is the most common error path for new users configuring their first checks. The fix is ~10 lines per function: wrap the `run_check`/`run_context` call in try/except and synthesize a failure result.
**Effort:** S (~20 lines across two functions)
**Risk:** Very low — strictly more resilient than current behavior. The synthetic failure result uses the same `CheckResult`/`ContextResult` types, so downstream code (formatting, events) works unchanged.
**Evidence:** `checks.py:154` — `return [run_check(check, project_root) for check in checks]`. `_runner.py:50` — `subprocess.run()` raises `FileNotFoundError` for missing commands, `PermissionError` for non-executable scripts. Neither is caught.

### O17: Graceful Frontmatter Type Coercion [MEDIUM PRIORITY]
**What:** Wrap the `_FIELD_COERCIONS` call in `_parse_kv_lines()` (`_frontmatter.py:50`) in a try/except. On failure, fall back to the raw string value and emit a warning (via `warnings.warn`, matching the pattern in `checks.py:75`).
**Job:** SJ7 → J5 (reliable workflow)
**Why:** `timeout: slow` in a CHECK.md causes `int("slow")` to raise `ValueError`, crashing discovery for ALL checks — not just the one with the bad value. The user sees a raw traceback with no indication which file caused the problem. The fix is 3 lines: wrap `coerce(value)` in try/except, warn with the filename context, use the raw string. Downstream code that expects `int` will still fail, but the failure will be localized to that check rather than crashing all discovery.
**Effort:** S (~5 lines)
**Risk:** Very low — additive error handling. The raw string fallback may cause later type errors, but they'll be localized to the single primitive rather than crashing all discovery.

### O18: Improve Ralph Name Resolution Error Messages [LOW PRIORITY]
**What:** In `resolve_ralph_source()` (`ralphs.py:116-121`), when a TOML ralph value fails name resolution, check if the fallback file path exists before returning. If neither exists, raise `ValueError` with a message that mentions both the name lookup failure and the file path failure. E.g., "Ralph 'myralph' not found as a named ralph or file path. Available ralphs: docs, refactor."
**Job:** SJ1 → J5 (reliable workflow)
**Why:** When `ralph.toml` contains `ralph = "myralph"` and `myralph` isn't found, the fallback silently treats it as a file path (`ralphs.py:121`). The error the user sees is "Prompt file 'myralph' not found" (`cli.py:325`) — which is confusing because the user intended a ralph name, not a file path. The user has no indication that name resolution was attempted.
**Effort:** S (~5 lines)
**Risk:** Very low — improves error message clarity only

### New Opportunities (from CLI, state machine, and API analysis)

### O19: Preserve Scoped Primitives for `--prompt-file` Pointing to a Ralph Directory [MEDIUM PRIORITY]
**What:** In `_resolve_prompt_dir()` (`engine.py:45-53`), detect when `config.prompt_file` points to a file inside `.ralphify/ralphs/<name>/` and derive `prompt_dir` from it, even when `prompt_name` is `None`. This way, `--prompt-file .ralphify/ralphs/docs/RALPH.md` gets the same scoped primitives as `ralph run docs`.
**Job:** SJ1 → J5 (reliable workflow), J10 (encode expertise)
**Why:** Currently, scoped primitives only activate for 2 of 5 prompt resolution paths (PR3 in the CLI resolution trace). A user who manually specifies a ralph file via `--prompt-file` loses all scoped checks/contexts/instructions with no warning. This is the kind of silent degradation that erodes trust — the user's checks stop running and they don't know why.
**Effort:** S (~10 lines — check if `config.prompt_file` is inside the ralphs directory)
**Risk:** Low — additive behavior. Only activates when the file is in a ralph directory structure.
**Evidence:** `engine.py:45-53` — `_resolve_prompt_dir` only returns non-None when `config.prompt_name` is set. `cli.py:314-315` — `resolve_ralph_source` returns `prompt_name=None` for `--prompt-file`.

### O20: Guard RunState Transitions Against Invalid States [LOW PRIORITY]
**What:** Add simple guards to `request_pause()`, `request_resume()`, and `request_stop()` that check the current status before transitioning. E.g., `request_pause()` should no-op if status is COMPLETED/FAILED/STOPPED. `request_resume()` should no-op if not PAUSED.
**Job:** SJ6 → J5 (reliable workflow), J8 (team — shared state via UI)
**Why:** Currently, `request_pause()` on a COMPLETED run sets `status = PAUSED` — a logically invalid state (ST3 in the state machine analysis). Under the current codebase this is harmless because nothing reads status during the post-loop phase. But as the UI layer grows, status-dependent behavior (e.g., "show stop button only when RUNNING") becomes fragile if invalid states are possible.
**Effort:** S (~5 lines per method — check status before mutating)
**Risk:** Very low — guards are purely defensive. No change to happy-path behavior.

### O21: Make Engine the Sole Writer of `status` [LOW PRIORITY]
**What:** Replace `request_pause()` setting `status = PAUSED` with a `_pause_requested` flag (same pattern as `_stop_requested`). The engine transitions to PAUSED itself in `_handle_loop_transitions`. Similarly for `request_resume()`.
**Job:** SJ6 → J3 (stop babysitting), J8 (team)
**Why:** `state.status` is currently written by both the engine thread and API threads (ST1-ST2). This creates brief windows where status doesn't reflect actual engine state (e.g., status shows PAUSED while agent is still running mid-iteration). Making the engine the sole status writer eliminates these windows and simplifies reasoning about state.
**Effort:** M (refactor 3 methods in `_run_types.py`, update `_handle_loop_transitions` in `engine.py`)
**Risk:** Medium — changes the control API contract. `request_pause()` would no longer immediately change status; callers must wait for the engine to acknowledge.
**Recommendation:** Only pursue if the UI layer needs accurate real-time status. For CLI-only use, the current pattern is fine.

### O22: Export Primitive Types and Composition Functions from `__init__.py` [LOW PRIORITY]
**What:** Add `Check`, `Context`, `Instruction`, `Ralph`, `CheckResult`, `ContextResult`, `format_check_failures`, `resolve_contexts`, `discover_enabled_checks`, `discover_enabled_contexts`, `discover_enabled_instructions`, and `ConsoleEmitter` to `__all__`.
**Job:** SJ1, SJ2, SJ5 → J8 (team — library consumers), alphify integration
**Why:** Library consumers (including alphify) must import from private modules to access the types returned by public functions (API1, API3, API4, API5 in the public API analysis). The discovery functions are public but the types they return are not. The execution functions are public but the formatting functions that complete the workflow are not. Exporting these symbols makes the library API self-sufficient.
**Effort:** S (~10 lines — add imports and `__all__` entries)
**Risk:** Low — purely additive. Increases the public surface area, which creates a stability commitment, but these types are already stable.
**Recommendation:** Do this incrementally — start with the primitive types (`Check`, `Context`, `Instruction`, `Ralph`) and the `discover_enabled_*` functions. Add formatting functions and `ConsoleEmitter` when there's a concrete consumer.

### O23: Separate CLI Entry Point from Library Imports [LOW PRIORITY]
**What:** Move `from ralphify.cli import app` out of `__init__.py` and into a `ralphify.__main__` or the `main()` function itself. This prevents importing the CLI module (and its `typer`/`rich` dependencies) when using ralphify as a library.
**Job:** SJ7 → J8 (team — library consumers)
**Why:** `__init__.py:23` imports `app` from `cli.py`, which triggers loading of `typer`, `rich`, `shutil`, `tomllib`, and all primitive modules with their full import chains. A library consumer who only wants `run_loop` pays this cost. This matters for alphify's startup time and for any integration that imports ralphify in a larger application.
**Effort:** S (move one import line, ensure `main()` does a lazy import)
**Risk:** Very low — `app` isn't in `__all__` but is accessible via `ralphify.app`. Moving it to lazy import is technically a breaking change for anyone doing `from ralphify import app`, but this is an internal detail.

### CLI Bridge Layer Opportunities (from cli.py deep dive)

### O24: Exit Code Propagation from Engine to CLI [HIGH PRIORITY]
**What:** After `run_loop()` returns, check `state.status` and `state.failed`. If the run failed or was stopped due to error, `raise typer.Exit(1)`. If all iterations completed but checks failed on the final iteration, exit with code 2 (partial success). If the run completed cleanly, exit 0.
**Job:** J5 (reliable workflow), J8 (team workflows — CI integration)
**Why:** `ralph run -n 1` exits 0 **even when all checks fail** or the run crashes with an exception (CL1). The CLI never translates `RunState.status` to a process exit code. For CI/automation, the exit code is the primary interface: `ralph run -n 3 && git push` pushes even if every iteration failed. `set -e` scripts don't catch failures. GitHub Actions steps don't fail. This is the single biggest gap for J5 (reliable workflow) in automated contexts.
**Effort:** S (~5 lines at end of `cli.py:run()` — check `state.status`, raise `typer.Exit(1)` on failure)
**Risk:** Very low — additive behavior. CLI callers who don't check exit codes are unaffected. Callers who DO check exit codes (CI, shell scripts) get correct behavior they currently lack.
**Evidence:** `cli.py:346` — `run_loop(config, state, emitter)` with no return value check. `engine.py:316` — `run_loop` returns `None`. After the call, `state.status` and `state.failed` are available but unused.

### O25: Ralph-Specific Status View [MEDIUM PRIORITY]
**What:** Add an optional `--ralph` argument to `ralph status` that shows the merged, filtered view for a specific named ralph. When provided, call `discover_enabled_*()` with the ralph's `prompt_dir` instead of `discover_*()` globally.
**Job:** J6 (feel in control), J10 (encode expertise)
**Why:** `ralph status` shows a different view than what `ralph run <name>` actually uses (CL5). Scoped primitives (checks/contexts/instructions under `.ralphify/ralphs/<name>/`) don't appear at all. A user who adds a scoped check to their ralph has no way to verify it was discovered correctly without actually running the loop. `ralph status --ralph docs` would show exactly what `ralph run docs` will use.
**Effort:** S-M (~20 lines — add `--ralph` option, resolve ralph name, pass `prompt_dir` to discovery)
**Risk:** Low — additive flag. Default behavior (no `--ralph`) is unchanged.

### O26: Resolve `project_root` to Absolute Path [LOW PRIORITY]
**What:** Change `RunConfig.project_root` default from `Path(".")` to `Path(".").resolve()`, or have the CLI explicitly set it to `Path.cwd()`.
**Job:** J8 (team — library consumers), SJ4 (subprocess execution)
**Why:** `RunConfig.project_root` defaults to `Path(".")` (`_run_types.py:58`), which is relative to wherever the Python process started. All check and context execution uses `cwd=project_root` (`_runner.py:54`). For CLI usage this works. For library consumers who call `run_loop()` from a different working directory (e.g., a web server), all subprocess execution silently runs in the wrong directory. The fix is 1 line.
**Effort:** S (change default in `_run_types.py:58`, or set explicitly in `cli.py`)
**Risk:** Very low — `Path(".").resolve()` produces the same result as `Path(".")` when CWD hasn't changed. Only changes behavior for library consumers, and the new behavior is correct.

### O27: Document Live Prompt Editing as a Feature [LOW PRIORITY]
**What:** Document that `_assemble_prompt()` re-reads the prompt file from disk on every iteration (`engine.py:162`), making live editing possible. Either: (a) document this as a feature with the caveat that primitives aren't dynamic, or (b) make primitives auto-reload too by calling `_discover_enabled_primitives` at the top of each iteration.
**Job:** J6 (feel in control), J2 (guardrails — mid-run adjustment)
**Why:** The prompt file is re-read each iteration (CL7), but this is undocumented. Users who discover it will expect primitives to be dynamic too, but primitives are fixed at startup unless reloaded via the API (not available from CLI). The half-dynamic behavior creates confusion. Either make both dynamic or document the asymmetry.
**Effort:** S for docs, M for auto-reload (move `_discover_enabled_primitives` call into `_run_iteration`)
**Risk:** Auto-reload adds a disk scan per iteration. At current scale (~10 primitives), this is negligible. Document-only approach has zero risk.

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

### 5. Head-Biased Truncation Inverts Signal Value
The feedback loop's truncation strategy (`_output.py:30-31`) is **anti-correlated with information value**. Test runner output follows a universal pattern: per-test status (low value, high volume) first, failure details and summary (high value, low volume) last. By keeping `text[:5000]`, the system preserves the low-value head and discards the high-value tail. This is the architectural equivalent of a hearing aid that amplifies background noise and attenuates speech. The agent is systematically denied the information it needs most to self-heal. (See O11 for the fix.)

### 6. Silent Context Corruption
`resolve_contexts()` (`contexts.py:129`) processes all context results identically regardless of `success` or `timed_out` status. A context that crashed injects its error output (or empty output) into the prompt without any warning. This violates the principle that the system should fail visibly, not invisibly. The `ContextResult.success` and `ContextResult.timed_out` fields exist but are dead reads — no downstream code inspects them for resolution purposes. (See O12 for the fix.)

### 8. Prompt Resolution Path Asymmetry
The `run` command has 5 distinct paths to determine the prompt source (inline text, positional name, --prompt-file, TOML file path, TOML name). These paths have silently different feature sets: scoped primitives only activate on 2 of 5 paths, frontmatter parsing happens on 4 of 5 paths, and the `-p` path masks config validation errors (PR1). The asymmetry is undocumented and creates "works with `ralph run docs`, breaks with `--prompt-file`" surprises. This isn't necessarily wrong — different input modes legitimately have different semantics — but the differences should be either eliminated (make `--prompt-file` detect ralph directories and activate scoping) or documented explicitly.

### 9. Dual-Writer State Pattern
`RunState.status` is written by both the engine thread (RUNNING/COMPLETED/FAILED/STOPPED at `engine.py:334,392,384,128`) and API threads (PAUSED/RUNNING via `request_pause`/`request_resume` at `_run_types.py:113,118`). This creates brief windows where status doesn't reflect actual engine state. The pattern works under CPython's GIL but is fragile — it assumes no code makes decisions based on `status` between the API write and the engine's acknowledgment. If the codebase grows to include status-conditional behavior, this becomes a race condition source.

### 7. Binary Error Handling: Crash or Swallow
The codebase has exactly two error handling modes with no middle ground:
- **Crash mode:** Any unhandled exception propagates to `run_loop`'s `except Exception` (`engine.py:383`) and terminates the entire run. This is how config errors, discovery errors, subprocess errors (FileNotFoundError, PermissionError), frontmatter coercion errors, and BrokenPipeError all behave.
- **Swallow mode:** Context failures, missing template placeholders, and output truncation are completely invisible. No warning, no event, no log entry.

The missing middle tier — **graceful degradation** — would let individual primitives fail without taking down the entire operation. Currently, a single check with `command: pytst` (typo) crashes the check phase for all checks. A single `CHECK.md` with `timeout: slow` crashes discovery for all checks. The blast radius of a single primitive's error extends to the entire primitive type.

This pattern is especially harmful for new users who are iterating on their configuration. Every configuration experiment is a potential run-killing error. (See O16 for check/context execution boundaries and O17 for frontmatter coercion boundaries.)

### 10. Silent Exit Code: Success on Failure
`ralph run` always exits 0, regardless of whether the run succeeded, failed, or crashed (CL1). The `run()` function at `cli.py:346` calls `run_loop()` and returns without checking `state.status`. This makes `ralph run` invisible to CI pipelines, shell script chaining (`&&`), and automation that relies on exit codes. A tool designed for reliable workflows (J5) that can't signal failure through the most basic Unix interface (exit codes) has a fundamental design gap. This is the CLI equivalent of a test runner that always says "passed." (See O24 for the fix.)

### 11. Status Command Shows Wrong View
`ralph status` uses a different discovery path than the engine, showing global-only primitives while the engine merges global + scoped primitives (CL5). The user asks "what's my setup?" and gets a snapshot that doesn't match what `ralph run <name>` actually uses. Scoped primitives are invisible in `status`. This is especially problematic for the J10 job (encode expertise) — a user who carefully scopes checks to a ralph has no way to verify the scoping worked without running the loop. (See O25 for the fix.)

### 12. Half-Dynamic Runtime Behavior
The prompt file is re-read from disk on every iteration (CL7), but primitives are fixed at startup. This creates a "half-dynamic" runtime where one input channel responds to live changes and another doesn't. Users who discover prompt live-editing (a useful, undocumented feature) will naturally expect primitives to be dynamic too. When they edit a CHECK.md or add a new check directory mid-run, nothing happens — and they have no way to know that a reload is needed (the reload API isn't exposed via CLI). The asymmetry is invisible and violates the principle of least surprise.

## Open Questions

1. **Is a 5th primitive type planned?** If yes, O9 (reduce discovery boilerplate) becomes higher priority. If no, the current explicit pattern is fine.

2. **Should `ralph init` be opinionated or minimal?** O3 proposes project-aware init with default checks. This makes the tool more opinionated (potentially alienating the Skeptical Senior persona) but dramatically improves time-to-first-useful-run (critical for Solo Founder and Vibe Coder personas). The right answer depends on which persona is the primary target.

3. **Is the web dashboard (`ralph ui`) still actively developed?** Several event types (AGENT_ACTIVITY, CONTEXTS_RESOLVED, PROMPT_ASSEMBLED) may be consumed by the UI layer even though the CLI ignores them. If the UI is active, the emit-but-don't-render pattern is justified for those events. If the UI is paused/abandoned, those events are dead code.

4. **Should non-Claude agents get first-class streaming support?** O7 proposes making streaming mode configurable. But streaming requires the agent to emit parseable output on stdout. If most non-Claude agents don't support this, the config option would be a trap (user enables streaming, agent doesn't support it, broken output). A middle ground: tee-based output capture that shows output live without requiring structured streaming.

5. **What's the relationship between `ralphify` and `alphify`?** Memory reference mentions alphify as a separate product for non-technical users. If alphify will wrap ralphify's library API, the public surface in `__init__.py` needs to be stable and well-documented. O4 (config schema extension) and O1 (config validation) become more important — library consumers need reliable, validated config handling.

6. **Should truncation strategy be configurable per check?** O11 proposes tail-biased truncation globally. But some check types (e.g., linters) produce useful output at the head (first N violations), while test runners produce it at the tail (summary). A `truncation: head|tail|smart` frontmatter field in CHECK.md could let users optimize per check, but adds complexity. Alternatively, `smart` truncation (keep head + tail, elide middle) works well for both patterns.

7. **How much iteration history should the agent receive?** O13 proposes a check progress diff (what improved/regressed). But should the agent also receive its own previous result_text? Claude Code's streaming mode captures `result_text` from the JSON stream (`_agent.py:121-124`), but this is never fed back. Giving the agent its own previous summary alongside check results could prevent it from repeating failed approaches.

8. **Should context failures be fatal or advisory?** O12 proposes surfacing context failures, but the behavior on failure is an open design question. Options: (a) skip the context entirely (safe but loses data), (b) inject the output with a warning prefix (agent sees the data is suspect), (c) abort the iteration (strict but disruptive). The right answer may depend on whether the context is critical (e.g., `git diff`) or supplementary (e.g., `uptime`).

9. **Should error boundaries be per-primitive or per-phase?** O16 proposes wrapping individual check/context execution in try/except. An alternative is wrapping the entire check phase — if any check crashes, skip the check phase and continue the loop. Per-primitive is more granular (the agent still gets feedback from healthy checks) but adds more error-handling code. Per-phase is simpler but throws away partial results. The right answer depends on whether users commonly have mixed healthy/broken check configurations.

10. **Should `_run_agent_streaming` defend against stdin failures?** `_agent.py:103` writes the prompt to `proc.stdin` with no protection against `BrokenPipeError`. This happens when the agent process exits immediately (bad args, crash on startup). The `try/finally` cleans up the process but the exception propagates to `run_loop` and terminates the run. Should this be caught and converted to a failed iteration (with a helpful message like "Agent exited before accepting input"), or is a run crash appropriate since the agent is fundamentally misconfigured?

11. **Should `--prompt-file` auto-detect ralph directories?** O19 proposes deriving `prompt_dir` when `--prompt-file` points inside `.ralphify/ralphs/<name>/`. This eliminates the PR3 asymmetry but introduces implicit behavior — a file path suddenly gains scoping semantics based on where it lives. The alternative is to document the limitation and tell users to use `ralph run <name>` for scoped behavior. The right answer depends on how common the `--prompt-file` path is in practice.

12. **Should `RunState.status` have a single writer?** O21 proposes making the engine the sole writer of status, using `_pause_requested`/`_resume_requested` flags. This eliminates the ST1-ST2 timing windows but changes the API contract — `request_pause()` would no longer immediately change status. For the CLI (single-threaded consumer), this doesn't matter. For the UI (dashboard polling status), the current "immediately visible" behavior may be preferred even if briefly inaccurate. The right answer depends on whether the UI prefers "fast but briefly wrong" or "correct but delayed."

13. **Should the public API commit to exporting primitive types?** O22 proposes adding `Check`, `Context`, `Instruction`, etc. to `__all__`. Once exported, these types become a stability commitment — changing fields would be a breaking change. If the primitive type system is still evolving (e.g., adding new fields, changing defaults), deferring the export preserves flexibility. If alphify needs these types now, the stability commitment is unavoidable.

14. **What exit code semantics should `ralph run` use?** O24 proposes exit code propagation, but the semantics need design. Options: (a) exit 1 if the run status is FAILED/STOPPED, exit 0 otherwise (simple but doesn't distinguish check failures from crashes), (b) exit 0 for COMPLETED, exit 1 for FAILED, exit 2 for STOPPED (granular but non-standard), (c) exit 0 if all checks passed on the final iteration, exit 1 otherwise (most useful for CI, but ignores run-level errors). The right answer depends on who the primary consumer of exit codes is: CI pipelines (want pass/fail), shell scripts (want error/no-error), or monitoring (want granular status).

15. **Should primitives auto-reload on disk changes?** O27 surfaces the asymmetry: prompt files are re-read each iteration but primitives are fixed at startup. Options: (a) auto-reload primitives every iteration (adds disk I/O, ~10 primitives × 1 file read each = negligible), (b) use filesystem watching (complex, platform-dependent), (c) document the behavior and rely on the API `request_reload()` (no code change, but CLI users can't trigger it). Option (a) is simplest and aligns with the prompt re-read behavior. The cost is one `_discover_enabled_primitives()` call per iteration — which already runs at startup and on reload.

16. **Should `ralph status` accept a ralph name?** O25 proposes `ralph status --ralph docs` to show the merged view. But there's a design tension: the current `status` command validates the global setup (command on PATH, config exists, primitives discoverable). A ralph-specific view adds a second mode. Should it replace the global view or supplement it? If supplementary, should it show the delta (what's different from global)? The right answer affects whether `status` remains a single-purpose validation tool or becomes a general inspection tool.
