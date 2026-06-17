# PLAN.md Experiments

Generate the new-environment held-out set:

```bash
python -m experiments.make_eval_data
```

Run one adaptive RLVE job:

```bash
python -m experiments.run_training \
  --wandb-project RLVE \
  --run-name exp1_adaptive_digit_sum_interval \
  --environment-list digit_sum_interval \
  --difficulty-mode adaptive \
  --steps 400
```

By default, `run_training.py` keeps non-PLAN training/resource parameters aligned with the repository training scripts. For non-8-GPU or lower-memory machines, pass `--resource-profile auto` or explicitly override flags such as `--num-gpus`, `--gpu-mem-gb`, `--context-parallel-size`, `--rollout-max-response-len`, `--rollout-batch-size`, or `--n-samples-per-prompt`. The `auto` profile uses conservative rollout length, batch size, sample count, and SGLang concurrency on 1-2 GPU machines; `repo` remains the exact repository-style setting. The launcher also unsets proxy variables for Ray local endpoints, because proxying `127.0.0.1:8265` can break `ray job submit`. Dynamic sampling keeps the repository filter by default; for a low-resource smoke test only, pass `--dynamic-sampling-filter-path ''` to avoid an endless wait when every sampled answer receives the same reward.

Use the DeepSeek 7B checkpoint with:

```bash
python -m experiments.run_training \
  --wandb-project RLVE \
  --run-name exp3_sorting_deepseek_r1_distill_qwen_7b \
  --environment-list Sorting \
  --model deepseek-r1-distill-qwen-7b \
  --difficulty-mode adaptive \
  --steps 400
```

Run one static-difficulty job:

```bash
python -m experiments.run_training \
  --wandb-project RLVE \
  --run-name exp1_static_0_20_digit_sum_interval \
  --environment-list digit_sum_interval \
  --difficulty-mode static \
  --static-min-difficulty 0 \
  --static-max-difficulty 20 \
  --steps 400
```

Run the implemented PLAN matrix:

```bash
python -m experiments.run_all --wandb-project RLVE --steps 400
# or
experiments/run_all.sh
```

Generate CSV metrics and any currently available PLAN figures from offline W&B stdout records:

```bash
python -m experiments.plot_results
```

The plotter writes `outputs/results/metrics.csv`, `outputs/results/plot_summary.json`, and PNGs under `outputs/figures`. It is safe to rerun while experiments are still incomplete; missing curves are skipped until their runs have logged the corresponding metrics.
