# Research Questions

## Open

### High Priority (directly actionable for ralphify)
- [ ] How do teams handle the reliability math problem (99%^20 = 82%) — shorter loops, better per-step accuracy, or acceptance of failure rates?
- [ ] Which memory architecture (observational, graph, self-editing, RAG) best fits ralph loops — and can a "memory ralph" replace vector DB infrastructure?
- [ ] What's the optimal credential architecture for ralph loops — env vars (simple), vault integration (better), or injection proxy (strongest)? At what scale does proxy complexity pay off? **[Partially answered in Ch24]** — credential injection proxy is the converged answer (Vercel/GitHub/NVIDIA), but no data on the complexity threshold.
- [ ] How does the authority hierarchy (specs>tests>code) interact with TDD loops where tests are written by the agent?
- [ ] At what point does architectural drift from agent-generated code become unrepairable — is there a measurable "point of no return"?
- [ ] How do teams decide which harness layers to rip when a new model ships — is there a systematic evaluation process?

### Medium Priority (emerging patterns worth tracking)
- [ ] How quickly will A2A adoption close the gap with MCP (97M downloads)? Will multi-ralph coordination benefit from A2A, or is file-based handoff sufficient?
- [ ] Does the "reasoning sandwich" generalize beyond Terminal Bench? **[Partially answered in Ch22]** — Outperforms uniform allocation by 12.6 points, but no real-world ralph loop validation yet.
- [ ] How does guardrails.md scale — at what point do accumulated guardrails become contradictory or context-consuming?
- [ ] What's the right cadence for garbage-collection/cleanup ralphs — daily, weekly, event-triggered? OpenAI did it weekly (Fridays) before automating.
- [ ] How does cross-company model diversity (Opus architect, Sonnet dev, Codex reviewer) compare to same-family self-review in measurable quality? **[Partially answered in Ch8/Ch22]** — 68% task overlap cross-vendor vs. 84% same-vendor, but no controlled review quality study.
- [ ] Will MCP Apps (UI rendering) compete with or complement AG-UI for agent frontend experiences?

## Answered
- [x] How does Stripe's "Blueprints" architecture compare to RALPH.md for defining deterministic+agent hybrid workflows? — Blueprints interleave deterministic nodes (linting, testing, file ops) with agentic nodes (code generation, PR writing). RALPH.md already implements this: commands = deterministic nodes, prompt body = agentic directive. Gap: Blueprints have explicit error recovery (bounded retry → human escalation). See Ch20.
- [x] Does the two-phase plan-then-build pattern measurably reduce "built the wrong thing" failures? — Partially. Authority hierarchy (specs>tests>code) and independent ground truth are the validated techniques. TiCoder doubled accuracy (40%→84%) via interactive spec disambiguation. No controlled study yet on plan-then-build specifically. See Ch21.
- [x] How do practitioners handle non-deterministic verification (e.g., subjective quality in writing/design tasks)? — Block's 4-layer testing pyramid: deterministic foundation + record/playback + probabilistic benchmarks + LLM-as-judge with rubrics (3 rounds, majority vote). See chapter 11.
- [x] What patterns exist for gradually increasing agent autonomy as trust builds? — Trust Equation (Competence × Consistency × Recoverability / Consequence), 4-level trust ladder, Anthropic's empirical data (20%→40% auto-approve over 750 sessions). See chapter 11.
- [x] What's the real-world false negative rate for LLM-as-judge verification beyond Spotify's 25%? — GPT-4 agrees with human experts 85% (MT-Bench), but faithfulness correlation only ρ=0.55. Verbosity bias >90%, position bias up to 70%. Panel-of-judges outperforms single judge. See chapter 11.
- [x] What tooling exists for A/B testing ralph loop configurations? — EDD methodology with Braintrust, Promptfoo, LangSmith, Langfuse, Skill Eval. Golden datasets + pass@k/pass^k metrics. Arize's prompt learning optimizes system prompts via automated meta-prompting. See Ch06.
- [x] How do practitioners test their harness/loop configurations themselves (not the agent output, but the harness)? — Block's TestProvider (record/playback pattern), LangChain's composable middleware with per-layer testing, Datadog's 5-layer verification pyramid. Key rule: live LLM tests never run in CI. See chapter 11.
- [x] What pass@k / pass^k thresholds do teams target before promoting an agent configuration to production? — pass^k is the production metric. 70% success = 97% pass@3 but 34% pass^3. Three enterprise tiers: internal (74-90%), customer-facing (limited at pass^8), autonomous (not ready). Promotion gates require pass^k stability across multiple k. Promptfoo recommends --repeat 3 minimum; high-reliability teams run k=5 or k=10. See Ch18.
- [x] How effective is the "meta-ralph" pattern — a ralph that optimizes other ralphs via eval feedback? — Five independent implementations exist: OpenAI Self-Evolving Agents, Weco tree-search, Arize PromptLearning (+6% SWE-bench), IBM AutoPDL (up to 67.5pp gains), Evidently mistake-driven. The eval script is the only domain-specific component. See Ch18.
- [x] What does a "rippable" harness look like in practice? — Permanent layers (context, constraints, safety) vs temporary (reasoning optimization, loop detection, planning scaffolding). Vercel removed 80% of tools and improved. Manus refactored 5x in 6 months. See chapter 12.
- [x] How do teams calibrate loop fingerprint thresholds (3 repeats? 5?) for different task types? — Production systems converge on 3 consecutive repeats for stuck detection. ralph-claude-code uses 3 loops/no changes, 5 same errors, 70% output decline. Boucle's 220-loop study validates mechanical counting over agent self-assessment. See Ch16.
- [x] What does multi-agent coordination look like at scale (1M+ lines)? — Cursor's planner-worker-judge: flat coordination fails, optimistic concurrency fails, role-based hierarchy succeeds. Workers must be fully independent. See Ch15.
- [x] What concrete, cookbook-ready ralph patterns are practitioners sharing? — PRD-driven (3 implementations), two-phase plan-then-build, TDD loop, guardrails accumulation, permission-gated, stale recovery. All converge on 5 shared properties. See Ch17.
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
- [x] What does long-running agent operation (30+ days) teach about state design that shorter loops miss? — Four competing memory architectures (observational, graph, self-editing, RAG), five compression failure modes, and the compound failure math (85% per step → 20% for 10 steps). Restorable compression (keep pointers, not content) is the emerging best practice. Periodic fresh starts beat accumulated memory. See Ch19.
