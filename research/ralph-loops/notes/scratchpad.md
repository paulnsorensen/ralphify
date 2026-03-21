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
