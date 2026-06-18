#!/usr/bin/env bash
set -euo pipefail

STEPS=${STEPS:-400}
WANDB_PROJECT=${WANDB_PROJECT:-RLVE}

python -m experiments.run_all \
  --wandb-project "${WANDB_PROJECT}" \
  --steps "${STEPS}" \
  "$@"

PLOT_ARGS=()
if [ -n "${PLOT_WANDB_START_TIME:-}" ]; then
  PLOT_ARGS+=(--wandb-start-time "${PLOT_WANDB_START_TIME}")
fi

python -m experiments.plot_results "${PLOT_ARGS[@]}"
