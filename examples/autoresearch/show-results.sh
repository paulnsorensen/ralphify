#!/bin/bash
# Show experiment history from results.tsv
if [ -f results.tsv ]; then
    cat results.tsv
else
    echo "No results.tsv yet — first iteration should create it and run the baseline."
fi
