# Autonomous Agent Loops & Harness Engineering: State of the Art (March 2026)

> The field has converged on a core architecture: iterative loops with fresh context per iteration, state persisted in files and git, and verification gates between cycles. The "ralph loop" pattern — named after the bash-loop technique popularized in mid-2025 — is now mainstream, with Karpathy's autoresearch, Meta's REA, Spotify's Honk, and OpenAI's Codex all implementing variants. The key differentiator between amateur and expert harness engineering is the quality of the verification layer and the state management strategy.

## Key Insights

1. **Fresh context beats accumulated context.** Every major practitioner system resets context each iteration rather than accumulating conversation history. State lives in files, not chat memory.
2. **The verification layer is the whole game.** Spotify's LLM-judge vetoes 25% of agent sessions; Karpathy's scalar metric auto-reverts bad experiments. Without strong verification, agents drift.
3. **Three primitives define a loop: editable asset, measurable metric, time-boxed cycle.** Karpathy's autoresearch distilled this to its essence — 630 lines of Python running 12 experiments/hour.
4. **Hibernate-and-wake > polling for long operations.** Meta's REA shuts down between async jobs rather than maintaining sessions — a pattern ralphify's loop-with-commands already enables.
5. **Agent Skills are becoming portable packages.** Reusable instruction sets that install like npm packages across agent platforms — directly relevant to ralphify's skill system.
6. **Multi-agent orchestration is shifting from conductor to fleet.** Tools like Conductor, Gas Town, and Vibe Kanban manage parallel agent instances in isolated worktrees.
7. **The human role inverts: from steering to specifying and reviewing.** Engineers define destinations and review complete output rather than micro-managing each step.
8. **AGENTS.md / CLAUDE.md files are the new infrastructure.** Specification documents that anchor agent execution across sessions are now considered essential project infrastructure.
9. **Git is the universal state backend.** Every serious system uses git commits as checkpoints, enabling revert-on-failure and progress tracking across iterations.
10. **Cost awareness is critical.** Multi-agent systems consume 4-15x more tokens; practitioners need iteration limits, spend caps, and cost monitoring.

## Chapters

| # | Chapter | Summary |
|---|---------|---------|
| 1 | [The Loop Architecture](chapters/01-loop-architecture.md) | Core patterns: plan-execute-verify-iterate, fresh context resets, state management |
| 2 | [Verification & Quality Gates](chapters/02-verification-gates.md) | How Spotify, Karpathy, and others build verification layers that prevent drift |
| 3 | [Karpathy's Autoresearch](chapters/03-autoresearch.md) | The minimal agent loop distilled to 3 primitives and 630 lines |
| 4 | [Production Systems at Scale](chapters/04-production-scale.md) | Meta's REA, Spotify's Honk, Codex long-horizon — enterprise patterns |
| 5 | [Multi-Agent Orchestration](chapters/05-multi-agent.md) | Fleet management, parallel worktrees, coordinator patterns |
| 6 | [Implications for Ralphify](chapters/06-ralphify-implications.md) | Cookbook ideas, framework directions, and competitive positioning |

## Open Questions

- How do practitioners handle non-deterministic verification (e.g., subjective quality)?
- What's the optimal iteration length for different task types?
- How should agents handle cascading failures across multi-file changes?
- What memory/learning mechanisms persist across loop sessions beyond AGENTS.md?

## Key Sources

- [Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — Anthropic
- [Background Coding Agents (Honk Part 3)](https://engineering.atspotify.com/2025/12/feedback-loops-background-coding-agents-part-3) — Spotify Engineering
- [Karpathy's Autoresearch](https://github.com/karpathy/autoresearch) — GitHub
- [Meta's REA](https://engineering.fb.com/2026/03/17/developer-tools/ranking-engineer-agent-rea-autonomous-ai-system-accelerating-meta-ads-ranking-innovation/) — Engineering at Meta
- [Codex Long Horizon Tasks](https://developers.openai.com/cookbook/examples/codex/long_horizon_tasks/) — OpenAI
- [Top AI Coding Trends for 2026](https://beyond.addy.ie/2026-trends/) — Addy Osmani
- [The Autonomous Agents Loop](https://daviddaniel.tech/research/articles/autonomous-agents-loop/) — David Daniel Research
- [Coding Agent Loop Spec (Attractor)](https://github.com/strongdm/attractor/blob/main/coding-agent-loop-spec.md) — StrongDM
