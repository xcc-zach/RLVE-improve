from typing import Dict, List

from Gym.parameter_controller import ParameterController


class DigitSumInterval_ParameterController(ParameterController) :
    def __init__(self, **kwargs) :
        super().__init__(**kwargs)
        self.difficulty = 0

    def update(self) -> None :
        self.difficulty += 1

    def get_parameter_list(self) -> List[Dict] :
        return [dict(difficulty = self.difficulty)]
