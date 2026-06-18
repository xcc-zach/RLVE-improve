import argparse
import ast
import re
import subprocess
import time

from experiments.metrics_recorder import append_metrics


RUN_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
METRIC_PATTERN = re.compile(r"^(?:\([^)]*\)\s*)?(eval|rlve|rollout|step|perf)\s+(-?\d+):\s+(\{.*\})\s*$")
TERMINAL = {"SUCCEEDED", "FAILED", "STOPPED"}


def strip_line(line : str) -> str :
    line = RUN_PATTERN.sub("", line)
    line = re.sub(r"^\([^)]* pid=\d+\)\s*", "", line)
    return line.strip()


def parse_rows(text : str) -> list[tuple[str, int, dict]] :
    rows = []
    for raw_line in text.splitlines() :
        line = strip_line(raw_line)
        match = METRIC_PATTERN.match(line)
        if not match :
            continue
        phase, step, payload = match.groups()
        try :
            metrics = ast.literal_eval(payload)
        except Exception :
            continue
        if isinstance(metrics, dict) :
            rows.append((phase, int(step), metrics))
    return rows


def run_ray_command(args : list[str]) -> subprocess.CompletedProcess :
    return subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def job_status(address : str, job_id : str) -> str | None :
    result = run_ray_command(["ray", "job", "status", "--address", address, job_id])
    if result.returncode != 0 :
        return None
    for status in ["PENDING", "RUNNING", "SUCCEEDED", "FAILED", "STOPPED"] :
        if status in result.stdout :
            return status
    return None


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="http://127.0.0.1:8265")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--run-name", required=True)
    parser.add_argument("--interval", type=float, default=15.0)
    args = parser.parse_args()

    seen = set()
    while True :
        result = run_ray_command(["ray", "job", "logs", "--address", args.address, args.job_id])
        if result.returncode == 0 :
            for phase, step, metrics in parse_rows(result.stdout) :
                new_metrics = {}
                for metric, value in metrics.items() :
                    key = (phase, step, metric, repr(value))
                    if key in seen :
                        continue
                    seen.add(key)
                    new_metrics[metric] = value
                append_metrics(args.run_name, phase, step, new_metrics, source=args.job_id)

        status = job_status(args.address, args.job_id)
        if status in TERMINAL :
            break
        time.sleep(args.interval)


if __name__ == "__main__" :
    main()
