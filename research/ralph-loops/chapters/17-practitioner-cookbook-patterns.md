# Practitioner Cookbook Patterns

> Concrete, reproducible loop configurations that practitioners are actually using in production. Each pattern is distilled from real implementations shared publicly in early 2026. These translate directly to ralphify RALPH.md cookbook entries.

## The PRD-Driven Feature Loop

The most popular pattern in the wild. Three independent implementations (Adam Tuttle, snarktank, iannuttall) converged on the same structure: a JSON-based product requirements document drives a loop that implements one feature per iteration.

**How it works:**

1. A `prd.json` file contains an array of feature objects, each with a `passes: boolean` field
2. Each iteration: agent reads the PRD, selects the highest-priority item where `passes: false`
3. Agent implements the feature, runs verification (tests, typecheck, lint)
4. If verification passes: mark `passes: true` in PRD, commit, append to `progress.md`
5. Loop exits when all items have `passes: true`

**Adam Tuttle's implementation** (the most detailed):

- Three bash scripts: `plan` (Claude planning sessions), `ralph` (executes `.ralph/ralph.sh`), `ralph-install` (project setup)
- PRD schema: `[{category, description, steps[], passes}]`
- Verification: `npm run check` + `npm run test` each iteration
- Completion signal: `<PROMISE>COMPLETE</PROMISE>` triggers loop exit + macOS audio confirmation
- Permission gating: agent outputs `<PROMISE>NEED_PERMISSIONS</PROMISE>` → loop exits → user adds permission to `.claude/settings.local.json` → resumes with `claude --continue`
- Cost data: exhausted $100/month Claude Pro quota in ~1 hour of intensive looping

**iannuttall/ralph** adds stale story recovery: `STALE_SECONDS` config auto-reopens stories stuck in `in_progress` after a crash, preventing permanent deadlock. Also adds `guardrails.md` — a persistent file of learned constraints that the agent reads each iteration.

**Key insight**: The PRD format works because each item is independently verifiable. The `passes` boolean is a scalar metric (Karpathy's principle). The agent can't drift because it must select ONE item and its completion is binary.

**Ralphify translation:**

```yaml
agent: claude -p --dangerously-skip-permissions
commands:
  - name: prd
    run: cat prd.json
  - name: tests
    run: npm test 2>&1 | tail -20
  - name: progress
    run: cat progress.md
args:
  - max_features
```

Prompt: "Read the PRD status below. Select the highest-priority feature where passes is false. Implement it. Run tests. If all pass, update prd.json to mark it as passes: true. Commit with a descriptive message. Append what you learned to progress.md."

---

## Two-Phase Plan-Then-Build

From GitHub's awesome-copilot cookbook. Separates planning from execution into two distinct ralphs that communicate through a shared `IMPLEMENTATION_PLAN.md` file.

**Phase 1 — Planning ralph** (run once or few times):
- Reads specs from `specs/` directory and existing source in `src/`
- Performs gap analysis: what's specified but not implemented?
- Produces `IMPLEMENTATION_PLAN.md` as a prioritized bullet-point list
- Critical constraint: "Do NOT implement anything"
- Includes anti-false-negative rule: "Search codebase before assuming functionality is absent"

**Phase 2 — Building ralph** (run many times):
- Reads `IMPLEMENTATION_PLAN.md`, picks the most important incomplete item
- Implements it, runs tests
- Updates the plan with discoveries and completed items
- Commits only after passing validation

**Key insight**: The plan file serves as persistent shared state between iterations. All coordination happens through disk, not accumulated context. The planning phase also prevents the "build the wrong thing" failure mode (intent-failure detection from Ch14).

**Ralphify translation** — two separate ralphs:

Plan ralph (`plan/RALPH.md`):
```yaml
agent: claude -p --dangerously-skip-permissions
commands:
  - name: specs
    run: cat specs/*.md
  - name: current_plan
    run: cat IMPLEMENTATION_PLAN.md 2>/dev/null || echo "No plan yet"
  - name: src_structure
    run: find src/ -type f -name "*.ts" | head -50
```

Build ralph (`build/RALPH.md`):
```yaml
agent: claude -p --dangerously-skip-permissions
commands:
  - name: plan
    run: cat IMPLEMENTATION_PLAN.md
  - name: tests
    run: npm test 2>&1 | tail -30
```

Usage: `ralph run plan -n 1` then `ralph run build -n 20`

---

## TDD Loop

From Florian Bruniaux's Claude Code guide. Adapts Test-Driven Development for autonomous loops: each iteration writes ONE failing test, then implements until it passes.

**How it works:**

1. Prompt explicitly says "Write FAILING tests" (without the word "FAILING", Claude generates working implementation alongside tests, defeating TDD)
2. Red-green-refactor within a single iteration
3. Iteration limit in prompt: "Continue for maximum 5 iterations. If tests still fail after 5 iterations, stop and show me the current state"
4. PostToolUse hooks auto-run tests after every Write/Edit tool call (instant feedback)

**Cost optimization (OpusPlan hybrid):**
- Opus for test strategy design (10-20% of cost) — better at identifying edge cases and test architecture
- Sonnet for red-green-refactor cycles (80-90% of cost) — handles routine implementation

**Verification by domain:**

| Domain | Tool | What agent sees |
|--------|------|-----------------|
| Backend | pytest/Jest | Pass/fail + stack traces |
| Types | tsc --noEmit | Type errors |
| Style | ESLint/Prettier | Violation lists |
| Security | Semgrep | Finding descriptions |

**Key insight**: "An agent that can 'see' what it has done produces better results." The immediate feedback loop (PostToolUse hooks) is what makes TDD work autonomously — the agent doesn't wait until the end of the iteration to discover failures.

**Ralphify translation:**

```yaml
agent: claude -p --dangerously-skip-permissions
commands:
  - name: test_results
    run: uv run pytest --tb=short 2>&1 | tail -40
  - name: coverage
    run: uv run pytest --cov=src --cov-report=term-missing 2>&1 | grep -E "^(src/|TOTAL)"
  - name: untested
    run: uv run pytest --cov=src --cov-report=term-missing 2>&1 | grep "0%" | head -10
```

Prompt: "You are doing TDD. Write a FAILING test for one untested behavior from the coverage report below. The test must fail because the implementation doesn't exist yet. Then implement the minimum code to make it pass. One test-implementation cycle per iteration. Commit the test and implementation together."

---

## Guardrails Accumulation

From iannuttall/ralph. A `guardrails.md` file persists learned constraints across iterations — mistakes the agent made that it should avoid repeating.

**How it works:**

1. `guardrails.md` starts empty
2. Each iteration: agent reads guardrails as part of its context
3. When the agent discovers a constraint (test quirk, API limitation, project convention), it appends to `guardrails.md`
4. Future iterations benefit from accumulated knowledge without re-discovering constraints

**Example guardrails.md entries:**
- "Do not modify `config/database.yml` — it's managed by Ansible"
- "The `users` table has a unique constraint on email — always check for existing records before INSERT"
- "Tests in `tests/integration/` require `DATABASE_URL` env var — skip if not set"

**Key insight**: This is the "signs" pattern (Ch14) made concrete. Guardrails survive context rotation, preventing repeated mistakes. Unlike `progress.md` (what was done), guardrails capture *what NOT to do* — a fundamentally different and equally important knowledge type.

**Ralphify translation**: Add a guardrails command:

```yaml
commands:
  - name: guardrails
    run: cat guardrails.md 2>/dev/null || echo "No guardrails yet"
```

Prompt addition: "Read the guardrails below. These are constraints discovered in previous iterations — respect all of them. If you discover a new constraint (something that broke, a convention you must follow, a file you must not touch), append it to guardrails.md."

---

## Permission-Gated Loop

From Adam Tuttle. An alternative to `--dangerously-skip-permissions` where the agent explicitly requests permissions it needs and the loop pauses for human approval.

**How it works:**

1. Agent runs WITHOUT skip-permissions flag
2. When agent needs a new permission: outputs `<PROMISE>NEED_PERMISSIONS</PROMISE>` with the specific command
3. Loop detects the signal and exits cleanly
4. Human reviews the request, adds permission to `.claude/settings.local.json`:
   ```json
   {"permissions": {"allow": ["Bash(git commit*)", "Bash(pnpm test*)", "Bash(pnpx tsc *)"]}}
   ```
5. Loop resumes with `claude --continue`

**Key insight**: This is the "Level 3: Act with Boundaries" trust level from Pascal Biese's trust equation (Ch11). The agent has autonomy within defined boundaries, but boundary expansion requires human approval. It's slower but dramatically safer — especially for new ralphs where the required permissions aren't yet known.

**Ralphify implication**: This pattern doesn't require framework changes — it's a prompt engineering technique. Document it as the "safe mode" approach in the cookbook, recommended for first runs of any new ralph.

---

## The Stale Recovery Pattern

From iannuttall/ralph. Handles the common failure mode where a loop crashes mid-iteration, leaving tasks in a locked `in_progress` state.

**How it works:**

1. Each task has a lifecycle: `open` → `in_progress` (with `startedAt` timestamp) → `done`
2. If the loop crashes, tasks remain `in_progress` indefinitely
3. `STALE_SECONDS` config (e.g., 600 = 10 minutes): any task stuck in `in_progress` longer than this threshold is automatically reset to `open`
4. Next loop iteration picks it up fresh

**Key insight**: This is the simplest form of crash recovery — no complex checkpoint system, just a timeout. Combined with git-based state (the task file is committed), it's robust against most failure modes.

**Ralphify implication**: This could be implemented as a command that checks task timestamps and resets stale ones, or as a pre-iteration hook. The simpler approach: include it in the prompt — "If you see a task marked in_progress with a startedAt older than 10 minutes, reset it to open."

---

## Cross-Cutting Observations

### What all successful patterns share

1. **One task per iteration** — PRD item, plan item, or test case. Never batch.
2. **Binary completion signal** — `passes: true`, plan item struck through, test green. No ambiguity.
3. **Deterministic verification** — tests, typecheck, lint. Not "does this look good?"
4. **Append-only progress** — `progress.md` or equivalent. Never overwrite history.
5. **Git as checkpoint** — commit after every successful iteration. Revert-ready.

### The practitioner cost reality

Adam Tuttle exhausted $100/month in ~1 hour. The PRD-driven loop is token-hungry because each iteration loads the full PRD, progress file, and test output. Cost optimization techniques from Ch10 (prompt caching, output redirection, model tiering) are essential for sustained use.

### What's missing from all implementations

None of the practitioner patterns include:
- **Automated revert-on-failure** — all trust the agent to self-correct. The ratchet pattern (Ch06) would add significant reliability.
- **Loop fingerprinting** — no stuck detection beyond iteration count limits. The fingerprint pattern (Ch15) would catch doom loops earlier.
- **Budget awareness** — no cost tracking within the loop. The Budget Guard MCP (Ch10) would prevent $100/hour surprises.

These gaps represent the difference between practitioner-shared patterns (which work for individuals) and production-grade loops (which need operational safeguards). Ralphify's opportunity is to bridge this gap by making these safeguards easy to add.

## Validated Case Studies (Iteration 26)

Two practitioner case studies provide the first concrete ROI data for ralph loop patterns:

### Production Feature Build (LPains)

Used go-ralph (custom Go implementation of snarktank/ralph) to build a production feature:
- **Time**: 6 hours vs 15-20 hours manual (60% savings)
- **Iterations**: 5 loop runs, ~100 premium API requests
- **Critical success factor**: Spec quality. First attempt produced unusable code because spec lacked detail. "Spend most of your time on the spec and then on reviewing the generated output."
- **Failure mode**: Without explicitly stating "new page," the agent created a popup instead — non-negotiable requirements must be verbalized
- **Tooling**: SonarCloud caught issues the agent missed (unused imports, invalid function calls that didn't break builds)

### SDK Migration (StackToHeap)

Used ralph loops for a multi-platform SDK migration:
- **Abstract stories fail**: 6 vague stories (23 min) produced code that "technically passes gates but does not actually solve the problem"
- **Concrete stories succeed**: 9 stories mapped to actual code boundaries (81 min, 60 files changed, +3,978/-1,978 lines)
- **Post-loop work**: 11 commits (~7 hours) for CI/deployment, runtime behaviors, architectural decisions
- **Pattern propagation**: When the agent migrated GitLab flows, it documented the pattern. GitHub migration then followed automatically by reading the progress log.
- **Ideal use cases**: SDK/framework migrations excel because they have clear before/after states, natural dependency ordering, mechanical pattern-following, and existing test suites.

Both studies validate the 80/20 split: ralph loops handle ~80% of mechanical work, humans handle ~20% of integration/design decisions.

## Sources

- [My RALPH Workflow for Claude Code](https://adamtuttle.codes/blog/2026/my-ralph-workflow-for-claude-code/) — Adam Tuttle — PRD-driven loop with permission gating, cost data, completion promises
- [ralph-claude-code](https://github.com/frankbria/ralph-claude-code) — Frank Bria — Circuit breaker, dual-condition exit, session management, 566 tests
- [snarktank/ralph](https://github.com/snarktank/ralph) — snarktank — PRD-driven loop with auto-archiving, skills system
- [iannuttall/ralph](https://github.com/iannuttall/ralph) — Ian Nuttall — Minimal file-based loop, guardrails.md, stale recovery, multi-agent support
- [awesome-copilot Ralph Loop](https://github.com/github/awesome-copilot/blob/main/cookbook/copilot-sdk/nodejs/ralph-loop.md) — GitHub — Two-phase plan-then-build, AGENTS.md size guidance
- [Fresh Context Pattern / TDD with Claude](https://deepwiki.com/FlorianBruniaux/claude-code-ultimate-guide/7.3-fresh-context-pattern-(ralph-loop)) — Florian Bruniaux — TDD loop, PostToolUse hooks, OpusPlan hybrid
- [Ralph Loop Pattern](https://asdlc.io/patterns/ralph-loop/) — ASDLC.io — Completion promise formalization, convergence formula
- [How I'm Vibe Coding in 2026](https://grahammann.net/blog/how-im-vibe-coding-2026) — Graham Mann — Multi-model orchestration, parallel conversation threads, minimal prompting
- [Real World Example: Ralph Wiggum Loop](https://blog.lpains.net/posts/2026-01-31-real-world-example-ralph/) — LPains — 60% time savings, 5 iterations, spec quality as critical success factor
- [Ralph Loops for SDK Migrations](https://stacktoheap.com/blog/2026/02/23/how-i-code-from-the-gym-part-4/) — StackToHeap — 9 stories, 81 min, 60 files changed, abstract vs concrete story comparison
- [Coding Agents in Feb 2026](https://calv.info/agents-feb-2026) — Calvin — Time-based model selection, skills at ~50-100 tokens, 3-4 overnight tasks standard
