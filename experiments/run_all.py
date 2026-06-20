import argparse
import json
import re
import subprocess
from pathlib import Path


NEW_ENVIRONMENTS = [
    "digit_sum_interval",
    "binary_string_no_adjacent_count",
    "grid_path_counting_with_blocks",
]
EXP1_ENVIRONMENTS = ["Division", *NEW_ENVIRONMENTS]

NEW_ENV_HELD_OUT_EVAL = ["NEW_ENV_HELD_OUT", "outputs/eval/new_environments/test.json"]
EXP1_OOD_EVAL = ["OOD", "outputs/eval/out_of_distribution/test.json"]

EXP2_ENVIRONMENTS = {
    "1" : ["Multiplication"],
    "4" : ["Division", "EuclidGame", "Multiplication", "Sorting"],
    "16" : [
        "Division",
        "EuclidGame",
        "GCDOne_Counting",
        "HamiltonianPath",
        "LampChanging",
        "LargestConvexPolygon",
        "Multiplication",
        "PCPPermutation",
        "Path_NoGoingBack_Counting",
        "SAT",
        "ShortestPath",
        "Sorting",
        "SpiralMatrix",
        "SubsequenceReversalLNDS",
        "UndamagedSubmatrixCounting",
        "WYRLevelingGround",
    ],
    "256" : None,
}


def checkpoint_exists(output_root : str, run_name : str, steps : int) -> bool :
    return (Path(output_root) / run_name / "rollout" / "rlve_manager_state_dict_{}.pt".format(steps - 1)).exists()


def run(args, run_name : str, environments : list[str], extra : list[str], eval_prompt_data : list[str]) -> None :
    if checkpoint_exists(args.output_root, run_name, args.steps) :
        print("skip existing {}".format(run_name), flush=True)
        return
    command = [
        "python",
        "-m",
        "experiments.run_training",
        "--wandb-project",
        args.wandb_project,
        "--run-name",
        run_name,
        "--steps",
        str(args.steps),
        "--eval-interval",
        str(args.eval_interval),
        "--output-root",
        args.output_root,
        "--environment-list",
        *environments,
        "--eval-prompt-data",
        *eval_prompt_data,
        *extra,
    ]
    if args.eval_max_response_len is not None :
        command.extend(["--eval-max-response-len", str(args.eval_max_response_len)])
    for flag, value in [
        ("--num-gpus", args.num_gpus),
        ("--gpu-mem-gb", args.gpu_mem_gb),
        ("--context-parallel-size", args.context_parallel_size),
        ("--rollout-max-response-len", args.rollout_max_response_len),
        ("--max-tokens-per-gpu", args.max_tokens_per_gpu),
        ("--rollout-batch-size", args.rollout_batch_size),
        ("--n-samples-per-prompt", args.n_samples_per_prompt),
        ("--over-sampling-batch-size", args.over_sampling_batch_size),
        ("--sglang-server-concurrency", args.sglang_server_concurrency),
        ("--sglang-mem-fraction-static", args.sglang_mem_fraction_static),
    ] :
        if value is not None :
            command.extend([flag, str(value)])
    if args.resource_profile is not None :
        command.extend(["--resource-profile", args.resource_profile])
    if args.wandb_mode is not None :
        command.extend(["--wandb-mode", args.wandb_mode])
    if args.dynamic_sampling_filter_path is not None :
        command.extend(["--dynamic-sampling-filter-path", args.dynamic_sampling_filter_path])
    if args.dry_run :
        command.append("--dry-run")
    subprocess.run(command, check=True)


def environments_from_script(path : str) -> list[str] :
    text = Path(path).read_text()
    matches = re.findall(r'"([^"]+)"', text)
    if not matches :
        raise RuntimeError("Could not find environment list in {}".format(path))
    return matches[-1].split()


def eval_config_matches(
    path : Path,
    *,
    num_samples : int,
    difficulty_min : int,
    difficulty_max : int,
    environments : list[str],
) -> bool :
    if not path.exists() :
        return False
    try :
        payload = json.loads(path.read_text())
    except Exception :
        return False
    generation = payload.get("generation")
    if not isinstance(generation, dict) :
        return False
    return (
        generation.get("num_samples") == num_samples
        and generation.get("difficulty_min") == difficulty_min
        and generation.get("difficulty_max") == difficulty_max
        and generation.get("environments") == environments
    )


def ensure_eval_data() -> None :
    output = Path("outputs/eval/new_environments/test.json")
    config_output = Path("outputs/eval/new_environments/evaluation_config.json")
    if output.exists() and eval_config_matches(
        config_output,
        num_samples = 100,
        difficulty_min = 0,
        difficulty_max = 9,
        environments = NEW_ENVIRONMENTS,
    ) :
        return
    subprocess.run(
        [
            "python",
            "-m",
            "experiments.make_eval_data",
            "--output",
            str(output),
            "--config-output",
            str(config_output),
            "--num-samples",
            "100",
            "--difficulty-min",
            "0",
            "--difficulty-max",
            "9",
            "--environments",
            *NEW_ENVIRONMENTS,
        ],
        check=True,
    )


def in_distribution_eval(environment : str) -> list[str] :
    path = Path("outputs/eval/in_distribution/{}.json".format(environment))
    config_path = path.with_name("{}_evaluation_config.json".format(environment))
    if not path.exists() or not eval_config_matches(
        config_path,
        num_samples = 100,
        difficulty_min = 0,
        difficulty_max = 9,
        environments = [environment],
    ) :
        subprocess.run(
            [
                "python",
                "-m",
                "experiments.make_eval_data",
                "--output",
                str(path),
                "--config-output",
                str(config_path),
                "--num-samples",
                "100",
                "--difficulty-min",
                "0",
                "--difficulty-max",
                "9",
                "--environments",
                environment,
            ],
            check=True,
        )
    return ["IN_DIST_{}".format(environment), str(path)]


def ensure_exp1_out_of_distribution_eval() -> None :
    path = Path("outputs/eval/out_of_distribution/test.json")
    config_path = Path("outputs/eval/out_of_distribution/evaluation_config.json")
    if not path.exists() or not eval_config_matches(
        config_path,
        num_samples = 100,
        difficulty_min = 0,
        difficulty_max = 9,
        environments = EXP1_ENVIRONMENTS,
    ) :
        subprocess.run(
            [
                "python",
                "-m",
                "experiments.make_eval_data",
                "--output",
                str(path),
                "--config-output",
                str(config_path),
                "--num-samples",
                "100",
                "--difficulty-min",
                "0",
                "--difficulty-max",
                "9",
                "--environments",
                *EXP1_ENVIRONMENTS,
            ],
            check=True,
        )


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb-project", required=True)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--eval-interval", type=int, default=20)
    parser.add_argument("--eval-max-response-len", type=int, default=None)
    parser.add_argument("--output-root", default="outputs/checkpoints")
    parser.add_argument("--resource-profile", choices=("repo", "auto"), default=None)
    parser.add_argument("--wandb-mode", choices=("online", "offline", "disabled"), default=None)
    parser.add_argument("--dynamic-sampling-filter-path", default=None)
    parser.add_argument("--num-gpus", type=int, default=None)
    parser.add_argument("--gpu-mem-gb", type=int, default=None)
    parser.add_argument("--context-parallel-size", type=int, default=None)
    parser.add_argument("--rollout-max-response-len", type=int, default=None)
    parser.add_argument("--max-tokens-per-gpu", type=int, default=None)
    parser.add_argument("--rollout-batch-size", type=int, default=None)
    parser.add_argument("--n-samples-per-prompt", type=int, default=None)
    parser.add_argument("--over-sampling-batch-size", type=int, default=None)
    parser.add_argument("--sglang-server-concurrency", type=int, default=None)
    parser.add_argument("--sglang-mem-fraction-static", type=float, default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_eval_data()
    ensure_exp1_out_of_distribution_eval()

    for environment in EXP1_ENVIRONMENTS :
        exp1_eval = in_distribution_eval(environment) + EXP1_OOD_EVAL
        run(
            args,
            "exp1_adaptive_{}".format(environment),
            [environment],
            ["--difficulty-mode", "adaptive", "--model", "openreasoning-nemotron-1.5b"],
            exp1_eval,
        )
        for static_range in [(0, 1), (0, 4), (0, 9)] :
            run(
                args,
                "exp1_static_{}_{}_{}".format(static_range[0], static_range[1], environment),
                [environment],
                [
                    "--model",
                    "openreasoning-nemotron-1.5b",
                    "--difficulty-mode",
                    "static",
                    "--static-min-difficulty",
                    str(static_range[0]),
                    "--static-max-difficulty",
                    str(static_range[1]),
                ],
                exp1_eval,
            )

    for count, environments in EXP2_ENVIRONMENTS.items() :
        if environments is None :
            environments = environments_from_script(
                "scripts/training/Nemotron-Research-Reasoning-Qwen-1.5B-v2/rlve/num-environment={}.sh".format(count)
            )
        run(
            args,
            "exp2_num_environment_{}".format(count),
            environments,
            ["--difficulty-mode", "adaptive", "--model", "openreasoning-nemotron-1.5b"],
            NEW_ENV_HELD_OUT_EVAL,
        )

    exp3_eval = in_distribution_eval("Division") + EXP1_OOD_EVAL
    run(
        args,
        "exp3_division_openreasoning_nemotron_7b",
        ["Division"],
        ["--difficulty-mode", "adaptive", "--model", "openreasoning-nemotron-7b"],
        exp3_eval,
    )


if __name__ == "__main__" :
    main()
