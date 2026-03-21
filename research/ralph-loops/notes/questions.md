# Research Questions

## Open
- [ ] How do practitioners handle non-deterministic verification (e.g., subjective quality in writing/design tasks)?
- [ ] What's the optimal iteration length for different task types (coding vs. research vs. optimization)?
- [ ] How should agents handle cascading failures across multi-file changes?
- [ ] What memory/learning mechanisms persist across loop sessions beyond AGENTS.md?
  - [ ] How does Beads (git-backed JSONL task graphs) compare to simpler file-based approaches?
- [ ] How are people combining multiple agents or agent loops for complex workflows in practice (not theory)?
- [ ] What are the failure modes specific to research loops vs. coding loops?
- [ ] How do cost-optimization strategies differ across loop types (tight cycles vs. long-horizon)?
- [ ] What patterns exist for gradually increasing agent autonomy as trust builds?
- [ ] How does the "agent skill" packaging ecosystem evolve — will there be a registry/marketplace?
- [ ] What's the real-world false negative rate for LLM-as-judge verification beyond Spotify's 25%?

## Answered
- [x] What are the most effective patterns for keeping agents on track during long-running loops? — Fresh context resets + file-based state + verification gates. See chapters 01-02.
- [x] How do practitioners handle context window limits? — Reset context each iteration; persist state in files and git. Universal pattern across all major systems.
- [x] What error recovery strategies work best? — Git revert on verification failure (Karpathy), failure pattern runbooks (Meta REA), verifier re-runs (Spotify). See chapter 02.
- [x] What are the highest-value use cases for autonomous agents? — ML optimization (autoresearch), code migration (Spotify Honk), long-horizon feature building (Codex), ads ranking (Meta REA). See chapter 04.
- [x] How do people structure prompts for iterative agent work? — Specification docs + dynamic command outputs + progress state. The prompt is assembled, not written. See chapter 01.
- [x] What state management approaches exist? — Git + 3-4 markdown files (spec, progress, tasks, knowledge base). See chapter 01.
- [x] What novel ralph/recipe patterns could we document? — Autoresearch ralph, migration ralph, doc audit ralph, security scan ralph, test coverage ralph. See chapter 06.
