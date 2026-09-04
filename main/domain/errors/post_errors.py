from core.errors import AppError
from main.domain.enums import PostType


class PostError(AppError):
    """Base class for all errors related to posts."""

class UnsupportedPostTypeError(PostError):
    """Raised where a branch on post_type has no case for the value it got."""

    user_message = "This type of post is not supported yet."

    def __init__(self, post_type: PostType | None = None) -> None:
        self.post_type = post_type
        super().__init__(f"Unsupported post type: {post_type!r}.")

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

class PostNotDraftError(PostError):
    user_message = "This post was already published or publishing now."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) is not a draft or scheduled post.")

class PostNotClaimedError(PostError):
    """mark_published found no post in PUBLISHING to mark.

    Every publish claims the post first, so this means the row was changed by
    something that skipped the claim — worth a loud line in the log.
    """

    user_message = "This post was already published or publishing now."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) is not in PUBLISHING status.")

class PostNotScheduledError(PostError):
    user_message = "This post is no longer scheduled."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) is not in SCHEDULED status.")