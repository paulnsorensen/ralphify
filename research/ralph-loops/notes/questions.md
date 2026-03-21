# Research Questions

## Open
- [ ] How do practitioners handle non-deterministic verification (e.g., subjective quality in writing/design tasks)?
- [ ] What patterns exist for gradually increasing agent autonomy as trust builds?
- [ ] What's the real-world false negative rate for LLM-as-judge verification beyond Spotify's 25%?
- [ ] How does cross-company model diversity (Opus architect, Sonnet dev, Codex reviewer) compare to same-family self-review in measurable quality?
- [ ] What's the optimal balance between plan-mode time and execution time? Boris Cherny iterates on plans extensively — is there a sweet spot?
- [ ] How will agent skills interoperability evolve — will SKILL.md become a true standard or fragment?
- [ ] What tooling exists for A/B testing ralph loop configurations? (Different prompts, different context strategies, same task set)
- [ ] How do practitioners test their harness/loop configurations themselves (not the agent output, but the harness)?

## Answered
- [x] What are the most effective patterns for keeping agents on track during long-running loops? — Fresh context resets + file-based state + verification gates. See chapters 01-02.
- [x] How do practitioners handle context window limits? — Reset context each iteration; persist state in files and git. Universal pattern across all major systems.
- [x] What error recovery strategies work best? — Git revert on verification failure (Karpathy), failure pattern runbooks (Meta REA), verifier re-runs (Spotify). See chapter 02.
- [x] What are the highest-value use cases for autonomous agents? — ML optimization (autoresearch), code migration (Spotify Honk), long-horizon feature building (Codex), ads ranking (Meta REA). See chapter 04.
- [x] How do people structure prompts for iterative agent work? — Three-phase architecture (research→plan→implement), specification docs + dynamic command outputs + progress state. See chapter 09.
- [x] What state management approaches exist? — Git + 3-4 markdown files (spec, progress, tasks, knowledge base). See chapter 01.
- [x] What novel ralph/recipe patterns could we document? — Autoresearch, migration, PRD-driven, test coverage, security scan, three-phase development. See chapter 06.
- [x] What are the main failure modes of autonomous agent loops? — Ten recurring anti-patterns: one-shotting, context poisoning, doom loops, unbounded autonomy, comprehension debt, premature completion, model-blaming, same-model judging, instruction overload, unreviewed PRs. See chapter 07.
- [x] What memory/learning mechanisms persist across loop sessions? — Self-improvement loops via lessons.md + MEMORY.md with SessionStart hooks. Verification canaries detect instruction fade. See chapter 08.
- [x] What real-world CLAUDE.md/AGENTS.md examples exist? — Freek Van der Herten (<15 lines), GitHub's 2,500+ analysis (six core areas), morphllm templates (domain-specific). See chapter 08.
- [x] How does the double-loop model map to agent workflows? — Loop 1 (exploration/vibing) then Loop 2 (refinement/review). Two ralph configurations per project: loose exploration ralph, strict refinement ralph. See chapter 09.
- [x] How do teams handle multi-agent coordination? — Parallel independence works; shared-state coordination is fragile. Filesystem coordination beats message-passing. See chapter 05.
- [x] What's the optimal iteration length for different task types? — Measure in actions not time: 3-7 meaningful actions is optimal. Beyond 15 actions, success probability drops. See chapter 10.
- [x] How does the "agent skill" packaging ecosystem evolve? — 500+ skills in SKILL.md format, cross-platform (18+ agents), marketplace launched (SkillsMP.com). See chapter 10.
- [x] What emerging tools/frameworks are challenging the "simple harness" philosophy? — BMAD+Ralph adds structured planning; ralph-claude-code adds circuit breakers; Aura Guard adds deterministic safety middleware. But "simple harness" still wins for most use cases. See chapter 10.
- [x] What's the optimal CLAUDE.md/RALPH.md length? — Validated at <300 lines broadly. Boris Cherny uses CLAUDE.md as living documentation (adding mistakes). Mario Giancini uses per-project configs for monorepos. See chapter 10.
