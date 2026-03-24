#!/bin/bash
pattern="$1"
files=$(grep -rl "$pattern" src/ 2>/dev/null)
count=$(echo "$files" | grep -c . 2>/dev/null || echo 0)
echo "$count files remaining"
echo "$files" | head -20
