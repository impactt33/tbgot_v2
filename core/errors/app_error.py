class AppError(Exception):
    """Base exception class for app errors."""

    user_message: str = "Something went wrong. Try again later."

    def __init__(self, detail: str = "", *, user_message: str | None = None) -> None:
        self.detail = detail or type(self).__name__
        if user_message is not None:
            self.user_message = user_message
        super().__init__(self.detail)