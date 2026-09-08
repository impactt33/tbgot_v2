from core.errors import AppError
from main.domain.enums import PostType


class PostTemplateError(AppError):
    """Base class for everything about per-channel post templates."""

class PostTemplateNotFoundError(PostTemplateError):
    user_message = "No template is set up for this channel yet."

    def __init__(self, channel_id: int | None = None, post_type: PostType | None = None) -> None:
        self.channel_id = channel_id
        self.post_type = post_type
        super().__init__(
            f"Template (channel_id: {channel_id!r}, post_type: {post_type!r}) was not found."
        )

class ExampleNotFoundError(PostTemplateError):
    user_message = "That example is gone. Open the list again."

    def __init__(self, index: int | None = None) -> None:
        self.index = index
        super().__init__(f"Example #{index!r} does not exist in that template.")

class TooManyExamplesError(PostTemplateError):
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.user_message = (
            f"There are already {limit} examples, which is the maximum. "
            "Remove one before adding another."
        )
        super().__init__(f"Example limit of {limit} reached.")

class NotEnoughExamplesError(PostTemplateError):
    """Raised at generation time, not while the admin is filling the template.

    Below the minimum the model latches onto whatever the one or two examples
    happen to share rather than onto the channel's manner, and the result is
    worse than generating with no examples at all. So generation is refused
    outright instead of quietly degrading.
    """

    def __init__(self, count: int, minimum: int) -> None:
        self.count = count
        self.minimum = minimum
        self.user_message = (
            f"This channel has {count} example posts of that type, and at least "
            f"{minimum} are needed. Add more in Bot management -> Set up channel."
        )
        super().__init__(f"Template has {count} examples, {minimum} required.")
