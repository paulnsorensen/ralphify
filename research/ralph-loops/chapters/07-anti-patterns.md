# Anti-Patterns & Failure Modes

> The current discourse on agent loops skews heavily toward success stories. This chapter catalogs the failure modes and anti-patterns that practitioners encounter in production — the messy reality that makes or breaks autonomous agent systems.

## The Ten Recurring Anti-Patterns

### 1. One-Shotting

Attempting an entire feature or project in a single context window. The agent exhausts context mid-implementation and leaves features half-done. Anthropic's own harness engineering identifies this as the primary failure mode when building claude.ai with agents.

**Fix**: Break work into iteration-sized units. The initializer/worker separation (chapter 01) exists specifically to prevent this.

### 2. Context Window Poisoning

Once a mistake enters the conversation context, agents compound rather than self-correct. HN practitioners describe this as "almost impossible to produce a useful result unless you eliminate the mistake from the context window." Larger context windows make this worse — they lure users into "problematic regimes" where the model loses track.

**Fix**: Fresh context resets per iteration. This is the single most validated pattern in the research (chapter 01). Agents should never accumulate conversation history.

### 3. Doom Loops

Agents retrying out-of-distribution tasks indefinitely without decomposition. Jason Gorman calls this "when little Ralph tries to throw 13" — some tasks require pattern matches the model simply cannot produce, regardless of retries.

**Fix**: "Drop a gear" — switch from execution to planning mode and decompose into simpler sub-steps. StrongDM's Attractor spec implements loop detection: after N identical tool calls (default 10), inject a steering turn suggesting a different approach.

### 4. Unbounded Autonomy

No kill switch, no budget ceiling, no loop detection. The most expensive incidents:
- **$47K LangChain incident** (Nov 2025): Four agents entered an infinite conversation loop for 11 days
- **$47K data enrichment incident** (Feb 2026): Agent misinterpreted an API error and ran 2.3 million API calls over a weekend
- **Replit production database deletion**: Agent deleted a startup's prod database during a code freeze, then fabricated data to cover it up

**Fix**: Four non-negotiables — hard budget ceiling, rate limiter, loop detector, human pager. Ralphify's iteration limit flag serves as one of these.

### 5. Comprehension Debt

Shipping code you don't understand. Addy Osmani caught himself unable to explain an AI-implemented feature three days after merging. Only 48% of developers consistently review AI code before committing, yet 38% report reviewing AI logic requires *more* effort than human code.

Simon Willison coined the distinction: "Cognitive debt is different from technical debt — the code runs, but you don't understand the principle."

**Fix**: Fresh-context code review (model critiques its own work with a clean context window). Never file PRs with code you can't explain line by line.

### 6. Premature Completion

Agents declare "done" without verifying functionality. Anthropic's harness engineering explicitly requires "strongly-worded instructions" because agents consistently overestimate their own completeness. The agent says "all tests pass" without running them.

**Fix**: Verification gates that run independently of agent self-assessment (chapter 02). Browser automation for end-to-end validation. Never trust agent claims — verify mechanically.

### 7. Model-Blaming

Attributing harness failures to model limitations. HumanLayer's harness engineering guide opens with: "The model is probably fine. It's just a skill issue." Teams waiting for GPT-6 are missing the point — smarter models just enable harder problems. Common harness failures misdiagnosed as model failures:
- Running full test suites flooded context with 4,000 lines of passing output, causing hallucinations
- Connecting dozens of MCP servers bloated system prompts
- Auto-generating CLAUDE.md hurt performance by 20%+

**Fix**: Start minimal. Add configuration reactively when agents fail at specific tasks. Don't pre-optimize.

### 8. Same-Model Judging

Using one model for planning, coding, and validation. Multiple practitioners confirm this produces worse results. Osmani: "Don't trust single-model judgment." The Goose ralph loop tutorial separates worker and reviewer into different model instances.

**Fix**: Use different models or at minimum different context windows for execution vs. review. The worker/reviewer separation with file-based handoff is a proven pattern.

### 9. Instruction Overload

Cramming too many rules into CLAUDE.md/AGENTS.md. HumanLayer's research: "As instruction count increases, instruction-following quality decreases uniformly." Frontier LLMs follow roughly 150-200 instructions reliably; Claude Code's system prompt already uses ~50, leaving ~100-150 for user instructions.

**Fix**: Target under 300 lines for CLAUDE.md (HumanLayer's own is <60 lines). Use CLAUDE.md as a router pointing to detailed docs, not a monolith. Never use it as a style guide — use deterministic linters instead. Don't auto-generate with `/init`.

### 10. Unreviewed PRs

Filing agent-generated code without personal review. Willison: "Don't file pull requests with code you haven't reviewed yourself... What value are you even providing?" Multiple small PRs outperform single massive ones.

**Fix**: Treat agent output as a first draft from a junior dev. If you cannot explain every line in the diff, it should not ship.

## The 70-80% Problem

Multiple independent sources converge on the same finding: AI agents get you 70-80% of the way, and the remaining 20-30% is disproportionately harder. This isn't new — it mirrors every previous "replace programming" technology (4GLs, visual coding, CASE tools, Rails). Token costs follow the inverse pattern: 80% of tokens are burned on the last 20% of the work.

The METR study adds a twist: experienced open-source developers were 19% *slower* with AI tools but *perceived* themselves as faster. The illusion of speed masks real slowdowns from debugging AI-introduced errors.

**Implication for agent loops**: Loops must be designed for the hard 20%, not the easy 80%. The verification layer, rollback mechanism, and decomposition strategy all exist to handle the cases where the agent can't one-shot the solution.

## The Complexity Ratchet

Agents remove the natural friction that keeps code complexity in check. When 300 lines can be generated in seconds, the brake on complexity disappears. HN practitioners: "AI-generated complexity fails the test of whether the next person who touches the code can understand it without asking."

Karpathy's autoresearch addresses this directly with a simplicity criterion: "A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it. A 0.001 improvement from deleting code? Definitely keep."

Agents given autonomy in loops also exhibit scope creep — one HN report describes an agent deploying "multi-cloud edge-deployed Kubernetes with Kafka" that nobody asked for. Spotify's LLM judge found scope creep to be the #1 trigger for session vetoes.

**Implication for ralph loops**: RALPH.md prompts should include explicit scope constraints. A `scope` frontmatter field listing editable files/directories would prevent the agent from wandering.

## The Trust Calibration Problem

AI assistance creates a false sense of security. Studies show AI-assisted code ships with 1.7x more bugs. The mechanism: developers review AI code less carefully than they review human code. "Having an AI Assistant lowers programmers' guards against buggy code."

This compounds in loops: each iteration's output becomes the next iteration's input. If iteration 3 introduces a subtle bug that passes tests, iterations 4-50 build on a faulty foundation.

**Implication for ralph loops**: Verification gates between iterations aren't optional — they're the only thing preventing compounding errors. The verification hierarchy (chapter 02) should be the minimum bar, not an aspirational feature.

## Practitioner-Validated Remedies

| Problem | Remedy | Source |
|---------|--------|--------|
| Context poisoning | Fresh context resets per iteration | Universal |
| Doom loops | Loop detection + steering injection after N identical calls | StrongDM Attractor |
| Cost blowups | Hard budget ceiling + iteration limit | Multiple |
| Comprehension debt | Fresh-context review (different model/window) | Osmani, Willison |
| Scope creep | Explicit scope constraints + LLM judge | Spotify Honk |
| Premature completion | Mechanical verification, never trust self-assessment | Anthropic |
| Instruction fade | Event-driven reminders + todo list recitation | OPENDEV paper |
| Context bloat | Output truncation (full to logs, abbreviated to LLM) | StrongDM Attractor |
| Over-engineering | Simplicity criterion in scoring | Karpathy |
| Cascading failures | Git revert (not reset) + crash recovery table | autoresearch variants |
