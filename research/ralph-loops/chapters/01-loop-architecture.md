# The Loop Architecture

> Every effective autonomous agent system converges on the same fundamental pattern: plan-execute-verify-iterate with fresh context per iteration and state persisted externally. The differences lie in what's verified, how state is managed, and how context is assembled.

## The Universal Pattern

All major systems — whether Karpathy's autoresearch, Anthropic's harness recommendations, Spotify's Honk, or the original ralph bash loop — follow the same core cycle:

1. **Orient** — Read external state (git history, progress files, task lists) to understand where things stand
2. **Plan** — Select the next unit of work and decide on approach
3. **Execute** — Make changes (code edits, experiments, document updates)
4. **Verify** — Run tests, check metrics, validate against acceptance criteria
5. **Persist** — Commit progress, update state files, log results
6. **Reset** — Clear context and start fresh with updated state

The critical insight is step 6: **context resets are a feature, not a bug.** Accumulated conversation history degrades agent performance. Fresh context with well-structured state files consistently outperforms long-running sessions.

## Fresh Context vs. Accumulated Context

David Daniel's research quantified the counterintuitive finding: developers *felt* 20% faster with continuous AI assistance but were actually 19% slower. The "impatience tax" — humans interrupting agent reasoning mid-cycle — accounts for much of the gap.

The fresh-context approach solves this by:
- **Preventing context window degradation** — no irrelevant history consuming tokens
- **Enabling clean error recovery** — each iteration starts from a known-good state
- **Supporting parallelization** — independent iterations can run concurrently
- **Reducing drift** — the agent re-reads specifications each cycle rather than relying on stale understanding

## State Management Strategies

### Git as the Universal Backend
Every serious system uses git commits as checkpoints:
- **Karpathy's autoresearch**: `git reset` on failed experiments, commits on improvements
- **Anthropic's harness**: Descriptive commit messages serve as progress documentation
- **The original ralph loop**: Git history enables agents to understand prior work

### File-Based Memory
Four document types recur across systems:

| Document | Purpose | Updates |
|----------|---------|---------|
| **Specification** (RALPH.md, Prompt.md, design.md) | Frozen goal definition | Rarely — only on scope changes |
| **Progress log** (claude-progress.txt, results.tsv) | Chronological record | Every iteration |
| **Task list** (feature_list.json, tasks.json) | What remains | As tasks complete |
| **Knowledge base** (AGENTS.md, CLAUDE.md) | Learned patterns | When discoveries accumulate |

### The Initializer Pattern
Anthropic's harness engineering recommends a two-phase approach:
1. An **initializer agent** runs once to set up the environment: creates the init script, generates the progress file, establishes the git repo, and expands requirements into a granular feature list
2. **Worker agents** run in subsequent sessions, following a startup routine (read progress → select task → verify environment → execute → commit)

This separation ensures consistent bootstrapping regardless of which agent instance picks up the work.

## Context Assembly

The quality of context assembly directly determines loop effectiveness. Key patterns:

**Hierarchical context loading**: Load specification first, then progress state, then relevant code — in decreasing order of importance. This ensures the agent prioritizes goals over implementation details.

**Command-based dynamic context**: Ralphify's `{{ commands.name }}` pattern — running shell commands to capture fresh data each iteration — is a powerful approach for assembling context that reflects current state rather than stale snapshots.

**Truncation strategies**: The StrongDM Attractor spec truncates tool output before sending to the LLM (character-based first, then line-based) while preserving full output in events. This prevents large outputs from consuming the context window.

## Loop Termination

Systems handle termination through:
- **Metric satisfaction**: Karpathy's autoresearch runs indefinitely until manually stopped (no goal, only improvement)
- **Task completion**: Feature lists with boolean completion status
- **Iteration limits**: Essential safety valve — 50 iterations can cost $50-100+
- **Time budgets**: Meta's REA operates within approved compute budgets
- **Human review gates**: Agents open PRs rather than auto-merging

The best systems combine multiple termination conditions: complete when all tasks pass, but always stop at the iteration limit.
