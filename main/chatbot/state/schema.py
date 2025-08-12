from typing import Any
from typing_extensions import TypedDict


class InputState(TypedDict):
    input: str

class OutputState(TypedDict):
    output: Any

class OverallState(TypedDict):
    input: InputState
    output: OutputState