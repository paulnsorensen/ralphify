#!/bin/bash
# Editorial review agent — reads the research workspace and gives feedback
WORKSPACE="${RALPH_ARG_WORKSPACE:-research-workspace}"
FOCUS="${RALPH_ARG_FOCUS:-}"

if [ ! -d "$WORKSPACE" ]; then
    echo "No workspace yet — skip review on first iteration."
    exit 0
fi

# Gather workspace state
report=""
if [ -f "$WORKSPACE/REPORT.md" ]; then
    report=$(cat "$WORKSPACE/REPORT.md")
fi

questions=""
if [ -f "$WORKSPACE/notes/questions.md" ]; then
    questions=$(cat "$WORKSPACE/notes/questions.md")
fi

insights=""
if [ -f "$WORKSPACE/notes/insights.md" ]; then
    insights=$(cat "$WORKSPACE/notes/insights.md")
fi

sources=""
if [ -f "$WORKSPACE/notes/sources.md" ]; then
    sources=$(cat "$WORKSPACE/notes/sources.md")
fi

chapters=""
if [ -d "$WORKSPACE/chapters" ]; then
    for f in "$WORKSPACE/chapters"/*.md; do
        [ -f "$f" ] || continue
        chapters="$chapters
=== $(basename "$f") ===
$(cat "$f")
"
    done
fi

recent_log=$(git log --oneline -10 -- "$WORKSPACE/" 2>/dev/null)

# Assemble review prompt and pipe to claude
cat <<PROMPT | claude -p --max-tokens 1000
You are a research editor reviewing an autonomous research agent's work. Your job is to give sharp, actionable feedback that steers the next iteration toward higher-signal output.

## Research focus
$FOCUS

## Current report
$report

## Chapters
$chapters

## Research questions
$questions

## Insights
$insights

## Sources
$sources

## Recent git log
$recent_log

## Your task

Write 3-5 bullet points of editorial feedback. Be specific and direct. Focus on:

- **Coverage gaps**: what important angles of the research focus are underexplored or missing entirely?
- **Weak spots**: which claims lack evidence, which chapters are thin, which insights are vague?
- **Signal vs noise**: what content is low-value and should be cut or deprioritized?
- **Source quality**: are there enough high-quality practitioner sources? Too much reliance on any one type?
- **Question tree health**: is the agent exploring broadly enough, or stuck in one branch?
- **Next move**: what single focus area would add the most value next iteration?

Be a tough but constructive editor. Don't praise — only give feedback that changes what the agent does next.
PROMPT
