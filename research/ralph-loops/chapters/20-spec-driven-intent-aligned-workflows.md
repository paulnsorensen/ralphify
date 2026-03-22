# Spec-Driven and Intent-Aligned Agent Workflows

> The emerging consensus: detailed specifications written BEFORE agent execution are the primary defense against "built the wrong thing" failures. This chapter catalogs the tools, patterns, academic research, and practitioner techniques that constitute spec-driven development (SDD) as of March 2026 — the most significant workflow shift since the ralph loop pattern itself.

## The Core Problem: Intent Misalignment at Machine Speed

Agent throughput exceeds human review capacity (Ch14 finding). Agents can pass all tests while building the wrong thing. When specification != intent, misalignment thrives — edge cases you didn't anticipate that an agent optimizing at machine speed will find. The spec-driven workflow is the architectural answer: make intent explicit, testable, and verifiable before a single line of code is generated.

**Key quote (Thoughtworks):** "Spec drift and hallucination are inherently difficult to avoid. We still need highly deterministic CI/CD practices to ensure software quality and safeguard our architectures." — Liu Shangqi, Technology Director, APAC Region

**Key quote (Addy Osmani):** "Most agent files fail because they're too vague." The spec becomes the contract between the human developer and the AI agent — and critically, it becomes the basis for code review, not the code itself.

## The Three Levels of Specification Rigor

The ICSE 2026 paper "Spec-Driven Development: From Code to Contract in the Age of AI Coding Assistants" (arXiv:2602.00180) establishes a taxonomy:

1. **Spec-First**: Specs guide initial development but may drift afterward. "The spec guides implementation, but once the code is written and tests pass, the spec may be discarded or allowed to drift." Best for prototypes and AI-assisted feature development.

2. **Spec-Anchored**: Specs evolve alongside code throughout the system lifecycle. "Changes to behavior require updating both the spec and the code, keeping them synchronized." Automated tests enforce alignment. The practical choice for production systems.

3. **Spec-As-Source**: Humans edit only specifications; machines generate all code. "The specification becomes, in effect, the source code — just expressed at a higher level of abstraction." Eliminates drift by construction but requires mature, trusted generation tooling.

**Key finding**: AI coding assistants perform significantly better with clear specifications, reducing errors by up to 50% compared to vague prompts. Integration failures dropped 75% when teams adopted API-first spec approaches before coding.

**Practical recommendation**: "Use the minimum level of specification rigor that removes ambiguity for your context." Avoid over-specification that becomes pseudo-code.

Source: https://arxiv.org/abs/2602.00180

## What a Specification Contains

A specification explicitly defines (per Thoughtworks):
- Input/output mappings
- Preconditions/postconditions
- Invariants and constraints
- Interface types
- Integration contracts
- Sequential logic/state machines

GitHub's analysis of 2,500+ agent configuration files reveals the most effective specs cover six areas:
1. Commands (with exact executable formats)
2. Testing (frameworks, coverage expectations)
3. Project structure (explicit file paths)
4. Code style (by example, not prose)
5. Git workflow (branching, commit conventions)
6. Boundaries (three-tier: "Always do" / "Ask first" / "Never do")

## Stripe's Blueprints: Deterministic + Agentic Hybrid Workflows

Stripe's "Minions" system generates ~1,300 PRs/week through a Blueprint architecture that interleaves deterministic and agentic nodes. This is the most mature production-grade spec-driven system documented publicly.

### How Blueprints Work

A blueprint is a sequence of nodes where some run deterministic code and others run an agentic loop. The analogy: "Think of a blueprint like a recipe. The recipe tells you exactly what to do and when — but some steps involve precise measurements (deterministic), while others involve judgment calls."

**Deterministic nodes** handle:
- Parsing code and extracting syntax trees
- Running test suites with pass/fail results
- Linting and code formatting
- File operations (read, write, copy)
- System queries and validation checks

**Agentic nodes** handle:
- Task interpretation from natural language
- Approach planning and code generation
- Test failure diagnosis and fixes
- PR description writing

### Concrete Example: Dependency Update Blueprint

1. **[Deterministic]** Identify import files
2. **[Deterministic]** Extract code context
3. **[Agentic]** Analyze usage patterns and determine changes
4. **[Agentic]** Generate updated code
5. **[Deterministic]** Write changes to disk
6. **[Deterministic]** Run test suite
7. **[Agentic]** Interpret failures; generate fixes if needed
8. **[Deterministic]** Verify compilation and test passage
9. **[Deterministic]** Format per style rules
10. **[Agentic]** Write PR summary
11. **[Deterministic]** Submit PR

### Why This Matters

"Making these deterministic saves tokens, reduces errors, and guarantees that critical steps happen every single time." Failed deterministic steps feed back to agentic nodes for bounded retry loops before human escalation. Every step is logged, enabling clear failure diagnosis without relying on AI self-verification.

Human review remains mandatory — agents submit PRs but engineers retain merge authority.

Sources:
- https://www.mindstudio.ai/blog/stripe-minions-blueprint-architecture-deterministic-agentic-nodes
- https://www.infoq.com/news/2026/03/stripe-autonomous-coding-agents/
- https://www.sitepoint.com/stripe-minions-architecture-explained/

## The Four Major SDD Frameworks

### 1. GitHub Spec Kit (72K+ stars)

Open-source toolkit providing a four-phase process: **Specify -> Plan -> Tasks -> Implement**.

- **Specify**: Developer provides high-level description of what and why; AI generates detailed specification
- **Plan**: Developer provides technical direction; AI generates implementation plan respecting architecture and constraints
- **Tasks**: AI breaks specs into small, reviewable, independently testable work chunks
- **Implement**: Agents execute tasks; developers review focused changes

CLI commands: `/specify`, `/plan`, `/tasks`. Supports 22+ AI agent platforms including Claude Code, GitHub Copilot, Gemini CLI.

**Key insight**: "Specs become the shared source of truth. When something doesn't make sense, you go back to the spec."

Source: https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/

### 2. AWS Kiro

Enterprise IDE built on Amazon Bedrock with a three-phase workflow: **Requirements -> Design -> Tasks -> Implementation**.

- Converts natural language prompts into structured requirements using EARS (Easy Approach to Requirements Syntax) notation
- Generates acceptance criteria automatically from requirements
- Creates implementation plans with dependency-sequenced tasks
- **Agent Hooks**: Automated triggers that execute predefined agent actions on file save/create/delete
- **Steering Files**: Persistent markdown knowledge about project patterns and standards

Source: https://kiro.dev/

### 3. OpenSpec (27K+ stars, YC-backed)

Lightweight, filesystem-based framework specifically targeting **brownfield development** (iterating on existing codebases). Enforces a strict four-phase state machine:

| Phase | Command | Output |
|-------|---------|--------|
| 1. Proposal | `/openspec:proposal` | proposal.md, tasks.md, design.md |
| 2. Definition | `openspec validate` | Spec deltas (ADDED/MODIFIED/REMOVED) |
| 3. Apply | `/openspec:apply` | Source code modifications |
| 4. Archive | `/openspec:archive` | Merged specs/ directory |

Uses GIVEN/WHEN/THEN format (Gherkin-style) for requirements:

```
### Requirement: Two-Factor Authentication
#### Scenario: OTP Verification Required
- **GIVEN** User has 2FA enabled
- **WHEN** Correct credentials provided
- **THEN** System returns OTP challenge instead of token
```

**Key differentiator**: Change isolation — "each feature development operates like an independent mini-project, merging only at conclusion." Where Spec Kit targets greenfield (0->1), OpenSpec targets brownfield (1->n).

Sources:
- https://redreamality.com/garden/notes/openspec-guide/
- https://openspec.pro/
- https://www.ycombinator.com/launches/Pdc-openspec-the-spec-framework-for-coding-agents

### 4. Chief (Autonomous PRD Agent)

Transforms PRDs into working code via autonomous execution. PRDs live in `.chief/prds/[feature-name]/` with structured user stories:

```markdown
### US-001: Story Title
**Status:** todo
**Priority:** 1
**Description:** Story narrative

- [ ] Specific, verifiable criterion
- [ ] Another criterion
```

**Story selection algorithm**: Filter completed -> sort by priority -> mark in-progress -> work until `<chief-done/>` -> update status -> repeat.

**Best practices**: 5-7 acceptance criteria per story maximum; "Error message shown for invalid credentials" beats "good error handling."

Source: https://chiefloop.com/concepts/prd-format.html

## PRD Structure for AI Coding Agents

An AI-optimized PRD restructures requirements as sequential phases rather than flat feature lists. Key structural principles:

- **Phase-based decomposition**: Phase 1: Database schema, Phase 2: API endpoints, Phase 3: Business logic, Phase 4: UI integration, Phase 5: Polish and error handling
- **Acceptance criteria as programming interfaces**: Precise enough to execute, structured enough to sequence, constrained enough to prevent scope drift
- **Three-tier boundary system** (per Addy Osmani):
  - Always do: Safe actions without approval
  - Ask first: High-impact changes requiring review
  - Never do: Hard stops (e.g., "Never commit secrets")

**Key insight (Addy Osmani)**: "The curse of instructions" — performance drops with too many simultaneous directives. Break work into modular prompts; deploy subagents for specialized domains.

Sources:
- https://addyosmani.com/blog/good-spec/
- https://medium.com/@haberlah/how-to-write-prds-for-ai-coding-agents-d60d72efb797

## The Technical Design Spec Pattern

Tom Yedwab's pattern treats specifications as "long-term memory" that keeps agents focused across sessions:

1. **Write specs before implementation** — markdown files documenting goals, tasks, modules, function definitions, APIs. "We are exerting oversight into what the agent has in its context window and minimizing the random behavior that all LLMs exhibit."
2. **Include full file paths** — `server/cmd/main/main.go` not `main.go`. Prevents duplicate files in wrong directories.
3. **Implement one step at a time** — each step explicitly includes the spec in context.
4. **Roll back and revise prompts on mistakes** — revert changes and clarify prompts rather than asking agents to self-correct. "The agent will not feel offended if you revert all their changes."
5. **Update specs and start new chat sessions** — model performance degrades as context fills; spec file serves as persistent memory across sessions.
6. **Convert completed specs to documentation** — delete project specs before merging to main.

Source: https://www.arguingwithalgorithms.com/posts/technical-design-spec-pattern.html

## Spec Validation: Verifying Specs Before Execution

### The Validation Gap

The verification layer cannot catch cases where the original specification itself is incorrect — a fundamental constraint. Validation must happen at the spec layer, not just the output layer.

### Validation Techniques

**Schema validation in CI pipelines**: Validate spec structure (required fields, proper formatting) before agents execute.

**Spec differential engines**: Detect divergence between specs and implementation over time.

**Human review gates**: The spec is reviewed by humans before any agent execution begins — the planning phase is where human judgment matters most.

**AI-assisted spec review**: Use a separate AI pass to identify ambiguities, contradictions, and missing edge cases in specifications before execution. "Start in Plan Mode, describe what you want to build, let the agent draft a spec while exploring existing code, ask the agent to clarify ambiguities, and refine the plan until there's no room for misinterpretation before execution."

**Failure mode pre-analysis**: Define 3-5 ways an objective could be misinterpreted. Red team the specification before deploying agents.

## BDD (Behavioral Driven Development) and AI Agents

### The Evolving Role of Gherkin

Traditional BDD: humans write Given/When/Then scenarios -> step definitions -> automated tests. The AI era inverts this — BDD becomes an output format rather than a starting point.

**Key shift (2025-2026)**: "With AI and LLMs becoming increasingly adept at handling code, perhaps we're entering a new era where behavior formulation can happen directly in code, removing the need for middleware like Gherkin." Gherkin is becoming an intermediate language to transfer, discuss and store scenarios, rather than for initial writing. Initial versions are generated by LLMs from raw business requirements.

### AI-Powered BDD Tools

- **Gherkinizer**: Converts plain-language requirements into executable BDD scenarios using Gemini AI; auto-creates step definitions for Playwright, Selenium, Cypress
- **Workik**: AI reviews existing Cucumber tests to identify untested flows and edge cases, suggesting additional scenarios
- **OpenSpec**: Uses GIVEN/WHEN/THEN format natively in spec definitions (see above)

### BDD Adoption Data

About 27% of sampled open-source projects use BDD frameworks, with prevalence highest in Ruby (68%). In 2025, hand-crafting hundreds of Gherkin scenarios is becoming obsolete — the industry is shifting toward orchestrating AI-powered QA.

Sources:
- https://automationpanda.com/2025/03/06/is-bdd-dying/
- https://gherkinizer.com/
- https://testquality.com/gherkin-user-stories-acceptance-criteria-guide/

## Contract Testing Applied to Agent Output

### Contracts as Code-Level Specifications

Contracts are preconditions and postconditions expressed in the code itself — "if you call me with valid input, I will return valid output, and here is precisely what 'valid' means for both." They can be checked statically (before anything runs) or at runtime (as continuous assertions).

### Practical Patterns

**Schema validation at boundaries**: "Not 'is this valid JSON' but 'does this JSON have the right shape' — the required fields, the expected types, the value ranges that downstream consumers depend on."

**Conformance suites**: Language-independent tests (often YAML-based) that any implementation must pass. These act as a contract: the conformance suite specifies expected inputs/outputs, and the agent's code must satisfy all cases.

**Separation of generation and validation**: "Use AI to generate test cases but execute them in a standard CI pipeline. Never trust AI to both generate and validate." Generate and verify in separate steps.

**AI-powered contract testing**: Every PR spins up an isolated sandbox, runs tests, and delivers immediate feedback without extra setup.

Sources:
- https://dev.to/choutos/stop-reading-ai-generated-code-start-verifying-it-1d1o
- https://dev.to/signadot/the-future-of-api-validation-a-deep-dive-into-ai-powered-contract-testing-4da7
- https://www.testsprite.com/use-cases/en/contract-testing

## Acceptance Criteria Verification: Multi-Stage Approaches

### Programmatic Verification Pipeline

The opslane/verify tool demonstrates a four-stage orchestration for verifying acceptance criteria:

1. **Bash pre-flight check** — validates server liveness and auth before spending any tokens
2. **Claude Opus planner** — interprets specifications and designs verification strategy
3. **Parallel Claude Sonnet instances** — each controls a Playwright browser agent to test one acceptance criterion, capturing screenshots and session recordings
4. **Claude Opus judge** — reviews all evidence and returns per-criterion pass/fail verdicts

### The Self-Congratulation Problem

"Having Claude write its own tests produces what he calls a 'self-congratulation machine' — the AI verifies its own assumptions rather than user intent." Independent verification layers avoid shared blind spots between writer and reviewer models.

### LLM-as-a-Judge for Subjective Criteria

For criteria hard to test automatically — code style, readability, architectural adherence — use a second agent to review the first agent's output against spec quality guidelines. Anthropic and others have found this effective for subjective evaluation.

**Key principle**: "The loop is only as good as your definition of done — tests and checks must drive completion, not vibes."

Source: https://agent-wars.com/news/2026-03-14-spec-driven-verification-claude-code-agents

## Constitutional Spec-Driven Development (CSDD)

A related paper (arXiv:2602.02584) introduces CSDD — embedding non-negotiable security constraints into the specification layer, ensuring AI-generated code is secure by construction rather than by post-hoc verification.

**Key finding**: A study of 31,132 AI agent skills found that 26.1% contain at least one security vulnerability, including prompt injection, data exfiltration, and privilege escalation risks.

Source: https://arxiv.org/abs/2602.02584

## Conversational Spec Building: From Intent to Specification

### The Workflow

Frameworks that generate specs from user intent through structured dialogue:

1. **Structured AI-human dialogue** — AI asks clarifying questions to surface implicit requirements
2. **Requirement conversion** — dialogue outputs converted to detailed technical specs with explicit scope boundaries
3. **Task decomposition** — specs broken into granular, actionable implementation tasks
4. **Iterative refinement** — "Refine the plan until there's no room for misinterpretation before execution"

### Collaboration Tiers

- **Tier 1 (AI autonomous)**: Boilerplate generation, CRUD operations, test scaffolding
- **Tier 2 (AI + human review)**: Complex business logic, external API integration, cross-file refactoring
- **Tier 3 (Human-led)**: Debugging complex issues, architectural decisions, security

**Key principle**: "Spec-Driven Development is not about handing requirements to an AI and walking away while it builds your app." It's a structured partnership where humans architect and review while AI handles implementation.

Source: https://dev.to/koustubh/part-1-spec-driven-development-building-predictable-ai-assisted-software-19ne

## The Anthropic Agentic Coding Trends Report (2026)

Anthropic's report (January 2026) identifies four strategic priorities relevant to spec-driven workflows:

1. **Multi-agent coordination** — parallel reasoning across context windows becomes standard
2. **Scaling human-agent oversight** — AI-automated review systems
3. **Extending agentic coding beyond engineering** — domain experts empowered across departments
4. **Security architecture as core design principle** — embedded from project inception

**Case study**: Rakuten engineers tested Claude Code on activation vector extraction in vLLM — completed in 7 hours of autonomous work, achieving 99.9% numerical accuracy without human code contribution during execution.

Source: https://resources.anthropic.com/2026-agentic-coding-trends-report

## Spec-Driven Development vs. Adjacent Approaches

| Approach | Focus | Spec Role | AI Role |
|----------|-------|-----------|---------|
| **Vibe Coding** | Speed, exploration | None — chat is the spec | Generate and iterate |
| **SDD (Spec-First)** | Correctness, alignment | Driving artifact | Implement from spec |
| **BDD** | Business collaboration | Given/When/Then scenarios | Generate scenarios + tests |
| **Contract Testing** | Interface compliance | Formal contracts | Verify compliance |
| **Waterfall** | Sequential phases | Heavy upfront docs | None (traditional) |
| **Blueprints (Stripe)** | Production reliability | Workflow template | Agentic nodes only |

**Key distinction (Thoughtworks)**: BDD uses specs for business collaboration; SDD extends this by separating requirements analysis from implementation, compressing context into formal specifications. Traditional waterfall has excessively long feedback cycles; SDD provides shorter, more effective cycles through rapid prototyping grounded in careful design.

## Common Anti-Patterns

1. **Overlong specifications** — exceeding the ~150-200 instruction ceiling causes performance degradation. Keep specs as routers to detailed docs, not monoliths.
2. **Spec rot** — specs that drift from implementation. Spec-anchored rigor (continuous sync) is the fix.
3. **Self-verifying agents** — having the same agent write code and verify it. Independent verification layers are essential.
4. **Vague acceptance criteria** — "good error handling" vs. "Error message shown for invalid credentials." Specificity is load-bearing.
5. **Skipping the planning phase** — jumping from intent to implementation without explicit spec review. "You don't move to coding until the spec is validated."
6. **Treating specs as pseudo-code** — over-specification constrains the agent's ability to find optimal implementations.

## Implications for Ralphify

### Direct Relevance

RALPH.md files are already a form of specification — YAML frontmatter defines the agent, commands, and args; the prompt body defines intent. The spec-driven pattern validates and extends this approach:

1. **RALPH.md as spec-first artifact**: The current structure (frontmatter + prompt body) maps naturally to the Specify -> Plan -> Implement pattern. Commands are deterministic nodes; the prompt body is the agentic directive.

2. **Stripe's Blueprint pattern maps to ralph loops**: Each loop iteration is effectively a blueprint execution — commands (deterministic) run first, their output fills placeholders, then the assembled prompt (agentic) runs. This is already the ralph architecture.

3. **Acceptance criteria in RALPH.md**: The `commands` field could support verification commands — deterministic checks that validate the agent's output each iteration, acting as acceptance criteria gates.

4. **Spec validation before loop execution**: A pre-flight check could validate RALPH.md structure and resolve placeholders before the first iteration runs, catching misconfigurations early.

5. **OpenSpec's brownfield approach**: The `changes/` directory pattern (proposal -> design -> tasks -> implementation) could inform how ralph loops handle multi-step feature development on existing codebases.

### Open Questions

- Should RALPH.md support a `spec` or `acceptance_criteria` frontmatter field for programmatic verification?
- Can the ralph loop's command system serve as a contract testing layer — deterministic commands verifying agent output each iteration?
- How does the 150-200 instruction ceiling interact with long RALPH.md prompt bodies? Should ralphify enforce or warn about length?
- Is there a role for a "spec ralph" that generates or refines RALPH.md files from conversational intent before the main loop runs?

## Sources

- [Spec-Driven Development (Thoughtworks)](https://www.thoughtworks.com/en-us/insights/blog/agile-engineering-practices/spec-driven-development-unpacking-2025-new-engineering-practices)
- [How to Write a Good Spec for AI Agents (Addy Osmani)](https://addyosmani.com/blog/good-spec/)
- [Spec-Driven Development: From Code to Contract (arXiv:2602.00180)](https://arxiv.org/abs/2602.00180)
- [Constitutional Spec-Driven Development (arXiv:2602.02584)](https://arxiv.org/abs/2602.02584)
- [Stripe Minions Blueprint Architecture (MindStudio)](https://www.mindstudio.ai/blog/stripe-minions-blueprint-architecture-deterministic-agentic-nodes)
- [Stripe Autonomous Coding Agents (InfoQ)](https://www.infoq.com/news/2026/03/stripe-autonomous-coding-agents/)
- [Deconstructing Stripe's Minions (SitePoint)](https://www.sitepoint.com/stripe-minions-architecture-explained/)
- [GitHub Spec Kit](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)
- [GitHub Spec Kit Repository](https://github.com/github/spec-kit)
- [AWS Kiro](https://kiro.dev/)
- [OpenSpec Framework](https://openspec.pro/)
- [OpenSpec Deep Dive](https://redreamality.com/garden/notes/openspec-guide/)
- [OpenSpec YC Launch](https://www.ycombinator.com/launches/Pdc-openspec-the-spec-framework-for-coding-agents)
- [Chief Autonomous PRD Agent](https://chiefloop.com/concepts/prd-format.html)
- [Technical Design Spec Pattern (Tom Yedwab)](https://www.arguingwithalgorithms.com/posts/technical-design-spec-pattern.html)
- [Spec-Driven Verification for Coding Agents (Agent Wars)](https://agent-wars.com/news/2026-03-14-spec-driven-verification-claude-code-agents)
- [SDD Building Predictable AI Software (DEV Community)](https://dev.to/koustubh/part-1-spec-driven-development-building-predictable-ai-assisted-software-19ne)
- [Is BDD Dying? (Automation Panda)](https://automationpanda.com/2025/03/06/is-bdd-dying/)
- [Gherkinizer](https://gherkinizer.com/)
- [Contract Testing via AI Agent (TestSprite)](https://www.testsprite.com/use-cases/en/contract-testing)
- [Stop Reading AI-Generated Code (DEV Community)](https://dev.to/choutos/stop-reading-ai-generated-code-start-verifying-it-1d1o)
- [AI-Powered Contract Testing (DEV Community)](https://dev.to/signadot/the-future-of-api-validation-a-deep-dive-into-ai-powered-contract-testing-4da7)
- [Anthropic 2026 Agentic Coding Trends Report](https://resources.anthropic.com/2026-agentic-coding-trends-report)
- [Spec-Driven Development 2026 (Alex Cloudstar)](https://www.alexcloudstar.com/blog/spec-driven-development-2026/)
- [SDD Is Eating Software Engineering (Medium)](https://medium.com/@visrow/spec-driven-development-is-eating-software-engineering-a-map-of-30-agentic-coding-frameworks-6ac0b5e2b484)
- [How to Keep Your AI Agent From Going Rogue (Arguing with Algorithms)](https://www.arguingwithalgorithms.com/posts/technical-design-spec-pattern.html)
- [Intent Engineering Framework (Product Compass)](https://www.productcompass.pm/p/intent-engineering-framework-for-ai-agents)
- [Why Plan Matters in Coding AI Agent (DEV Community)](https://dev.to/chenverdent/why-plan-matters-in-coding-ai-agent-fixing-misaligned-prompts-1d74)
- [Gherkin User Stories Guide 2026 (TestQuality)](https://testquality.com/gherkin-user-stories-acceptance-criteria-guide/)
- [Best SDD Tools 2026 (Augment Code)](https://www.augmentcode.com/tools/best-spec-driven-development-tools)
