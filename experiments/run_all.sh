#!/usr/bin/env bash
set -euo pipefail

STEPS=${STEPS:-400}
WANDB_PROJECT=${WANDB_PROJECT:-RLVE}

python -m experiments.run_all \
  --wandb-project "${WANDB_PROJECT}" \
  --steps "${STEPS}" \
  "$@"

python -m experiments.plot_results
