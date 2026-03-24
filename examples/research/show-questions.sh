#!/bin/bash
# Show the current research question tree
WORKSPACE="${RALPH_ARG_WORKSPACE:-research-workspace}"

if [ -f "$WORKSPACE/notes/questions.md" ]; then
    cat "$WORKSPACE/notes/questions.md"
else
    echo "(no questions file yet — will be created on first iteration)"
fi
