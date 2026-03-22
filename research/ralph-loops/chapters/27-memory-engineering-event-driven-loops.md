# Practical Memory Engineering & Event-Driven Loop Architecture

> Ch19 established the four competing memory architectures and their tradeoffs. This chapter goes deeper: how practitioners actually implement cross-session learning, why most self-improvement attempts fail, and how event-driven primitives (Claude Code Channels) are reshaping what agent loops can react to.

## The Knowing-Doing Gap: Why Self-Improvement Fails

ngrok's BMO coding agent is the most honest post-mortem on agent self-improvement. Across ~100 sessions, BMO built 11 new tools and 7 skills — but only 2 tools were built during active work. The rest were deferred to "maintenance passes" that rarely happened.

**The four-loop system and where each broke**:
1. **Build It Now** — hot-reload new tools on first friction. In practice, agents deferred nearly everything.
2. **Active Learning Capture** — log corrections and preferences in real time. The Learning Event Capture skill was used only **twice across 60+ sessions** despite detailed instructions.
3. **Self-Reflection** — structured end-of-session analysis answering three questions (What went well? What was slow? What next?). **This worked every time** — structured triggers with time/place bounds execute reliably.
4. **Battery Change** — comprehensive 10-session analysis. Never produced the compound improvement expected.

The critical finding: **creating an OPPORTUNITIES.md bucket paradoxically increased procrastination.** Adding items to the opportunities file became the path of least resistance — the agent satisfied its "improve something" directive without actually improving anything. This isn't laziness; it's probabilistic behavior following training data patterns where logging is more common than acting.

**Design principle for ralph loops**: Structured triggers (session-end reflections, iteration-boundary consolidation) execute reliably. Vigilance-based behaviors (watch for improvement opportunities, build tools on first friction) fail consistently. Design memory systems around **boundary events**, not continuous monitoring.

## Claude Code's Two-Tier Memory Architecture

The most mature production memory system for coding agents uses a stratified approach:

**Tier 1 (Automatic — CLAUDE.md)**:
- ~150 lines, loaded on every session start
- Ranked by confidence × access frequency
- Budget system: 25 lines architecture, 25 decisions, 25 patterns, 20 gotchas, 30 progress, 15 context
- Survives `/compact` — always in context
- "80% of sessions need only Tier 1"

**Tier 2 (On-Demand — .memory/state.json)**:
- Unlimited storage, accessible via MCP tools (`memory_search`, `memory_related`, `memory_ask`)
- Deeper recall for the 20% of sessions that need it
- Haiku synthesizes across top 30 results for natural-language queries

**Capture pipeline**: Three hooks extract knowledge from conversation transcripts:
- **Stop** — after each response
- **PreCompact** — before context compaction
- **SessionEnd** — at session termination

Content exceeding 6,000 chars is chunked. Haiku performs structured extraction with deduplication via Jaccard similarity (>60% overlap triggers supersession of older memory). LLM consolidation runs every 10 extractions or when memories exceed 80 active entries.

**Memory decay**: Permanent memories (architecture, decisions, patterns, gotchas) never decay. Progress has a 7-day half-life. Context has a 30-day half-life. Memories below 0.3 confidence are excluded from Tier 1 but remain searchable in Tier 2.

**Cost**: ~$0.001 per extraction, $0.05–$0.10 daily. No external vector databases or embedding APIs required.

**Key insight for ralph loops**: This validates that a "memory ralph" — a periodic consolidation loop that reads recent progress, extracts patterns, and updates a knowledge file — is architecturally sound without vector infrastructure. The decay model (permanent vs. half-life) is directly implementable as a RALPH.md command that ages entries.

## The Three-Layer Practitioner Consensus

A consensus is emerging on how to structure agent memory for coding contexts:

1. **Semantic Layer** — "what are we building and why" (CLAUDE.md, RALPH.md prompt body)
2. **Task Tracking Layer** — structured storage combining "Jira meets Git" with metadata on blockers, dependencies, and decision paths
3. **Version Control Layer** — Git handles historical records

The core principle: **separating understanding from tracking from versioning reduces cognitive load on the agent.** Practitioners report that this separation produces "something closer to judgment rather than just following rules."

Notably, this directly maps to ralphify's existing architecture:
- Semantic layer = RALPH.md prompt body
- Task tracking = `{{ commands.tasks }}` loading a tasks.md file
- Version control = Git (already the state backend)

## New Memory Frameworks (March 2026)

| Framework | Approach | Key Result | Vector DB? |
|-----------|----------|------------|------------|
| Google Always On Memory Agent | SQLite + 3-sub-agent LLM consolidation | Works for thousands of facts; drift risk | No |
| MemOS v2.0 (Stardust) | MemCubes with provenance/versioning | 159% improvement in temporal reasoning vs OpenAI's global memory | Optional |
| SimpleMem | Three-stage compression pipeline | 30x token reduction, 43.24 F1 on LoCoMo (vs Mem0's 34.20) | No |
| Mastra Observational Memory | Observer + Reflector background agents | 84.23% accuracy, 3-40x compression | No |
| AutoMem | FalkorDB graph + Qdrant vector | Dual-DB local memory for Claude Code | Yes |
| OpenMemory (CaviraOSS) | Local SQL-native + temporal graphs | Zero-config MCP endpoint for Claude/Copilot/Codex | No |
| Hindsight | Institutional memory | 91.4% on LongMemEval vs Mem0's 49.0% | Optional |

**Trend**: The leading frameworks are moving **away** from vector databases toward structured storage (SQLite, markdown) with LLM-powered consolidation. This validates ralph loops' filesystem-first design. The vector DB becomes optional infrastructure for scale, not a prerequisite.

## Restorable Compression in Practice

Factory.ai's production implementation reveals the mechanics:

**Two-threshold system**:
- **T_max** ("fill line") — triggers compression when total context reaches this count
- **T_retained** ("drain line") — max tokens preserved post-compression, always lower than T_max
- Narrow gap = frequent compression + better preservation; wide gap = less frequent + more aggressive truncation

**What survives**:
- Session intent and user objectives
- High-level action play-by-play (not details)
- Artifact trail (file modifications, test results)
- **Breadcrumbs** — file paths, function names, and key identifiers the agent can query to re-access prior outputs

**Critical principle**: "Minimize tokens per task, not per request." Over-compression backfires when agents must repeatedly re-fetch information in iterative workflows, offsetting token savings through extra inference calls.

**Direction**: Moving from reactive compression ("compress when forced") to proactive memory management at natural breakpoints — agents recognizing completion points and self-directing compression. This maps to ralph loop iteration boundaries, where each iteration is a natural compression point.

The academic formalization comes from **Memex(RL)**: separating a compact in-context indexed summary from full-fidelity artifacts stored externally under stable indices. Pointer-heavy index maps that remain usable later, combined with selective retrieval, significantly improve long-horizon returns.

**Ralph loop implementation**: Commands already implement restorable compression by design. `{{ commands.recent_changes }}` re-derives state rather than relying on a summary. The lesson: prefer commands that query current state over static progress files that accumulate stale summaries.

## Claude Code Channels: Event-Driven Loop Architecture

Claude Code Channels (research preview, v2.1.80+, March 2026) introduce a fundamentally new primitive for agent loops: **push events into a running session from external sources**.

**What channels are**: An MCP server that pushes events into a running Claude Code session. Events arrive as `<channel source="name">` elements in the agent's context. The agent reads the event and can reply back through the same channel — two-way communication.

**Currently supported**: Telegram, Discord (via plugins), with a `fakechat` localhost demo. Custom channels can be built via the Channels Reference API.

**How it changes loop architecture**:

Traditional ralph loop: `run commands → assemble prompt → pipe to agent → repeat on timer`

Event-driven ralph loop: `run commands → assemble prompt → pipe to agent → react to external events → repeat`

**Key use cases**:
1. **CI webhook receiver** — CI results push into the running session; Claude sees test failures in context and can immediately react
2. **Chat bridge** — ask Claude from Telegram/Discord while it's working on your codebase; the answer comes back in the same chat
3. **Monitoring alerts** — production errors arrive where Claude has your files open and remembers what you were debugging
4. **Deploy pipeline events** — staging deploys complete, the agent gets notified and can verify

**Security model**: Sender allowlists — only paired accounts can push messages. Being in `.mcp.json` isn't enough; a server must also be named in `--channels`.

**Limitation**: Events only arrive while the session is open. For always-on setups, Claude runs in a background process or persistent terminal. If a permission prompt is hit while the user is away, the session pauses.

**Implications for ralph loops**: This enables a new pattern — the **reactive ralph** — where the loop doesn't just run on a timer but also responds to external signals. A ralph that monitors CI, reacts to failures, and pushes fixes could operate as a continuous integration agent rather than a batch processor. The `--channels` flag effectively turns Claude Code from a request-response tool into an event-driven agent.

## Guardrails Bloat: The Memory Scaling Problem

As agents accumulate learning across sessions, the guardrails/rules file grows. Practitioner strategies for preventing bloat:

1. **Rule count caps** — hard limit (e.g., 30 rules). Adding a new rule requires removing or merging an existing one.
2. **Expiration dates** — rules tagged with `added: 2025-01-15`; cleanup pass removes rules older than N days unless marked permanent.
3. **Categorization** — group by domain (testing, git, style, architecture) with per-category limits. Makes contradictions easier to spot.
4. **Periodic human review** — most common approach, typically monthly.
5. **Severity tiers** — critical (security, data loss) vs. preferences. Under context pressure, drop preferences first.
6. **Cleanup agent** — a dedicated agent that reads all rules, identifies contradictions, merges duplicates, and proposes removals (the "gardener" pattern from Ch12).

The Claude Code memory system's budget allocation (25 lines for architecture, 25 for decisions, etc.) is the first automated approach to guardrails scaling. By assigning fixed budgets per category, it structurally prevents any single category from consuming the full context allocation.

**For ralph loops**: A `guardrails.md` file loaded via `{{ commands.guardrails }}` should include a header noting the maximum rule count and requiring the agent to consolidate when adding new rules. The "cleanup ralph" pattern (Ch12) is the automated solution.

## Implications for Ralphify

1. **The "memory ralph" is validated as architecturally sound.** Google's Always On Memory Agent, Claude Code's two-tier system, and SimpleMem all prove that structured storage + periodic LLM consolidation works without vector infrastructure. A cookbook recipe for a memory ralph that consolidates recent progress into a knowledge file is ready to write.

2. **Boundary-triggered learning beats vigilance-based learning.** ngrok's BMO proved that structured triggers (end-of-session, every-N-iterations) execute reliably while "always watch for improvements" fails. Ralph loops should consolidate at iteration boundaries, not continuously.

3. **Commands are restorable compression by design.** `{{ commands.X }}` re-derives state each iteration — the pattern Factory.ai and Memex(RL) describe as optimal. Ralph authors should prefer commands that query current state over static files that accumulate stale summaries.

4. **Claude Code Channels enable reactive ralphs.** The event-driven push model (CI webhooks, chat bridges, monitoring alerts arriving in-session) creates a new loop pattern: the reactive ralph that both runs on a schedule AND responds to external events. This could be a framework feature — `channels` field in RALPH.md frontmatter declaring event sources.

5. **Memory decay is a feature, not a bug.** Claude Code's half-life model (permanent architecture decisions, 7-day progress decay, 30-day context decay) should inform ralph state file design. Progress files should be periodically consolidated, not infinitely appended.

6. **Guardrails need structural scaling limits.** Fixed budgets per category (Claude Code's approach) or hard rule count caps prevent the inevitable bloat from agent-accumulated learning. The `ralph new` template should include a max-rules header in guardrails.md.
