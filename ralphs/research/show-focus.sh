#!/bin/bash
# Show what the agent focused on last iteration (from scratchpad)
WORKSPACE="${RALPH_ARG_WORKSPACE:-research-workspace}"

if [ -f "$WORKSPACE/notes/scratchpad.md" ]; then
    # Show last 20 lines — most recent focus/notes
    tail -20 "$WORKSPACE/notes/scratchpad.md"
else
    echo "(no scratchpad yet — first iteration)"
fi
