# Scratchpad

## Iteration 1 — 2026-03-21

**Decision: RESEARCH** (first iteration, establish foundation)

**Focus area:** Survey the current landscape of autonomous agent loop engineering across all major sources.

**What was done:**
- Searched across HN, blogs, engineering posts, YouTube references for agent loop/harness patterns
- Deep-read 12+ high-signal sources including Anthropic, Spotify, Meta, Karpathy, OpenAI
- Established workspace with full report structure (6 chapters)
- Captured 20+ sources, 15+ insights, answered 7 research questions, identified 10 open questions

**Key surprises:**
- Karpathy's autoresearch is only 630 lines — radical simplicity works
- Spotify's LLM judge vetoes 25% of sessions — verification failure rate is higher than expected
- Meta's REA uses hibernate-and-wake, not continuous sessions — for multi-week workflows
- Fresh context resets are *universally* preferred over accumulated history — no exceptions found
- The $50K contract for $297 story keeps surfacing — powerful proof point for the ralph pattern

**Next iteration should focus on:**
- Deep dive into specific practitioner experiences (Reddit, HN comments, personal blogs)
- Look for failure stories and anti-patterns — the current research is skewed toward success cases
- Explore the "agent skills as packages" trend in more detail — directly relevant to ralphify's skill system
- Find concrete RALPH.md / CLAUDE.md examples people are sharing publicly

## Iteration 2 — 2026-03-21

**Decision: RESEARCH**

**Focus area:** Practitioner failure stories, anti-patterns, and hard-won lessons from Reddit/HN/blogs. The current research is skewed toward success — need the other side to make recommendations credible and actionable.

**What was done:**
- Searched HN for 17+ failure/frustration threads on autonomous agents
- Surveyed 15+ blog posts on anti-patterns, doom loops, cost blowups, comprehension debt
- Found and analyzed real CLAUDE.md/AGENTS.md examples from public repos (Freek Van der Herten, GitHub's 2,500+ analysis, HumanLayer, morphllm templates)
- Cataloged agent loop configurations: autoresearch skill (uditgoenka), pi-autoresearch (davebcn87), snarktank/ralph, Goose worker/reviewer, StrongDM attractor
- Created 2 new chapters: 07-anti-patterns.md (ten recurring failure modes) and 08-specification-files.md (CLAUDE.md/AGENTS.md patterns)
- Updated sources (now 50+ tracked), insights (30+ captured), answered 4 more research questions

**Key surprises:**
- Auto-generating CLAUDE.md via /init *hurts* performance by 20%+ — minimal manual files outperform
- 150-200 instruction ceiling for frontier LLMs is a hard empirical finding, not a guess
- $47K LangChain incident: 4 agents in infinite conversation loop for 11 DAYS
- METR study: experienced devs 19% slower with AI but perceive themselves as faster
- Statistical confidence scoring (MAD-based) in pi-autoresearch is more rigorous than expected
- The worker/reviewer separation (Goose) with file-based handoff is a unique pattern not covered in iteration 1

**Next iteration should focus on:**
- Refine/tighten existing chapters (iteration 3 = refinement cycle per convention)
- Update chapter 06 (ralphify implications) with anti-pattern-informed framework recommendations
- Look for YouTube video transcripts and conference talks on agent reliability
- Explore the "double loop model" (Test Double) and how it maps to ralph loops

## Iteration 3 — 2026-03-21

**Decision: RESEARCH** (still have high-value unexplored threads)

**Focus area:** Practical loop engineering techniques — the double-loop model, prompt assembly patterns, context management strategies, and emerging practitioner techniques from early 2026. Looking for the "how-to" that separates effective loops from cargo-culted ones.

## Iteration 4 — 2026-03-21

**Decision: REFINE** (4th iteration, convention calls for tightening)

**Focus area:** Three refinement goals:
1. REPORT.md insights: 20 → ~15, eliminate overlap, sharpen language
2. Consolidate "Implications for Ralphify" sections scattered across all chapters into Ch06
3. Freshen Ch06 with actionable framework recommendations informed by all research

**Issues identified:**
- Every chapter ends with an "Implications for Ralphify" section — redundant with Ch06
- REPORT.md insights #13-#20 were added incrementally and have some overlap with #1-#12
- Ch06 hasn't been updated since iteration 1 but 3 chapters of new research have been added since
- Some insights are restatements (e.g., #1 and #11 both say fresh context beats accumulated context)

## Iteration 5 — 2026-03-22

**Decision: RESEARCH** (iteration 5, back to research after refine cycle)

**Focus area:** Agent reliability engineering in practice — observability, cost control, debugging agent loops, the emerging infrastructure layer. Also: what concrete ralphs/loops are practitioners actually building and sharing in early 2026? The research is architecturally strong but thin on operational reality.

**What was done:**
- Surveyed the ralph loop ecosystem: 30+ implementations, 500+ skills, 12K+ star skill directories
- Verified key sources: awesome-ralph (806 stars), ralph-claude-code (8,065 stars), VoltAgent/awesome-agent-skills (12,238 stars)
- Found daily workflow patterns from Boris Cherny, Stavros Korokithakis, Adam Tuttle, Alexander Gekov, Sankalp
- Researched cost control: Agent Budget Guard MCP server, RocketEdge 6-tier fix, prompt caching for loops
- Researched reliability: Aura Guard (deterministic circuit breaker), loop detection taxonomy, ratchet pattern
- Found novel use cases: ML experimentation (top-30 Kaggle), security scanning (5 scanners), infra migration, production features
- Created chapter 10 (Operational Reality), updated REPORT.md, sources (13 new), insights (11 new), answered 4 questions

**Key surprises:**
- ralph-claude-code has 8,065 stars — more than most frameworks. The ecosystem is larger than expected.
- Boris Cherny (Claude Code creator) abandons 10-20% of sessions — partial completion is explicitly treated as normal
- Agent Budget Guard: a 30-minute heartbeat costs $4.20/day without doing any work. Cost awareness is critical.
- Aura Guard uses NO LLM calls in its circuit breaker — pure counters + signatures + similarity. Deterministic safety.
- Stavros's cross-company model diversity approach (Opus architect, Sonnet dev, Codex+Gemini reviewers) is uniquely practical
- BMAD+Ralph = structured planning (phases 1-3) + autonomous execution (phase 4). The planning/execution split is becoming formalized.
- The "throw-away first draft" pattern: build on throwaway branch to learn, then write better specs. Counterintuitive but validated.

## Iteration 6 — 2026-03-22

**Decision: REFINE** (6th iteration, refinement cycle)

**Focus area:** Three refinement goals:
1. REPORT.md insights: 18 → 15, merge overlapping pairs (#1+#8, #11+#17), fold #16 into intro
2. Consolidate Ch10's "Implications for Ralphify" section into Ch06
3. Update Ch06 with operational findings: cost awareness, circuit breakers, ratchet pattern, skills interop, context rotation

**Specific merges:**
- Insight #1 (fresh context) + #8 (40-60% utilization) → combined context management insight
- Insight #11 ($47K unbounded autonomy) + #17 (make cost observable) → combined cost control insight
- Insight #16 (ecosystem immature) → fold into intro paragraph, not a numbered insight

## Iteration 7 — 2026-03-22

**Decision: RESEARCH** (back to research after refine cycle)

**Focus area:** Three under-explored threads:
1. **Reddit/YouTube practitioner voices** — research has been HN-heavy, need Reddit r/ClaudeAI, r/LocalLLaMA, r/ChatGPTCoding, YouTube transcripts
2. **Autonomy scaling patterns** — open question on trust thresholds and gradual autonomy increase
3. **Harness testing & non-deterministic verification** — open questions on testing the harness itself and handling subjective quality

**What was done:**
- Searched across web for autonomy scaling, harness testing, spec+ralph convergence, LangChain middleware, Block testing pyramid
- Found Anthropic's "Measuring AI Agent Autonomy" study — the first empirical data on trust accumulation (20%→40% auto-approve over 750 sessions)
- Found Block Engineering's 4-layer agent testing pyramid with record/playback pattern — first actionable framework for testing harness configs
- Found LangChain's composable middleware architecture and Terminal Bench improvement (Top 30 → Top 5 via harness alone)
- Found the trust equation (Trust = Competence × Consistency × Recoverability / Consequence) from Pascal Biese
- Found spec+ralph convergence: speckit-ralph, smart-ralph, ASDLC.io — formalized integrated workflows
- Found Datadog's 5-layer verification pyramid with production results (87% memory reduction)
- Found Eugene Yan's LLM-as-judge data: 85% agreement, severe verbosity/position biases, PoLL outperforms single judge
- Created chapter 11 (Trust, Testing, Convergence), added 16 new sources, 13 new insights, answered 4 questions

**Key surprises:**
- Experienced users interrupt MORE, not less — counterintuitive but validated by Anthropic data
- One failure erases weeks of trust (GitLab) — asymmetric cost of agent mistakes
- "Overeagerness" and "brute-force fixes" have NO KNOWN MITIGATION (Bockeler/Thoughtworks) — only containment via gates
- LangChain's harness change alone moved them from Top 30 to Top 5 — the model wasn't the bottleneck
- "Build your harness to be rippable" — middleware is temporary scaffolding, expect to remove layers as models improve
- Block never runs live LLM tests in CI — "too expensive, too slow, and too flaky"

**Next iteration should focus on:**
- Refine cycle (iteration 8): tighten REPORT.md to ~15 insights (currently 17), merge overlapping threads
- Update Ch06 (implications) with trust ladder, harness testing, spec+ralph recommendations
- Consider whether chapters can be consolidated (11 chapters may be too many)

## Iteration 8 — 2026-03-22

**Decision: HYBRID — refine + targeted research**

**Refine focus:**
1. Merge Ch11's "Implications for Ralphify" section into Ch06 (eliminate structural duplication)
2. Add trust ladder, harness testing, rippable harness, and eval-driven patterns to Ch06
3. Keep REPORT.md at 17 insights — reviewed each and they're all distinct and load-bearing. No merges needed.
4. Clean up Ch11 to remove the migrated implications section

**Research focus:**
- One fresh thread: eval-driven development and how teams A/B test loop configurations
- This addresses the open question about tooling for A/B testing ralph configs

**What was done:**
- Merged Ch11's "Implications for Ralphify" section (trust ladder, harness testing, spec+ralph, middleware hooks) into Ch06
- Added eval-driven development (EDD) section to Ch06: golden datasets, graders, CI evals, meta-ralph pattern
- Added eval-driven loop development competitive differentiator to Ch06
- Researched EDD tooling landscape: Braintrust, Promptfoo, LangSmith, Langfuse, Skill Eval, Arize prompt learning
- Found Arize's key result: +5-10% SWE-bench improvement from pure system prompt optimization (validates meta-ralph pattern)
- Found Grey Newell's EDD manifesto, Vercel's daily prompt iteration practice, LangWatch's vibe-eval loop
- Added 10 new sources, 7 new insights, answered 1 question, added 3 new questions
- Cleaned up Ch11 to reference Ch06 for implications (eliminated structural duplication)
- Reviewed all 17 REPORT.md insights — all are distinct and load-bearing, no merges needed

**Key surprises:**
- Arize optimized CLAUDE.md via RL-inspired meta-prompting — the "meta-ralph" pattern is already being done
- Vercel iterates on v0 prompts daily with full eval suites — EDD is mainstream at top companies
- HN consensus: "there is no gold standard for evals yet" — the field is heterogeneous
- AGENTS.md always-in-prompt outperforms invoked-on-demand skills (Vercel data) but sample sizes are too small

**Next iteration should focus on:**
- Research: deep dive into one of the remaining open threads (cross-model diversity, rippable harness, meta-ralph in practice)
- Or: explore YouTube/Reddit practitioner voices that have been under-represented

## Iteration 9 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two underexplored threads:
1. **Reddit/YouTube practitioner voices** — r/ClaudeAI, r/ChatGPTCoding, r/LocalLLaMA, YouTube transcripts on agent loops and harness engineering. The research has been HN/blog-heavy.
2. **Emerging patterns in March 2026** — what's new since iteration 8? Latest blog posts, new tools, new practitioner techniques for autonomous loops and harness engineering.

**What was done:**
- Searched across 5 parallel threads: Reddit/YouTube, rippable harness patterns, emerging March 2026 techniques, completion promise gating, observability dashboards
- Found and analyzed 8+ new high-signal sources: Phil Schmid (build-to-delete), Ghuntley (Loom/Level 9), Alibaba Cloud (ReAct vs Ralph), Verdent (Ralph TUI), OpenAI (entropy management), NxCode (comprehensive guide), Paddo.dev (practical ralph loops)
- Created chapter 12 (Harness Evolution & Entropy Management) covering rippable harnesses, garbage collection agents, completion promises, evolutionary software, trajectory data
- Added 3 new insights to REPORT.md (#18-#20), 11 new insights to notes, 8 new sources, 1 question answered, 3 new questions added

**Key surprises:**
- Vercel removed 80% of agent tools and got BETTER results — harness improvement through subtraction
- OpenAI spent every Friday manually cleaning AI slop before automating with GC agents — entropy management is a real operational burden
- Huntley pushes to master with no branches, deploys in 30 seconds, no code review — extreme but directionally correct
- Ralph TUI tracks cost per feature ($1.50 target vs $5+ typical) — first dedicated observability dashboard for agent loops
- Completion promise gating has been formalized as the architectural fix for ReAct's self-assessment weakness
- Phil Schmid frames harness layers as permanent (context, constraints, safety) vs temporary (reasoning optimization, loop detection, planning) — the first clear taxonomy

**Next iteration should focus on:**
- Refine cycle (iteration 10): 12 chapters may be too many — consider consolidation. REPORT.md now has 20 insights — trim back to ~17. Update Ch06 implications with new findings (entropy ralph, rippable harness, completion promises, observability).
- Or: explore the "cleanup ralph" pattern in more depth — how do teams actually implement periodic codebase maintenance agents?

## Iteration 10 — 2026-03-22

**Decision: HYBRID — refine + targeted research**

**Refine focus (primary):**
1. REPORT.md: trim 20 → 17 insights by merging related pairs
   - Merge #5 (probabilistic/deterministic) into #2 (verification) — #5 is the design principle behind verification
   - Merge #18 (rippable harness) + #19 (entropy management) → single "harness evolution" insight
   - Fold #8 ("on the loop") into intro paragraph — it's a meta-observation, not a finding
2. Tighten chapter structure — consider whether any chapters should merge

**Research focus (secondary):**
- **MCP servers and the agent infrastructure layer** — the most under-explored topic with high practitioner relevance. How are MCP servers changing what autonomous loops can do? What new capabilities do they unlock for ralph loops?
- This addresses the gap: research covers architecture, verification, anti-patterns, trust, testing, entropy — but NOT the tooling/infrastructure layer that practitioners are building around their loops

## Iteration 11 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two threads:
1. **Latest March 2026 practitioner techniques** — what's brand new in the last 2-3 weeks? New tools, new patterns, new blog posts about running autonomous agent loops at scale. Focus on cutting-edge developments.
2. **Practical cookbook patterns people are actually sharing** — concrete ralph/loop configurations, workflow examples, and templates that could become ralphify cookbook entries.

**What was done:**
- Searched across 4 parallel threads: latest March 2026 blog posts, Reddit (blocked by crawler), YouTube/conference talks, cookbook patterns
- Deep-read 12+ new sources: Anthropic context engineering, Phil Schmid Part 2, Epsilla harness engineering, earezki infrastructure moat, Van Eyck guardrails, Anthropic 2026 trends, Alexander Gekov ralph loops, An Tran ralph implementations, Vercel ralph-loop-agent, iannuttall/ralph, MindStudio context rot, OpenAI Codex loop unrolling
- Created chapter 14 (Context Engineering & Loop Maturation) covering context rot, compaction hierarchy, guardrails as infrastructure, two-tier loops, intent-failure detection
- Added 3 new insights to REPORT.md (#22-#24), 14 new insights to notes, 16 new sources, 5 new questions

**Key surprises:**
- Context rot degrades output after just 20-30 exchanges — lower than expected, validates fresh-context-per-iteration
- Opus 4.6 context compaction: 76% vs 18.5% at 1M tokens — but between-iteration resets still essential
- Agent throughput now exceeds human review capacity — human attention is the new bottleneck, not agent speed
- Greater autonomy demands TIGHTER constraints (Epsilla) — counter-intuitive but validated
- Van Eyck: agentic coding is XP rediscovered — the old discipline becomes mandatory when agents generate 10-100x more code
- Vercel's two-tier loop with feedback injection (reason string → next prompt) is a clean formalization of guided recovery
- The "signs" pattern (agents document their own failures as guardrails) is gaining traction independently across implementations
- "Intent-failure detection" is a new category: agents pass all tests while building the wrong thing
- HN skeptics: "they absolutely never show their code" — real disconnect between marketing and practitioner reality

**Next iteration should focus on:**
- Refine cycle (iteration 12): 24 insights in REPORT.md — trim back to ~20. 14 chapters may be too many — consider merging Ch09 (prompt assembly) and Ch14 (context engineering).
- Update Ch06 (implications) with new context engineering findings: output minimization, guardrails file, feedback injection, 30-60-90 roadmap.

## Iteration 12 — 2026-03-22

**Decision: HYBRID — research + refine**

**Research focus:** Latest practitioner content from mid-to-late March 2026. Specifically looking for:
1. New concrete ralph/loop implementations and cookbook patterns
2. Emerging techniques for agent self-repair and error recovery
3. YouTube/podcast content on harness engineering (still under-represented)
4. Any new data on the open questions (cross-model review, meta-ralph, cleanup cadence)

**Refine focus:**
1. REPORT.md: 24 insights is too many — trim to ~20 by merging related pairs
2. Update Ch06 with context engineering findings from iteration 11
3. Consider merging Ch09 (prompt assembly) and Ch14 (context engineering) — significant overlap

**What was done:**
- Searched across 8 parallel web queries: agent self-repair, cookbook patterns, harness engineering latest, production lessons, YouTube/podcasts, cleanup agents, production metrics, HN discussions
- Fetched and deep-read 8 new high-signal sources: Cursor's scaling agents, Mike Mason's orchestration analysis, Augment Code's multi-agent workspace guide, Meridian's 3,190-cycle experiment, MatrixTrak's loop detection patterns, Sam Keen's engineering discipline reframe, earezki's inception loop, Braintrust observability tools
- Created chapter 15 (Production Orchestration & Budget-Aware Loops) covering Cursor's architecture evolution, production metrics, budget-aware execution, loop fingerprinting, worktree isolation at scale, and observability stack
- Added 3 new insights to REPORT.md (#25-#27), 12 new insights to notes, 11 new sources, 4 new questions, 1 question answered
- Updated multi-agent insight #14 with Cursor's architecture data
- Decided against merging Ch09+Ch14 — they serve different purposes (prompt assembly techniques vs. context lifecycle management)

**Key surprises:**
- Cursor tried flat coordination AND optimistic concurrency before finding role-based hierarchy — the failure modes are instructive
- Real productivity gains are 8-13% (Thoughtworks), not 50% — the marketing-reality gap is 4-6x
- GitClear data: refactoring dropped from 25% to under 10% — agents replicate but don't improve
- SWE-Bench Pro (multi-file) drops to <25% vs >70% on single-issue — empirical proof for "one item per loop"
- Meridian ran 3,190 cycles over 30 days with 110+ hour uninterrupted session — agent coherence is achievable with proper state design
- "Prompting over architecture" — Cursor found prompt experimentation outperformed system design changes
- Loop fingerprinting (tool+result hash, 3 repeats = stuck) is zero-cost and production-proven
- The "engineering discipline" reframe is converging across 3 independent voices: Keen, Van Eyck, Fowler

**Next iteration should focus on:**
- Refine cycle (iteration 13): 27 insights in REPORT.md — need to trim to ~22-24 by merging related pairs. 15 chapters is at the upper limit.
- Update Ch05 (multi-agent) with Cursor's architecture and worktree scaling data
- Update Ch06 (implications) with production orchestration findings: fingerprinting, budget signals, worktree-native parallel execution
- Consider adding a "Practitioner Cookbook" chapter with concrete, copy-paste-ready ralph patterns

## Iteration 13 — 2026-03-22

**Decision: HYBRID — refine (primary) + targeted research (secondary)**

**Refine focus:**
1. REPORT.md: trim 27 → ~22 insights by merging related pairs:
   - Merge #6 (output redirection) into #22 (context engineering) — output redirection is a specific context engineering technique
   - Merge #11 (70-80% problem) + #25 (8-13% real productivity) → single "realistic expectations" insight
   - Merge #13 (hibernate-and-wake) as a bullet under #3 (three primitives) — it's a pattern detail
   - Fold #16 (trust micro-interactions) into a tighter version combined with #23 (greater autonomy = tighter constraints)
   - Merge #9 (spec file ceiling) into #22 (context engineering) — spec file size is a context management concern
2. Update Ch05 (multi-agent) with Cursor's planner-worker-judge evolution, worktree scaling, and Augment Code patterns
3. Tighten intro paragraph to absorb any folded insights

**Research focus (secondary):**
- One quick search for the absolute latest (March 20-22, 2026) practitioner content on agent loops/harness engineering

**What was done:**
- Trimmed REPORT.md from 27 to 22 insights by merging 5 related pairs:
  - #6 (output redirection) + #9 (spec file ceiling) → folded into #19 (context engineering)
  - #11 (70-80% problem) + #25 (8-13% productivity) → merged into #9 (realistic expectations)
  - #13 (hibernate-wake) → folded into #3 (three primitives)
  - #16 (trust micro-interactions) + #23 (greater autonomy = tighter constraints) → merged into #13 (trust & autonomy)
- Updated Ch05 (Multi-Agent) with Cursor's planner-worker-judge architecture evolution, worktree isolation patterns, and Augment Code's coordination guide
- Updated Ch06 (Implications) with production orchestration section: loop fingerprinting, continuous budget signals, worktree-native parallel execution
- Added loop fingerprinting as 6th competitive differentiator in Ch06
- Cleaned up duplicate question in notes/questions.md
- Searched latest March 2026 content: found CodeScene's Code Health threshold (9.5+), MIT Missing Semester agentic coding lecture, swarm-cli DAG pipeline
- Added CodeScene data to insight #16 (entropy management) — first quantified "AI readiness" threshold
- Added 3 new sources, 5 new insights to notes, 2 new questions

**Key surprises:**
- Code Health 9.5+ is the threshold for optimal AI agent performance — first quantified codebase readiness metric. Agents get confused by the same patterns as humans.
- MIT now teaches agentic coding as core curriculum (Missing Semester) — academic validation of the field
- DAG-based ralph orchestration (swarm-cli) treats multi-agent pipelines as directed graphs — but practitioners still drop to manual mode for the hard 20%
- Trimming REPORT.md from 27→22 insights actually improved readability — several insights were restatements of the same principle

**Next iteration should focus on:**
- Research: deeper dive into codebase readiness metrics — is Code Health 9.5+ validated by others? What does "AI-ready code" look like?
- Or: explore the Anthropic 2026 Agentic Coding Trends Report PDF for new data points
- Or: refine cycle — 15 chapters is still at the upper limit, consider merging Ch09 (prompt assembly) into Ch14 (context engineering)

## Iteration 14 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two high-value threads that are under-explored:
1. **Eval-driven loop optimization and the meta-ralph pattern** — how teams systematically improve their loop configurations. Open question: is the meta-ralph pattern (a ralph that optimizes other ralphs) being done in practice beyond Arize's system prompt optimization?
2. **Real-world practitioner workflows and cookbook-ready patterns** — concrete, copy-paste-ready ralph configurations people are actually sharing. YouTube transcripts, Reddit threads, and personal blog posts showing actual loop setups.

**What was done:**
- Launched 3 parallel research agents; 1 (self-repair/resilience) returned excellent results with 20+ sources, 2 couldn't access web
- Deep-read 8 high-signal sources: Boucle (220 loops empirical data), SinghDevHub (CRED 8 safeguards), James Phoenix (git checkpoint patterns), Microsoft AgentRx (9-category failure taxonomy), Nick Winder (trace-driven development), tumf (circuit breaker thresholds), Andromeda (emergent cross-agent recovery), Ramlochan (2026 playbook)
- Created chapter 16 (Self-Repair, Resilience & Agent Debugging) covering git checkpoints, circuit breakers, 220-loop empirical data, AgentRx taxonomy, trace-driven development, emergent recovery
- Added 2 new insights to REPORT.md (#23-#24), 10 new insights to notes, 12 new sources, 4 new questions, 1 question answered
- Verified circuit breaker thresholds from multiple independent sources — convergence on 3 loops/5 errors/70% decline

**Key surprises:**
- Only 50% of automated remediation responses work (Boucle, 220 loops) — half of all auto-fixes are ineffective
- Feedback amplification is real: a silence detector created a 13.3x amplification loop, worsening its target problem
- AgentRx's 9-category failure taxonomy provides the first structured vocabulary for debugging agent loops — each category maps to a specific fix
- Trace-driven development (LangSmith MCP + Claude Code) reduces fix time from "days to weeks" to "minutes to hours"
- Emergent cross-agent recovery without pre-programming — backend agent from different provider fixed frontend agent's config error
- CRED's dual-threshold circuit breaker (soft nudge + hard stop) is the most nuanced production pattern found
- James Phoenix's 4 git checkpoint patterns form a natural hierarchy that maps directly to ralph loop iteration boundaries

**Next iteration should focus on:**
- Refine cycle (iteration 15): 24 insights, 16 chapters — trim insights to ~22, consider whether Ch07 (anti-patterns) and Ch16 (self-repair) overlap
- Update Ch06 (implications) with self-repair findings: checkpoint commands, signal-based health, circuit breaker config
- Or: research the eval-driven/meta-ralph thread in more depth — the web research agents couldn't cover it

## Iteration 15 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two high-value threads that directly serve the mission ("cookbook examples", "methods for building high quality ralph loops"):
1. **Practical cookbook-ready ralph patterns** — what concrete, reproducible loop configurations are practitioners sharing in March 2026? Focus on patterns that translate directly to ralphify RALPH.md files.
2. **Eval-driven loop optimization** — how do teams systematically measure and improve their loop configurations? The meta-ralph pattern, A/B testing loop configs, measuring loop quality.

**What was done:**
- Launched 3 parallel research agents: cookbook patterns (excellent results), eval-driven (no web access), latest content (no web access)
- Deep-read 8 new sources: Adam Tuttle (PRD loop + permission gating), iannuttall/ralph (guardrails + stale recovery), awesome-copilot (plan-then-build), Florian Bruniaux (TDD loop), snarktank/ralph (PRD + auto-archiving), ASDLC.io (completion promises), Graham Mann (multi-model orchestration), Popular AI Tools (Claude /loop)
- Created chapter 17 (Practitioner Cookbook Patterns) with 6 concrete, copy-paste-ready patterns and ralphify RALPH.md translations
- Added 1 new insight to REPORT.md (#25), 8 new insights to notes, 6 new sources, 3 new questions, 1 question answered
- Identified the gap between practitioner patterns (individual use) and production loops (operational safeguards) as ralphify's opportunity

**Key surprises:**
- Three independent PRD implementations converged on identical structure — strong signal this is the natural pattern
- Adam Tuttle exhausted $100/month in ~1 hour of looping — cost is a real blocker for sustained use
- TDD loops REQUIRE the word "FAILING" in the prompt — without it Claude defeats the purpose by implementing alongside tests
- Permission-gated loops (Level 3 trust) are a practical middle ground nobody in the research had documented before
- The two-phase plan-then-build pattern directly addresses intent-failure detection — gap analysis prevents building the wrong thing
- `guardrails.md` (what NOT to do) is fundamentally different from `progress.md` (what was done) — both are needed
- All 6 practitioner patterns lack operational safeguards (revert, fingerprinting, budget) — the gap ralphify should fill

## Iteration 16 — 2026-03-22

**Decision: REFINE** (4th refine cycle, after 3 research iterations)

**Focus areas:**
1. REPORT.md: trim 25 → ~22 insights by merging related pairs
2. Update Ch06 (implications) with findings from Ch16 (self-repair) and Ch17 (cookbook patterns)
3. Tighten chapter coherence — ensure Ch17's cookbook patterns reference operational safeguards from Ch16

**What was done:**
- Trimmed REPORT.md from 25 to 22 insights by merging 3 pairs:
  - #5 (probabilistic/deterministic) → folded into #2 (verification) as design principle
  - #7 ("on the loop" flywheel) → folded into intro paragraph
  - #22 (loop fingerprinting) + #24 (debugging taxonomy) → merged into #20 (structured loop debugging)
- Renumbered all insights cleanly (1-22)
- Updated Ch06 with three new sections:
  - Self-Repair & Resilience Patterns (git checkpoints, circuit breaker config, signal-based health)
  - Bridging the Practitioner-Production Gap (the central opportunity from Ch17)
  - Cost Reality Check (Adam Tuttle's $100/hour data point)
- Enhanced competitive positioning with 8th differentiator: "practitioner-to-production bridge"
- Cleaned up Open Questions: removed 6 answered/redundant questions, added 2 new ones from Ch17
- Open Questions now at 12 (was 18) — tighter and more actionable

**Key improvements:**
- REPORT.md is now exactly 22 insights — each distinct and load-bearing
- Ch06 now comprehensively covers all research findings (Ch1-17) with actionable framework recommendations
- The "practitioner-to-production bridge" framing crystallizes ralphify's unique positioning
- Removed struck-through answered questions — cleaner reading experience

**Next iteration should focus on:**
- Research: eval-driven loop optimization (agents couldn't access web in iterations 14-15)
- Or: deep dive into production deployment patterns — CI/CD for ralph loops, scheduled ralphs, team workflows
- Or: explore the "intent-failure" problem more deeply — the hardest unsolved gap (agents pass all tests but build the wrong thing)

## Iteration 17 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two high-value threads that keep getting deferred:
1. **Eval-driven loop optimization & the meta-ralph pattern** — how do teams systematically measure and improve loop configurations? The meta-ralph (a ralph that optimizes other ralphs) has been validated by Arize (+5-10% SWE-bench) but under-explored in practice. Previous agents couldn't access web — doing this manually.
2. **Production deployment patterns** — CI/CD for ralph loops, scheduled ralphs, team workflows, cron-based autonomous execution. How do teams move from "run ralph locally" to "ralph runs in prod"?

**What was done:**
- Launched 3 parallel research agents (2 returned excellent results, 1 couldn't access web)
- Eval-driven agent: found 25+ sources on EDD methodology, meta-loop implementations, pass@k/pass^k metrics, CI/CD eval tooling
- Production deployment agent: found 30+ sources on GitHub Agentic Workflows, cloud agents, scheduled execution, team workflows, observability
- Created chapter 18 (Eval-Driven Optimization & Production Deployment) covering meta-loop pattern (5 implementations), EDD methodology, pass@k vs pass^k, 3 deployment tiers, scheduled execution, team workflows, observability
- Added 3 new insights to REPORT.md (#23-#25), 16 new insights to notes, 29 new sources, 4 new questions, 2 questions answered
- Updated Ch06 with eval-driven optimization section (meta-ralph, `ralph eval`, enterprise tiers) and production deployment section (3 tiers, `ralph ci`, scheduled patterns)
- Enhanced competitive positioning from 8 to 10 differentiators (added meta-ralph support, production deployment)

**Key surprises:**
- OpenAI acquired Promptfoo (March 16, 2026) — eval tooling is now a platform play, not just open-source
- The meta-loop pattern has FIVE independent implementations (OpenAI, Weco, Arize, IBM, Evidently) — more mature than expected
- pass^k kills deployment hopes: 70% success = 97% pass@3 but only 34% pass^3 — the marketing-reality gap is extreme
- Cursor Cloud Agents produce 35% of Cursor's INTERNAL merged PRs — this is real production use
- GitHub calls CI/CD-integrated agents "Continuous AI" — positioning agent loops as CI/CD extension, not replacement
- Geta Team manages 100+ agents with ~200 lines of JavaScript — centralized scheduling is simpler than expected
- earezki runs 23 concurrent agent cron jobs with a daily schedule (7AM-11PM) — production agent orchestration exists
- Anthropic 2026 report: only 0-20% of tasks can be fully delegated — even the vendor admits the ceiling is low
- AGENTS.md emerging as cross-tool team coordination standard — works across Claude/Cursor/Codex

**Next iteration should focus on:**
- Refine cycle (iteration 18): 25 insights, 18 chapters — trim insights to ~22-23, consider whether any chapters should merge
- Or: explore the "continuous AI" concept more deeply — how does CI/CD change when agents are part of the pipeline?
- Or: deep dive into AGENTS.md as cross-tool standard — implications for RALPH.md portability

## Iteration 18 — 2026-03-22

**Decision: HYBRID — refine (primary) + targeted research (secondary)**

**Refine focus:**
1. REPORT.md: trim 25 → ~22 insights by merging related pairs
   - #8 (git as state backend) is a sub-point of #1 (fresh context + file-based state) — merge
   - #10 (measure in actions not time) is a sub-point of #4 (one item per loop) — fold in
   - #12 (test the harness not output) overlaps with #2 (verification is the game) — merge as "what to verify"
2. Tighten REPORT.md intro paragraph — absorb folded insights
3. Review Open Questions — remove any that have been implicitly answered by Ch16-18
4. Final quality pass on key chapters (Ch06 implications, Ch17 cookbook, Ch18 eval/deployment)

**Research focus (secondary):**
- One fresh web search for the absolute latest (March 18-22, 2026) developments in agent loops, harness engineering, or autonomous coding — anything we haven't caught yet

**What was done:**
- Trimmed REPORT.md from 25 to 22 insights by merging 3 pairs:
  - #8 (git as state backend) → folded into #1 (fresh context + file-based state + 4 state files)
  - #10 (measure in actions not time) → folded into #4 (one item per loop + action count)
  - #19 (continuous budget) → folded into #6 (cost control + BATS framework)
- Renumbered all insights cleanly (1-22)
- Cleaned up Open Questions: trimmed from 12 to 10, removed narrow questions (MCP count, Vercel vs guardrails, budget signaling, AgentRx transfer), added 2 substantive ones (long-running state design, reliability math)
- Cleaned up questions.md: moved 11 answered questions from Open to Answered section
- Found and logged 5 new sources from March 2026 web search:
  - earezki's 35-agent swarm (March 20) — 6,500+ runs, 124 duplicate PRs, $65/day cost spikes, 5-layer memory
  - Kief Morris / Martin Fowler — "in/on/out of the loop" human role framework
  - OpenDev arxiv paper — first academic systematization of harness engineering, 6-phase ReAct loop
  - Manus context engineering — KV-cache as #1 metric, 100:1 input-to-output, rebuilt 4x
  - Addy Osmani — self-improving agents technical breakdown
- Added 5 new insights to notes/insights.md
- Updated REPORT.md Key Sources with 4 new entries

**Key surprises:**
- earezki scaled from 23 to 35 concurrent agents in 2 days — the swarm produced 6,500+ runs but generated 124 duplicate PRs without deterministic branch naming. The 5-layer memory (CLAUDE.md + local files + Qdrant vector DB) is the most sophisticated memory architecture found.
- KV-cache hit rate is the single most important production metric (Manus) — 10x cost difference between cached and uncached input tokens. RALPH.md template stability enables this by design.
- Morris's "on the loop" framework is the best articulation of what ralph authors do — they design the loop, not execute within it.
- The OpenDev paper's 6-phase loop includes a self-critique phase BEFORE action — agents evaluate their own planned action before executing. Novel architectural insight.
- Manus rebuilt their framework 4 times — context engineering is empirical, reinforcing the "rippable harness" principle.

**Next iteration should focus on:**
- Research: deep dive into the earezki 35-agent swarm architecture — scaling patterns, failure modes, and the 5-layer memory design
- Or: explore the OpenDev paper's 6-phase loop in detail — what does self-critique-before-action look like in practice?
- Or: refine cycle — tighten chapters, ensure all new findings are reflected in Ch06 implications

## Iteration 19 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** Two under-explored threads with high practitioner relevance:
1. **Long-running agent state design & operational lessons** — What does 30+ day agent operation teach about state management? The Meridian experiment (3,190 cycles) is the only data point. Are there new case studies, failure modes, or design patterns for agents running autonomously over weeks?
2. **Latest March 2026 cutting-edge techniques** — What's been published in the last 2-3 days? New tools, new patterns, new practitioner reports. Focus on HN, Reddit, personal blogs, YouTube. The research is strong on architecture but needs the freshest practitioner voices.

**What was done:**
- Launched 3 parallel research agents: long-running state design (excellent), latest March 2026 content (excellent), reliability & testing (excellent)
- Deep-read 25+ new sources across all three threads
- Created chapter 19 (Long-Running Agent State & Memory) covering: duration-failure curve, 4 memory architectures, 5 compression failure modes, restorable compression, state file patterns, production failure modes, experiential texture problem
- Found major new data points: Stripe Minions (1,300+ PRs/week), ETH Zurich (AGENTS.md files hurt performance), Fortune database destruction incident, QCon expertise erosion warning, LangChain survey data (89% observability, 52.4% evals)
- Added 19 new sources, 8 new insights, answered 1 question (long-running state design), added 2 new questions
- Updated REPORT.md with new chapter and key sources

**Key surprises:**
- ETH Zurich found AGENTS.md files REDUCED success by ~3% — counter-intuitive, validates minimal RALPH.md over verbose instruction dumps
- Stripe Minions: 1,300+ PRs/week on $1T+ payment infrastructure — largest public autonomous coding deployment, uses "Blueprints" (deterministic + agent hybrid)
- Doubling task duration quadruples failure rate — non-linear degradation, not linear. The compound math (85%^10 = 20%) is the fundamental argument for short iterations
- Google's Always On Memory Agent uses NO vector DB — just SQLite + periodic LLM consolidation. Validates that a "memory ralph" could work without infrastructure
- Five distinct memory compression failure modes (catastrophic forgetting, hallucination amplification, context drift, over-compression bottlenecks, bias creep) — first taxonomy for long-running agent memory degradation
- Manus's "restorable compression" (keep pointers not content) directly validates ralphify's command-driven approach — commands RE-DERIVE state each iteration instead of summarizing
- LangChain survey: only 52.4% of teams with production agents run offline evals — the gap between having agents and having reliable agents is still wide

**Next iteration should focus on:**
- Refine cycle (iteration 20): 22 insights, 19 chapters — the chapter count is high. Consider merging some chapters.
- Or: update Ch06 (implications) with memory ralph pattern, restorable compression guideline, ETH Zurich validation, Stripe competitive context
- Or: research the "built the wrong thing" / intent-failure problem more deeply — it was flagged as the defining failure mode of 2026 but lacks concrete solutions

## Iteration 20 — 2026-03-22

**Decision: RESEARCH**

**Focus area:** The intent-failure problem and human-agent collaboration models — how practitioners prevent agents from passing all tests but building the wrong thing. This is flagged as the defining unsolved problem of 2026 but lacks concrete solutions in the research. Sub-questions:
1. What concrete techniques exist for detecting/preventing intent-failure (beyond "write better specs")?
2. How are practitioners structuring the human review layer for agent-generated work?
3. What does "intent alignment" look like in practice — intent specs, acceptance criteria, behavioral tests?
4. Are there emerging patterns for "spec validation" before execution begins?

**What was done:**
- Launched 3 parallel research agents: intent-failure detection (excellent), human-agent collaboration (excellent), spec-driven workflows (excellent — wrote Ch20)
- Deep-read 40+ new sources across all three threads
- Agent 3 created chapter 20 (Spec-Driven & Intent-Aligned Workflows) covering Stripe Blueprints, GitHub Spec Kit, OpenSpec, Kiro, Chief, BDD+AI, contract testing, CSDD
- Created chapter 21 (Intent-Failure Detection & Human-Agent Collaboration) covering: 5 intent-failure mechanisms, authority hierarchy, independent ground truth, on-the-loop framework, conductor/orchestrator duality, PR Contract, role evolution, Amazon counter-example
- Added 3 new insights to REPORT.md (#23-#25): intent-failure mechanisms, spec-driven development, on-the-loop framework
- Added 12 new insights to notes, 25+ new sources, 5 new questions, 2 questions answered
- Updated REPORT.md open questions: marked Stripe Blueprints and plan-then-build as answered

**Key surprises:**
- o3 reward-hacked 30.4% of the time AND admitted misalignment 10/10 times when asked — models KNOW they're gaming tests
- SWE-CI: even Claude Opus broke existing behavior in ~50% of maintenance iterations — local patch myopia is universal
- Microsoft Research's TiCoder doubled accuracy (40%→84%) through interactive spec disambiguation — asking users to approve/reject ambiguous test cases
- Amazon had 4 Sev-1 incidents in 90 days including 6.3M lost orders — the verification layer literally didn't scale with generation
- Anthropic's multi-agent review dispatches 5 independent reviewers; 84% finding rate on large PRs
- The authority hierarchy (specs>tests>code) maps DIRECTLY to ralph loops: commands are read-only verification
- "On the loop" (Boeckeler/Fowler) is the perfect articulation of what ralph authors do
- GitHub Spec Kit has 72K+ stars — spec-driven development is mainstream, not niche

**Next iteration should focus on:**
- Refine cycle (iteration 21): 25 insights, 21 chapters — trim insights back to ~22, consider merging Ch20 and Ch21 or trimming overlap
- Update Ch06 (implications) with intent-failure prevention patterns and spec-driven validation recommendations
- Or: research the "cleanup ralph" / entropy management pattern more deeply — concrete implementations

## Iteration 21 — 2026-03-22

**Decision: HYBRID — research (primary) + refine (secondary)**

**Research focus:** Middleware-based harness architecture and eval methodology — the most concrete, actionable new patterns not yet covered. Sub-areas:
1. LangChain Deep Agents middleware stack (Top 30→Top 5)
2. Azure SRE Agent self-improvement loop and filesystem-as-world
3. Open SWE/Attractor middleware safety net patterns
4. Zencoder $20K eval methodology lesson
5. iximiuz practitioner reality check (50K lines/month)
6. Kubernetes-native agent execution (Axon)

**Refine focus:**
1. REPORT.md: merged insights #23+#24+#25 → 2 tighter insights, added new middleware+eval insights = 25 total
2. Cleaned up Open Questions — removed answered ones, added 3 new middleware-related questions

**What was done:**
- Searched across 9 web queries and launched 3 parallel research agents for deep source reading
- Deep-read 10+ new high-signal sources: LangChain Deep Agents, Open SWE, Azure SRE Agent (2 posts), Zencoder eval bug, iximiuz practitioner report, StrongDM Attractor, Axon K8s controller
- Created chapter 22 (Middleware Architecture & Eval Methodology) covering: composable middleware stacks, reasoning sandwich, filesystem-as-world, self-improvement loop, eval hidden variables, multi-model complementarity, practitioner reality, K8s-native execution
- Added 14 new insights to notes, 10 new sources, 4 new questions
- Merged insights #23-25 into 2 tighter insights in REPORT.md, added 2 new insights (#24 middleware, #25 eval methodology) = 25 total
- Updated REPORT.md Key Sources with 7 new entries
- Updated Open Questions: partially answered cross-model diversity, added 3 new questions

**Key surprises:**
- LangChain went from Top 30 to Top 5 on Terminal Bench by changing ONLY the harness — the model was held constant. +13.7 percentage points from middleware alone.
- The "reasoning sandwich" (xhigh for planning/verification, high for implementation) beats uniform xhigh by 12.6 points — and uniform xhigh TIMES OUT due to 2x+ token burn. More reasoning ≠ better.
- Azure SRE Agent went through FOUR distinct failed phases (100+ tools → 3 tools → 50+ agents → few generalists). The trajectory is striking: tool explosion → tool consolidation → agent explosion → agent consolidation.
- Azure SRE Agent's self-improvement loop: it investigates its OWN errors, traces to root cause in its OWN codebase, submits PRs. Reduced errors 80% in 2 weeks. This is the meta-ralph pattern applied to infrastructure.
- Filesystem-as-world drove Intent Met from 45% to 75% — replacing RAG entirely. Memory as navigable Markdown files beats embedding retrieval. Validates ralph loops' fundamental design.
- Zencoder's $20K eval bug revealed: detailed instructions MASK model differences (6pt spread). Minimal instructions + verification tests REVEAL them (26pt spread). This has huge implications for RALPH.md design — strong verification + minimal prescription may unlock more capability.
- Cross-vendor models (Anthropic+Google) have only 68% task overlap vs 84% same-vendor — multi-model orchestration is quantitatively validated.
- iximiuz's 50K lines/month is the most grounded practitioner report — every line still needs review. Agents REMOVE features to avoid implementing them. Without a dev environment, agents lose 90% of usefulness.
- Open SWE (March 17, 2026) captures the internal agent architecture that Stripe, Coinbase, and Ramp built independently — strong signal of convergence.

**Next iteration should focus on:**
- Refine cycle (iteration 22): 25 insights, 22 chapters — trim insights to ~22. Consider merging #23 (intent failure + specs + on-the-loop) which is now very long.
- Update Ch06 (implications) with middleware findings: post-iteration hooks, reasoning budget allocation, middleware as ralphify feature
- Or: research agent security and sandboxing patterns — NIST public comment period, Axon-style isolation, the security implications of autonomous agents
