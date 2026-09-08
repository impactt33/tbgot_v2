from datetime import datetime

from pydantic import BaseModel

from main.domain.enums import PostType


class PostTemplateEntity(BaseModel):
    """How posts of one type should look in one particular channel.

    Two things, both optional on their own:

    `examples` are real posts from the channel, stored as Telegram HTML exactly
    as the admin sent them. They are never distilled into a summary: the model
    gets them verbatim on every generation and does the abstraction itself, with
    the actual task in front of it. A summary written once would freeze whatever
    it happened to miss.

    `instruction` is free text from the channel owner. It goes after the
    examples in the prompt, so it overrides what they show.
    """

    id: int
    channel_id: int
    post_type: PostType
    examples: list[str]
    instruction: str | None
    created_at: datetime
    updated_at: datetime
