from core.errors import AppError


class PostError(AppError):
    """Base class for all errors related to posts."""

class PostNotFoundError(PostError):
    user_message = "Post not found."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) was not found.")

class PostWasNotCreated(PostError):
    user_message = "Post was not created. Try again later."

    def __init__(self) -> None:
        super().__init__(f"Post was not created.")