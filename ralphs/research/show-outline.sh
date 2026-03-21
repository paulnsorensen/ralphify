#!/bin/bash
# Show report headings and chapter listing
WORKSPACE="${RALPH_ARG_WORKSPACE:-research-workspace}"

echo "## Report headings"
if [ -f "$WORKSPACE/REPORT.md" ]; then
    grep -E '^#{1,3} ' "$WORKSPACE/REPORT.md"
else
    echo "(no report yet)"
fi

echo ""
echo "## Chapters"
if [ -d "$WORKSPACE/chapters" ]; then
    for f in "$WORKSPACE/chapters"/*.md; do
        [ -f "$f" ] || continue
        filename=$(basename "$f")
        heading=$(head -5 "$f" | grep -m1 -E '^# ' || echo "(no heading)")
        lines=$(wc -l < "$f" | tr -d ' ')
        echo "- $filename ($lines lines): $heading"
    done
    chapter_count=$(find "$WORKSPACE/chapters" -name '*.md' | wc -l | tr -d ' ')
    if [ "$chapter_count" -eq 0 ]; then
        echo "(no chapters yet)"
    fi
else
    echo "(no chapters/ directory yet)"
fi
