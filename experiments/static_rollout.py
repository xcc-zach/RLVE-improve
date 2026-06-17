from types import MethodType
from typing import Any, Dict, List

from slime.rollout.sglang_rollout import generate_rollout as default_generate_rollout
from slime.utils.types import Sample


def _reward_accuracy(sample : Sample) -> int :
    if isinstance(sample.reward, dict) :
        return int(sample.reward.get("accuracy", 0))
    return int(bool(sample.reward))


def _static_update(self, samples : List[Sample]) -> Dict[str, Any] :
    log_dict = {"rollout/problem_generation_seed" : self.problem_generation_seed}

    for sample in samples :
        environment = sample.metadata["environment"]
        problem_difficulty = sample.metadata["problem_difficulty"]
        maximum_difficulty = self.environment2difficulty[environment]
        if problem_difficulty < maximum_difficulty :
            continue
        self.environment2accuracy[environment]["num_samples"] += 1
        self.environment2accuracy[environment]["accuracy"] += _reward_accuracy(sample)

    for environment in self.args.environment_list :
        num_samples = self.environment2accuracy[environment]["num_samples"]
        accuracy = self.environment2accuracy[environment]["accuracy"]
        if num_samples >= self.args.min_prompts_before_difficulty_check * self.args.n_samples_per_prompt :
            accuracy = accuracy / num_samples
            log_dict["RLVE/{}/accuracy".format(environment)] = accuracy
            log_dict["RLVE/{}/difficulty".format(environment)] = self.environment2difficulty[environment]
            self.environment2accuracy[environment] = dict(accuracy = 0, num_samples = 0)

    return log_dict


def _patch_static_update(data_buffer) -> None :
    manager = getattr(data_buffer, "rlve_manager", None)
    if manager is None or getattr(manager, "_experiments_static_update", False) :
        return
    manager.update = MethodType(_static_update, manager)
    manager._experiments_static_update = True


def generate_rollout(args, rollout_id, data_buffer, evaluation=False) :
    if not evaluation :
        _patch_static_update(data_buffer)
    return default_generate_rollout(args, rollout_id, data_buffer, evaluation=evaluation)
