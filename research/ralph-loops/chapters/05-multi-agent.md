# Multi-Agent Orchestration

> The field is shifting from single agents to coordinated fleets. The key challenge: maintaining coherence across agents without the overhead of complex orchestration. The winning pattern is simple coordination through shared filesystem state, not elaborate message-passing protocols.

## The Orchestration Spectrum

```
Single Agent → Agent + Sub-agents → Parallel Agents → Agent Fleet
    ↑                                                       ↑
  Simplest, most reliable                       Highest throughput
  Limited by context window                     Coordination overhead
```

## Leading Multi-Agent Tools (2026)

### Conductor (macOS)
- Runs multiple Claude Code agents in isolated Git worktrees
- Each agent works on a separate branch/task
- Coordination through the filesystem, not inter-agent messaging

### Gas Town
- Orchestrates dozens of Claude Code instances
- **"Mayor" model**: Distribution agent assigns tasks
- **"Deacon" model**: Health monitoring of agent instances
- Emphasis on throughput over perfection for industrial-scale migrations

### Vibe Kanban
- CLI + web UI with Kanban workflow management
- Visual code review across agent outputs
- Cross-platform support

## The Sub-Agent Pattern

The StrongDM Attractor spec defines sub-agents as specialized instances handling specific tasks in isolated contexts:
- **Context isolation**: Each sub-agent has its own conversation and tool set
- **Depth limiting**: `max_subagent_depth` prevents infinite recursion
- **Steering injection**: Parent can inject messages mid-execution via `session.steer()`

Benefits:
- Prevents context pollution between tasks
- Enables parallelization
- Supports role-based specialization (implementation, review, testing)

## Skepticism and Anti-Patterns

### Judge Loops Gone Wrong
HN commenters report that multi-agent judge setups often create "unproductive loops rather than convergence." One experienced developer found single agents doing their own quality checks more effective for simpler tasks.

### Cost Explosion
Multi-agent systems consume 4-15x more tokens than single-agent approaches. Practitioners report costs "running into several hundred dollars per run" for complex multi-agent workflows.

### The Understanding Problem
> "You can do it ahead of time while writing the prompts, you can do it while reviewing the code, you can do it while writing the test suite... but the work to understand the system can't be outsourced to the LLM."

Multi-agent doesn't eliminate the need for human understanding of the system being built.

## What Actually Works

### Parallel Independence
The most successful multi-agent patterns involve **fully independent** tasks:
- Different files/modules on different branches
- No shared state beyond the repository
- Merge at the end with human review

### Planner-Worker-Judge Hierarchy (Cursor's Architecture Evolution)

Cursor's journey to scaling agents across 1M+ line codebases is the most instructive case study. They tried three architectures before finding one that works:

1. **Flat coordination (failed)** — All agents shared state and communicated as peers. Collapsed under coordination overhead.
2. **Optimistic concurrency (failed)** — Agents worked independently and merged optimistically. Merge conflicts and semantic conflicts escalated unpredictably.
3. **Role-based hierarchy (succeeded)** — Distinct roles with clear responsibilities:
   - **Planner**: Decomposes work, assigns tasks. Can spawn sub-planners recursively for large tasks.
   - **Workers**: Execute independently in isolated worktrees. No awareness of other workers.
   - **Judge**: Reviews outputs against specifications. Deterministic checks first, LLM evaluation second.

Key findings from Cursor's production deployment:
- **Workers must be fully independent.** Any shared state between workers creates fragile coordination.
- **Model selection per role matters.** GPT-5.2 outperforms coding-specialized GPT-5.1-Codex as a planner. Match model capability to role, not task type.
- **"Prompting over architecture."** Extensive prompt experimentation yielded better results than architectural refinements. The model is probably fine — it's a skill issue.
- **3-5 parallel worktrees is the practical ceiling.** Beyond 5-7 agents, rate limits, merge conflicts, and review bottleneck eat the gains (validated independently by Boris Cherny and Augment Code).

### Worktree Isolation at Scale

Augment Code's guide to multi-agent workspaces identifies 6 coordination patterns, with worktree isolation as the clear winner:
- Each agent gets its own git worktree (isolated branch, shared object store)
- Sequential merge with rebase is the validated integration strategy
- Failure taxonomy: semantic conflicts (hardest), test regressions, style drift, dependency conflicts
- The review bottleneck is the practical limit — human attention, not agent capacity

### Karpathy's Vision for Collaborative Research
> "The goal is not to emulate a single PhD student, it's to emulate a research community of them."

Multiple agents exploring different optimization strategies in parallel, with promising findings promoted to larger scales. This is population-based search, not sequential improvement.

See [Chapter 6: Implications for Ralphify](06-ralphify-implications.md) for how multi-agent patterns map to the framework.
