# Trust Calibration, Harness Testing, and the Spec+Ralph Convergence

> Three threads that matured in early 2026: empirical data on how practitioners calibrate agent autonomy, frameworks for testing agent harness configurations themselves, and the convergence of spec-driven development with ralph loop execution.

## Progressive Trust: How Autonomy Actually Scales

The question of "how much freedom should I give the agent?" now has empirical answers.

### Anthropic's Data: Trust Is Earned in Sessions, Not Configured

Anthropic's February 2026 study ("Measuring AI Agent Autonomy in Practice") analyzed millions of Claude Code interactions and found a clear trust accumulation curve:

- **New users (<50 sessions)**: full auto-approve ~20% of the time
- **Experienced users (750+ sessions)**: auto-approve rises to ~40%
- **99.9th percentile turn duration**: nearly doubled from <25 min to >45 min between Oct 2025 and Jan 2026
- **Counterintuitive**: experienced users auto-approve *more* but also *interrupt more often* (~9% vs ~5% of turns) — they shift from action-by-action approval to outcome-focused monitoring
- **Agent-initiated stops exceed human interrupts**: Claude pauses for clarification more than users stop it

The key insight: trust isn't a switch, it's a gradient that emerges from hundreds of micro-interactions. Users don't decide to trust agents — they gradually stop intervening.

### The Trust Equation

Pascal Biese (LLM Watch) formalized the intuition into an actionable rubric:

> **Trust = (Competence × Consistency × Recoverability) / Consequence**

This produces a 4-level trust ladder:

| Level | Mode | Agent Does | Human Does |
|-------|------|-----------|------------|
| 1 | Observe & Report | Analyze, summarize | All decisions |
| 2 | Draft & Suggest | Propose actions | Approve/reject |
| 3 | Act with Boundaries | Execute within guardrails | Monitor, handle exceptions |
| 4 | Autonomous with Oversight | Plan and execute | Review outcomes, tune harness |

Each level requires: defined capability scope, success metrics, and graduation criteria. A logistics company shadowed human dispatchers for 2 months at Level 1 before earning Level 3 routing autonomy.

**Implementation patterns**: Shadow Mode (risk-free parallel operation), Gradual Handoff (incremental subtask delegation), Circuit Breaker Architecture (automatic constraint triggers).

### GitLab's User Research: Micro-Inflection Points

GitLab studied 13 participants and found trust builds through "micro-inflection points" — countless small interactions, not dramatic breakthroughs. Trust follows compound growth. But: **a single significant failure can erase weeks of accumulated confidence.** This asymmetry means the cost of agent mistakes is disproportionate to the benefit of agent successes.

### Bockeler's Complexity Thresholds (Thoughtworks)

Birgitta Bockeler tested how far autonomy can be pushed on concrete tasks:

| Task Complexity | Outcome | Time | Cost |
|----------------|---------|------|------|
| 3-5 entity CRUD app | Achievable | 25-30 min | $2-3/iter |
| 10 entity system | Possible with intervention | 4-5 hours | Multiple checkpoints |
| Production software | Not recommended | — | Non-deterministic failures |

Two failure modes were rated **critical with no known mitigation**:
1. **Overeagerness** — unrequested features, "recurs despite prompting"
2. **Brute-force fixes** — skipping tests, ignoring errors to make progress

These are exactly the failure modes that verification gates and scope constraints address.

### Swarmia's Five Levels

Swarmia defines a coding-specific autonomy taxonomy:

- **Level 1**: Inline suggestions (Copilot autocomplete)
- **Level 2**: Chat-based assistance (ask questions, get code)
- **Level 3**: Background agents (Copilot coding agent, Cursor background) — matured significantly 2025-2026
- **Level 4**: Agent picks work from backlog without human initiation
- **Level 5**: Fully autonomous, plans and executes over long horizons

Core argument: **the appropriate level depends on the task, not the capability.** Level 5 for test coverage; Level 2 for security-critical auth logic.

## Testing the Harness Itself

A critical gap in the research until now: how do you know your harness configuration works *before* burning tokens?

### Block Engineering's Agent Testing Pyramid

Angie Jones (Block) reimagined the testing pyramid for agents. The key shift: **layers represent uncertainty tolerance, not test types.**

**Layer 1 — Deterministic Foundations** (run in CI, fast, cheap):
- Mock LLM providers with canned responses
- Test retry logic, max turn limits, tool schema validation
- Record/playback: capture real LLM interactions to JSON, replay deterministically
- Question: "Did we write correct software?"

**Layer 2 — Reproducible Reality** (record mode):
- Run real MCP servers, capture full stdin/stdout/stderr
- `TestProvider` operates in Recording mode (calls real LLM, saves to JSON) or Playback mode (returns saved responses for matching inputs)
- Validates tool sequences without external dependencies

**Layer 3 — Probabilistic Performance** (on-demand, not CI):
- Run benchmarks multiple times, measure success rates
- "A single run tells us almost nothing but patterns tell us everything"
- Statistical significance over anecdotal passes

**Layer 4 — Vibes and Judgment** (human + LLM judge):
- LLM-as-judge with rubrics, 3 evaluation rounds, majority vote
- Reserved for subjective quality assessment

**Critical rule**: Live LLM testing does NOT run in CI — "too expensive, too slow, and too flaky." CI validates deterministic layers; humans validate probabilistic layers when it matters.

### Datadog's Verification Loop

Datadog's "harness-first" approach closes the verification gap with a continuous feedback cycle:

> Agent generates → harness verifies → production telemetry validates → feedback updates harness → agent iterates

Their verification pyramid has five layers with concrete tools:
1. **Symbolic** (TLA+ specs, ~2 min)
2. **Primary** (deterministic simulation testing, ~5 sec)
3. **Exhaustive** (model checking, 30-60 sec)
4. **Bounded** (Kani formal verification, ~60 sec)
5. **Empirical** (production telemetry, seconds-minutes)

Results: 87% memory reduction on redis-rust after agent-guided optimization. The harness-first approach means: "Instead of reading every line of agent-generated code, invest in automated checks that tell us with high confidence, in seconds, whether the code is correct."

### LLM-as-Judge: The Numbers

Eugene Yan's comprehensive survey provides the data behind LLM-based evaluation:

| Metric | Value | Source |
|--------|-------|--------|
| GPT-4 agreement with human experts | 85% | MT-Bench |
| Human-human agreement | 81% | MT-Bench |
| GPT-4 faithfulness correlation | ρ = 0.55 | — |
| Verbosity bias | >90% preference for longer responses | Claude-v1, GPT-3.5 |
| Position bias | Up to 70% toward first position | Claude-v1 |
| CriticGPT bug detection | 80-85% of inserted bugs | OpenAI |
| Panel (PoLL) vs single judge | Panel outperforms | Multiple studies |

**Practical takeaway**: Single LLM judges are biased. Use a panel of diverse models (PoLL approach) with explicit rubrics. Calibrate frequently against human judgment. For coding: deterministic checks first, LLM judgment only for what tests can't catch.

## The Spec+Ralph Convergence

The biggest architectural trend in early 2026: spec-driven development and ralph loops are merging into a unified workflow.

### Two Methodologies Becoming One

The field has converged on the insight that **specs define what to build; ralphs provide relentless execution**:

- **Spec Kit** (Open Spec) — structured requirements with acceptance criteria, constraints, and intent
- **Ralph Loop** — naive persistence with fresh context resets

Neither works well alone. Pure specs lack execution power. Pure ralph loops lack direction. The integrated workflow: specs as the durable artifact that steers every loop iteration, tests/CI as hard rails.

Multiple implementations have emerged:
- **speckit-ralph** (merllinsbeard) — execution engine for Spec Kit workflows
- **smart-ralph** (tzachbon) — spec-driven development with smart compaction
- **BMAD+Ralph** — phases 1-3 produce specs, phase 4 picks stories and implements with TDD
- **ASDLC.io** — formalized "Agentic Software Development Lifecycle" with ralph as pattern

### LangChain's Composable Middleware

LangChain's DeepAgents introduced a composable middleware architecture that formalizes the harness as stackable layers:

```
Agent Request
  → LocalContextMiddleware (maps codebase)
  → LoopDetectionMiddleware (prevents repetition)
  → ReasoningSandwichMiddleware (optimizes compute)
  → PreCompletionChecklistMiddleware (enforces verification)
Agent Response
```

Each middleware adds capability without modifying core agent logic. The key design principle: **build your harness to be "rippable"** — you should be able to remove "smart" logic when the model gets smart enough to not need it.

Performance impact: LangChain's coding agent jumped from 52.8% to 66.5% on Terminal Bench 2.0 (Top 30 → Top 5) by changing the harness alone. No model changes.

The LoopDetectionMiddleware specifically addresses doom loops: it tracks per-file edit counts via tool call hooks and injects "consider reconsidering your approach" after N edits to the same file.

### Anthropic's Eval Framework

Anthropic published "Demystifying Evals for AI Agents" with three grader types:

1. **Code-based** — string matching, binary pass/fail tests
2. **Model-based** — rubric scoring, pairwise comparison (calibrate against human judgment)
3. **Human** — SME review, spot-check sampling

For research agents: combine groundedness checks + coverage checks + source quality checks. Key metrics: **pass@k** (at least one correct in k attempts) and **pass^k** (all k trials succeed).

*Ralphify implications from trust, testing, and convergence findings are consolidated in [Chapter 6: Implications for Ralphify](06-ralphify-implications.md).*
