import argparse
import ast
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

try :
    from wandb.proto import wandb_internal_pb2
    from wandb.sdk.internal.datastore import DataStore
except ImportError :
    wandb_internal_pb2 = None
    DataStore = None


RUN_PATTERN = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
METRIC_PATTERN = re.compile(r"^(?:\([^)]*\)\s*)?(eval|rlve|rollout|step|perf)\s+(-?\d+):\s+(\{.*\})\s*$")
WANDB_DIR_PATTERN = re.compile(r"^offline-run-(\d{8}_\d{6})-[^-]+$")

EXP1_ENVIRONMENTS = [
    "Division",
    "digit_sum_interval",
    "binary_string_no_adjacent_count",
    "grid_path_counting_with_blocks",
]
EXP1_CONFIGS = [
    ("adaptive", "Adaptive [h-1,h]", "exp1_adaptive_{environment}"),
    ("static_0_1", "Static [0,1]", "exp1_static_0_1_{environment}"),
    ("static_0_4", "Static [0,4]", "exp1_static_0_4_{environment}"),
    ("static_0_9", "Static [0,9]", "exp1_static_0_9_{environment}"),
]
EXP2_RUNS = [
    ("1", "1 env", "exp2_num_environment_1"),
    ("4", "4 envs", "exp2_num_environment_4"),
    ("16", "16 envs", "exp2_num_environment_16"),
    ("256", "256 envs", "exp2_num_environment_256"),
]
EXP3_RUNS = [
    ("1.5B", "OpenReasoning-Nemotron-1.5B", "exp1_adaptive_Division"),
    ("7B", "OpenReasoning-Nemotron-7B", "exp3_division_openreasoning_nemotron_7b"),
]


def strip_line(line : str) -> str :
    return RUN_PATTERN.sub("", line).strip()


def parse_json(value : str) :
    try :
        return json.loads(value)
    except Exception :
        return value


def scan_wandb_file(path : Path) -> tuple[dict, list[dict]] :
    if DataStore is None or wandb_internal_pb2 is None :
        raise SystemExit("wandb is required to parse offline W&B files; use --live-metrics-root only or install wandb.")
    if path.stat().st_size == 0 :
        return {}, []
    datastore = DataStore()
    try :
        datastore.open_for_scan(str(path))
    except AssertionError :
        return {}, []
    config = {}
    rows = []
    try :
        while True :
            data = datastore.scan_data()
            if data is None :
                break
            record = wandb_internal_pb2.Record()
            record.ParseFromString(data)
            record_type = record.WhichOneof("record_type")
            if record_type == "run" :
                for update in record.run.config.update :
                    config[update.key] = parse_json(update.value_json)
            elif record_type == "output_raw" :
                line = strip_line(record.output_raw.line)
                match = METRIC_PATTERN.match(line)
                if not match :
                    continue
                phase, step, payload = match.groups()
                try :
                    metrics = ast.literal_eval(payload)
                except Exception :
                    continue
                for metric, value in metrics.items() :
                    if isinstance(value, (int, float)) :
                        rows.append(
                            {
                                "run_name" : config.get("wandb_group") or config.get("run_name") or path.parent.name,
                                "phase" : phase,
                                "line_step" : int(step),
                                "metric" : metric,
                                "value" : float(value),
                                "wandb_file" : str(path),
                            }
                        )
    finally :
        datastore.close()
    return config, rows


def parse_wandb_start_time(value : str | None) -> datetime | None :
    if not value :
        return None
    try :
        return datetime.strptime(value, "%Y%m%d_%H%M%S")
    except ValueError as exc :
        raise SystemExit("--wandb-start-time must use YYYYMMDD_HHMMSS, got {}".format(value)) from exc


def wandb_run_time(path : Path) -> datetime | None :
    match = WANDB_DIR_PATTERN.match(path.parent.name)
    if not match :
        return None
    return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")


def collect_metrics(wandb_root : Path, start_time : datetime | None = None) -> list[dict] :
    all_rows = []
    for path in sorted(wandb_root.glob("offline-run-*/run-*.wandb")) :
        run_time = wandb_run_time(path)
        if start_time is not None and run_time is not None and run_time < start_time :
            continue
        _, rows = scan_wandb_file(path)
        all_rows.extend(rows)
    return all_rows


def collect_live_metrics(live_metrics_root : Path) -> list[dict] :
    rows = []
    for path in sorted(live_metrics_root.glob("*/metrics.jsonl")) :
        for line in path.read_text().splitlines() :
            if not line.strip() :
                continue
            try :
                row = json.loads(line)
            except json.JSONDecodeError :
                continue
            if {"run_name", "phase", "line_step", "metric", "value"}.issubset(row) :
                rows.append(
                    {
                        "run_name" : row["run_name"],
                        "phase" : row["phase"],
                        "line_step" : int(row["line_step"]),
                        "metric" : row["metric"],
                        "value" : float(row["value"]),
                        "wandb_file" : row.get("source", "live"),
                    }
                )
    return rows


def write_csv(rows : list[dict], output : Path) -> None :
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["run_name", "phase", "line_step", "metric", "value", "wandb_file"]
    with output.open("w", newline="") as handle :
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows :
            writer.writerow(row)


def metric_points(rows : list[dict], run_name : str, metric : str) -> list[tuple[int, float]] :
    points = [(row["line_step"], row["value"]) for row in rows if row["run_name"] == run_name and row["metric"] == metric]
    if not points :
        return []
    by_step = {}
    for step, value in points :
        by_step[step] = value
    return sorted(by_step.items())


def plot_series(series : list[tuple[str, list[tuple[int, float]]]], title : str, ylabel : str, output : Path) -> bool :
    series = [(label, points) for label, points in series if points]
    if not series :
        return False

    import matplotlib.pyplot as plt

    output.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(8, 4.5))
    for label, points in series :
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        plt.plot(xs, ys, marker="o", linewidth=1.8, markersize=3.5, label=label)
    plt.title(title)
    plt.xlabel("step")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.25)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()
    return True


def make_plots(rows : list[dict], output_dir : Path) -> list[Path] :
    created = []

    for environment in EXP1_ENVIRONMENTS :
        config_series = [
            (label, metric_points(rows, template.format(environment=environment), "rollout/effective_prompt_rate"))
            for _, label, template in EXP1_CONFIGS
        ]
        output = output_dir / "exp1" / environment / "effective_prompt_rate.png"
        if plot_series(config_series, "Experiment 1: {} effective prompt rate".format(environment), "effective prompt rate", output) :
            created.append(output)

        in_dist_metric = "eval/IN_DIST_{}".format(environment)
        config_series = [
            (label, metric_points(rows, template.format(environment=environment), in_dist_metric))
            for _, label, template in EXP1_CONFIGS
        ]
        output = output_dir / "exp1" / environment / "in_distribution_accuracy.png"
        if plot_series(config_series, "Experiment 1: {} in-distribution accuracy".format(environment), "accuracy", output) :
            created.append(output)

        config_series = [
            (label, metric_points(rows, template.format(environment=environment), "eval/OOD"))
            for _, label, template in EXP1_CONFIGS
        ]
        output = output_dir / "exp1" / environment / "out_of_distribution_accuracy.png"
        if plot_series(config_series, "Experiment 1: {} out-of-distribution accuracy".format(environment), "accuracy", output) :
            created.append(output)

    exp2_series = [(label, metric_points(rows, run_name, "eval/NEW_ENV_HELD_OUT")) for _, label, run_name in EXP2_RUNS]
    output = output_dir / "exp2" / "new_environment_held_out_accuracy.png"
    if plot_series(exp2_series, "Experiment 2: held-out accuracy by number of training environments", "accuracy", output) :
        created.append(output)

    exp3_series = [(label, metric_points(rows, run_name, "rollout/effective_prompt_rate")) for _, label, run_name in EXP3_RUNS]
    output = output_dir / "exp3" / "division_effective_prompt_rate.png"
    if plot_series(exp3_series, "Experiment 3: Division effective prompt rate by model size", "effective prompt rate", output) :
        created.append(output)

    exp3_series = [(label, metric_points(rows, run_name, "eval/IN_DIST_Division")) for _, label, run_name in EXP3_RUNS]
    output = output_dir / "exp3" / "division_in_distribution_accuracy.png"
    if plot_series(exp3_series, "Experiment 3: Division in-distribution accuracy by model size", "accuracy", output) :
        created.append(output)

    exp3_series = [(label, metric_points(rows, run_name, "eval/OOD")) for _, label, run_name in EXP3_RUNS]
    output = output_dir / "exp3" / "division_out_of_distribution_accuracy.png"
    if plot_series(exp3_series, "Experiment 3: Division out-of-distribution accuracy by model size", "accuracy", output) :
        created.append(output)

    return created


def write_summary(rows : list[dict], plots : list[Path], output : Path) -> None :
    by_run = defaultdict(set)
    for row in rows :
        by_run[row["run_name"]].add(row["metric"])
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "num_rows" : len(rows),
                "num_runs" : len(by_run),
                "runs" : {run_name : sorted(metrics) for run_name, metrics in sorted(by_run.items())},
                "plots" : [str(path) for path in plots],
            },
            indent=2,
        )
    )


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb-root", default=None)
    parser.add_argument("--live-metrics-root", default="outputs/results/live")
    parser.add_argument("--output-dir", default="outputs/figures")
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--summary-output", default="outputs/results/plot_summary.json")
    parser.add_argument(
        "--wandb-start-time",
        default=None,
        help="Only parse offline W&B runs at or after this UTC timestamp, formatted as YYYYMMDD_HHMMSS.",
    )
    args = parser.parse_args()

    rows = collect_live_metrics(Path(args.live_metrics_root))
    if args.wandb_root :
        rows.extend(collect_metrics(Path(args.wandb_root), parse_wandb_start_time(args.wandb_start_time)))
    if args.csv_output :
        write_csv(rows, Path(args.csv_output))
    plots = make_plots(rows, Path(args.output_dir))
    write_summary(rows, plots, Path(args.summary_output))
    print("parsed {} metric rows from {}".format(len(rows), args.wandb_root))
    print("created {} plots under {}".format(len(plots), args.output_dir))


if __name__ == "__main__" :
    main()
