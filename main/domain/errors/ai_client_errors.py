from core.errors import AppError


class AIClientError(AppError):
    """Base class for all errors related to AIClients."""

class RequestFailedError(AIClientError):
    user_message = "Request to AI client failed. Try again later."

    def __init__(self, telegram_id: int | None = None, username: str | None = None):
        self.telegram_id = telegram_id
        self.username = username
        super().__init__(f"Request to AI client by user (telegram_id={telegram_id!r}, username={username!r}) failed.")

class AnswerIsEmptyError(AIClientError):
    user_message = "Answer from model is empty. Try again later."

class AIClientUnavailable(AIClientError):
    user_message = "AI client is not available. Try again later."

class AIClientRejected(AIClientError):
    user_message = "AI client rejected. Try again later."

class AIClientUnparsableAnswer(AIClientError):
    user_message = "Answer from model is unparsable. Try again later."

class AnswerTooBigError(AIClientError):
    user_message = "Answer is too big. Try to change prompt and ask again."