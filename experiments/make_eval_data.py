import argparse
import json
import random
from pathlib import Path

from Gym.environments import identifier2environment
from Gym.parameter_controllers import identifier2controller


DEFAULT_ENVIRONMENTS = [
    "digit_sum_interval",
    "binary_string_no_adjacent_count",
    "grid_path_counting_with_blocks",
]


def parameter_for_difficulty(environment : str, difficulty : int) -> dict :
    controller = identifier2controller[environment]()
    for _ in range(difficulty) :
        controller.update()
    return random.choice(controller.get_parameter_list())


def build_sample(environment : str, difficulty : int, seed : int) -> dict :
    problem = identifier2environment[environment]()
    parameter = parameter_for_difficulty(environment, difficulty)
    if not problem.generator(seed = seed, parameter = parameter) :
        raise RuntimeError("Failed to generate problem for {} at difficulty {}".format(environment, difficulty))
    return {
        "user_prompt" : problem.prompt_generator(),
        "metadata" : json.dumps(
            {
                "environment" : environment,
                "config" : problem.get_config(),
            }
        ),
    }


def main() -> None :
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="outputs/eval/new_environments/test.json")
    parser.add_argument("--config-output", default="outputs/eval/new_environments/evaluation_config.json")
    parser.add_argument("--num-samples", type=int, default=100)
    parser.add_argument("--difficulty-min", type=int, default=0)
    parser.add_argument("--difficulty-max", type=int, default=9)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--environments", nargs="+", default=DEFAULT_ENVIRONMENTS)
    args = parser.parse_args()

    random.seed(args.seed)
    samples = []
    next_seed = 0
    while len(samples) < args.num_samples :
        environment = random.choice(args.environments)
        difficulty = random.randint(args.difficulty_min, args.difficulty_max)
        samples.append(build_sample(environment, difficulty, next_seed))
        next_seed += 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(samples, indent=2))

    config_output = Path(args.config_output)
    config_output.parent.mkdir(parents=True, exist_ok=True)
    config_output.write_text(
        json.dumps(
            {
                "label_key" : None,
                "rm_type" : "rlve",
                "n_samples_per_eval_prompt" : 1,
                "accuracy_key" : "accuracy",
                "generation" : {
                    "num_samples" : args.num_samples,
                    "difficulty_min" : args.difficulty_min,
                    "difficulty_max" : args.difficulty_max,
                    "environments" : args.environments,
                    "seed" : args.seed,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__" :
    main()
