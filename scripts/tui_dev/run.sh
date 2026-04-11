#!/usr/bin/env bash
# Regenerate all TUI dev snapshots.
#
#   ./scripts/tui_dev/run.sh              # both modes
#   ./scripts/tui_dev/run.sh snapshot     # fast path only (no subprocess)
#   ./scripts/tui_dev/run.sh live         # real ralph run via pty
#
# Output goes to scripts/tui_dev/output/*.png — Read those in Claude
# Code to see exactly what the terminal output looks like.

set -euo pipefail
cd "$(dirname "$0")/../.."

MODE="${1:-all}"

case "$MODE" in
  snapshot|all)
    uv run python scripts/tui_dev/snapshot.py
    ;;
esac

case "$MODE" in
  live|all)
    uv run --with pyte python scripts/tui_dev/live.py
    ;;
esac

echo ""
echo "Snapshots:"
ls -1 scripts/tui_dev/output/*.png 2>/dev/null | sed 's|^|  |'
