from core.errors import AppError


class AIClientError(AppError):
    """Base class for errors raised by AI clients."""

class RequestFailedError(AIClientError):
    user_message = "Request to AI client failed. Try again later."

    def __init__(self, telegram_id: int | None = None, username: str | None = None):
        self.telegram_id = telegram_id
        self.username = username
        super().__init__(f"Request to AI client by user (telegram_id={telegram_id!r}, username={username!r}) failed.")

class AnswerTooBigError(AIClientError):
    user_message = "Answer is too big. Try to change prompt and ask again."