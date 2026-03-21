# Verification & Quality Gates

> The verification layer is the single most important component of an agent loop. Without it, agents drift, accumulate errors, and produce plausible-looking but incorrect output. The best systems combine deterministic checks (tests, linting, builds) with LLM-as-judge evaluation and scalar metrics.

## The Verification Spectrum

Verification approaches range from fully deterministic to fully LLM-based:

```
Tests/Lint/Build ← Deterministic ————————————— Subjective → LLM Judge
     ↑                                                           ↑
  Most reliable                                          Most flexible
  Least flexible                                        Least reliable
```

The best systems layer multiple approaches.

## Spotify's Three-Layer Verification (Honk)

Spotify's background coding agent uses three verification layers:

### 1. Auto-Activating Verifiers
- Verifiers detect file types and activate automatically (Maven for `pom.xml`, etc.)
- The agent never knows *how* verification works — only that it can call a verify tool
- Verifiers abstract build system complexity and return only relevant error messages
- **Key detail**: Regex extraction filters output to return only errors, reducing context window consumption

### 2. Stop Hook Verification
- Verifiers run automatically via stop hooks *before* PR creation
- This catches issues the agent didn't think to check
- Acts as a safety net regardless of agent behavior

### 3. LLM-as-Judge
- Evaluates proposed diffs against the original prompt
- **Vetoes ~25% of agent sessions** across thousands of runs
- When vetoed, agents self-correct ~50% of the time
- Primary trigger: **agent scope creep** — refactoring or disabling tests outside the prompt's instructions

## Karpathy's Scalar Metric (Autoresearch)

The most elegant verification: a single number.

- **val_bpb** (validation bits per byte) — lower is better
- Vocabulary-size-independent, enabling architecture changes without breaking evaluation
- Binary decision: metric improved → keep (git commit); metric worsened → revert (git reset)
- No ambiguity, no judgment calls, no LLM evaluation needed

**Constraint that enables this**: The editable asset is a single file, the metric is objective, and the time budget is fixed. Not all tasks can be reduced to this, but when they can, it's the most reliable approach.

## The Verification Hierarchy for Agent Loops

Based on practitioner experience, verification gates should be ordered:

1. **Syntax/Type checks** — fastest, catch trivial errors immediately
2. **Unit tests** — verify individual component behavior
3. **Integration tests** — verify component interactions
4. **Build verification** — ensure the whole system compiles/runs
5. **End-to-end validation** — Anthropic recommends browser automation (Puppeteer MCP) to test as end-users would
6. **LLM-as-judge** — catch semantic issues tests can't (scope creep, style violations, logic correctness)

## Anti-Patterns in Verification

### Trusting Self-Assessment
Agents consistently mark tasks as "done" prematurely. Anthropic's harness engineering explicitly uses "strongly-worded instructions" warning that "removing or editing tests could lead to missing or buggy functionality."

### Over-Reliance on LLM Judges
HN commenters noted that adding separate QA agents often leads to "unproductive loops rather than convergence." Single agents doing their own quality checks can be more effective than multi-agent judge setups for simpler tasks.

### Mocking in Verification
The LinearB interview highlights that "you cannot rely on prompting alone to manage failure; the model must be constrained by explicit system signals." Mocked tests create a dangerous illusion of correctness.

## Implications for Ralph Loop Design

The ideal ralph loop verification strategy:
1. **Commands as verifiers**: Use `{{ commands.test_results }}` to run tests and feed results back into the prompt each iteration
2. **Exit criteria in the prompt**: Define what "done" looks like in measurable terms
3. **Iteration limits as safety**: Always cap iterations to prevent runaway costs
4. **Git as rollback**: On verification failure, the agent can revert to the last good state
