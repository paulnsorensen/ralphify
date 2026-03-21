# Research Workspace Conventions

This file defines the structure and formatting rules for research workspaces. Read this when you need to create or restructure the workspace. You do not need to re-read it every iteration.

## Workspace structure

```
workspace/
├── CONVENTIONS.md       # Copy of this file (optional, for reference)
├── REPORT.md            # Executive overview + table of contents (<150 lines)
├── chapters/
│   ├── 01-topic-slug.md # Deep-dive chapter
│   ├── 02-topic-slug.md
│   └── ...
└── notes/
    ├── questions.md     # Research question tree (checkbox format)
    ├── sources.md       # Source log
    ├── insights.md      # Distilled insights
    └── scratchpad.md    # Raw ideas, current focus, loose threads
```

## REPORT.md format

REPORT.md is an executive briefing, not the full report. It must stay under 150 lines. Structure:

```markdown
# [Topic Title]

> One-paragraph executive summary of current findings.

## Key Insights

1. Most important finding
2. Second most important finding
... (5-10 numbered insights, updated as research evolves)

## Chapters

| # | Chapter | Summary |
|---|---------|---------|
| 1 | [Chapter Title](chapters/01-slug.md) | One-line summary |
| 2 | [Chapter Title](chapters/02-slug.md) | One-line summary |

## Open Questions

- What we still don't know (pulled from notes/questions.md)

## Key Sources

- Most important sources referenced (pulled from notes/sources.md)
```

If REPORT.md is growing beyond 150 lines, you're putting too much detail in it. Move detail to chapters.

## Chapter format

Each research area gets its own file: `chapters/NN-slug.md`. Chapters should be self-contained — a reader should understand one without reading the others.

```markdown
# [Chapter Title]

> 2-3 sentence summary of this chapter's findings.

## [Section]
...detailed findings, analysis, evidence...

## [Section]
...
```

Create new chapters as research areas emerge. Split chapters that grow too large or cover multiple distinct areas.

## notes/questions.md format

Use checkbox format so maturity can be tracked automatically:

```markdown
# Research Questions

## Open
- [ ] High-priority question here
- [ ] Another question
  - [ ] Sub-question that emerged from research

## Answered
- [x] Question that was answered — brief answer summary
- [x] Another answered question — see chapter 02
```

## notes/sources.md format

```markdown
# Sources

- https://example.com/article — Author Name — One-line summary of what's valuable — **high**
- https://example.com/other — Org Name — Summary — **medium**
```

Include: URL, author/org, one-line value summary, relevance rating (high/medium/low).

## notes/insights.md format

Each insight is a concise, actionable statement with supporting evidence:

```markdown
# Insights

## [Category or theme]
- **Insight statement.** Supporting evidence or source reference.
- **Another insight.** Evidence.
```
