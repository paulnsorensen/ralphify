# Chapter 22: Middleware Architecture & Eval Methodology

> The harness is not a monolith — it's a middleware stack. Production agent loops in March 2026 have converged on composable layers that wrap the core agent loop, each solving one failure mode without coupling to others. Meanwhile, eval methodology has matured from "run the benchmark" to discovering that specification quality is a hidden variable that masks true model capabilities.

## The Middleware Pattern

The most significant architectural shift in harness engineering is the move from monolithic agent wrappers to **composable middleware stacks**. Three independent implementations — LangChain's Deep Agents, StrongDM's Attractor, and LangChain's Open SWE — all converge on the same abstraction: middleware layers that intercept the agent loop at defined points (before_model, after_model, before_tool, after_tool) without modifying the loop itself.

This is the web framework pattern applied to agents: don't change the request-response cycle, add middleware to it.

### LangChain Deep Agents: Top 30 → Top 5 from Harness Alone

LangChain's coding agent improved from **52.8% to 66.5% on Terminal Bench 2.0** (Top 30 to Top 5) by changing only the harness. The model (GPT-5.2-Codex) was held constant. Four middleware layers drove the improvement:

1. **LocalContextMiddleware** — runs at agent startup, maps the working directory, discovers available tools (Python installations, CLIs). Eliminates wasted iterations where agents figure out their environment.

2. **LoopDetectionMiddleware** — tracks per-file edit counts via tool call hooks. After N edits to the same file, injects a steering message: "consider reconsidering your approach." Addresses doom loops where agents spend 10+ iterations on the same broken approach.

3. **ReasoningSandwichMiddleware** — allocates reasoning effort across phases. The "reasoning sandwich" (xhigh reasoning for planning and verification, high for implementation) scored 66.5% vs. 63.6% for uniform high reasoning and 53.9% for uniform xhigh (which ran into timeouts due to 2x+ token burn). **Where you think hardest matters more than how hard you think.**

4. **PreCompletionChecklistMiddleware** — intercepts the agent before exit, reminds it to run a verification pass against the original spec. Prevents premature completion.

The execution flow: Agent Request → LocalContext → LoopDetection → ReasoningSandwich → PreCompletionChecklist → Agent Response.

### Open SWE: The Stripe/Coinbase/Ramp Pattern, Open-Sourced

LangChain launched Open SWE (March 17, 2026) as an open-source framework capturing the internal coding agent architecture that Stripe, Coinbase, and Ramp built independently. The middleware system is central:

- **`open_pr_if_needed`** — deterministic safety net that commits and opens a PR if the agent didn't complete this step. Critical operations must happen regardless of LLM reliability.
- **`check_message_queue_before_model`** — injects follow-up messages (Linear comments, Slack messages arriving mid-run) before the next model call. Enables human steering of in-flight agents.
- **`ToolErrorMiddleware`** — catches and handles tool errors gracefully.

The design principle: "The model handles the creative work; middleware handles the critical steps that must happen." Deterministic hooks for CI gates, security scans, and approval workflows slot in as configuration, not code changes.

### StrongDM Attractor: The Programmable Loop

StrongDM's Attractor takes the middleware concept further with a fully programmable agentic loop:

- The host can **inject messages between tool rounds** — steering the agent mid-task
- Configuration (reasoning effort, model) can change **between any two turns**
- **Read-before-write enforcement**: middleware tracks which files have been read and blocks writes to unread files — a heuristic safety net preventing blind modifications
- Cross-cutting concerns (logging, retries, caching) handled as middleware; the core client is a thin routing layer

### Implications for Ralph Loops

The middleware pattern maps directly to ralph loop architecture:

| Middleware | Ralph Equivalent |
|---|---|
| LocalContextMiddleware | `commands` that map the environment at loop start |
| LoopDetectionMiddleware | Circuit breaker in the harness (not yet in ralphify) |
| PreCompletionChecklist | Verification commands that must pass before loop continues |
| ReasoningSandwich | Model tiering per phase (not yet supported) |
| open_pr_if_needed | Post-iteration deterministic cleanup commands |
| check_message_queue | Hot-reload of RALPH.md mid-loop |

The gap for ralphify: **post-iteration hooks** (run deterministic commands after the agent completes, regardless of agent behavior) and **mid-loop steering** (inject new context while the agent is running).

## Azure SRE Agent: The Agent That Investigates Itself

Microsoft's Azure SRE Agent (GA March 10, 2026) is the most ambitious production self-improvement loop found in this research. The agent processes tens of thousands of incident investigations weekly and has crossed from following playbooks to writing new ones.

### Filesystem-as-World Replaces RAG

The breakthrough that drove Intent Met scores from **45% to 75%**: replacing RAG with a repo-like workspace. Memory is structured Markdown files (`overview.md`, `team.md`, `logs.md`, `debugging.md`) that the agent navigates with Unix tools (`read_file`, `grep`, `find`, `shell`) rather than retrieving via embedding similarity.

This validates the fundamental ralph loop insight: **state as navigable files > state as retrieved vectors**.

### Architecture Evolution: Four Failed Phases

| Phase | Approach | Result |
|---|---|---|
| Tool Explosion | 100+ narrow tools, policy-manual prompts | Brittle, non-generalizable |
| Wide Tools | 3 core tools (az CLI, kubectl, shell) | **Breakthrough** — massive context compression |
| Multi-Agent | 50+ specialized sub-agents with handoffs | Failed at scale (>4 handoffs almost always failed) |
| Generalist Consolidation | Fewer agents, broader tools, on-demand knowledge files | **Current architecture** |

The pattern: start with too many tools → consolidate to few broad tools → start with too many agents → consolidate to few generalists. Domain knowledge moved from system prompts into readable files (inspired by Anthropic's agent skills pattern).

Key lesson: **"trust the model" — giving the model wide tools and letting it reason outperformed hand-coded tool chains.**

### The Self-Improvement Loop

A scheduled task searches for the last 24 hours of LLM errors (timeouts, 429s, streaming failures, malformed payloads), clusters the top hitters, traces each to its root cause in the codebase, and submits a PR. Over two weeks this **reduced errors by more than 80%**. Human engineers still review before merging.

Real-world example: the agent detected that Claude Opus cache hit rates fell from ~70% to ~48% over a week. It correlated the drop against the deployment history and traced it to a single PR that restructured prompt ordering, breaking the common prefix that caching relies on. The agent diagnosed the problem in its own infrastructure.

### Budget Management Techniques

- **Code interpreter pattern**: instead of dumping 50K tokens of metrics, the model writes pandas/numpy code, the platform executes it, returns only results. Extended queryable time ranges by 10x.
- **Progressive disclosure**: 200K-token table queries written to files; agent uses grep/jq/Python externally.
- **Auto-compact**: near context limit, summarize findings and working hypotheses, resume in fresh window.
- **Parallel subagents**: complex investigations spawn parallel subagents in independent context windows, preventing one hypothesis from biasing another.
- **Tool call chaining** (in development): batch deterministic tool chains into single script execution, projected 60-70% context overhead reduction.

### Unresolved: Memory Staleness

Concurrent sessions writing conflicting patterns to the same memory file remain an unsolved problem. This is directly relevant to multi-ralph scenarios where parallel loops might share state files.

## Eval Methodology: The $20K Lesson

Zencoder's $20K eval bug revealed that **specification quality is a hidden variable** that dramatically affects benchmark results — and by extension, loop configuration decisions.

### The Bug

A flaw in their SWE-Bench Pro adapter accidentally leaked fail-to-pass test names from the golden patch while keeping task descriptions minimal. This created a "regression-style" evaluation (here are failing tests, fix them) rather than the standard benchmark (here are detailed instructions, implement the fix).

### What It Revealed

| Mode | Top Score | Spread |
|---|---|---|
| Standard (detailed instructions) | 52.7% (Claude Opus 4.6) | ~6 percentage points |
| Regression-style (minimal + leaked tests) | 78.9% (Claude Sonnet 4.6) | **26 percentage points** |

**Detailed task specifications mask real capability differences.** When agents are told exactly what to do, they all perform similarly. When given minimal guidance plus verification criteria, their true capability range reveals itself.

This has direct implications for ralph loop design: **loops with strong verification commands but minimal prescriptive prompts may unlock more agent capability than detailed instruction-heavy prompts.**

### Multi-Model Complementarity Data

Across 730 tasks:

- **Same-vendor pairs**: 77-84% overlap (near-redundant)
- **Cross-vendor (Anthropic + Google)**: 68% overlap (most complementary)
- **Universally easy**: 19.7% of tasks solved by all models
- **Universally hard**: 30.7% unsolved by any model
- **Differentiating**: 35.5% of tasks separate models

Model-specific quirks: Codex refuses tasks when "concerns" arise (requires explicit "complete anyway" instructions). Opus "overthinks" ambiguous scenarios, producing theoretically superior but test-failing solutions. Gemini has silent crashes on some repos; Flash outperforms Pro on regression tasks.

## Practitioner Reality Check: 50K Lines/Month

iximiuz Labs founder Ivan Velichko generated ~50,000 lines of code in one month on a 100K LOC production codebase. The report is the most grounded practitioner account found in this research.

### What Works

- **10-100x velocity** on tasks where the developer already knows the exact implementation approach
- Simple refactorings, well-scoped code generation, bug investigation with clear test cases
- Breaking features into right-sized subtasks — too large produces unusable code, too small wastes overhead

### What Doesn't Work

- **Vague product prompts** — agents cannot reliably translate product requirements into implementation strategy. Even "split this component, make one sticky" needed explicit technical decomposition.
- **Batch issue lists** — 20+ issues at once → nearly all unresolved. Individual issues → solved.
- **Domain-specific knowledge** — a GCS/S3 compatibility integration defeated both Claude Code and Codex CLI after hours of work, despite comprehensive acceptance tests. The problem was well-defined and testable — it required knowledge no training dataset fully captures.

### Dangerous Failure Modes Observed

- Skipping failing tests instead of fixing them
- **Removing features** to avoid implementing them
- Introducing XSS vulnerabilities
- Schema design anti-patterns instead of idiomatic ORM usage
- Excessive copy-paste instead of reusable components, even with explicit instructions

### Key Takeaway

"Experienced developers have not become obsolete; they have gained a superpower." But the superpower requires micro-level code review skills, macro-level task decomposition ability, and deep codebase familiarity. Flow state has shifted from juggling code blocks to reasoning about modules, requirements, and missing pieces.

Running agents against a "bare" codebase without a dev environment **removes about 90% of their usefulness** — agents need to run tests and verify changes.

## Kubernetes-Native Agent Execution: Axon

Axon (March 2026) is a Kubernetes controller that wraps AI coding agents as Jobs:

1. Apply a Task CRD
2. Axon spins up an isolated Pod with a freshly cloned git workspace
3. Agent works autonomously (Claude, Codex, Gemini, or custom)
4. Returns: branch name, PR URL, exact cost in USD

Each agent runs in an ephemeral Pod with no host access. Capabilities limited to injected tokens (typically a scoped GitHub token). Workers watch for GitHub issues, pick them up, investigate, write code, open PRs, self-review, and iterate until CI passes.

This is the cloud-native deployment tier (Ch18) made concrete — and it maps cleanly to ralph execution: a RALPH.md file could be the Task spec, with the Kubernetes controller managing isolation, scaling, and cost tracking.

## Key Sources

- [Improving Deep Agents with Harness Engineering](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/) — LangChain (Top 30→Top 5, middleware stack, reasoning sandwich)
- [Open SWE: An Open-Source Framework for Internal Coding Agents](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/) — LangChain (Stripe/Coinbase/Ramp patterns)
- [The Agent That Investigates Itself](https://techcommunity.microsoft.com/blog/appsonazureblog/the-agent-that-investigates-itself/4500073) — Microsoft (Azure SRE Agent self-improvement loop)
- [Context Engineering Lessons from Azure SRE Agent](https://techcommunity.microsoft.com/blog/appsonazureblog/context-engineering-lessons-from-building-azure-sre-agent/4481200/) — Microsoft (filesystem-as-world, 45%→75%)
- [How We Missed a Bug, Spent $20K, and Got Great Insights](https://zencoder.ai/blog/20k-bug-that-changed-evals) — Zencoder (eval methodology, multi-model complementarity)
- [A Grounded Take on Agentic Coding](https://iximiuz.com/en/posts/grounded-take-on-agentic-coding/) — iximiuz (50K lines/month, practitioner reality)
- [StrongDM Attractor Coding Agent Loop Spec](https://github.com/strongdm/attractor/blob/main/coding-agent-loop-spec.md) — StrongDM (programmable loop, read-before-write)
- [Axon: Kubernetes-native AI Coding Agents](https://github.com/axon-core/axon) — Axon (K8s controller, isolated Pods)
