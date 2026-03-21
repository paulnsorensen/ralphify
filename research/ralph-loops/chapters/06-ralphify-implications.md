# Implications for Ralphify

> This chapter distills the research into actionable directions for the ralphify framework: cookbook recipes to build, framework features to consider, and competitive positioning in the emerging harness engineering ecosystem.

## Cookbook Recipes to Build

### 1. Autoresearch Ralph
Replicate Karpathy's pattern as a ralph:
- **RALPH.md prompt**: Optimization strategy with `{{ commands.metrics }}` and `{{ commands.current_code }}`
- **Commands**: `run experiment` (time-boxed), `extract metrics`, `read current code`
- **Value**: Demonstrates ralphify for ML experimentation — the hottest use case right now

### 2. Code Migration Ralph
Spotify's Honk use case as a ralph:
- **RALPH.md prompt**: Migration spec with `{{ commands.test_results }}` and `{{ commands.remaining_files }}`
- **Commands**: `run tests`, `list files still using old pattern`
- **Value**: Batch code transformation is a proven high-value agent use case

### 3. Documentation Audit Ralph
An agent that iteratively improves documentation:
- **RALPH.md prompt**: Style guide + `{{ commands.coverage_report }}` + `{{ commands.stale_docs }}`
- **Commands**: `check doc coverage`, `find stale docs`, `validate links`
- **Value**: Low-risk, high-reward — great starter ralph for new users

### 4. Security Scan Ralph
Iterative security review loop:
- **RALPH.md prompt**: Security checklist + `{{ commands.scan_results }}` + `{{ commands.open_issues }}`
- **Commands**: `run security scanner`, `list open findings`
- **Value**: Continuous security improvement with clear success metrics

### 5. Test Coverage Ralph
Iterative test generation:
- **RALPH.md prompt**: Coverage targets + `{{ commands.coverage }}` + `{{ commands.uncovered_functions }}`
- **Commands**: `run coverage report`, `list uncovered functions`
- **Value**: Very clear scalar metric (coverage %) — similar to autoresearch's clarity

## Framework Feature Directions

### Verification Commands (High Priority)
Add a `verify` field to RALPH.md frontmatter — commands that run *after* the agent completes, with results determining whether to keep or revert the iteration. This is the pattern that makes Spotify, Karpathy, and Codex reliable.

```yaml
verify:
  - name: tests
    run: uv run pytest
  - name: lint
    run: uv run ruff check
```

### Iteration Metrics (Medium Priority)
Track per-iteration data: token cost, duration, verification pass/fail. Surface this in the CLI and in a `results.tsv`-style log. Essential for cost awareness and optimization.

### Revert-on-Failure (Medium Priority)
When verification fails, automatically `git reset` to the pre-iteration state. Karpathy's autoresearch does this; it should be a first-class ralphify feature.

### Parallel Ralphs (Lower Priority, High Impact)
The `manager.py` concurrent run capability is already there. The missing piece: coordination patterns. Consider:
- Shared state files that multiple ralphs read/write
- A "planner" ralph that generates task-specific RALPH.md files
- Fleet-style execution across isolated worktrees

## Competitive Positioning

### What Ralphify Already Gets Right
- **Fresh context per iteration** — the core insight that everyone converges on
- **File-based state** — git + filesystem is the universal backend
- **Commands as dynamic context** — unique strength for assembling iteration-specific context
- **Simplicity** — a ralph is just a directory with RALPH.md, no complex config

### Where the Gap Is
- **Verification gates** — no built-in verify step; users must build this into their prompt/commands
- **Revert-on-failure** — no automatic rollback on bad iterations
- **Metrics/observability** — no built-in cost or iteration tracking
- **Ecosystem** — need more cookbook examples showing real-world patterns

### The Opportunity
Ralphify is positioned at a sweet spot: simpler than full orchestration frameworks (LangGraph, CrewAI) but more structured than raw bash loops. The Karpathy autoresearch moment — showing that 630 lines can run 700 experiments — validates the "simple harness, powerful results" philosophy that ralphify embodies.

The key differentiator to develop: **verification as a first-class citizen**. Every major system has converged on this. Making it native to RALPH.md frontmatter would be the single highest-impact framework improvement.
