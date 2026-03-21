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

## Ralphify-Specific
- **Ralphify's command system naturally supports the "commands as verifiers" pattern.** Running tests/metrics as commands and injecting results into the prompt is exactly what Spotify and Karpathy do — ralphify just needs to formalize verification as a first-class concept.
- **Agent skills as portable packages is a validated trend.** Ralphify's skill system aligns with the industry direction of installable, reusable instruction sets.
- **The autoresearch pattern maps directly to a ralph.** editable asset = code, commands = run experiment + extract metrics, RALPH.md = program.md. This is the highest-value cookbook example to build.
