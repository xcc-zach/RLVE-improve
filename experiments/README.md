# 启动命令

```bash
env http_proxy= https_proxy= all_proxy= HTTP_PROXY= HTTPS_PROXY= ALL_PROXY= \
  NO_PROXY=127.0.0.1,localhost,0.0.0.0,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16 \
  no_proxy=127.0.0.1,localhost,0.0.0.0,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16 \
  python -m experiments.run_all \
    --wandb-project RLVE \
    --steps 400 \
    --resource-profile auto \
    --wandb-mode offline \
    --dynamic-sampling-filter-path slime.rollout.filter_hub.dynamic_sampling_filters.check_reward_nonzero_std
```

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
  --model openreasoning-nemotron-1.5b \
  --difficulty-mode adaptive \
  --steps 400
```

By default, `run_training.py` keeps non-PLAN training/resource parameters aligned with the repository training scripts. For non-8-GPU or lower-memory machines, pass `--resource-profile auto` or explicitly override flags such as `--num-gpus`, `--gpu-mem-gb`, `--context-parallel-size`, `--rollout-max-response-len`, `--rollout-batch-size`, or `--n-samples-per-prompt`. The `auto` profile uses conservative batch size, sample count, and SGLang concurrency on 1-2 GPU machines while keeping the 1.5B response limit aligned with the repository default of 24576 tokens; on 2x40GB+ GPUs it uses 24576 response tokens for 1.5B and 4096 for 7B. `repo` remains the exact repository-style setting. The launcher also unsets proxy variables for Ray local endpoints, because proxying `127.0.0.1:8265` can break `ray job submit`. Dynamic sampling keeps the repository filter by default; for a low-resource smoke test only, pass `--dynamic-sampling-filter-path ''` to avoid an endless wait when every sampled answer receives the same reward.

Use the OpenReasoning 7B checkpoint with:

```bash
python -m experiments.run_training \
  --wandb-project RLVE \
  --run-name exp3_sorting_openreasoning_nemotron_7b \
  --environment-list Sorting \
  --model openreasoning-nemotron-7b \
  --difficulty-mode adaptive \
  --steps 400
```

Run one static-difficulty job:

```bash
python -m experiments.run_training \
  --wandb-project RLVE \
  --run-name exp1_static_0_4_digit_sum_interval \
  --environment-list digit_sum_interval \
  --model openreasoning-nemotron-1.5b \
  --difficulty-mode static \
  --static-min-difficulty 0 \
  --static-max-difficulty 4 \
  --steps 400
```

Run the implemented PLAN matrix:

```bash
python -m experiments.run_all --wandb-project RLVE --steps 400
# or
experiments/run_all.sh
```

`run_all.py` generates 100 in-distribution evaluation problems per environment by uniformly sampling difficulty from `[0,4]`, and regenerates stale evaluation files if they were created with older difficulty settings. The new-environment held-out set is generated with 100 samples from difficulty `[0,4]`.

Generate CSV metrics and any currently available PLAN figures from offline W&B stdout records:

```bash
python -m experiments.plot_results
# Exclude older smoke runs when plotting a specific PLAN run:
python -m experiments.plot_results --wandb-start-time 20260617_083616
```

The plotter writes `outputs/results/metrics.csv`, `outputs/results/plot_summary.json`, and PNGs under `outputs/figures`. It is safe to rerun while experiments are still incomplete; missing curves are skipped until their runs have logged the corresponding metrics.
