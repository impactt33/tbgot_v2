from enum import Enum

from main.domain.errors import AIClientError, AnswerIsEmptyError, AIClientUnavailable, AIClientRejected, \
    AIClientUnparsableAnswer


class AIFailure(AIClientError, Enum):
    UNAVAILABLE = AIClientUnavailable
    REJECTED = AIClientRejected
    EMPTY = AnswerIsEmptyError
    UNPARSEABLE = AIClientUnparsableAnswer