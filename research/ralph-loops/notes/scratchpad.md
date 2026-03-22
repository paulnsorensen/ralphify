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
