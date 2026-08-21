from core.errors import AppError
from main.domain.enums import PostType, post_type


class PublisherError(AppError):
    """Base class for publisher errors."""

class PublishError(PublisherError):
    user_message = f"Cannot publish the post. Try again later."

    def __init__(self, post_id: int | None = None, exc: Exception | None = None):
        self.post_id = post_id
        self.exc = exc

        super().__init__(f"Cannot publish the post (id={post_id!r}). Traceback: {exc!r} Try again later.")

class UnsupportedPostTypeError(PublisherError):
    user_message = "This type of the post is not supported. Try again later."

    def __init__(self, post_type: PostType | None = None):
        self.post_type = post_type

        super().__init__(f"Unsupported post type: {post_type!r}.")