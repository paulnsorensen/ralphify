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

### Planner-Worker Hierarchy
When coordination is needed:
1. **Planner agent** decomposes work and assigns tasks
2. **Worker agents** execute independently
3. **Judge agent** reviews outputs (optional, use sparingly)

### Karpathy's Vision for Collaborative Research
> "The goal is not to emulate a single PhD student, it's to emulate a research community of them."

Multiple agents exploring different optimization strategies in parallel, with promising findings promoted to larger scales. This is population-based search, not sequential improvement.

## Implications for Ralphify

Ralphify's `manager.py` already supports concurrent runs via threads. The opportunity:

1. **Parallel ralphs on different tasks**: Run multiple RALPH.md files simultaneously, each working on independent modules
2. **Collaborative ralphs sharing state**: Multiple loops writing to a shared results file, with each loop's commands reading the shared state
3. **Hierarchical ralphs**: A "planner ralph" that generates task RALPH.md files, then worker ralphs that execute them

The filesystem-based coordination model is perfectly aligned with ralphify's architecture — no message passing needed, just shared files.
