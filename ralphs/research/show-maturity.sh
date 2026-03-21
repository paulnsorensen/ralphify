#!/bin/bash
# Show research maturity metrics so the agent can gauge progress
WORKSPACE="${RALPH_ARG_WORKSPACE:-research-workspace}"

if [ ! -d "$WORKSPACE" ]; then
    echo "Workspace not created yet — first iteration."
    exit 0
fi

# Iteration count (research commits)
iterations=$(git log --oneline -- "$WORKSPACE/" 2>/dev/null | wc -l | tr -d ' ')
echo "Iterations: $iterations"

# Questions
if [ -f "$WORKSPACE/notes/questions.md" ]; then
    open=$(grep -c -E '^\s*-\s*\[[ ]\]' "$WORKSPACE/notes/questions.md" 2>/dev/null || echo 0)
    answered=$(grep -c -E '^\s*-\s*\[[xX]\]' "$WORKSPACE/notes/questions.md" 2>/dev/null || echo 0)
    echo "Questions: $answered answered, $open open"
else
    echo "Questions: (none yet)"
fi

# Sources
if [ -f "$WORKSPACE/notes/sources.md" ]; then
    sources=$(grep -c -E '^- http|^\d+\.' "$WORKSPACE/notes/sources.md" 2>/dev/null || echo 0)
    echo "Sources logged: $sources"
else
    echo "Sources: (none yet)"
fi

# Chapters
if [ -d "$WORKSPACE/chapters" ]; then
    chapter_count=$(find "$WORKSPACE/chapters" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    total_words=$(cat "$WORKSPACE/chapters"/*.md 2>/dev/null | wc -w | tr -d ' ')
    echo "Chapters: $chapter_count ($total_words words total)"
else
    echo "Chapters: (none yet)"
fi

# REPORT.md size
if [ -f "$WORKSPACE/REPORT.md" ]; then
    report_lines=$(wc -l < "$WORKSPACE/REPORT.md" | tr -d ' ')
    echo "REPORT.md: $report_lines lines (target: <150)"
    if [ "$report_lines" -gt 150 ]; then
        echo "WARNING: REPORT.md exceeds 150 lines — move detail to chapters"
    fi
else
    echo "REPORT.md: (not created yet)"
fi

# Convergence signal
if [ -f "$WORKSPACE/notes/questions.md" ]; then
    total_q=$((open + answered))
    if [ "$total_q" -gt 0 ] && [ "$answered" -gt 0 ]; then
        pct=$((answered * 100 / total_q))
        echo ""
        if [ "$pct" -ge 80 ] && [ "$sources" -ge 20 ]; then
            echo "SIGNAL: Research is maturing ($pct% questions answered, $sources sources). Balance new exploration with refinement — keep generating questions in new directions, but shift more iterations toward polishing existing work."
        elif [ "$pct" -ge 60 ]; then
            echo "SIGNAL: Good progress ($pct% questions answered). Keep going."
        fi
    fi
fi
