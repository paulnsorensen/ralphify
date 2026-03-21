# Karpathy's Autoresearch: The Minimal Agent Loop

> In March 2026, Andrej Karpathy released autoresearch — a 630-line Python script that runs an AI agent in an autonomous optimization loop. It distills the agent loop to three primitives: an editable asset, a scalar metric, and a time-boxed cycle. It ran 700 experiments in 2 days and discovered 20 optimizations yielding 11% training speedup.

## The Three Primitives

### 1. Editable Asset (`train.py`)
- The single file the agent is permitted to modify
- Confines the search space to keep every hypothesis reviewable as a diff
- Other files (`prepare.py`, `program.md`) are read-only

### 2. Scalar Metric (`val_bpb`)
- Validation bits per byte — vocabulary-size-independent
- Enables architecture changes without breaking evaluation
- Binary keep/discard decision with no ambiguity

### 3. Time-Boxed Cycle (5 minutes)
- Training always runs for exactly 5 minutes of wall-clock time (excluding startup/compilation)
- ~12 experiments/hour, ~100 experiments overnight
- Makes throughput × learning effectiveness the implicit objective

## Loop Structure

```
1. Agent reads train.py and program.md (human strategy doc)
2. Agent proposes a hypothesis and edits train.py
3. Training runs for 5 minutes
4. val_bpb is extracted from logs
5. If improved → git commit (keep)
   If worse → git reset (revert)
6. Results logged to results.tsv
7. GOTO 1
```

## State Management

- **Git branch**: `autoresearch/<tag>` — each experiment committed or reverted
- **results.tsv**: Tabular log with per-experiment metrics, VRAM usage, keep/discard
- **Session reports**: Auto-posted to GitHub Discussions with experiment counts and performance deltas
- **Single lineage**: Only one branch accumulates improvements (hill-climbing, not population-based)

## Governance Separation

| File | Owner | Purpose |
|------|-------|---------|
| `program.md` | Human | Strategy, rules, constraints (read-only for agent) |
| `prepare.py` | Human | Evaluation harness and data pipeline (forbidden to modify) |
| `train.py` | Agent | Hyperparameters, architecture, optimizer (agent's search space) |

This separation is key: humans define *what* to optimize and *how to measure*; the agent handles *what to try*.

## Results

- **Karpathy**: 700 experiments in 2 days → 20 optimizations → 11% speedup on larger models
- **Tobi Lütke** (Shopify CEO): 37 experiments overnight → 19% performance gain
- Community: Active experimentation on GitHub, session reports showing steady metric improvements

## Why This Matters for Ralphify

Autoresearch is essentially a ralph loop with:
- `agent`: the AI coding agent
- `commands`: `run train.py`, `extract val_bpb from logs`
- The prompt: `program.md` with `{{ commands.metrics }}` placeholder

A "research ralph" that replicates this pattern would be a high-value cookbook example. The key ingredients:
1. A RALPH.md with the optimization strategy
2. Commands that run the experiment and capture metrics
3. A prompt that feeds metrics back and asks for the next hypothesis
4. Git-based state for revert-on-failure

## Karpathy's Vision: Collaborative Agent Research

> "The next step for autoresearch is that it has to be asynchronously massively collaborative for agents. The goal is not to emulate a single PhD student, it's to emulate a research community of them."

This maps to ralphify's multi-run capability — running multiple ralph loops in parallel with different strategies, sharing results via the filesystem.
