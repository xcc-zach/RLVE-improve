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
EXP3_MODELS=${EXP3_MODELS:-both}

COMMON_ARGS=(
  --wandb-project "${WANDB_PROJECT}"
  --environment-list Sorting
  --difficulty-mode adaptive
  --steps "${STEPS}"
  --eval-interval "${EVAL_INTERVAL}"
  --resource-profile "${RESOURCE_PROFILE}"
  --wandb-mode "${WANDB_MODE}"
  --rollout-max-response-len "${ROLLOUT_MAX_RESPONSE_LEN}"
  --eval-max-response-len "${EVAL_MAX_RESPONSE_LEN}"
  --dynamic-sampling-filter-path "${DYNAMIC_SAMPLING_FILTER_PATH}"
  --eval-prompt-data IN_DIST_Sorting outputs/eval/in_distribution/Sorting.json NEW_ENV_HELD_OUT outputs/eval/new_environments/test.json
)

if [ ! -f outputs/eval/in_distribution/Sorting.json ]; then
  python -m experiments.make_eval_data \
    --output outputs/eval/in_distribution/Sorting.json \
    --config-output outputs/eval/in_distribution/Sorting_evaluation_config.json \
    --num-samples 100 \
    --difficulty-min 0 \
    --difficulty-max 9 \
    --environments Sorting
fi

if [ ! -f outputs/eval/new_environments/test.json ]; then
  python -m experiments.make_eval_data \
    --output outputs/eval/new_environments/test.json \
    --config-output outputs/eval/new_environments/evaluation_config.json \
    --num-samples 100 \
    --difficulty-min 0 \
    --difficulty-max 9 \
    --environments digit_sum_interval binary_string_no_adjacent_count grid_path_counting_with_blocks
fi

case "${EXP3_MODELS}" in
  both)
    python -m experiments.run_training \
      "${COMMON_ARGS[@]}" \
      --run-name exp3_sorting_openreasoning_nemotron_1_5b \
      --model openreasoning-nemotron-1.5b
    python -m experiments.run_training \
      "${COMMON_ARGS[@]}" \
      --run-name exp3_sorting_openreasoning_nemotron_7b \
      --model openreasoning-nemotron-7b
    ;;
  1.5b)
    python -m experiments.run_training \
      "${COMMON_ARGS[@]}" \
      --run-name exp3_sorting_openreasoning_nemotron_1_5b \
      --model openreasoning-nemotron-1.5b
    ;;
  7b)
    python -m experiments.run_training \
      "${COMMON_ARGS[@]}" \
      --run-name exp3_sorting_openreasoning_nemotron_7b \
      --model openreasoning-nemotron-7b
    ;;
  *)
    echo "Unsupported EXP3_MODELS=${EXP3_MODELS}. Use one of: both, 1.5b, 7b." >&2
    exit 1
    ;;
esac

PLOT_ARGS=()
if [ -n "${PLOT_WANDB_START_TIME:-}" ]; then
  PLOT_ARGS+=(--wandb-start-time "${PLOT_WANDB_START_TIME}")
fi

python -m experiments.plot_results "${PLOT_ARGS[@]}"
