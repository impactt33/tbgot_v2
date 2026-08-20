from typing import TypeVar

from main.domain.enums import AIFailure
from main.domain.errors import (
    AIClientError,
    AIClientRejected,
    AIClientUnavailable,
    AIClientUnparsableAnswer,
    AnswerIsEmptyError,
)

_FAILURE_TO_ERROR: dict[AIFailure, type[AIClientError]] = {
    AIFailure.UNAVAILABLE: AIClientUnavailable,
    AIFailure.REJECTED: AIClientRejected,
    AIFailure.EMPTY: AnswerIsEmptyError,
    AIFailure.UNPARSEABLE: AIClientUnparsableAnswer,
}

T = TypeVar("T")


def unwrap_ai(result: T | AIFailure) -> T:
    """AIFailure -> Domain Error."""
    if isinstance(result, AIFailure):
        raise _FAILURE_TO_ERROR[result]()
    return result