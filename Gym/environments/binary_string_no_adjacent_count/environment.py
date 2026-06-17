from typing import Optional

from Gym.environment import VerifiableEnvironment


class BinaryStringNoAdjacentCount_Environment(VerifiableEnvironment) :
    prompt_template = (
        "How many binary strings of length {N} contain no two adjacent 1 bits?\n\n"
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

    def _generate(self) -> None :
        difficulty = self.parameter.get("difficulty", 0)
        assert difficulty >= 0, "difficulty should be greater than or equal to 0"

        N = max(1, difficulty)
        a, b = 1, 2
        if N == 1 :
            answer = b
        else :
            for _ in range(2, N + 1) :
                a, b = b, a + b
            answer = b

        self.parameter["N"] = N
        self.parameter["reference_answer"] = answer

    def _prompt_generate(self) -> str :
        return self.prompt_template.format(N = self.parameter["N"])

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
            if processed_result == 0 :
                return 0.0
            return self.rewards["rewarding_weight"] * ((min(gold, processed_result) / max(gold, processed_result)) ** self.rewards["rewarding_beta"])
        elif self.rewards["rewarding_strategy"] == "gold=answer" :
            return self.rewards["rewarding_weight"] * (gold == processed_result)
        else :
            raise NotImplementedError("Unknown rewarding strategy: {}".format(self.rewards["rewarding_strategy"]))
