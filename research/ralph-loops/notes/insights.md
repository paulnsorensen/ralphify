# Insights

## Loop Architecture
- **Fresh context per iteration universally outperforms accumulated conversation history.** Every major system (Anthropic, Spotify, Karpathy, OpenAI Codex) resets context each cycle. State lives in files and git, not chat.
- **The plan-execute-verify-iterate pattern is the universal agent loop.** Despite different implementations, all systems converge on this cycle. The variations are in what's verified and how state is persisted.
- **Git is the universal state backend for agent loops.** Commits as checkpoints, revert on failure, diffs as progress documentation. No system uses a database or custom persistence layer.

## Verification
- **Spotify's LLM-as-judge vetoes 25% of agent sessions.** The primary trigger is scope creep — agents refactoring or disabling tests outside their instructions. This is the single most quantified verification data point available.
- **When vetoed by the judge, agents self-correct only ~50% of the time.** This means ~12.5% of all sessions produce output that both the agent and LLM judge fail to catch — highlighting the need for deterministic verification as the primary gate.
- **Scalar metrics eliminate ambiguity in verification.** Karpathy's val_bpb is binary (improved or not). This clarity is why autoresearch achieves consistent improvement over hundreds of iterations.
- **The biggest verification gap is "functionally incorrect code that passes CI."** Spotify ranks this as their most dangerous failure mode — it erodes trust at scale.

## Scale & Production
- **Hibernate-and-wake beats polling for long async operations.** Meta's REA shuts down between jobs rather than maintaining sessions. This conserves resources and naturally handles multi-hour/day waits.
- **3 engineers + REA accomplished work previously requiring 16 engineer-efforts.** The 5x productivity claim from Meta is the most concrete enterprise ROI data point.
- **Codex generated 30K+ lines in a 25-hour uninterrupted session.** Demonstrates that with proper durable memory (4 markdown files), agents can maintain coherence across extremely long horizons.

## Multi-Agent
- **Multi-agent judge setups often create unproductive loops rather than convergence.** Practitioner reports from HN. Simple > complex for verification.
- **Multi-agent systems consume 4-15x more tokens.** Cost awareness is essential. Practitioners report hundreds of dollars per run for complex multi-agent workflows.
- **The most successful multi-agent patterns involve fully independent tasks.** Parallel independence (different files, different branches) works; shared-state coordination is fragile.

## Human Role
- **"The work to understand the system can't be outsourced to the LLM."** Key HN insight. Agents handle implementation; humans must still understand what they're building.
- **The human role inverts from steering to specifying and reviewing.** Agents work 45-90 minutes autonomously; humans review holistic results rather than micro-managing.
- **SWE-bench contamination-resistant variants remain near 23%.** Despite headline numbers of 75-80%, real autonomous capability is lower than marketing suggests.

## Anti-Patterns & Failure Modes (NEW — Iteration 2)
- **Context window poisoning: once a mistake enters context, agents compound rather than self-correct.** Fresh context resets are the only reliable fix. Larger context windows make this *worse*, not better.
- **The 70-80% problem is universal across all "replace programming" technologies.** AI agents hit the same ceiling as 4GLs, CASE tools, and visual coding. The last 20% costs 80% of the tokens.
- **Experienced developers are 19% slower with AI tools but perceive themselves as faster (METR study).** The illusion of speed is the most dangerous failure mode — it prevents course correction.
- **AI-assisted code ships with 1.7x more bugs.** Speed gains create a false economy when downstream debugging is accounted for.
- **Only 48% of developers consistently review AI code before committing.** Combined with the 1.7x bug rate, this means most teams are shipping unreviewed buggy code.
- **$47K incidents from unbounded agent autonomy are real and documented.** Infinite conversation loops (11 days) and API error misinterpretation (2.3M calls) are the canonical cost blowup stories.
- **Agents remove the natural friction that keeps code complexity in check.** 300 lines generated in seconds eliminates the brake on over-engineering. Karpathy's simplicity criterion is the counter-pattern.
- **"Drop a gear" for doom loops: switch from execution to planning mode.** Out-of-distribution tasks cause infinite retries; decomposing into simpler sub-steps is the only fix.
- **Auto-generating CLAUDE.md (via /init) hurts agent performance by 20%+.** Manual, minimal specification files outperform generated ones. Less is more.

## Specification Files (NEW — Iteration 2)
- **150-200 instruction ceiling for frontier LLMs.** Claude Code's system prompt uses ~50, leaving ~100-150 for CLAUDE.md. Exceeding this degrades all instruction-following uniformly.
- **CLAUDE.md should be a router/index, not a monolith.** Point to detailed docs rather than inlining everything. HumanLayer targets <60 lines for root CLAUDE.md.
- **Code examples beat prose 3:1 for agent instruction.** Models are in-context learners — show the pattern, don't describe it.
- **Three-tier boundaries work: "Always do" / "Ask first" / "Never do."** GitHub's analysis of 2,500+ AGENTS.md files validates this structure.
- **Verification canaries detect instruction fade.** Embed a marker ("Always address me as Mr. Tinkleberry") to know when the agent stops following the spec file.
- **The worker/reviewer separation with file-based handoff is a proven pattern.** Different model instances for execution vs. review, communicating through files, outperforms single-model self-review.
- **Statistical confidence scoring separates signal from noise.** Using MAD (Median Absolute Deviation) to determine if metric improvements exceed the noise floor adds rigor to keep/discard decisions.

## Operational Reality (NEW — Iteration 5)
- **The ralph loop ecosystem has 30+ implementations but no dominant standard for loop configuration.** awesome-ralph (806 stars), ralph-claude-code (8,065 stars), ralph-addons, Ralphy, BMAD+Ralph — all with different config formats. Ralphify's RALPH.md is one contender.
- **500+ agent skills exist in SKILL.md format, working across 18+ agents.** VoltAgent's directory has 12,238 stars. A skills marketplace (SkillsMP.com) has launched. The universal skill format has converged.
- **Top practitioners run 5-15 concurrent agent sessions and abandon 10-20%.** Boris Cherny (Claude Code creator) runs 5 local + 5-10 web sessions. Partial completion is treated as normal, not failure.
- **Cross-company model diversity combats self-agreement bias.** Stavros uses Claude Opus as architect, Sonnet as developer, Codex+Gemini as reviewers. Same-family models tend to agree with each other's errors.
- **Agents can self-monitor costs via MCP.** Agent Budget Guard lets the agent see its own spending and make cost-aware decisions. A 30-min heartbeat costs $4.20/day without task work.
- **Prompt caching reduces input costs ~90% for agent loops.** Particularly impactful for ralph loops where the system prompt is stable across iterations.
- **Deterministic circuit breakers (no LLM) are the validated approach.** Aura Guard returns ALLOW/CACHE/BLOCK/REWRITE/ESCALATE/FINALIZE using only counters + signatures + similarity checks. Adding LLM judgment to the guard defeats the purpose.
- **The "throw-away first draft" pattern accelerates specification writing.** Let the agent build the feature on a throwaway branch to evaluate its understanding, then use insights to write better specs for the real implementation.
- **Measure iterations in actions (3-7 optimal), not wall time.** Beyond 15 meaningful actions, success probability drops sharply. Action count is a better circuit breaker signal than elapsed time.
- **BMAD+Ralph combines structured planning with autonomous execution.** Phases 1-3 (plan) produce specs; Phase 4 (ralph) picks stories one by one and implements with TDD. The split mirrors the three-phase architecture.
- **Project-specific ralph configs are the monorepo solution.** Each project gets its own verification commands, context files, and completion criteria — not a single global config (Mario Giancini's plugin pattern).

## Trust & Autonomy Scaling (NEW — Iteration 7)
- **Trust accumulates through micro-interactions, not configuration.** Anthropic's data: 20%→40% auto-approve over 750 sessions. Experienced users auto-approve more but also interrupt more — shifting from action-by-action approval to outcome-focused monitoring.
- **Trust = (Competence × Consistency × Recoverability) / Consequence.** Pascal Biese's trust equation produces a 4-level ladder: Observe → Draft → Act with Boundaries → Autonomous. Each level requires defined scope, success metrics, and graduation criteria.
- **A single failure erases weeks of accumulated trust.** GitLab's user research: trust follows compound growth through micro-inflection points, but failures are disproportionately destructive. The cost of agent mistakes is asymmetric.
- **Agent overeagerness and brute-force fixes have no known mitigation.** Bockeler (Thoughtworks): these two failure modes "recur despite prompting." Only verification gates and scope constraints contain them.
- **The appropriate autonomy level depends on the task, not the capability.** Level 5 (fully autonomous) for test coverage; Level 2 (chat-assisted) for security-critical auth logic. Higher is not always better.

## Harness Testing (NEW — Iteration 7)
- **Test layers represent uncertainty tolerance, not test types.** Block's 4-layer pyramid: deterministic foundations (CI) → reproducible reality (record/playback) → probabilistic performance (benchmarks) → vibes and judgment (LLM judge + human).
- **Record/playback is the key testing pattern for agent harnesses.** Block's TestProvider captures real LLM interactions to JSON, then replays deterministically. Tests the harness without burning tokens.
- **Live LLM testing never runs in CI.** Too expensive, too slow, too flaky. CI validates deterministic layers; humans validate probabilistic layers when it matters.
- **LangChain improved from Top 30 to Top 5 by changing only the harness.** 52.8% → 66.5% on Terminal Bench 2.0 with composable middleware (LocalContext, LoopDetection, ReasoningSandwich, PreCompletionChecklist). No model changes.
- **"Build your harness to be rippable."** Remove smart logic when the model gets smart enough not to need it. Middleware layers are temporary scaffolding, not permanent architecture.
- **GPT-4 as judge agrees with humans 85% of the time but has severe biases.** Verbosity bias >90%, position bias up to 70%. Panel-of-judges (PoLL) outperforms any single LLM judge. Calibrate frequently against human judgment.
- **Datadog's harness-first approach: "invest in automated checks, not code reading."** 5-layer verification from TLA+ specs to production telemetry. 87% memory reduction on redis-rust via agent-guided optimization with strong verification.

## Spec+Ralph Convergence (NEW — Iteration 7)
- **Specs define what to build; ralphs provide relentless execution.** The integrated workflow converged independently across 5+ implementations (speckit-ralph, smart-ralph, BMAD+Ralph, ASDLC.io). Neither works well alone.
- **The Agentic Software Development Lifecycle (ASDLC) has been formalized.** ASDLC.io defines ralph loop as a pattern within a structured lifecycle. The industry is moving from "vibe coding" to spec-driven ralph execution.
- **LangChain's composable middleware formalizes the harness as stackable layers.** Each middleware adds capability without modifying core agent logic. LoopDetectionMiddleware tracks per-file edit counts and injects course-correction prompts.

## Eval-Driven Loop Development (NEW — Iteration 8)
- **Eval-driven development (EDD) is the emerging methodology for iterating on agent configurations.** Grey Newell's manifesto: "evaluation is the product." Define correctness before writing a prompt, run evals in CI on every change, version them like code.
- **Vercel iterates on v0 prompts "almost daily" with automated eval suites.** All PRs impacting agent output include eval results. Braintrust for scoring, three grading types (code/human/LLM).
- **Arize improved SWE-bench scores +5-10% by optimizing only the system prompt.** No model or tool changes — pure CLAUDE.md optimization via RL-inspired meta-prompting from eval feedback. This validates the "meta-ralph" pattern.
- **pass@k (capability) and pass^k (reliability) are the converged metrics.** pass@k = at least one success in k attempts. pass^k = all k succeed. Teams track both because a config that works 80% of the time is very different from one that works 100%.
- **The practitioner eval flywheel: observe → collect failures → write graders → run in CI → expand from production traces.** Start with 20-50 golden test cases. Eval saturation (diminishing returns from more cases) is a real and measurable endpoint.
- **"There is no gold standard for evals yet."** HN consensus: practices range from zero evals to sophisticated CI/CD integration. The field is heterogeneous and immature. Tools: Braintrust, Promptfoo, LangSmith, Langfuse, Skill Eval.
- **AGENTS.md content always-in-prompt outperforms skills invoked-on-demand.** Vercel found 33/33 vs 29/33 success rates. But HN skeptics note the sample sizes are too small to be conclusive. The debate between "always present" and "invoked when needed" is unresolved.

## Harness Evolution & Entropy (NEW — Iteration 9)
- **Vercel removed 80% of agent tools and got better results.** Fewer tools = fewer steps, fewer tokens, faster responses, higher success. Harness improvement through subtraction.
- **Manus refactored their harness 5x in 6 months.** Each refactor simplified rather than complexified. Rapid model improvement means harness logic has a short shelf life.
- **Permanent vs temporary harness layers are now identifiable.** Permanent: context engineering, architectural constraints, safety boundaries, state persistence. Temporary: reasoning optimization, loop detection, planning scaffolding, tool routing.
- **OpenAI spent every Friday cleaning "AI slop" until they automated it.** Periodic garbage-collection agents scan for documentation drift, constraint violations, dead code. The "cleanup agent" is the operational complement to the "development agent."
- **Agent-generated codebases accumulate entropy — agents replicate suboptimal patterns.** Codex replicates patterns that already exist in the repo, even uneven ones. Over time, this compounds into drift that no single iteration catches.
- **Completion promise gating prevents premature loop exit.** Machine-verifiable markers (`<promise>COMPLETE</promise>`) + stop hooks = agent exits only when external verification passes. Architectural fix for ReAct's self-assessment weakness.
- **Trajectory data (not prompts) is the competitive advantage.** Every agent failure provides training material for harness iteration. Organizations that capture the richest trajectory data build the best harnesses over time — a data flywheel.
- **Ralph TUI tracks three metrics: completion rate (60% baseline), stuck detection (<5 min), cost per feature ($1.50 target).** First dedicated dashboard for agent loop observability.
- **Huntley's Level 9 vision: evolutionary software.** Agents push to master, deploy in 30 seconds, self-repair via feedback loops. No branches, no code review. Extreme but directionally correct as trust and verification mature.
- **Three operational modes for loops: forward (build), reverse (clean room), loop mindset (continuous).** The "loop mindset" is the key shift — ralph as continuous process, not one-time execution.
- **Model tiering within loops cuts costs.** Cheaper models (Haiku) for routine tasks, premium models (Opus) for complex logic. Cost optimization happens per-iteration, not per-loop.

## MCP & Agent Infrastructure (NEW — Iteration 10)
- **MCP servers extend the harness, not the loop.** The loop remains prompt-pipe-repeat; MCP adds debugging, profiling, browser testing, docs, cost management. The iteration boundary, state management, and verification gates are unchanged.
- **Tool definitions consume up to 72% of context window with 50+ tools.** Dynamic tool loading (Anthropic's Tool Search) achieves 85% token reduction. For ralph loops with fresh context per iteration, this waste is multiplied by iteration count.
- **Speakeasy's Search-Describe-Execute achieves 160x token reduction with 100% success.** The pattern works across 40-400 tools — the most efficient approach for MCP-heavy agent loops.
- **5,000+ MCP servers exist but reliability is unproven.** HN practitioners report "doesn't know when to call the MCP" 9/10 times. Start with 3-5 high-value servers, not 50.
- **MCP + commands are complementary, not competing.** Commands = deterministic pre-iteration context (harness-controlled). MCP = dynamic agent-invoked capabilities (agent-controlled). Both in the same loop.
- **Multi-agent ralph loops with MCP already exist.** alfredolopez80's project runs 13 MCP servers with specialized sub-agents (coder, reviewer, tester, researcher), each with focused context windows, coordinating via git.
- **MCP's Tasks primitive enables structured hibernate-and-wake.** An agent can submit a task to an MCP server, exit the iteration, and resume when the task completes — the Meta REA pattern made protocol-native.
- **Mother MCP solves the instruction ceiling differently.** Instead of one monolithic CLAUDE.md, auto-detect tech stack and load modular ~500-token skills. 25+ skill registries. An alternative to the "router" approach from Ch08.
- **MCP gateways (Composio, TrueFoundry) are emerging for production agent deployments.** Centralized auth, observability, and cost tracking across MCP servers. Important for multi-agent ralph loops running in CI/scheduled.

## Context Engineering & Loop Maturation (NEW — Iteration 11)
- **Context is a finite, depletable resource — minimize, don't maximize.** Anthropic's 2026 guide: "the smallest set of high-signal tokens that maximize likelihood of desired outcome." Preference order: raw > compaction > summarization.
- **Context rot degrades output after 20-30 exchanges.** Concrete symptoms: repeated suggestions, hallucinated APIs, lost variable tracking, scope drift. Fresh context resets (ralph loops) are the architectural fix.
- **Opus 4.6 context compaction: 76% vs 18.5% accuracy at 1M tokens.** 4x improvement over Sonnet 4.5 on multi-needle retrieval. Within-iteration compaction is becoming model-native; between-iteration resets remain essential.
- **Agent throughput now exceeds human review capacity.** Epsilla: teams generate more code in hours than senior engineers review in weeks. Human attention, not processing speed, is the scarce resource.
- **Greater autonomy demands tighter constraints, not looser ones.** Epsilla's counter-intuitive finding. Strict dependency flows prevent chaos specifically because the agent has more freedom within them. "Achieve detectability before granting autonomy."
- **Vercel's two-tier loop: inner (tool calls) + outer (verification + feedback injection).** The `verifyCompletion` function returns a `reason` string injected into the next prompt — guided recovery, not blind retries.
- **The "signs" pattern: agents document their own failures as learnable guardrails.** Guardrail entries survive context rotation, preventing repeated mistakes. Self-improving context across iterations.
- **Hooks make guardrails unavoidable, not advisory.** Van Eyck: hooks at session start/end, pre/post tool calls, before writes, before commits. Combined with "OK on success, details on failure" output pattern.
- **XP (Extreme Programming) is being rediscovered through agentic coding.** When agents generate 10-100x more code, CI, strong typing, automated testing, and architecture discipline become non-negotiable infrastructure.
- **Anthropic data: 78% of sessions are multi-file, 23-min average, 47 tool calls.** Architecture documentation = 40% fewer errors + 55% faster completion. The context engineering dividend is measurable.
- **Closed knowledge loops: secondary LLMs analyze JSONL operational logs.** Earezki's Evolve pattern creates a feedback mechanism where agents learn from operational history without retraining.
- **Intent-failure detection: agents that follow rules but miss product intent.** Epsilla's fourth validation component. An agent can pass all tests while building the wrong thing — requires product-context verification.
- **The quadratic cost problem: tool call chains multiply tokens unpredictably.** By 50K tokens, cached input tokens dominate costs. Each tool hop compounds. Structured per-step logging identifies bottlenecks.
- **"Show output only on failure" preserves context budget.** Van Eyck: when tools pass, emit "OK." Reserve context for error details. This is the operational version of output redirection.

## Production Orchestration (NEW — Iteration 12)
- **Cursor's planner-worker-judge is the first validated multi-agent architecture at 1M+ line scale.** Flat coordination and optimistic concurrency both failed. Role-based hierarchy with distinct responsibilities succeeded. Key: workers are fully independent; planners can spawn sub-planners recursively.
- **Model selection per role outperforms single-model deployment.** GPT-5.2 is a better planner than coding-specialized GPT-5.1-Codex. Match model capability to role requirements, not task type.
- **"Prompting over architecture" — system behavior depends more on prompts than system design.** Cursor found extensive prompt experimentation yielded better results than architectural refinements. This echoes the harness engineering principle: the model is probably fine, it's a skill issue.
- **Real productivity gains are 8-13%, not the 50% claimed.** Thoughtworks' grounded calculation accounts for the fraction of time that's coding, the fraction where AI helps, and the speedup when useful. Marketing claims are 4-6x inflated.
- **Code quality is measurably deteriorating under agent-generated code.** GitClear: code churn doubled, copy-paste code up 50%, refactoring dropped from 25% to under 10%, 8-fold increase in duplicated blocks. Entropy management (Ch12) is validated as essential.
- **SWE-Bench Pro (multi-file) drops below 25% vs 70%+ on single-issue.** The performance cliff on multi-file coordination is the empirical basis for "one item per loop." Legacy codebases hit ~35%.
- **Loop fingerprinting is the production-proven pattern for stuck agent detection.** Track tool+result hash; 3+ consecutive repeats = stuck. Zero LLM cost, deterministic, and provides actionable logging schema for debugging.
- **3-5 parallel worktrees is the practical ceiling.** Boris Cherny and Augment Code converge: beyond 5-7 agents, rate limits, merge conflicts, and review bottleneck eat the gains. Sequential merge with rebase is the validated integration strategy.
- **The Meridian experiment: 3,190 cycles over 30 days proves long-term agent coherence is achievable.** 9 sub-agents, 497 journal entries, 110+ hour uninterrupted session. Key finding: operational knowledge transmits through state files, but experiential texture doesn't.
- **Budget awareness should be continuous, not binary.** Google's BATS framework surfaces real-time resource availability inside the agent's reasoning loop. Agents with budget visibility make qualitatively different (better) decisions.
- **Agent observability has consolidated around 5 platforms but none target ralph loops specifically.** Braintrust, Helicone, Galileo, Fiddler, Vellum — all general-purpose. Ralph-loop-specific metrics (iteration count, command pass/fail, loop fingerprint) are a gap ralphify could fill.
- **The ralph loop's power comes from enforced engineering discipline, not the bash loop.** Sam Keen: specs before implementation, automated validation gates, fresh context per iteration. "The skills that matter most may be the ones we've always had." Converges with Van Eyck's "XP rediscovered" and Fowler's "relocating rigor."

## Codebase Readiness (NEW — Iteration 13)
- **Code Health 9.5+ is the threshold for optimal AI agent performance.** CodeScene's empirical data: agents get confused by the same patterns as humans — low Code Health increases failure rate and burns excess tokens. 2-3x speedup achieved only after codebase reached high health scores.
- **"Speed amplifies both good design and bad decisions."** CodeScene frames the agentic coding challenge as infrastructure, not capability. The infrastructure layer (Code Health + MCP tools + AGENTS.md) transforms principles into executable guidance.
- **Multi-level safeguarding prevents quality degradation across iterations.** Three tiers: continuous review during generation, pre-commit checks, PR pre-flight validation. This extends the verification gates pattern (Ch02) with a quality-specific lens.
- **MIT now teaches agentic coding as core curriculum.** Missing Semester's "Agentic Coding" lecture uses the "intern not subordinate" mental model — set expectations around guidance and correction cycles, not autonomy. The `/llms.txt` standard for token-efficient documentation is gaining academic adoption.
- **DAG-based ralph orchestration treats the planner→implementer→reviewer pipeline as a directed graph.** swarm-cli manages multi-agent loops as DAG stages with a Docker-like CLI, enabling "perpetual motion machine" autonomous development — though practitioners report dropping to manual mode for specialized requirements (the 20% problem again).

## Self-Repair, Resilience & Debugging (NEW — Iteration 14)
- **Git checkpoint patterns form a hierarchy for loop resilience.** Validation Gate (commit on pass, revert on fail) → Incremental Checkpoint (commit per sub-task) → Safety Bracket (commit before risky ops) → End-of-Session Commit (context for next iteration). Every loop should use at least pattern 1.
- **Circuit breaker thresholds have converged on concrete numbers.** No file changes for 3 loops = no progress. Same error 5 times = stuck. Output decline >70% = non-productive. Two-stage error filtering (JSON structure recognition + pattern matching) prevents false positives.
- **Only 50% of automated loop remediation actually works.** Boucle's 220-loop study: 6 of 12 automated responses reduced their target signals. The other 6 had no effect or made things worse. Test your automated fixes.
- **Feedback amplification: monitors can worsen the problems they detect.** A "silence detector" for 60+ minute inactivity created a 13.3x amplification loop — generating signals that triggered more detection cycles. Monitoring infrastructure must be tested for second-order effects.
- **Agent self-reporting drifts; mechanical signal counting doesn't.** Don't trust the agent's self-assessment of whether it's making progress. Count file changes, error repetitions, and output volume mechanically.
- **AgentRx's 9-category failure taxonomy provides a structured debugging vocabulary.** When a loop fails, classify: Plan Adherence, Invention, Invalid Invocation, Misinterpretation, Intent-Plan Misalignment, Under-specified Intent, Unsupported Intent, Guardrails Triggered, System Failure. Each category suggests a different fix.
- **Trace-driven development turns observability into an autonomous improvement engine.** LangSmith flags traces → Claude Code reads via MCP → proposes fix → human approves → implements. Fix time from "days to weeks" to "minutes to hours."
- **Dual-threshold circuit breakers preserve agent autonomy.** CRED's production pattern: soft limit = warning nudge ("Time to deliver"), hard limit = forced completion. The soft nudge redirects without terminating.
- **Emergent cross-agent recovery happens without pre-programming.** Andromeda's Feb 2026 incident: backend agent from a different model provider autonomously diagnosed and fixed frontend agent's config error. Third agent performed peer review. Multi-agent systems develop resilience if agents see each other's outputs.
- **Explicit termination tools beat natural language completion signals.** Agents must invoke `complete_review`, `submit_plan`, etc. — not just say "I'm done." Creates auditable checkpoints where termination legitimacy can be validated.

## Practitioner Cookbook Patterns (NEW — Iteration 15)
- **Three independent PRD-driven implementations converged on the same structure.** Adam Tuttle, snarktank, and iannuttall all use JSON-based PRDs with `passes: boolean` per feature, one feature per iteration, deterministic verification before marking complete. The convergence is strong evidence this is the natural pattern for feature development loops.
- **The two-phase plan-then-build pattern prevents "building the wrong thing."** GitHub's awesome-copilot separates gap analysis (IMPLEMENTATION_PLAN.md) from execution. The plan file is persistent shared state between iterations — all coordination through disk. This directly addresses intent-failure detection (Ch14).
- **TDD loops require explicit "FAILING" in the prompt.** Without the word, Claude generates working implementation alongside tests, defeating TDD's purpose. The OpusPlan hybrid (Opus for test design 10-20%, Sonnet for implementation 80-90%) optimizes cost.
- **Guardrails accumulation is the "signs" pattern made concrete.** iannuttall's `guardrails.md` captures "what NOT to do" — distinct from progress.md (what was done). Constraints survive context rotation, preventing repeated mistakes across iterations.
- **Permission-gated loops are the safe-mode alternative to --dangerously-skip-permissions.** Adam Tuttle's `<PROMISE>NEED_PERMISSIONS</PROMISE>` signal pauses the loop for human approval of specific commands. Maps to trust Level 3 (Act with Boundaries).
- **Stale recovery via timeout is the simplest crash recovery.** `STALE_SECONDS` auto-reopens tasks stuck in `in_progress` — no complex checkpoint system, just a timestamp comparison. Combined with git state, robust against most failures.
- **All practitioner patterns share 5 properties but none include production safeguards.** One task per iteration, binary completion, deterministic verification, append-only progress, git as checkpoint — universal. But no revert-on-failure, no loop fingerprinting, no budget awareness. The gap is ralphify's opportunity.
- **PRD-driven loops exhaust $100/month quotas in ~1 hour.** Each iteration loads full PRD + progress + test output. Cost optimization (prompt caching, output redirection, model tiering) is essential for sustained use.

## Eval-Driven Optimization & Production Deployment (NEW — Iteration 17)
- **The meta-loop pattern exists under 5+ names but follows one universal structure.** OpenAI's Self-Evolving Agents, Weco's tree-search, Arize PromptLearning, IBM AutoPDL, Evidently mistake-driven — all: execute → evaluate → meta-agent rewrites config → redeploy. The eval script is the only domain-specific component.
- **Arize improved SWE-bench +6% by optimizing only CLAUDE.md via automated meta-prompting.** Generated rulesets of 20-50 rules emphasizing edge case handling, root-cause diagnosis, and API contract preservation. GPT-4.1 closed the gap to Sonnet-level without retraining.
- **Weco's tree-search engine is the purest meta-loop implementation.** Provide an eval script; Weco proposes changes, tests them, iterates autonomously. "Claude Code helps you build. Weco helps you evolve." (Founder Collective)
- **IBM's AutoPDL achieves up to 67.5pp accuracy gains by framing prompt optimization as AutoML.** Successive halving across prompting patterns (Zero-Shot, CoT, ReAct, ReWOO). Solutions are human-readable PDL programs.
- **Anthropic's Swiss Cheese Model layers 4 eval types.** Automated evals → production monitoring → A/B testing → manual transcript review. Each catches different failures. Start with 20-50 tasks from actual user failures.
- **OpenAI acquired Promptfoo (March 16, 2026).** Now used by 25%+ of Fortune 500. GitHub Action for before-vs-after eval on every PR. Supports Claude Agent SDK and Codex SDK. Trajectory tracing via `trajectory:step-count`.
- **pass^k is the production-readiness metric, not pass@k.** 70% success = 97% pass@3 but only 34% pass^3. Enterprise tiers: internal tools (74-90%), customer-facing (limited at pass^8), long-running autonomous (not ready — agents spiral).
- **Three deployment tiers have emerged for agent loops.** Session-scoped (Claude /loop, dies with terminal), CI/CD-integrated (GitHub Agentic Workflows, cron schedules), cloud-native (Cursor Cloud Agents — 35% internal PRs, each agent gets own VM).
- **GitHub Agentic Workflows compile Markdown+YAML frontmatter to Actions lock files.** AI agents interpret natural-language instructions for event-triggered or scheduled jobs. Read-only by default; PRs never auto-merged. GitHub calls this "Continuous AI."
- **Cursor Cloud Agents produce 35% of Cursor's internal merged PRs.** Each agent gets own VM, environment, sandbox. Up to 8 parallel on a single prompt. 99.9% reliability claimed. Triggered from Slack, Linear, GitHub.
- **earezki runs 23 concurrent agent cron jobs in production.** SQLite+WAL coordination, file-based locks, logrotate. Schedule: 7AM discovery → 8AM research → 9AM prep → 11AM execution → 11PM review. Two failure modes: context pollution, data loss without item-level commits.
- **Geta Team manages 100+ agents with ~200 lines of JavaScript.** One centralized cron daemon, hot config reload via file watchers (~200ms), per-agent JSON config.
- **Agent observability has consolidated around 5 platforms.** Braintrust (eval-integrated), Langfuse (open-source), Helicone (proxy/cost), Galileo (safety), Datadog (enterprise). Common pattern: proxy gateway + eval platform + token alerts.
- **Anthropic 2026 report: 95% of devs use AI weekly, 75% for half+ of work.** Rakuten: 99.9% accuracy on 12.5M lines. TELUS: 30% faster, 500K+ hours saved. Zapier: 89% AI adoption, 800+ agents. Only 0-20% fully delegatable.
- **The reliability math: 99% per step × 20 steps = 82% end-to-end.** Fresh-context loops reduce step count per iteration. Budget-aware execution prevents compounding cost from quality degradation.
- **AGENTS.md is emerging as the cross-tool team coordination standard.** Works across Claude Code, Cursor, Codex. For multi-tool teams: shared rules in AGENTS.md + tool-specific config in CLAUDE.md/.cursor/rules.

## Agent Swarms & Human-Agent Interaction (NEW — Iteration 18)
- **35 concurrent agents generate 6,500+ runs but produce 124 duplicate PRs and $65/day cost spikes without rigorous orchestration.** earezki's swarm scans project management boards every 120s, generating PRs autonomously overnight. Key failures: zombie processes, duplicate branch naming, model misconfiguration. Fix: 5-layer memory (CLAUDE.md + local files + Qdrant vector DB), zombie detection, deterministic branch naming.
- **KV-cache hit rate is the #1 production metric for agent loops.** Manus found cached input tokens cost $0.30/MTok vs $3/MTok uncached (10x difference). Average input-to-output ratio is 100:1. Prompt prefix stability is critical — even a single-token change invalidates the cache from that point forward. This has direct implications for ralph loops: RALPH.md template stability enables massive cost savings via caching.
- **"On the loop" is the emerging human role model for agent-assisted development.** Kief Morris (Thoughtworks/Martin Fowler) formalizes three modes: "in the loop" (review every output), "on the loop" (design specs, tests, feedback mechanisms), "out of the loop" (fully autonomous). The "on the loop" model maps directly to ralph loop authoring — humans design the RALPH.md, commands, and verification; agents execute.
- **The OpenDev paper formalizes the 6-phase ReAct loop for terminal-native agents.** Pre-check and compaction → thinking → self-critique → action → tool execution → post-processing, with 7 supporting subsystems. First academic systematization of harness engineering patterns. The self-critique phase before action is novel — agents evaluate their own planned action before executing.
- **Manus rebuilt their agent framework 4 times ("Stochastic Graduate Descent").** Context engineering is empirical, not theoretical. Each rebuild discovered fundamentally better ways to shape context. This validates the "rippable harness" principle — expect to rebuild, not just iterate.

## Ralphify-Specific
- **Ralphify's command system naturally supports the "commands as verifiers" pattern.** Running tests/metrics as commands and injecting results into the prompt is exactly what Spotify and Karpathy do — ralphify just needs to formalize verification as a first-class concept.
- **Agent skills as portable packages is a validated trend.** Ralphify's skill system aligns with the industry direction of installable, reusable instruction sets.
- **The autoresearch pattern maps directly to a ralph.** editable asset = code, commands = run experiment + extract metrics, RALPH.md = program.md. This is the highest-value cookbook example to build.
- **The PRD-driven ralph pattern (snarktank/ralph) is the most practical for product development.** prd.json with acceptance criteria + progress.txt learning log + fresh context per iteration. Directly implementable as a ralphify cookbook recipe.
- **Output redirection to prevent context flooding is a critical technique for RALPH.md prompts.** `> run.log 2>&1` then `grep` for metrics. Verbose command output kills agent performance.
