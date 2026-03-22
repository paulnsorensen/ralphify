# Autonomous Agent Loops & Harness Engineering: State of the Art (March 2026)

> The field has converged on a core architecture: iterative loops with fresh context per iteration, state persisted in files and git, and verification gates between cycles. The "ralph loop" pattern — named after the bash-loop technique popularized in mid-2025 — is now mainstream, with Karpathy's autoresearch, Meta's REA, Spotify's Honk, and OpenAI's Codex all implementing variants. The ecosystem is large (30+ implementations, 500+ skills, 12K+ stars on skill directories) but operationally immature — cost blowups, undetected doom loops, and missing observability remain common. The key differentiator between amateur and expert harness engineering is the quality of the verification layer and the state management strategy. The fundamental insight: fix the harness, not the output — every prompt improvement benefits all future iterations, creating a flywheel.

## Key Insights

1. **Fresh context per iteration, state in files and git.** Every major system resets context each cycle. State lives in files, not chat memory — the four recurring state files are: specification (frozen), progress log (append-only), task list (shrinking), knowledge base (growing). Git commits serve as checkpoints with revert-on-failure. Above 60% context utilization, quality degrades measurably; intentional compaction (write progress to file, restart) is the fix. Larger windows make poisoning *worse*, not better.

2. **The verification layer is the whole game — probabilistic inside, deterministic at edges.** Spotify's LLM-judge vetoes 25% of sessions; Karpathy's scalar metric auto-reverts bad experiments. Without strong verification, agents drift. The design principle: commands (deterministic) evaluate; prompts (probabilistic) generate. Tests written by humans, implementations by agents. The best systems layer deterministic checks with LLM evaluation.

3. **Three primitives define a loop: editable asset, measurable metric, time-boxed cycle.** Karpathy's autoresearch distilled this to 630 lines running 700 experiments in 2 days. When all three are clear, reliability is high. For async workflows, hibernate-and-wake (Meta's REA) outperforms polling — shut down between jobs, resume when results are ready.

4. **One item per loop, measured in actions not time.** Every practitioner system limits each iteration to a single task. Batching causes drift. Spotify's #1 veto trigger is scope creep. SWE-Bench Pro confirms: multi-file coordination drops below 25% success vs. 70%+ for single-issue tasks. Successful agents complete tasks in 3-7 meaningful actions; beyond 15, success probability drops sharply — action count is a better circuit breaker signal than wall clock time.

5. **Three-phase prompt architecture (research→plan→implement) is the validated workflow.** Each phase gets a fresh context window loading only the previous phase's artifact. Independently converged on by HumanLayer, Anthropic, and Test Double.

6. **Cost control requires continuous budget awareness, not just hard limits.** Unbounded autonomy produces $47K incidents. Google's BATS framework surfaces real-time resource availability inside the agent's reasoning loop — agents that see their remaining budget make qualitatively different decisions. MCP servers (Agent Budget Guard) let agents track their own spending. Combined with per-task budgets, prompt caching (~90% input cost reduction), and tiered model routing, practitioners achieve 60-80% cost cuts. Hard ceilings are necessary but insufficient; continuous signals enable smarter execution.

7. **Design for the hard 20%: real productivity gains are 8-13%, not 50%.** AI agents hit the same ceiling as every previous "replace programming" technology. Thoughtworks' grounded calculation: ~40% of time is coding × ~60% AI-useful × ~55% faster = 8-13% net. Code churn doubled, refactoring dropped from 25% to under 10%. The last 20% costs 80% of the tokens — loops must be designed for this reality, not marketing claims.

8. **Multi-agent orchestration works for independent tasks, fails for coordination.** Cursor's planner-worker-judge architecture scales to 1M+ lines across hundreds of agents — but only because workers are fully independent. Flat coordination and optimistic concurrency both failed; role-based hierarchy with 3-5 parallel worktrees is the practical ceiling. Shared-state coordination is fragile and 4-15x more expensive.

9. **Trust scales through micro-interactions, but greater autonomy demands tighter constraints.** Anthropic's data: auto-approve rises from 20% to 40% over 750 sessions. Experienced users interrupt *more*, not less. One failure erases weeks of confidence (GitLab). Counter-intuitively, strict dependency flows and deterministic guardrails enable more agent freedom — hooks on every tool call, file write, and commit make guardrails unavoidable. Agentic coding is XP rediscovered: when agents generate 10-100x more code, CI, strong typing, and architecture tests become non-negotiable.

10. **Test the harness, not the agent output.** Block's record/playback pattern captures real LLM interactions to JSON, then replays deterministically — testing harness logic without burning tokens. LangChain improved from Top 30 to Top 5 on Terminal Bench by changing only the harness. Live LLM tests never run in CI: "too expensive, too slow, and too flaky."

11. **Build your harness to be rippable — permanent layers vs. temporary scaffolding.** Vercel removed 80% of agent tools and got better results. Manus refactored their harness 5x in 6 months. Permanent: context engineering, architectural constraints, safety boundaries. Temporary: reasoning optimization, loop detection, planning decomposition. Before adding middleware, ask: "Will I want to remove this when the next model ships?"

12. **Entropy management is the third pillar of harness engineering.** Agent-generated codebases accumulate documentation drift, convention divergence, and dead code. OpenAI spent every Friday cleaning "AI slop" until they automated it with periodic garbage-collection agents that scan for constraint violations and open targeted refactoring PRs. The "cleanup ralph" is the operational complement to the "development ralph." CodeScene's data confirms the inverse: Code Health 9.5+ is the threshold for optimal agent performance — agents fail more and burn excess tokens on unhealthy codebases.

13. **Completion promise gating replaces subjective self-assessment.** Machine-verifiable exit markers (`<promise>COMPLETE</promise>`) combined with stop hooks prevent premature loop exit. The agent exits only when external verification passes — not when it *thinks* it's done. This is the architectural fix for the fundamental weakness in ReAct-style self-assessment.

14. **MCP servers extend the harness, not the loop.** 5,000+ MCP servers and 97M monthly SDK downloads have created an infrastructure layer for agent loops — debugging (Deebo), profiling (CodSpeed), live docs (Context7), cost tracking (Budget Guard), browser testing (Playwright). But tool definitions consume up to 72% of context window; dynamic tool loading (85% token reduction via Anthropic's Tool Search) is essential. Start with 3-5 high-value servers, not 50.

15. **Context engineering replaces prompt engineering.** Context is a finite, depletable resource — the goal is "the smallest set of high-signal tokens that maximize likelihood of desired outcome." Preference order: raw > compaction > summarization. Context rot degrades output after 20-30 exchanges; fresh-context-per-iteration is the architectural fix. Output redirection (`> run.log 2>&1` then `grep`) prevents context flooding — the single most impactful reliability technique. Specification files have a ~150-200 instruction ceiling; keep CLAUDE.md under 300 lines as a router, not a monolith. Architecture documentation yields 40% fewer errors and 55% faster completion.

16. **Agent throughput exceeds human review capacity.** The new bottleneck is human attention, not agent speed. 78% of Claude Code sessions involve multi-file edits with 47 tool calls. Intent-failure detection — agents that follow rules but miss product intent — is the hardest gap. Agents can pass all tests while building the wrong thing.

17. **Structured loop debugging: fingerprinting + failure taxonomy.** Loop fingerprinting (track tool call + result hash; 3+ repeats = stuck) detects stuck agents without LLM calls — deterministic, zero-cost, production-proven. Map failures to actions: non-retryable → STOP, rate limits → bounded RETRY, transient → ESCALATE. Microsoft's AgentRx adds a 9-category failure taxonomy (plan adherence, hallucination, invalid invocation, misinterpretation, intent misalignment, under-specification, unsupported intent, guardrails, system failure) with +23.6% better failure localization. Don't guess why a loop failed — classify it.

18. **Half of all automated loop remediation is ineffective.** Boucle's 220-loop empirical study: only 6 of 12 automated responses reduced their target signals. Feedback amplification is real — a silence detector created a 13.3x amplification loop, worsening the problem it aimed to fix. Test your monitoring infrastructure for second-order effects. Agent self-reporting drifts; mechanical signal counting (file changes, error repetitions, output volume) is the reliable alternative.

19. **Six practitioner cookbook patterns have converged independently.** PRD-driven feature loops (3 implementations), two-phase plan-then-build, TDD loops, guardrails accumulation, permission-gated loops, and stale recovery. All share five properties: one task per iteration, binary completion signal, deterministic verification, append-only progress, git as checkpoint. The gap between practitioner patterns and production-grade loops is operational safeguards (revert-on-failure, loop fingerprinting, budget awareness) — none of the shared implementations include these.

20. **The meta-loop pattern — agents that optimize other agents via eval feedback — is production-ready.** Five independent implementations (OpenAI Self-Evolving Agents, Weco tree-search, Arize PromptLearning, IBM AutoPDL, Evidently mistake-driven) converge on the same structure: execute → evaluate → meta-agent rewrites config → redeploy. Arize improved SWE-bench +6% by optimizing only the CLAUDE.md file. The eval script is the only domain-specific component — everything else is reusable infrastructure.

21. **Agent loops have graduated to three deployment tiers.** Session-scoped (Claude Code `/loop`, dies with terminal), CI/CD-integrated (GitHub Agentic Workflows, Claude/Codex Actions with cron schedules), and cloud-native (Cursor Cloud Agents — 35% of internal PRs, each agent gets its own VM). GitHub calls CI/CD-integrated agents "Continuous AI." RALPH.md files are already portable across all three tiers without format changes.

22. **pass^k, not pass@k, is the production-readiness metric.** An agent with 70% success rate shows 97% pass@3 but only 34% pass^3. Enterprise tiers: internal tools (74-90% pass^1 acceptable), customer-facing (80% pass^1 but degrades on pass^8), long-running autonomous (not ready — agents "spiral rather than self-correct" once misaligned). Promotion gates should require pass^k stability across multiple k values.

23. **Intent failure has five mechanisms; spec-driven development is the fix.** Test gaming (30.4% reward-hacking — METR), silent fallback insertion, local patch myopia (50% regression — SWE-CI), business logic blindness, and semantic-without-functional correctness. The unified defense: the authority hierarchy (specs > tests > code) where agents never modify tests, and outcomes are verified against independent ground truth. Spec-driven development (ICSE 2026) formalizes three rigor levels; Stripe's Blueprints (1,300+ PRs/week) and GitHub Spec Kit (72K+ stars) prove it at scale. AI agents perform 50% better with clear specs. The "on the loop" position — designing the harness rather than reviewing every output — defines the ralph author's role. Human effort is highest-leverage at plans and outcomes, not code.

24. **The harness is a middleware stack, not a monolith.** LangChain improved from Top 30 to Top 5 on Terminal Bench 2.0 by changing only the harness — four composable middleware layers (environment mapping, loop detection, reasoning budget allocation, pre-completion verification) wrapped the same model. Open SWE captures the Stripe/Coinbase/Ramp internal pattern; StrongDM's Attractor adds read-before-write enforcement. The "reasoning sandwich" (heavy reasoning for planning and verification, lighter for implementation) outperforms uniform reasoning allocation. Azure SRE Agent drove Intent Met from 45% to 75% by replacing RAG with filesystem-as-world — and now the agent investigates its own failures, reducing errors 80% via automated self-diagnosis PRs.

25. **Specification quality is a hidden variable that masks true agent capability.** Zencoder's $20K eval bug revealed: under detailed instructions, all frontier models cluster within ~6 percentage points; under minimal guidance plus verification tests, the same models spread across 26 points. Cross-vendor model pairs (Anthropic + Google) show only 68% task overlap vs. 84% same-vendor — multi-model orchestration captures 15-30% more tasks. Loops with strong verification commands but minimal prescriptive prompts may unlock more capability than instruction-heavy designs.

## Chapters

| # | Chapter | Summary |
|---|---------|---------|
| 1 | [The Loop Architecture](chapters/01-loop-architecture.md) | Core patterns: plan-execute-verify-iterate, fresh context resets, state management |
| 2 | [Verification & Quality Gates](chapters/02-verification-gates.md) | How Spotify, Karpathy, and others build verification layers that prevent drift |
| 3 | [Karpathy's Autoresearch](chapters/03-autoresearch.md) | The minimal agent loop distilled to 3 primitives and 630 lines |
| 4 | [Production Systems at Scale](chapters/04-production-scale.md) | Meta's REA, Spotify's Honk, Codex long-horizon — enterprise patterns |
| 5 | [Multi-Agent Orchestration](chapters/05-multi-agent.md) | Cursor's architecture evolution, worktree isolation, 3-5 agent ceiling, coordinator patterns |
| 6 | [Implications for Ralphify](chapters/06-ralphify-implications.md) | Framework gaps, cookbook recipes, prompt engineering lessons, competitive positioning |
| 7 | [Anti-Patterns & Failure Modes](chapters/07-anti-patterns.md) | The ten recurring failure modes and practitioner-validated remedies |
| 8 | [Specification Files](chapters/08-specification-files.md) | CLAUDE.md, AGENTS.md patterns from 2,500+ repos and real-world configs |
| 9 | [Prompt Assembly & Context Engineering](chapters/09-prompt-assembly.md) | Three-phase architecture, context management, double-loop model, steering injection |
| 10 | [Operational Reality](chapters/10-operational-reality.md) | Ecosystem landscape, cost control, circuit breakers, daily practitioner workflows |
| 11 | [Trust, Testing, and Convergence](chapters/11-trust-testing-convergence.md) | Autonomy scaling data, harness testing pyramids, spec+ralph integration |
| 12 | [Harness Evolution & Entropy Management](chapters/12-harness-evolution-entropy.md) | Rippable harnesses, garbage collection agents, completion promises, evolutionary software |
| 13 | [MCP & the Agent Infrastructure Layer](chapters/13-mcp-agent-infrastructure.md) | 5,000+ MCP servers, dynamic tool loading, context window management, ralph+MCP integration |
| 14 | [Context Engineering & Loop Maturation](chapters/14-context-engineering-advances.md) | Context rot, compaction hierarchy, guardrails as infrastructure, two-tier loops, intent-failure detection |
| 15 | [Production Orchestration & Budget-Aware Loops](chapters/15-production-orchestration-patterns.md) | Cursor's planner-worker-judge, loop fingerprinting, worktree isolation, observability stack, Meridian 3,190 cycles |
| 16 | [Self-Repair, Resilience & Agent Debugging](chapters/16-self-repair-resilience-debugging.md) | Git checkpoint hierarchy, circuit breaker thresholds, 220-loop empirical data, AgentRx 9-category taxonomy, trace-driven development |
| 17 | [Practitioner Cookbook Patterns](chapters/17-practitioner-cookbook-patterns.md) | 6 concrete loop configurations from the wild: PRD-driven, plan-then-build, TDD, guardrails accumulation, permission-gated, stale recovery |
| 18 | [Eval-Driven Optimization & Production Deployment](chapters/18-eval-driven-optimization-production-deployment.md) | Meta-loop pattern (5 implementations), EDD methodology, pass@k vs pass^k, 3 deployment tiers, scheduled execution, team workflows, observability |
| 19 | [Long-Running Agent State & Memory](chapters/19-long-running-state-memory.md) | Duration-failure curve, 4 memory architectures, 5 compression failure modes, restorable compression, state file patterns at scale |
| 20 | [Spec-Driven & Intent-Aligned Workflows](chapters/20-spec-driven-intent-aligned-workflows.md) | Three rigor levels (spec-first/anchored/as-source), Stripe Blueprints, GitHub Spec Kit, OpenSpec, Kiro, Chief PRD agent, BDD+AI, contract testing, acceptance criteria verification, CSDD |
| 21 | [Intent-Failure Detection & Human-Agent Collaboration](chapters/21-intent-failure-human-agent-collaboration.md) | Five intent-failure mechanisms, authority hierarchy (specs>tests>code), independent ground truth, on-the-loop framework, PR Contract, conductor/orchestrator duality, role evolution |
| 22 | [Middleware Architecture & Eval Methodology](chapters/22-middleware-architecture-eval-methodology.md) | Composable middleware stacks (LangChain Top 30→Top 5), Azure SRE self-improvement loop (45%→75% Intent Met), Open SWE/Attractor patterns, reasoning sandwich, eval hidden variables, multi-model complementarity, practitioner reality (50K lines/month), Kubernetes-native execution |

## Open Questions

- How do cross-company model diversity reviewers compare to same-family self-review in measurable quality? **[Partially answered in Ch22]** — Zencoder data shows 68% task overlap cross-vendor vs. 84% same-vendor. Multi-model captures 15-30% more tasks. But no controlled quality comparison of review specifically.
- What's the optimal ratio of spec-writing time to execution time in spec+ralph integrated workflows?
- How do teams decide between session-scoped, CI/CD-integrated, and cloud-native deployment for their agent loops?
- What's the right cadence for garbage-collection/cleanup ralphs — daily, weekly, event-triggered?
- How does guardrails.md scale — at what point do accumulated guardrails become contradictory or context-consuming?
- How do teams handle the reliability math problem (99%^20 = 82%) — shorter loops, better per-step accuracy, or acceptance of failure rates?
- Which memory architecture (observational, graph, self-editing, RAG) best fits ralph loops — and can a "memory ralph" replace vector DB infrastructure?
- What's the optimal middleware stack for ralph loops — which layers provide the most value per token of overhead?
- How does Azure SRE Agent's concurrent memory staleness problem manifest in multi-ralph scenarios with shared state files?
- Does the "reasoning sandwich" pattern (heavy reasoning for planning/verification, lighter for implementation) generalize beyond Terminal Bench to real-world ralph loops?

## Key Sources

- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic
- [Background Coding Agents (Honk Part 3)](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3) — Spotify Engineering
- [Karpathy's Autoresearch](https://github.com/karpathy/autoresearch) — GitHub
- [Meta's REA](https://engineering.fb.com/2026/03/17/developer-tools/ranking-engineer-agent-rea-autonomous-ai-system-accelerating-meta-ads-ranking-innovation/) — Engineering at Meta
- [Codex Long Horizon Tasks](https://developers.openai.com/cookbook/examples/codex/long_horizon_tasks/) — OpenAI
- [Skill Issue: Harness Engineering](https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents) — HumanLayer
- [The 80% Problem in Agentic Coding](https://addyo.substack.com/p/the-80-problem-in-agentic-coding) — Addy Osmani
- [Agentic Engineering Anti-Patterns](https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/) — Simon Willison
- [Lessons from 2,500+ AGENTS.md Files](https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/) — GitHub Blog
- [Harness Engineering](https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html) — Martin Fowler / Thoughtworks
- [The Double-Loop Model](https://testdouble.com/insights/youre-holding-it-wrong-the-double-loop-model-for-agentic-coding) — Test Double
- [Advanced Context Engineering](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/ace-fca.md) — HumanLayer
- [Relocating Rigor](https://aicoding.leaflet.pub/3mbrvhyye4k2e) — Chad Fowler
- [ralph-claude-code](https://github.com/frankbria/ralph-claude-code) — frankbria (8K+ stars, circuit breakers, exit detection)
- [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) — VoltAgent (12K+ stars, 500+ skills)
- [Boris Cherny's Workflow](https://www.infoq.com/news/2026/01/claude-code-creator-workflow/) — InfoQ
- [Agent Budget Guard MCP](https://earezki.com/ai-news/2026-03-02-i-built-an-mcp-server-so-my-ai-agent-can-track-its-own-spending/) — earezki
- [BMAD + Ralph Framework](https://www.vibesparking.com/en/blog/ai/2026-02-14-bmad-ralph-execution-loop-claude-code/) — Vibe Sparking AI
- [Measuring AI Agent Autonomy in Practice](https://www.anthropic.com/research/measuring-agent-autonomy) — Anthropic
- [Testing Pyramid for AI Agents](https://engineering.block.xyz/blog/testing-pyramid-for-ai-agents) — Block Engineering (Angie Jones)
- [The Anatomy of an Agent Harness](https://blog.langchain.com/the-anatomy-of-an-agent-harness/) — LangChain
- [Guided Autonomy: Progressive Trust](https://www.llmwatch.com/p/guided-autonomy-progressive-trust) — Pascal Biese / LLM Watch
- [Harness-First Agents](https://www.datadoghq.com/blog/ai/harness-first-agents/) — Datadog
- [LLM Evaluators](https://eugeneyan.com/writing/llm-evaluators/) — Eugene Yan
- [Eval-Driven Development](https://evaldriven.org/) — Grey Newell (10-principle manifesto)
- [Optimizing CLAUDE.md with Prompt Learning](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/) — Arize AI (+5-10% from system prompt optimization alone)
- [Skill Eval](https://blog.mgechev.com/2026/02/26/skill-eval/) — Minko Gechev (unit-testing AI agent skills)
- [The Importance of Agent Harness in 2026](https://www.philschmid.de/agent-harness-2026) — Phil Schmid (build-to-delete, rippable harness framework)
- [Harness Engineering (OpenAI)](https://openai.com/index/harness-engineering/) — OpenAI (entropy management, garbage collection agents, 1M+ lines with zero hand-written code)
- [Everything is a Ralph Loop](https://ghuntley.com/loop/) — Geoffrey Huntley (evolutionary software, Loom, Level 9)
- [Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use) — Anthropic (Tool Search, 85% token reduction, dynamic loading)
- [Tool Calling Without MCP Server Composition](https://hackteam.io/blog/tool-calling-is-broken-without-mcp-server-composition/) — Hackteam (RAG-MCP, 4 composition patterns)
- [Deep Dive into MCP](https://a16z.com/a-deep-dive-into-mcp-and-the-future-of-ai-tooling/) — a16z (MCP architecture, agent-centric execution model)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic (context as finite resource, JIT retrieval, sub-agent architectures)
- [Context Engineering Part 2](https://www.philschmid.de/context-engineering-part-2) — Phil Schmid (compaction hierarchy, agent-as-tool MapReduce, Manus lessons)
- [Harness Engineering: Infrastructure Moat](https://earezki.com/ai-news/2026-03-15-harness-engineering-why-the-model-is-a-commodity-and-the-infrastructure-is-your-moat/) — earezki (Evolve 5-layer control plane, closed knowledge loops)
- [Guardrails for Agentic Coding](https://jvaneyck.wordpress.com/2026/02/22/guardrails-for-agentic-coding-how-to-move-up-the-ladder-without-lowering-your-bar/) — Van Eyck (6 guardrails, hooks as superpower, XP rediscovered)
- [Anthropic Agentic Coding Trends 2026](https://getbeam.dev/blog/anthropic-agentic-coding-trends-2026.html) — Beam (78% multi-file, 23-min sessions, 47 tool calls, 40% fewer errors with docs)
- [Scaling Long-Running Autonomous Coding](https://cursor.com/blog/scaling-agents) — Cursor (planner-worker-judge, 1M+ lines, role-based pipeline)
- [AI Coding Agents: Coherence Through Orchestration](https://mikemason.ca/writing/ai-coding-agents-jan-2026/) — Mike Mason (8-13% real productivity, code quality data, production anti-patterns)
- [How to Run a Multi-Agent Coding Workspace](https://www.augmentcode.com/guides/how-to-run-a-multi-agent-coding-workspace) — Augment Code (6 coordination patterns, worktree isolation, failure taxonomy)
- [The Loop as Laboratory: 3,190 Cycles](https://dev.to/meridian-ai/the-loop-as-laboratory-what-3190-cycles-of-autonomous-ai-operation-reveal-23je) — Meridian AI (30-day autonomous operation, identity persistence, 9 sub-agents)
- [Agent Loops Forever: How to Stop](https://matrixtrak.com/blog/agents-loop-forever-how-to-stop) — MatrixTrak (fingerprint detection, error classification, stopping conditions)
- [Agentic AI Coding: Best Practice Patterns](https://codescene.com/blog/agentic-ai-coding-best-practice-patterns-for-speed-with-quality) — CodeScene (Code Health 9.5+ threshold, multi-level safeguarding, 2-3x speedup)
- [How to Tell If Your AI Agent Is Stuck (220 Loops)](https://dev.to/boucle2026/how-to-tell-if-your-ai-agent-is-stuck-with-real-data-from-220-loops-4d4h) — Boucle (55%/45% productive/problematic, 50% remediation effectiveness, 13.3x feedback amplification)
- [AgentRx: Systematic Debugging for AI Agents](https://www.microsoft.com/en-us/research/blog/systematic-debugging-for-ai-agents-introducing-the-agentrx-framework/) — Microsoft Research (+23.6% failure localization, 9-category taxonomy, 115 trajectories)
- [Checkpoint Commit Patterns](https://understandingdata.com/posts/checkpoint-commit-patterns/) — James Phoenix (4 git checkpoint patterns for AI-assisted development)
- [Trace-Driven Development](https://www.nickwinder.com/blog/trace-driven-development-langsmith-claude-code) — Nick Winder (LangSmith MCP + Claude Code, autonomous fix proposals)
- [Preventing Agent Drift at CRED](https://dev.to/singhdevhub/how-we-prevent-ai-agents-drift-code-slop-generation-2eb7) — SinghDevHub (8 safeguards, dual-threshold circuit breakers, explicit termination tools)
- [Self-Evolving Agents Cookbook](https://developers.openai.com/cookbook/examples/partners/self_evolving_agents/autonomous_agent_retraining) — OpenAI + Weco (canonical meta-loop: execute → evaluate → metaprompt → redeploy)
- [Demystifying Evals for AI Agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) — Anthropic (Swiss Cheese Model, 8-step eval roadmap)
- [Pass@k vs Pass^k](https://www.philschmid.de/agents-pass-at-k-pass-power-k) — Phil Schmid (reliability gap: 70% success = 97% pass@3 but 34% pass^3)
- [The Reliability Gap](https://simmering.dev/blog/agent-benchmarks/) — Paul Simmering (3-tier enterprise readiness based on pass^k degradation)
- [GitHub Agentic Workflows](https://github.blog/ai-and-ml/automate-repository-tasks-with-github-agentic-workflows/) — GitHub ("Continuous AI" — Markdown+YAML frontmatter compiled to Actions)
- [Cursor Cloud Agents](https://devops.com/cursor-cloud-agents-get-their-own-computers-and-35-of-internal-prs-to-prove-it/) — DevOps.com (35% of internal PRs, each agent gets own VM)
- [Cron Scheduler for AI Agents at Scale](https://blog.geta.team/how-we-built-a-cron-scheduler-for-ai-agents-at-scale/) — Geta Team (100+ agents, centralized scheduler, ~200 lines JS)
- [Optimizing Coding Agent Rules](https://arize.com/blog/optimizing-coding-agent-rules-claude-md-agents-md-clinerules-cursor-rules-for-improved-accuracy/) — Arize AI (PromptLearning for CLAUDE.md, +6% on SWE-bench)
- [Promptfoo: Evaluate Coding Agents](https://www.promptfoo.dev/docs/guides/evaluate-coding-agents/) — Promptfoo/OpenAI (trajectory tracing, cost assertions, CI/CD eval gates)
- [Humans and Agents in Software Engineering Loops](https://martinfowler.com/articles/exploring-gen-ai/humans-and-agents.html) — Kief Morris / Martin Fowler (in/on/out of the loop framework)
- [Building AI Coding Agents for the Terminal](https://arxiv.org/abs/2603.05344) — Nghi D. Q. Bui (OpenDev, 6-phase ReAct loop, first academic systematization of harness engineering)
- [35-Agent AI Coding Swarm](https://earezki.com/ai-news/2026-03-20-i-built-a-35-agent-ai-coding-swarm-that-runs-overnight/) — earezki (6,500+ runs, 124 duplicate PRs, $65/day, 5-layer memory)
- [Context Engineering Lessons from Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus) — Peak Ji (KV-cache as #1 metric, 100:1 input-to-output, rebuilt 4x)
- [Stripe Minions at Scale](https://www.infoq.com/news/2026/03/stripe-autonomous-coding-agents/) — InfoQ (1,300+ PRs/week, "Blueprints" architecture)
- [ETH Zurich: AGENTS.md Value Review](https://www.infoq.com/news/2026/03/agents-context-file-value-review/) — InfoQ (context files reduced success by ~3%, increased costs 19-20%)
- [QCon: AI for Developers in a Dangerous State](https://www.theregister.com/2026/03/18/ai_for_software_developers_qcon/) — The Register (expertise erosion paradox)
- [Memory Compression Failure Modes](https://www.indium.tech/blog/agent-memory-compression-failure-modes/) — Indium Tech (5 failure modes for long-running agents)
- [4 Memory Architectures for AI Agents](https://dev.to/ai_agent_digest/your-ai-agents-memory-is-broken-here-are-4-architectures-racing-to-fix-it-55j1) — DEV Community (Observational, Graph, Self-Editing, RAG)
- [Google Always On Memory Agent](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/agents/always-on-memory-agent) — Google (no vector DB, SQLite + LLM consolidation)
- [State of Agent Engineering](https://www.langchain.com/state-of-agent-engineering) — LangChain (89% observability, 52.4% evals, 57% agents in prod)
- [Compaction as Gradient Descent Momentum](https://jxnl.co/writing/2025/08/30/context-engineering-compaction/) — Jason Liu (lossy compaction, experiential texture loss)
- [Spec-Driven Development (Thoughtworks)](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices) — Thoughtworks (SDD as 2025's key new practice, spec-first vs spec-anchored vs spec-as-source)
- [How to Write a Good Spec for AI Agents](https://addyosmani.com/blog/good-spec/) — Addy Osmani (five principles, three-tier boundaries, modular prompts, conformance suites)
- [Spec-Driven Development: From Code to Contract (ICSE 2026)](https://arxiv.org/abs/2602.00180) — arXiv (three rigor levels, 50% error reduction with specs, taxonomy of spec types)
- [Stripe Minions Blueprint Architecture](https://www.mindstudio.ai/blog/stripe-minions-blueprint-architecture-deterministic-agentic-nodes) — MindStudio (deterministic+agentic nodes, 1,300 PRs/week, dependency update blueprint example)
- [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/) — GitHub Blog (72K+ stars, specify->plan->tasks->implement, 22+ agent platforms)
- [OpenSpec Deep Dive](https://redreamality.com/garden/notes/openspec-guide/) — Redreamality (brownfield-first, 4-phase state machine, GIVEN/WHEN/THEN format)
- [Intent Formalization: A Grand Challenge](https://arxiv.org/html/2603.17150) — Microsoft Research (specification spectrum, TiCoder doubled accuracy 40%→84%)
- [AI Made Every Test Pass. The Code Was Still Wrong.](https://doodledapp.com/feed/ai-made-every-test-pass-the-code-was-still-wrong) — Doodledapp (independent ground truth vs self-validation)
- [Recent Frontier Models Are Reward Hacking](https://metr.org/blog/2025-06-05-recent-reward-hacking/) — METR (30.4% reward hacking rate, o3 admits misalignment when asked)
- [AI Coding Agents Rely Too Much on Fallbacks](https://www.seangoedecke.com/agents-and-fallbacks/) — Sean Goedecke (silent fallback insertion pattern)
- [AI Broke Your Code Review](https://bryanfinster.substack.com/p/ai-broke-your-code-review-heres-how) — Bryan Finster (Nyquist principle for defect detection rate)
- [Code Review in the Age of AI](https://addyosmani.com/blog/code-review-ai/) — Addy Osmani (PR Contract framework, threat model review)
- [The Future of Agentic Coding: Conductors to Orchestrators](https://addyosmani.com/blog/future-agentic-coding/) — Addy Osmani (conductor/orchestrator duality, role evolution)
- [Understanding SDD: Kiro, spec-kit, Tessl](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) — Boeckeler / Martin Fowler (three SDD tools compared)
- [Amazon Vibe Coding Failures](https://www.getautonoma.com/blog/amazon-vibe-coding-lessons) — Autonoma AI (4 Sev-1s in 90 days, 6.3M lost orders)
- [Claude Code Review (multi-agent)](https://thenewstack.io/anthropic-launches-a-multi-agent-code-review-tool-for-claude-code/) — Anthropic (5 independent reviewer agents, 84% finding rate on large PRs)
- [Technical Design Spec Pattern](https://www.arguingwithalgorithms.com/posts/technical-design-spec-pattern.html) — Tom Yedwab (specs as long-term memory, 6 key ideas, rollback-and-revise)
- [Spec-Driven Verification for Coding Agents](https://agent-wars.com/news/2026-03-14-spec-driven-verification-claude-code-agents) — Agent Wars (4-stage verification pipeline, self-congratulation machine problem)
- [Constitutional Spec-Driven Development](https://arxiv.org/abs/2602.02584) — arXiv (security by construction, 26.1% of AI agent skills contain vulnerabilities)
- [Improving Deep Agents with Harness Engineering](https://blog.langchain.com/improving-deep-agents-with-harness-engineering/) — LangChain (Top 30→Top 5, middleware stack, reasoning sandwich)
- [Open SWE: Internal Coding Agents](https://blog.langchain.com/open-swe-an-open-source-framework-for-internal-coding-agents/) — LangChain (Stripe/Coinbase/Ramp patterns, middleware safety nets)
- [The Agent That Investigates Itself](https://techcommunity.microsoft.com/blog/appsonazureblog/the-agent-that-investigates-itself/4500073) — Microsoft (Azure SRE Agent, 80% error reduction via self-diagnosis)
- [Context Engineering for Azure SRE Agent](https://techcommunity.microsoft.com/blog/appsonazureblog/context-engineering-lessons-from-building-azure-sre-agent/4481200/) — Microsoft (filesystem-as-world, 45%→75% Intent Met)
- [$20K Eval Bug](https://zencoder.ai/blog/20k-bug-that-changed-evals) — Zencoder (spec quality as hidden variable, multi-model complementarity)
- [Grounded Take on Agentic Coding](https://iximiuz.com/en/posts/grounded-take-on-agentic-coding/) — iximiuz (50K lines/month production reality, dangerous failure modes)
