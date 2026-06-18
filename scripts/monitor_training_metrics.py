#!/usr/bin/env python3
"""Monitor RLVE training logs and write per-step training metrics to outputs.

This script tails a Ray driver log and emits one JSON object per training step.
It is intentionally log-based so it can be used without changing the training
code.
"""

import argparse
import ast
import glob
import json
import os
import re
import time
from typing import Dict, Optional


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
METRIC_RE = re.compile(r"\b(rlve|rollout|step)\s+(\d+):\s+(\{.*\})")


TRAINING_KEYS = {
    "rollout/raw_reward",
    "rollout/rewards",
    "rollout/truncated",
    "rollout/response_lengths",
    "rollout/total_lengths",
    "rollout/effective_prompt_rate",
    "train/loss",
    "train/pg_loss",
    "train/entropy_loss",
    "train/ppo_kl",
    "train/grad_norm",
    "train/step",
}


def strip_ansi(line: str) -> str:
    return ANSI_RE.sub("", line)


def latest_driver_log(run_name: Optional[str]) -> str:
    pattern = "/tmp/ray/session_latest/logs/job-driver-*.log"
    candidates = glob.glob(pattern)
    if run_name:
        candidates = [path for path in candidates if run_name in os.path.basename(path)]
    if not candidates:
        if run_name:
            raise SystemExit(f"No Ray driver log found for run name: {run_name}")
        raise SystemExit("No Ray driver log found under /tmp/ray/session_latest/logs")
    return max(candidates, key=os.path.getmtime)


def default_output_path(log_file: str) -> str:
    base = os.path.basename(log_file)
    if base.startswith("job-driver-"):
        base = base[len("job-driver-") :]
    if base.endswith(".log"):
        base = base[:-len(".log")]
    return os.path.join("outputs", f"{base}_training_metrics.jsonl")


def metric_is_training_signal(key: str) -> bool:
    if key in TRAINING_KEYS:
        return True
    if key.startswith("RLVE/") and (key.endswith("/accuracy") or key.endswith("/difficulty")):
        return True
    return False


def parse_metric_line(line: str):
    match = METRIC_RE.search(strip_ansi(line))
    if not match:
        return None
    kind, step_text, payload_text = match.groups()
    try:
        payload = ast.literal_eval(payload_text)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return kind, int(step_text), payload


def filtered_payload(payload: Dict) -> Dict:
    return {key: value for key, value in payload.items() if metric_is_training_signal(key)}


def follow_file(path: str, from_end: bool, poll_interval: float):
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        if from_end:
            handle.seek(0, os.SEEK_END)
        while True:
            line = handle.readline()
            if line:
                yield line
                continue
            time.sleep(poll_interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write per-step RLVE training metrics from a Ray driver log.")
    parser.add_argument("--log-file", help="Ray driver log path. If omitted, use the latest matching job-driver log.")
    parser.add_argument("--run-name", help="Substring used to find the Ray driver log.")
    parser.add_argument("--output", help="Output JSONL path. Defaults to outputs/<run>_training_metrics.jsonl.")
    parser.add_argument("--from-end", action="store_true", help="Only collect metrics written after this script starts.")
    parser.add_argument("--poll-interval", type=float, default=1.0)
    args = parser.parse_args()

    log_file = args.log_file or latest_driver_log(args.run_name)
    output = args.output or default_output_path(log_file)
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)

    by_step: Dict[int, Dict] = {}

    with open(output, "a", encoding="utf-8") as out:
        for line in follow_file(log_file, args.from_end, args.poll_interval):
            parsed = parse_metric_line(line)
            if parsed is None:
                continue

            kind, step, payload = parsed
            metrics = filtered_payload(payload)
            if not metrics:
                continue

            record = by_step.setdefault(step, {"step": step})
            record.update(metrics)

            if kind == "step":
                record["timestamp"] = time.time()
                out.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                out.flush()


if __name__ == "__main__":
    main()
