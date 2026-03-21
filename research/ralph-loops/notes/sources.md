# Sources

## High Relevance

- https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents — Anthropic — Definitive guide to initializer/worker agent pattern with progress files and feature lists — **high**
- https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3 — Spotify Engineering — Honk system: auto-activating verifiers, LLM-as-judge (25% veto rate), sandboxed containers — **high**
- https://github.com/karpathy/autoresearch — Andrej Karpathy — 630-line autonomous ML optimization loop, 3 primitives (editable asset, scalar metric, time-boxed cycle) — **high**
- https://engineering.fb.com/2026/03/17/developer-tools/ranking-engineer-agent-rea-autonomous-ai-system-accelerating-meta-ads-ranking-innovation/ — Meta Engineering — REA: hibernate-and-wake pattern for multi-week autonomous ML workflows, 5x productivity — **high**
- https://developers.openai.com/cookbook/examples/codex/long_horizon_tasks/ — OpenAI — Codex 25-hour sessions with 4-file durable memory system, 30K+ lines generated — **high**
- https://daviddaniel.tech/research/articles/autonomous-agents-loop/ — David Daniel — Research showing autonomous loops outperform interactive assistance; the $50K contract for $297 story — **high**
- https://github.com/strongdm/attractor/blob/main/coding-agent-loop-spec.md — StrongDM — Formal spec for coding agent loop: session management, event system, loop detection, steering injection — **high**
- https://beyond.addy.ie/2026-trends/ — Addy Osmani — 2026 trends: agent skills as packages, multi-agent fleet tools (Conductor, Gas Town, Vibe Kanban), Beads memory — **high**
- https://addyosmani.com/blog/self-improving-agents/ — Addy Osmani — Self-improving agents via AGENTS.md knowledge base, compound learning, planner-worker model — **high**
- https://news.ycombinator.com/item?id=46081704 — HN Discussion — Practitioner skepticism on multi-agent judges, "understanding can't be outsourced" insight — **high**
- https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents — HumanLayer/Kyle — "The model is probably fine. It's just a skill issue." Context flooding, tool overload, auto-CLAUDE.md hurting performance 20%+ — **high**
- https://www.humanlayer.dev/blog/writing-a-good-claude-md — HumanLayer/Kyle — 150-200 instruction ceiling, <300 lines target, never auto-generate, progressive disclosure — **high**
- https://addyo.substack.com/p/the-80-problem-in-agentic-coding — Addy Osmani — Comprehension debt: "you understand less of your own codebase over time"; only 48% consistently review AI code — **high**
- https://simonwillison.net/guides/agentic-engineering-patterns/anti-patterns/ — Simon Willison — Cognitive debt vs technical debt, unreviewed PRs as #1 anti-pattern — **high**
- https://github.blog/ai-and-ml/github-copilot/how-to-write-a-great-agents-md-lessons-from-over-2500-repositories/ — GitHub Blog — Analysis of 2,500+ AGENTS.md files: six core areas, code examples > prose, three-tier boundaries — **high**
- https://news.ycombinator.com/item?id=43536868 — HN — Context window poisoning: once a mistake enters context, agents compound rather than self-correct — **high**
- https://news.ycombinator.com/item?id=47257212 — HN — Agentic engineering anti-patterns: treat agent output as first draft, equal review time — **high**
- https://codemanship.wordpress.com/2026/03/11/the-ai-ready-software-developer-21-stuck-in-a-doom-loop-drop-a-gear/ — Jason Gorman — Doom loops happen when tasks are out-of-distribution; fix by decomposing into simpler steps — **high**
- https://testdouble.com/insights/youre-holding-it-wrong-the-double-loop-model-for-agentic-coding — Test Double — Double loop model: Loop 1 (vibing/exploring) then Loop 2 (review/polish). Overly prescriptive prompts are counterproductive — **high**
- https://arxiv.org/abs/2603.05344 — Nghi D. Q. Bui — OPENDEV paper: doom-loop detection, adaptive context compaction, event-driven reminders against instruction fade — **high**
- https://github.com/uditgoenka/autoresearch — Udit Goenka — Autoresearch as Claude Code skill: 8 rules, verify/guard separation, crash recovery table — **high**
- https://github.com/davebcn87/pi-autoresearch — davebcn87 — MCP extension with statistical confidence scoring (MAD), checks vs metrics separation — **high**
- https://github.com/snarktank/ralph — snarktank — PRD-driven ralph: prd.json with acceptance criteria, progress.txt learning log, auto-archive — **high**
- https://block.github.io/goose/docs/tutorials/ralph-loop/ — Goose/Block — Worker/reviewer separation with file-based handoff (task.md, review-feedback.txt, review-result.txt) — **high**
- https://www.humanlayer.dev/blog/brief-history-of-ralph — HumanLayer — Origin of ralph loops (Geoff Huntley, July 2025), cascading specifications, "overbaking" emergent behavior — **high**

## Medium Relevance

- https://muraco.ai/en/articles/harness-engineering-claude-code-codex/ — Muraco.ai — Harness engineering 101: 4 essential documents (design.md, task_checklist.md, session_handoff.md, AGENTS.md) — **medium**
- https://fortune.com/2026/03/17/andrej-karpathy-loop-autonomous-ai-agents-future/ — Fortune — Karpathy's vision: "emulate a research community" of collaborative agents — **medium**
- https://kingy.ai/ai/autoresearch-karpathys-minimal-agent-loop-for-autonomous-llm-experimentation/ — Kingy AI — Detailed autoresearch architecture: git-based state, results.tsv tracking — **medium**
- https://blogs.oracle.com/developers/what-is-the-ai-agent-loop-the-core-architecture-behind-autonomous-ai-systems — Oracle Developers — Overview of agent loop architecture: plan-execute-observe pattern — **medium**
- https://www.leanware.co/insights/ralph-wiggum-ai-coding — Leanware — Ralph Wiggum pattern history and implementation guide — **medium**
- https://linearb.io/blog/dex-horthy-humanlayer-rpi-methodology-ralph-loop — LinearB — RPI methodology, context isolation through dumb/smart model separation — **medium**
- https://github.com/Chachamaru127/claude-code-harness — GitHub — Plan→Work→Review autonomous cycle harness for Claude Code — **medium**
- https://venturebeat.com/technology/andrej-karpathys-new-open-source-autoresearch-lets-you-run-hundreds-of-ai — VentureBeat — Autoresearch release coverage with community results — **medium**
- https://news.ycombinator.com/item?id=42336553 — HN — The 70% problem: AI gets you 70% there, last 30% still requires real engineering — **medium**
- https://news.ycombinator.com/item?id=46312159 — HN — AI helps ship faster but produces 1.7x more bugs — **medium**
- https://news.ycombinator.com/item?id=44574465 — HN — METR study: AI tools made experienced devs 19% slower but they perceived themselves as faster — **medium**
- https://news.ycombinator.com/item?id=44632575 — HN — Replit agent deleted production database, fabricated data to cover it up — **medium**
- https://news.ycombinator.com/item?id=45005434 — HN — Agent in a while loop deployed multi-cloud Kubernetes nobody asked for — **medium**
- https://news.ycombinator.com/item?id=47006615 — HN — Breaking the spell of vibe coding: hallucinated bugs, dead-end architectures, code ownership loss — **medium**
- https://rocketedge.com/2026/03/15/your-ai-agent-bill-is-30x-higher-than-it-needs-to-be-the-6-tier-fix/ — RocketEdge — $47K LangChain incident, $47K data enrichment incident from unbounded agent autonomy — **medium**
- https://medium.com/@danielmanzke/burning-tokens-with-ai-coding-agents-3621f67c9776 — Daniel Manzke — 80% of tokens burned on last 20% of work — **medium**
- https://sankalp.bearblog.dev/my-experience-with-claude-code-20-and-how-to-get-better-at-using-coding-agents/ — Sankalp — Start compaction at 60% context, lossy sub-agent summaries, prompt erosion after 50+ tool calls — **medium**
- https://www.augmentcode.com/blog/how-to-build-your-agent-11-prompting-techniques-for-better-ai-agents — Augment Code — Models overfit to examples, frequent tool calling violations, context-first matters more than prompt tricks — **medium**
- https://news.ycombinator.com/item?id=44193056 — HN — "What do you put in claude.md?" — directory/index pattern, supporting docs, local overrides — **medium**
- https://news.ycombinator.com/item?id=46098838 — HN — Verification canaries, subdirectory CLAUDE.md files, bootstrap commands — **medium**
- https://github.com/Mizoreww/awesome-claude-code-config — Mizoreww — Self-improvement loop via lessons.md, adversarial cross-model review, 16-step statusline — **medium**
- https://freek.dev/3026-my-claude-code-setup — Freek Van der Herten — Anti-sycophancy instruction, skill delegation, whitelist permissions — **medium**
- https://www.morphllm.com/claude-md-examples — morphllm.com — Six domain-specific CLAUDE.md templates (minimal, monorepo, Next.js, ML, DevOps, hooks) — **medium**
- https://github.com/hesreallyhim/awesome-claude-code — hesreallyhim — 29.8k star curated list: skills, workflows, hooks, statuslines, alternative clients — **medium**
- https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap — Composio — 85% per-action accuracy = 20% success for 10-step workflows — **medium**
- https://stackoverflow.blog/2025/12/29/developers-remain-willing-but-reluctant-to-use-ai-the-2025-developer-survey-results-are-here/ — Stack Overflow — 66% frustrated with "almost right" AI solutions, 45% say debugging AI code takes longer — **medium**

## Lower Relevance

- https://www.permit.io/blog/human-in-the-loop-for-ai-agents-best-practices-frameworks-use-cases-and-demo — Permit.io — Human-in-the-loop patterns for AI agents — **low**
- https://hatchworks.com/blog/ai-agents/ai-agent-design-best-practices/ — HatchWorks — General agent design best practices — **low**
- https://agentsarcade.com/blog/error-handling-agentic-systems-retries-rollbacks-graceful-failure — Agents Arcade — Error handling patterns: retries, rollbacks, graceful failure — **low**
- https://news.ycombinator.com/item?id=44294633 — HN — Agent produces invalid code repeating same logical errors despite explicit correction — **low**
- https://news.ycombinator.com/item?id=47096937 — HN — Context limits fill up unpredictably, breaking flow — **low**
- https://news.ycombinator.com/item?id=46876455 — HN — AI-generated "slop" flooding open source projects — **low**
- https://news.ycombinator.com/item?id=47246979 — HN — Agent-generated complexity removes natural friction on code size — **low**
- https://news.ycombinator.com/item?id=34137990 — HN — AI assistance lowers programmers' guards against buggy code — **low**
