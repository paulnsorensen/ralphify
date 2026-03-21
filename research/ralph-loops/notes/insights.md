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

## Ralphify-Specific
- **Ralphify's command system naturally supports the "commands as verifiers" pattern.** Running tests/metrics as commands and injecting results into the prompt is exactly what Spotify and Karpathy do — ralphify just needs to formalize verification as a first-class concept.
- **Agent skills as portable packages is a validated trend.** Ralphify's skill system aligns with the industry direction of installable, reusable instruction sets.
- **The autoresearch pattern maps directly to a ralph.** editable asset = code, commands = run experiment + extract metrics, RALPH.md = program.md. This is the highest-value cookbook example to build.
- **The PRD-driven ralph pattern (snarktank/ralph) is the most practical for product development.** prd.json with acceptance criteria + progress.txt learning log + fresh context per iteration. Directly implementable as a ralphify cookbook recipe.
- **Output redirection to prevent context flooding is a critical technique for RALPH.md prompts.** `> run.log 2>&1` then `grep` for metrics. Verbose command output kills agent performance.
