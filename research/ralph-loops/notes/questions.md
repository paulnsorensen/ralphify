# Research Questions

## Open
- [ ] How do practitioners handle non-deterministic verification (e.g., subjective quality in writing/design tasks)?
- [ ] What's the optimal iteration length for different task types (coding vs. research vs. optimization)?
- [ ] How should agents handle cascading failures across multi-file changes?
- [ ] How are people combining multiple agents or agent loops for complex workflows in practice (not theory)?
- [ ] How do cost-optimization strategies differ across loop types (tight cycles vs. long-horizon)?
- [ ] What patterns exist for gradually increasing agent autonomy as trust builds?
- [ ] How does the "agent skill" packaging ecosystem evolve — will there be a registry/marketplace?
- [ ] What's the real-world false negative rate for LLM-as-judge verification beyond Spotify's 25%?
- [ ] How do practitioners detect and recover from "comprehension debt" once it's accumulated?
- [ ] What's the optimal CLAUDE.md/RALPH.md length for different project types? (HumanLayer says <300 lines, but is this validated beyond their experience?)
- [ ] How does the double-loop model (vibing then polishing) translate to ralph loops? Should RALPH.md support a "mode" field?
- [ ] What statistical methods beyond MAD are practitioners using for confidence scoring in optimization loops?
- [ ] How do teams handle the transition from "agent-assisted" to "agent-autonomous" — what trust thresholds trigger it?

## Answered
- [x] What are the most effective patterns for keeping agents on track during long-running loops? — Fresh context resets + file-based state + verification gates. See chapters 01-02.
- [x] How do practitioners handle context window limits? — Reset context each iteration; persist state in files and git. Universal pattern across all major systems.
- [x] What error recovery strategies work best? — Git revert on verification failure (Karpathy), failure pattern runbooks (Meta REA), verifier re-runs (Spotify). See chapter 02.
- [x] What are the highest-value use cases for autonomous agents? — ML optimization (autoresearch), code migration (Spotify Honk), long-horizon feature building (Codex), ads ranking (Meta REA). See chapter 04.
- [x] How do people structure prompts for iterative agent work? — Specification docs + dynamic command outputs + progress state. The prompt is assembled, not written. See chapter 01.
- [x] What state management approaches exist? — Git + 3-4 markdown files (spec, progress, tasks, knowledge base). See chapter 01.
- [x] What novel ralph/recipe patterns could we document? — Autoresearch ralph, migration ralph, doc audit ralph, security scan ralph, test coverage ralph, PRD-driven ralph. See chapter 06.
- [x] What are the main failure modes of autonomous agent loops? — Ten recurring anti-patterns: one-shotting, context poisoning, doom loops, unbounded autonomy, comprehension debt, premature completion, model-blaming, same-model judging, instruction overload, unreviewed PRs. See chapter 07.
- [x] What memory/learning mechanisms persist across loop sessions beyond AGENTS.md? — Self-improvement loops via lessons.md (cross-project) + MEMORY.md (project-specific) with SessionStart hooks. Verification canaries detect instruction fade. See chapter 08.
- [x] What are the failure modes specific to research loops vs. coding loops? — Research loops suffer from noise-vs-signal (need statistical confidence scoring), coding loops from comprehension debt and scope creep. Both suffer from context poisoning. See chapters 07-08.
- [x] What real-world CLAUDE.md/AGENTS.md examples exist? — Freek Van der Herten (<15 lines, skill delegation), GitHub's 2,500+ file analysis (six core areas), morphllm templates (domain-specific). See chapter 08.
