from typing import Any
from typing_extensions import TypedDict


class InputState(TypedDict):
    input: str
    egen_teto_data: str

class OutputState(TypedDict):
    output: Any

class OverallState(InputState, OutputState):
    """OverallState is a combination of InputState and OutputState."""