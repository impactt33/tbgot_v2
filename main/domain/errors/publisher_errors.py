from core.errors import AppError


class PublisherError(AppError):
    """Base class for publisher errors."""

class PublishError(PublisherError):
    user_message = "Cannot publish the post. Try again later."

    def __init__(self, post_id: int | None = None, exc: Exception | None = None):
        self.post_id = post_id
        self.exc = exc

        super().__init__(f"Cannot publish the post (id={post_id!r}). Traceback: {exc!r} Try again later.")