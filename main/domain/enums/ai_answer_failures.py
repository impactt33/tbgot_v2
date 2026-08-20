from enum import Enum, auto

class AIFailure(Enum):
    UNAVAILABLE = auto()
    REJECTED = auto()
    EMPTY = auto()
    UNPARSEABLE = auto()