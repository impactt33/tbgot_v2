from core.errors import AppError


class QuizTopicError(AppError):
    """Base class for all errors related to quiz topics."""

class QuizTopicNotFoundError(QuizTopicError):
    user_message = "Quiz topic not found."

    def __init__(self, topic_id: int | None = None ) -> None:
        self.topic_id = topic_id
        super().__init__(f"Quiz topic (id={topic_id!r}) was not found.")

class CannotGenerateTopicError(QuizTopicError):
    user_message = "Cannot generate new topic. Try again later."

    def __init__(self, channel_id: int | None = None ) -> None:
        self.channel_id = channel_id
        super().__init__(f"Cannot generate new topic for channel (id={channel_id!r}).")

class InvalidQuizDraftError(QuizTopicError):
    user_message = "Model returned invalid quiz draft format. Try again later."