# Production Systems at Scale

> Meta's REA, Spotify's Honk, and OpenAI's Codex long-horizon demonstrate how agent loops work at enterprise scale. Common themes: hibernate-and-wake for async operations, layered verification, and human oversight at strategic decision points rather than tactical ones.

## Meta's Ranking Engineer Agent (REA)

### Architecture
REA manages the complete ML lifecycle for ads ranking models across multi-week workflows:
- **REA Planner**: Generates experiment strategies and hypotheses
- **REA Executor**: Manages asynchronous job execution and handles failures
- Built on the Confucius AI agent framework for complex, multistep reasoning

### Hibernate-and-Wake Pattern
The most notable innovation: rather than maintaining continuous sessions, REA:
1. Delegates work to a background system (job scheduler)
2. Shuts down to conserve resources
3. Automatically resumes where it left off when jobs complete

This pattern is essential for ML workflows where training runs take hours/days. It's fundamentally different from the tight-loop approach of autoresearch.

### Three-Phase Planning
1. **Validation**: Test individual hypotheses in parallel
2. **Combination**: Merge promising approaches for synergistic gains
3. **Exploitation**: Aggressively optimize top candidates within approved budgets

### Dual Hypothesis Generation
- **Historical Insights Database**: Patterns from prior successes and failures
- **ML Research Agent**: Investigates baseline configurations and proposes novel strategies
- Cross-pollination surfaces ideas unlikely from single methodologies

### Results
- 2x model accuracy improvement across six models
- 5x engineering productivity: 3 engineers did work previously requiring 2 per model across 8 models

## Spotify's Honk

### Focused Agent Design
Honk deliberately limits the agent to a single function: accepting a prompt and executing code changes. Complex tasks (pushing, communication, prompt authoring) happen in surrounding infrastructure.

### Failure Mode Hierarchy
1. **PR generation failure** → acceptable (manual fallback)
2. **CI test failures** → problematic (creates review burden)
3. **Functionally incorrect code passing CI** → most dangerous (erodes trust)

Design decisions optimize for preventing category 3 failures above all.

### Sandboxed Execution
The agent runs in a container with:
- Limited file system access (only relevant codebase)
- Few available binaries
- Minimal external system access
- Reduced flexibility **directly improves predictability**

## OpenAI Codex Long-Horizon

### 25+ Hour Sessions
GPT-5.3-Codex generated 30,000+ lines across 25 uninterrupted hours using ~13M tokens.

### Durable Project Memory
Four markdown files serve as the agent's memory:
- **Prompt.md** — Frozen specification preventing scope creep
- **Plans.md** — Milestones with "done when" validation rules and decision notes
- **Implement.md** — Operational discipline runbook
- **Documentation.md** — Audit log recording decisions and state

### Continuous Verification
After each milestone: lint → typecheck → test → build → export validation. Failures are repaired immediately before progressing.

## Patterns Across All Three

| Pattern | REA | Honk | Codex |
|---------|-----|------|-------|
| State in files/git | ✓ | ✓ | ✓ |
| Layered verification | ✓ | ✓ | ✓ |
| Human oversight at strategy level | ✓ | ✓ | ✓ |
| Scope containment | Explicit budgets | Sandboxed container | Frozen spec |
| Error recovery | Failure runbooks | Verifier re-runs | Immediate repair |

## Implications for Ralphify

**Hibernate-and-wake**: Ralphify's command system already supports this — commands can poll for job completion, and the loop only proceeds when data is ready.

**Layered verification**: Ralphify could support multiple verification commands, with the prompt template incorporating all their outputs.

**Scope containment**: The RALPH.md specification serves the same role as Codex's Prompt.md — a frozen goal that prevents drift.
