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
        super().__init__("Post was not created.")

class PostAlreadyPublishedError(PostError):
    user_message = "This post was already published."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id

        super().__init__(f"Post (post_id: {post_id!r}) was already published.")

class NoMaterialFoundError(PostError):
    user_message = "Ничего подходящего не нашлось. Попробуй ещё раз."

    def __init__(self, query: str | None = None) -> None:
        self.query = query
        super().__init__(f"Web search returned nothing for {query!r}.")

class PostNotDraftError(PostError):
    user_message = "This post was already published or publishing now."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) is not a draft or scheduled post.")

class PostNotScheduledError(PostError):
    user_message = "Publishing started already, cannot reject."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) is not in SCHEDULED status.")