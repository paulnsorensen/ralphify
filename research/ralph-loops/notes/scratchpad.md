# Scratchpad

## Iteration 1 — 2026-03-21

**Decision: RESEARCH** (first iteration, establish foundation)

**Focus area:** Survey the current landscape of autonomous agent loop engineering across all major sources.

**What was done:**
- Searched across HN, blogs, engineering posts, YouTube references for agent loop/harness patterns
- Deep-read 12+ high-signal sources including Anthropic, Spotify, Meta, Karpathy, OpenAI, Addy Osmani
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
