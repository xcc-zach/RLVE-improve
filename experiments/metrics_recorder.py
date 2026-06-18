import csv
import json
from pathlib import Path


FIELDNAMES = ["run_name", "phase", "line_step", "metric", "value", "source"]


def _safe_run_name(run_name : str | None) -> str :
    if not run_name :
        return "unknown_run"
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in run_name)


def _numeric_rows(run_name : str, phase : str, line_step : int, metrics : dict, source : str) -> list[dict] :
    rows = []
    for metric, value in metrics.items() :
        if isinstance(value, bool) :
            value = int(value)
        if isinstance(value, (int, float)) :
            rows.append(
                {
                    "run_name" : run_name,
                    "phase" : phase,
                    "line_step" : int(line_step),
                    "metric" : metric,
                    "value" : float(value),
                    "source" : source,
                }
            )
    return rows


def append_metrics(run_name : str | None, phase : str, line_step : int, metrics : dict, source : str = "live") -> None :
    rows = _numeric_rows(_safe_run_name(run_name), phase, line_step, metrics, source)
    if not rows :
        return

    run_dir = Path("outputs/results/live") / rows[0]["run_name"]
    run_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = run_dir / "metrics.jsonl"
    with jsonl_path.open("a") as handle :
        for row in rows :
            handle.write(json.dumps(row, sort_keys=True) + "\n")

    csv_path = run_dir / "metrics.csv"
    needs_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="") as handle :
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        if needs_header :
            writer.writeheader()
        writer.writerows(rows)

