#!/bin/bash
# Show key metrics from the most recent training run
if [ -f run.log ]; then
    grep "^val_bpb:\|^training_seconds:\|^peak_vram_mb:\|^mfu_percent:\|^num_params_M:\|^depth:" run.log
else
    echo "No run.log yet — no training runs have been executed."
fi
