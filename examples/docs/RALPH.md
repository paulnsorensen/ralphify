---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: docs-build
    run: uv run mkdocs build --strict
  - name: git-log
    run: git log --oneline -20
  - name: git-diff
    run: git diff --name-only HEAD~10
args:
  - focus
---

# Docs

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

## Docs build output

{{ commands.docs-build }}

If there are warnings or errors above, fix them first.

## Recent changes

{{ commands.git-log }}

## Recently changed files

{{ commands.git-diff }}

## Task

Maintain and improve the ralphify documentation.
{{ args.focus }}

Pick one thing per iteration. Read the relevant code and existing docs
before making any change.

## What the docs are for

The docs serve two jobs:

1. **Users who want to build cool ralphs** — they need to understand
   the ralph format, prompt patterns, CLI flags, and how to get the
   most out of the loop. Get them productive fast.

2. **Project growth** — people discovering ralphify need to immediately
   understand what it does, why it matters, and how to get started.
   First impressions count: landing page, README, SEO, and visual
   polish all matter here.

Contributor docs (`docs/contributing/`) help developers and coding
agents understand the codebase so they can contribute effectively.

## Principles

- **Don't over-document.** Only document what helps someone do
  something. If it's obvious from the CLI help or the code, skip it.
  Not every function or flag needs a docs page.

- **Don't gold-plate.** Good enough is good enough. Clean, correct,
  and scannable beats comprehensive and polished. Move on.

- **Close important gaps.** When recent code changes introduced new
  features or changed behavior, update the relevant doc surfaces.
  Not every change needs a docs update — use judgement.

- **Keep all surfaces in sync.** When something user-facing changes,
  check: `docs/`, `README.md`, `src/ralphify/skills/new-ralph/SKILL.md`,
  and `docs/quick-reference.md`. Update what's relevant.

- **SEO basics.** Every page should have a clear `description` and
  `keywords` in its frontmatter. Titles should be descriptive. Don't
  over-optimize — just make sure search engines can understand what
  each page is about.

- **Branding and feel.** Ralphify's tone is direct, casual, and
  practical. The visual identity uses violet/deep-purple (#8B6CF0)
  and orange (#E87B4A) as brand colors. Keep the look consistent
  with existing pages. Don't introduce new visual patterns without
  good reason.

- **Think jobs-to-be-done**, not feature lists. Frame docs around
  what the user is trying to accomplish: "How do I pass arguments to
  my ralph?" not "The args field accepts a list of strings."

## What to work on

Look at the recent commits and changed files above. Then:

1. Fix any mkdocs build warnings or errors
2. Close gaps between code changes and docs
3. Improve existing pages (clarity, examples, scannability)
4. Improve SEO metadata where it's missing or weak
5. Clean up anything that feels bloated or gold-plated

## Rules

- One improvement per iteration
- Read the code and existing docs before changing anything
- Run `mkdocs build --strict` and ensure zero warnings before committing
- Commit with a descriptive message and push
