import random
from typing import Optional

from Gym.environment import VerifiableEnvironment


class DigitSumInterval_Environment(VerifiableEnvironment) :
    prompt_template = (
        "For every integer x in the interval [{L}, {R}], let s(x) be the sum of the decimal digits of x. "
        "Compute the value of sum(s(x)) over all integers x such that {L} <= x <= {R}.\n\n"
        "**Output Format:** Your final answer should be a single integer."
    )

    def __init__(
        self,
        wrong_format : float = -1.0,
        rewarding_strategy : str = "(min/max)^beta",
        rewarding_weight : float = 1.0,
        rewarding_beta : float = 5.0,
        **kwargs,
    ) :
        super().__init__(**kwargs)
        self.rewards = {
            "wrong_format" : wrong_format,
            "rewarding_strategy" : rewarding_strategy,
            "rewarding_weight" : rewarding_weight,
            "rewarding_beta" : rewarding_beta,
        }

    @staticmethod
    def _prefix_digit_sum(n : int) -> int :
        if n <= 0 :
            return 0

        total = 0
        factor = 1
        while factor <= n :
            lower = n % factor
            current = (n // factor) % 10
            higher = n // (factor * 10)

            total += higher * 45 * factor
            total += current * (current - 1) // 2 * factor
            total += current * (lower + 1)
            factor *= 10
        return total

    def _generate(self) -> None :
        difficulty = self.parameter.get("difficulty", 0)
        assert difficulty >= 0, "difficulty should be greater than or equal to 0"

        max_digits = min(2 + difficulty // 10, 12)
        span_digits = min(1 + difficulty // 15, max_digits)
        allow_arbitrary_L = difficulty >= 20

        R_max = 10 ** max_digits - 1
        R = random.randint(1, R_max)
        span_max = min(10 ** span_digits - 1, R - 1)
        span = random.randint(0, span_max)

        L = R - span if allow_arbitrary_L else 1

        self.parameter["L"] = L
        self.parameter["R"] = R
        self.parameter["reference_answer"] = self._prefix_digit_sum(R) - self._prefix_digit_sum(L - 1)

    def _prompt_generate(self) -> str :
        return self.prompt_template.format(L = self.parameter["L"], R = self.parameter["R"])

    def _process(self, answer : Optional[str]) -> Optional[int] :
        if answer is None :
            return None
        try :
            return int(answer.strip())
        except ValueError :
            return None

    def scorer(self, output : str) -> float :
        processed_result = self.processor(output)
        if processed_result is None or processed_result < 0 :
            return self.rewards["wrong_format"]

        gold = self.parameter["reference_answer"]
        if self.rewards["rewarding_strategy"] == "(min/max)^beta" :
            if gold == processed_result :
                return self.rewards["rewarding_weight"]
            if gold == 0 or processed_result == 0 :
                return 0.0
            return self.rewards["rewarding_weight"] * ((min(gold, processed_result) / max(gold, processed_result)) ** self.rewards["rewarding_beta"])
        elif self.rewards["rewarding_strategy"] == "gold=answer" :
            return self.rewards["rewarding_weight"] * (gold == processed_result)
        else :
            raise NotImplementedError("Unknown rewarding strategy: {}".format(self.rewards["rewarding_strategy"]))
