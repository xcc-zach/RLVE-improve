#!/usr/bin/env bash
set -euo pipefail

STEPS=${STEPS:-10}
EVAL_INTERVAL=${EVAL_INTERVAL:-1}
WANDB_PROJECT=${WANDB_PROJECT:-RLVE}
RESOURCE_PROFILE=${RESOURCE_PROFILE:-auto}
WANDB_MODE=${WANDB_MODE:-offline}
ROLLOUT_MAX_RESPONSE_LEN=${ROLLOUT_MAX_RESPONSE_LEN:-8192}
EVAL_MAX_RESPONSE_LEN=${EVAL_MAX_RESPONSE_LEN:-8192}
DYNAMIC_SAMPLING_FILTER_PATH=${DYNAMIC_SAMPLING_FILTER_PATH:-slime.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std}

COMMON_ARGS=(
  --wandb-project "${WANDB_PROJECT}"
  --environment-list Division
  --difficulty-mode adaptive
  --steps "${STEPS}"
  --eval-interval "${EVAL_INTERVAL}"
  --resource-profile "${RESOURCE_PROFILE}"
  --wandb-mode "${WANDB_MODE}"
  --rollout-max-response-len "${ROLLOUT_MAX_RESPONSE_LEN}"
  --eval-max-response-len "${EVAL_MAX_RESPONSE_LEN}"
  --dynamic-sampling-filter-path "${DYNAMIC_SAMPLING_FILTER_PATH}"
  --eval-prompt-data IN_DIST_Division outputs/eval/in_distribution/Division.json OOD outputs/eval/out_of_distribution/test.json
)

python -m experiments.make_eval_data \
  --output outputs/eval/in_distribution/Division.json \
  --config-output outputs/eval/in_distribution/Division_evaluation_config.json \
  --num-samples 100 \
  --difficulty-min 0 \
  --difficulty-max 9 \
  --environments Division

python -m experiments.make_eval_data \
  --output outputs/eval/out_of_distribution/test.json \
  --config-output outputs/eval/out_of_distribution/evaluation_config.json \
  --num-samples 100 \
  --difficulty-min 0 \
  --difficulty-max 9 \
  --environments Division digit_sum_interval binary_string_no_adjacent_count grid_path_counting_with_blocks

python -m experiments.run_training \
  "${COMMON_ARGS[@]}" \
  --run-name exp3_division_openreasoning_nemotron_7b \
  --model openreasoning-nemotron-7b

PLOT_ARGS=()
if [ -n "${PLOT_WANDB_START_TIME:-}" ]; then
  PLOT_ARGS+=(--wandb-start-time "${PLOT_WANDB_START_TIME}")
fi

python -m experiments.plot_results "${PLOT_ARGS[@]}"
