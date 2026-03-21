# Specification Files: CLAUDE.md, AGENTS.md, and Configuration Patterns

> Agent specification files — CLAUDE.md, AGENTS.md, RALPH.md — have become the new infrastructure. This chapter catalogs the patterns, anti-patterns, and concrete examples from public repositories and practitioner discussions.

## The Empirical Data: 2,500+ AGENTS.md Files

GitHub's analysis of 2,500+ repositories with AGENTS.md files reveals what actually works:

**Six core areas** that successful files address:
1. Commands (with exact flags, placed early)
2. Testing (how to run, what frameworks)
3. Project structure (key directories, entry points)
4. Code style (by example, not by prose description)
5. Git workflow (branching, commit conventions)
6. Boundaries (three-tier: "Always do" / "Ask first" / "Never do")

**What fails**: "Helpful coding assistant" as a role description. What works: "Test engineer who writes React tests, follows examples, never modifies source code." Specificity beats generality.

**Code examples beat prose**: One snippet outperforms three paragraphs of description. Models are in-context learners — show the pattern, don't describe it.

## CLAUDE.md Best Practices

### The HumanLayer Research

The most rigorous guidance on CLAUDE.md comes from HumanLayer's analysis:

- **150-200 instruction ceiling**: Frontier LLMs follow roughly this many instructions with reasonable consistency. Claude Code's system prompt uses ~50, leaving ~100-150 for user content.
- **Target under 300 lines** — shorter is better. HumanLayer's own root CLAUDE.md is under 60 lines.
- **Never auto-generate** with `/init` — the file's high leverage demands deliberate crafting.
- **Never use as a style guide** — deterministic linters enforce formatting; LLMs ignore style instructions inconsistently.
- **Progressive disclosure**: Use CLAUDE.md as a router with pointers to detailed docs, not a monolith.

### The Directory/Index Pattern

HN practitioners converge on using CLAUDE.md as an index:
```
When adding CSS, refer to: docs/ADDING_CSS.md
For database migrations, see: docs/MIGRATIONS.md
Architecture overview: docs/ARCHITECTURE.md
```

Supporting files hold the detail; CLAUDE.md holds the map.

### Real-World Examples

**Freek Van der Herten (Spatie/Laravel)** — ~15 lines:
- Anti-sycophancy: "Do not tell me I am right all the time. Be critical. We're equals."
- Skill delegation: "When working with Laravel/PHP projects, always use the php-guidelines-from-spatie skill"
- Tool whitelisting in settings.json: pre-approved commands for `gh`, `composer`, `vendor/bin/pest`
- Statusline hook showing context window percentage

**Morphllm.com templates** — domain-specific CLAUDE.md examples:
- DevOps: "NEVER run `terraform destroy` without explicit user instruction" — mandatory `plan` before `apply`
- ML projects: ~70 lines covering experiment tracking, data pipeline conventions
- Monorepo: ~60 lines with per-package navigation hints

## Agent Loop Configuration Patterns

### The Autoresearch Pattern (Karpathy)

The gold standard for agent loop configuration. Key techniques:

**Output redirection**: `uv run train.py > run.log 2>&1` — prevents verbose training output from flooding the context window. Then `grep "^val_bpb:" run.log` extracts only the metric.

**Simplicity criterion**: "A 0.001 val_bpb improvement that adds 20 lines of hacky code? Probably not worth it. A 0.001 improvement from deleting code? Definitely keep." Quality is weighted alongside the metric.

**Single editable file**: Only `train.py` is editable. `prepare.py` is read-only. This constraint prevents scope creep.

**Dedicated branch**: All experiments run on `autoresearch/<tag>`, keeping main clean.

### The Autoresearch Skill Pattern (uditgoenka)

Port of Karpathy's concept as a reusable Claude Code skill with 8 rules:
1. Loop until done
2. Read before write
3. One change per iteration (atomic for clear causality)
4. Mechanical verification only (metrics, never subjective judgment)
5. Automatic rollback via `git revert` (not `git reset`)
6. Simplicity wins
7. Git is memory
8. When stuck, think harder

**Verify/Guard separation**: Primary metric determines keep/discard. Optional "guard" command (e.g., lint passes) acts as a safety net — if metric improves but guard fails, rework up to 2 times before reverting.

**Crash recovery table**:
| Error Type | Action |
|-----------|--------|
| Syntax error | Fix immediately |
| Runtime error | Max 3 fix attempts |
| Resource exhaustion | Revert, try smaller |
| Infinite loop | Kill after timeout, revert |

### The PRD-Driven Pattern (snarktank/ralph)

For product development, not optimization:
- `prd.json` contains user stories with acceptance criteria and pass/fail status
- Agent selects highest-priority story where `passes: false`
- `progress.txt` is append-only learning log
- Fresh context per iteration; memory relies entirely on committed code + state files
- Completion signal: `<promise>COMPLETE</promise>` when all stories pass
- Previous runs auto-archive to `archive/YYYY-MM-DD-feature-name/`

### The Worker/Reviewer Pattern (Goose)

State files in `.goose/ralph/`:
- `task.md` — original task description
- `iteration.txt` — current iteration number
- `review-feedback.txt` — reviewer guidance for next work phase
- `review-result.txt` — "SHIP" or "REVISE"
- `work-complete.txt` — worker signals completion

Worker and reviewer are different model instances. Reviewer examines actual files and runs verification commands, then writes feedback consumed by the next worker iteration.

### Statistical Confidence Scoring (davebcn87/pi-autoresearch)

Beyond keep/discard, this implementation scores confidence:
- After 3+ experiments: `|best_improvement| / MAD` (Median Absolute Deviation)
- Green (>=2.0x): improvement clearly exceeds noise
- Yellow (1.0-2.0x): improvement may be noise
- Red (<1.0x): within noise floor

**Checks vs. Metrics separation**: Primary metric (val_bpb) determines optimization. Separate `autoresearch.checks.sh` runs correctness checks (tests, typecheck, lint) that don't affect the primary metric but log as `checks_failed` if they break.

## The Self-Improvement Loop

Mizoreww's awesome-claude-code-config implements a two-tier memory system:
- Cross-project corrections go to `~/.claude/lessons.md`
- Project-specific preferences go to `MEMORY.md`
- `SessionStart` hooks auto-inject global lessons into every new session

This creates a learning loop across sessions: mistakes in project A inform behavior in project B.

## Verification Canaries

A creative technique from HN: embed an instruction like "Always address me as Mr. Tinkleberry" to detect when the agent stops following CLAUDE.md instructions. If the greeting disappears, you know instruction fade has occurred and it's time to compact or restart.

## Key Takeaway

The most effective specification files share three properties:
1. **Brevity** — under 300 lines, ideally under 100
2. **Concreteness** — exact commands, code examples, explicit boundaries
3. **Delegation** — point to detailed docs rather than inlining everything

The specification file is a bottleneck: every token in it competes with task context for the model's attention. Treat it like a limited resource, not a documentation dump.
