import random
from typing import Optional

from Gym.environment import VerifiableEnvironment


class GridPathCountingWithBlocks_Environment(VerifiableEnvironment) :
    prompt_template = (
        "You are given a {N} x {N} grid. You start at the top-left cell (row 0, column 0) and want to reach "
        "the bottom-right cell (row {LAST}, column {LAST}). You may only move one cell down or one cell right. "
        "Cells marked # are blocked and cannot be used; cells marked . are open.\n\n"
        "{GRID}\n\n"
        "How many valid paths are there from the top-left cell to the bottom-right cell?\n\n"
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
    def _block_probability(difficulty : int) -> float :
        if difficulty < 20 :
            return 0.05 + 0.005 * difficulty
        if difficulty < 50 :
            return 0.15 + 0.002 * (difficulty - 20)
        return 0.21

    def _generate(self) -> None :
        difficulty = self.parameter.get("difficulty", 0)
        assert difficulty >= 0, "difficulty should be greater than or equal to 0"

        N = min(2 + difficulty // 8, 14)
        p = self._block_probability(difficulty)
        grid = []
        for i in range(N) :
            row = []
            for j in range(N) :
                row.append("#" if random.random() < p else ".")
            grid.append(row)

        grid[0][0] = "."
        grid[N - 1][N - 1] = "."

        dp = [[0] * N for _ in range(N)]
        dp[0][0] = 1
        for i in range(N) :
            for j in range(N) :
                if grid[i][j] == "#" :
                    dp[i][j] = 0
                    continue
                if i > 0 :
                    dp[i][j] += dp[i - 1][j]
                if j > 0 :
                    dp[i][j] += dp[i][j - 1]

        self.parameter["N"] = N
        self.parameter["block_probability"] = p
        self.parameter["grid"] = ["".join(row) for row in grid]
        self.parameter["reference_answer"] = dp[N - 1][N - 1]

    def _prompt_generate(self) -> str :
        N = self.parameter["N"]
        return self.prompt_template.format(
            N = N,
            LAST = N - 1,
            GRID = "\n".join(self.parameter["grid"]),
        )

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
