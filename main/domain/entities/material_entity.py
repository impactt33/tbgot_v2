from datetime import datetime

from pydantic import BaseModel


class MaterialEntity(BaseModel):
    """A file the admin forwarded to the bot and the bot stored for itself.

    The material originally lives in someone else's channel, which the bot has
    no access to: the Bot API refuses to copy from a chat the bot is not in.
    So the admin forwards the post, the bot re-sends the file into our own
    storage channel by file_id, and from then on we own a copy we can link to.

    `file_unique_id` is the deduplication key rather than `file_id`, because
    the Bot API says it is "supposed to be the same over time and for different
    bots" — it survives a token change, which `file_id` does not.

    The source_* fields come from the forwarded message's `forward_origin` and
    are all optional: a channel can hide where a forward came from, and then
    Telegram sends MessageOriginHiddenUser with no chat at all.
    """

    id: int
    channel_id: int
    file_unique_id: str
    source_chat_id: int | None
    source_username: str | None
    source_message_id: int | None
    storage_chat_id: int
    storage_message_id: int
    created_at: datetime
    used_in_post: int | None


class AddMaterialEntity(BaseModel):
    channel_id: int
    file_unique_id: str
    source_chat_id: int | None = None
    source_username: str | None = None
    source_message_id: int | None = None
    storage_chat_id: int
    storage_message_id: int
