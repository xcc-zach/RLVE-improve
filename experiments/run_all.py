import argparse
import re
import subprocess
from pathlib import Path


NEW_ENVIRONMENTS = [
    "digit_sum_interval",
    "binary_string_no_adjacent_count",
    "grid_path_counting_with_blocks",
]

HELD_OUT_EVAL = ["HELD_OUT", "data/HELD-OUT_ENVIRONMENTS/test.json"]
NEW_ENV_HELD_OUT_EVAL = ["NEW_ENV_HELD_OUT", "outputs/eval/new_environments/test.json"]

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
        "--output-root",
        args.output_root,
        "--environment-list",
        *environments,
        "--eval-prompt-data",
        *eval_prompt_data,
        *extra,
    ]
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


def ensure_eval_data() -> None :
    if not Path("outputs/eval/new_environments/test.json").exists() :
        subprocess.run(["python", "-m", "experiments.make_eval_data"], check=True)


def in_distribution_eval(environment : str) -> list[str] :
    path = Path("outputs/eval/in_distribution/{}.json".format(environment))
    if not path.exists() :
        subprocess.run(
            [
                "python",
                "-m",
                "experiments.make_eval_data",
                "--output",
                str(path),
                "--config-output",
                str(path.with_name("{}_evaluation_config.json".format(environment))),
                "--num-samples",
                "4000",
                "--difficulty-min",
                "0",
                "--difficulty-max",
                "19",
                "--environments",
                environment,
            ],
            check=True,
        )
    return ["IN_DIST_{}".format(environment), str(path)]


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--wandb-project", required=True)
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--output-root", default="outputs/checkpoints")
    parser.add_argument("--resource-profile", choices=("repo", "auto"), default=None)
    parser.add_argument("--wandb-mode", choices=("online", "offline", "disabled"), default=None)
    parser.add_argument("--dynamic-sampling-filter-path", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_eval_data()

    exp1_envs = ["Division", *NEW_ENVIRONMENTS]
    for environment in exp1_envs :
        exp1_eval = in_distribution_eval(environment) + HELD_OUT_EVAL
        run(args, "exp1_adaptive_{}".format(environment), [environment], ["--difficulty-mode", "adaptive"], exp1_eval)
        for static_range in [(0, 1), (0, 20), (0, 100)] :
            run(
                args,
                "exp1_static_{}_{}_{}".format(static_range[0], static_range[1], environment),
                [environment],
                [
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
                "scripts/training/DeepSeek-R1-Distill-Qwen-1.5B/rlve/num-environment={}.sh".format(count)
            )
        run(args, "exp2_num_environment_{}".format(count), environments, ["--difficulty-mode", "adaptive"], NEW_ENV_HELD_OUT_EVAL)

    exp3_eval = in_distribution_eval("Sorting") + HELD_OUT_EVAL
    run(args, "exp3_sorting_deepseek_r1_distill_qwen_1_5b", ["Sorting"], ["--difficulty-mode", "adaptive"], exp3_eval)
    run(
        args,
        "exp3_sorting_deepseek_r1_distill_qwen_7b",
        ["Sorting"],
        ["--difficulty-mode", "adaptive", "--model", "deepseek-r1-distill-qwen-7b"],
        exp3_eval,
    )


if __name__ == "__main__" :
    main()
