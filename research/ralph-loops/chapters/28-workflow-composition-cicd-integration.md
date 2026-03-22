# Chapter 28: Workflow Composition, CI/CD Integration & Agent Fleet Patterns

The agent orchestration landscape in March 2026 has bifurcated into two camps: heavyweight frameworks (LangGraph, CrewAI, AutoGen) that manage state in memory and databases, and lightweight harness-first approaches (ralph loops, Claude Code /loop, Codex) that use git + filesystem. The emerging consensus from practitioners: **start with single agents and strong prompts; add tools before adding agents; graduate to multi-agent only when facing clear limitations.** The 40% predicted cancellation rate for agentic AI projects (Deloitte) is driven almost entirely by premature orchestration complexity.

## Workflow Composition Taxonomy

Google ADK formalized eight core multi-agent patterns, providing the first comprehensive taxonomy:

| Pattern | Description | When to Use |
|---------|-------------|-------------|
| Sequential | Fixed chain of agents | Predictable multi-step pipelines |
| Coordinator/Dispatcher | Central router → specialists | Heterogeneous task types |
| Parallel Fan-Out/Gather | Concurrent → aggregate | Independent subtasks |
| Hierarchical Decomposition | Recursive breakdown | Complex nested tasks |
| Generator/Critic | Produce → evaluate | Quality-sensitive output |
| Iterative Refinement | Loop until satisfactory | Convergent optimization |
| Human-in-the-Loop | Agent pauses for approval | High-stakes decisions |
| Composite | Hybrid of the above | Real-world systems |

Ralph loops implement the **Iterative Refinement** pattern with external verification gates and forced context rotation — the key differentiator from framework-native loops that accumulate context. Production systems are typically hybrid: e.g., a sequential pipeline with a hierarchical step in the middle, or a single agent routing into a specialist swarm.

## CI/CD Integration: Agents in the Pipeline

The most actionable new pattern is agents embedded directly in CI/CD pipelines. Three independent implementations have converged:

### Elastic: Claude Code in Buildkite

Over one month (limited to 45% of dependencies): Claude fixed **24 broken PRs**, made **22 commits**, and **saved approximately 20 days of active engineering work**. Key findings:

- "Tuning AI agents' behaviour marks the difference between failure and success" — updating CLAUDE.md with team guidelines transformed performance
- "Never commit AI work without human supervision" — auto-merge explicitly disabled
- The hybrid pattern: deterministic pre-processing → AI agent stage → deterministic post-processing

This is structurally identical to a ralph loop: CLAUDE.md as spec + iterative fix cycle + human review gate.

### Red Hat Cicaddy: Pipeline-Native Agent Framework

Cicaddy treats CI as the scheduling infrastructure for agents, not a separate "agentic platform":

- **One-shot execution with multi-turn reasoning**: single pipeline job, agent iterates 10-30+ inference turns using ReAct pattern within one CI step
- **Three agent types**: MR Agent (merge requests), Branch Agent (push events), Task Agent (scheduled/manual)
- **MCP as tool interface**: transforms integration from code to configuration
- **Deterministic sandwich**: pre/post-processing is deterministic, AI reasoning fills the middle

Critical insight: *"Agentic AI workflows don't require a dedicated agentic platform — engineering teams with established CI/CD pipelines already have the necessary scheduling system and execution environment."*

### GitHub Agentic Workflows ("Continuous AI")

GitHub compiles Markdown+YAML frontmatter to Actions lock files. AI agents interpret natural-language instructions for event-triggered or scheduled jobs. Read-only by default; PRs never auto-merged. GitHub positions this as "Continuous AI" — agent loops as CI/CD extension, not replacement.

**Implication for ralphify**: `ralph run` in a CI build step is the minimal integration. RALPH.md is already YAML frontmatter + Markdown — the same format GitHub uses for agentic workflows. A `ralph ci` command that outputs structured JSON (pass/fail, cost, iteration count) would make ralph loops first-class CI citizens.

## Typed Schemas at Handoff Points

GitHub's engineering blog identifies the #1 cause of multi-agent failure: **context loss at handoff points**. The fix: typed schemas.

- "Natural language is messy. Typed schemas make it reliable."
- "Treat agents like code, not chat interfaces."
- "Typed schemas are table stakes in multi-agent workflows. Without them, nothing else works."
- Most "agent failures" are actually orchestration and context-transfer issues at handoff points.

Ralph's YAML frontmatter (`agent`, `commands`, `args`) is already a typed schema for the agent interface. The `{{ commands.<name> }}` placeholder system enforces structured data flow. The HANDOFF.md pattern (BSWEN, March 21, 2026) — passing state through structured files rather than relying on agents to reconstruct context — is exactly what ralph's command system does: structured state injection at each iteration boundary.

## Agent Fleet Management: Scale vs. Complexity

The market data tells a cautionary tale:

| Metric | Value | Source |
|--------|-------|--------|
| Autonomous agent market | $8.5B (2026), $35B (2030 est.) | Deloitte |
| Projects potentially cancelled by 2027 | 40% | Deloitte |
| IT leaders citing complexity concern | 86% | Salesforce |
| Mature basic automation | 80% of leaders | Salesforce |
| Mature AI agents | 28% of leaders | Salesforce |
| Multi-agent adoption surge expected | 67% by 2027 | Salesforce |

**Shipyard's verdict**: "Multi-agent workflows aren't for everyone and don't make sense for 95% of agent-assisted development tasks."

Three Claude Code multi-agent orchestrators have emerged:
- **Agent Teams** (official): hierarchical with peer communication, team lead + teammates in separate context windows
- **Gas Town** (Steve Yegge): "Kubernetes for AI agents" — mayor agent decomposes tasks, spawns designated agents
- **Multiclaude**: supervisor assigns to subagents with optional code review gates, Brownian ratchet philosophy

Ralph's `manager.py` (concurrent runs via threads) is already a lightweight fleet orchestrator. The market data confirms that complexity is the enemy — ralph's minimalist approach (a directory with a RALPH.md file, no project-level config) directly addresses the "more complexity than value" concern.

## Framework Landscape (LangGraph vs. CrewAI vs. AutoGen)

The framework comparison data provides context for ralphify's positioning:

- **LangGraph**: Graph-based state machines, durable execution, human-in-the-loop. Most battle-tested. 2.2x faster than CrewAI. Used by Klarna, Replit, Elastic.
- **CrewAI**: Role-based teams, fastest setup, growing A2A support. Less mature monitoring.
- **AutoGen**: Microsoft shifted to maintenance mode in favor of broader Microsoft Agent Framework. Best for conversational multi-agent.
- **Selection factor**: "Framework architecture matters most for tool execution patterns and context management, not agent handoffs."
- **2026 differentiator**: how frameworks model time, memory, and failure — not basic tool calling.
- **LangGraph Skills pattern**: progressive disclosure of specialized prompts — closest to how ralph loads RALPH.md with frontmatter-declared commands. Subagents require 4 LLM calls per request (extra aggregation); Skills/Handoffs save 40% tokens.

**Ralphify occupies a different niche**: it's a harness, not a framework. Where LangGraph/CrewAI manage state in memory/databases, ralph uses git + filesystem. This is a feature: ralph loops are framework-free, agent-agnostic, and composable via shell primitives.

## Fresh Practitioner Metrics (March 2026)

New data points crystallize the production reality of agent loops:

**IntelligentTools — 47 Commits While I Slept**: 8-hour overnight session (11PM-7AM), 8 files refactored (~1,200 lines), test coverage 62%→87%, cost **$23.14**, 80% success rate across 5 production tasks. Failures: external service downtime caused infinite loops; subjective goals produced unfocused 50-iteration runs. Key takeaway: *"Tests are non-negotiable — Ralph requires measurable success criteria."*

**Shopify CEO replication of Karpathy loop**: Tobias Lutke ran 37 experiments overnight, achieved 19% performance gain. Karpathy: "all LLM frontier labs will do this. It's the final boss battle." Vision: multiple agents exploring in parallel, "emulating a research community."

**Hash-based line identification (blog.can.ac)**: Replacing traditional diff formats with hash-based line IDs yielded **5-14 percentage point gains** on coding benchmarks with ~20% token reduction. Key HN comment: *"Treating 'the AI' as a complete system — combining the LLM with its harness — reveals substantial optimization potential."* Anthropic's own Claude Code nearly doubled Opus performance through harness changes alone.

**Alibaba Cloud's ReAct→Ralph comparison**: ReAct = internal single-session loop with context rot; Ralph Loop = external forced-iteration with cross-session state via "Stop Hook" (intercept exit, reinject task prompt). Token costs: $50-150 for large tasks. Production recommendation: 5-50 iteration limits depending on scope.

**Context Harness (HN, Feb 27)**: Rust-based local-first context engine — SQLite + FTS5 hybrid search, MCP-compatible, Lua extensibility. WAL mode for concurrent read/write. Represents the emerging infrastructure layer for persistent cross-loop memory.

## DAG Orchestration: The Next Frontier

The 2026 landscape bridges traditional data pipeline tools (Airflow, Dagster, Flyte) with agent-native DAG frameworks (LangGraph, Lyzr):

- DAGs provide: explicit dependencies, parallel execution, built-in retries/fallbacks, scalability for hundreds of workflows
- Hybrid recommended: "Use Airflow for fixed pipelines; let agents branch only where data demands it"
- Lyzr treats DAGs as first-class orchestration primitives with agent nodes

**Implication for ralphify**: Ralph's current model is a single-node loop. The DAG pattern suggests a natural extension: multi-ralph orchestration where RALPH.md files declare dependencies on other ralphs, enabling fan-out/gather patterns. The `manager.py` concurrent runs feature already moves in this direction. A `depends_on` frontmatter field would formalize inter-ralph dependencies.

## Cursor Automations: Event-Triggered Agents

Cursor's "Automations" feature (March 2026) introduces always-on agents triggered by external events:

- Triggers: Slack messages, Linear issues, GitHub events, PagerDuty alerts, webhooks, timers
- Background agents run in isolated Ubuntu VMs with internet access
- Agentic Security Review: thousands of PRs scanned, hundreds of issues prevented

This represents a different paradigm from ralph loops: **event-triggered (reactive)** vs **spec-driven (proactive)**. Ralph loops define what to do and iterate until done; Cursor Automations respond to external events. Combined with Claude Code Channels (Ch27), the distinction is blurring — ralph loops can now receive events mid-iteration.

## Implications for Ralphify

1. **`ralph ci` command**: output structured JSON (pass/fail, cost, iterations, files changed) for CI integration. The Elastic and Red Hat patterns prove that CI is the natural scheduling infrastructure.

2. **`depends_on` frontmatter field**: enable inter-ralph dependencies for DAG-style orchestration. `manager.py` already supports concurrent execution — adding dependency resolution would unlock pipeline patterns.

3. **Typed command output schemas**: the #1 multi-agent failure is context loss at handoffs. RALPH.md commands should optionally declare expected output format to catch format drift early.

4. **The anti-complexity positioning**: 40% of agentic AI projects may be cancelled due to complexity. Ralphify's value proposition is the opposite — a directory with a RALPH.md file, no framework, no platform, no config. This is a feature, not a limitation.

5. **Event-triggered ralphs**: Claude Code Channels + CI webhooks enable reactive ralph loops. A `triggers` frontmatter field could declare what events start a ralph run.

## Sources

- [CI/CD Pipelines with Claude AI (Elastic)](https://www.elastic.co/search-labs/blog/ci-pipelines-claude-ai-agent) — 24 PRs fixed, 20 days saved, CLAUDE.md as team guidelines
- [Cicaddy: Agentic Workflows in CI (Red Hat)](https://developers.redhat.com/articles/2026/03/12/how-develop-agentic-workflows-ci-pipeline-cicaddy) — pipeline-native agents, MCP as tool interface
- [Multi-Agent Workflows Often Fail (GitHub)](https://github.blog/ai-and-ml/generative-ai/multi-agent-workflows-often-fail-heres-how-to-engineer-ones-that-dont/) — typed schemas, action schemas, MCP
- [Developer's Guide to Multi-Agent Patterns in ADK (Google)](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) — 8 core patterns
- [Deloitte AI Agent Orchestration Predictions](https://www.deloitte.com/us/en/insights/industry/technology/technology-media-and-telecom-predictions/2026/ai-agent-orchestration.html) — $8.5B market, 40% cancellation
- [Ralph Loop + Claude Code: 47 Commits (IntelligentTools)](https://intelligenttools.co/blog/claude-code-unsupervised-8-hours-ralph-loop) — $23/night, 80% success
- [Improving 15 LLMs — Only the Harness Changed (blog.can.ac)](https://news.ycombinator.com/item?id=46988596) — hash-based line ID, +5-14pp
- [Choosing the Right Multi-Agent Architecture (LangChain)](https://blog.langchain.com/choosing-the-right-multi-agent-architecture/) — Subagents vs Skills vs Handoffs vs Router
- [Cursor Automations (TechCrunch)](https://techcrunch.com/2026/03/05/cursor-is-rolling-out-a-new-system-for-agentic-coding/) — event-triggered agents in VMs
- [Shipyard: Multi-Agent for Claude Code](https://shipyard.build/blog/claude-code-multi-agent/) — Agent Teams, Gas Town, Multiclaude
- [The Karpathy Loop: 700 Experiments (Fortune)](https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/) — Shopify CEO replication
- [From ReAct to Ralph Loop (Alibaba Cloud)](https://www.alibabacloud.com/blog/from-react-to-ralph-loop-a-continuous-iteration-paradigm-for-ai-agents_602799) — ReAct vs Ralph comparison
- [Context Harness (HN)](https://news.ycombinator.com/item?id=47162581) — Rust/SQLite/FTS5 context engine
- [Agent Task Handoff (BSWEN)](https://docs.bswen.com/blog/2026-03-21-agent-task-handoff-coordination/) — HANDOFF.md files for state transfer
