from enum import Enum

from aiogram.filters.callback_data import CallbackData

from main.domain.enums import PostType


class ChannelCB(CallbackData, prefix="npc"):
    """Channel picked, ask for the post type next."""

    channel_id: int

class GenerateCB(CallbackData, prefix="npg"):
    """Type picked: everything needed to start generating."""

    channel_id: int
    post_type: PostType

class DraftAction(str, Enum):
    SHOW = "show"
    PUBLISH = "publish"
    SCHEDULE = "schedule"
    REGENERATE = "regenerate"
    DISCARD = "discard"

class DraftCB(CallbackData, prefix="npd2"):
    """Action on a freshly built draft.

    preview_id rides along so the handler can delete the preview message
    without keeping any per-user state between updates. preview_count says how
    many messages that preview took: an album is several, and they get
    consecutive ids because Telegram sends them in one call.

    The prefix is "npd2" rather than "npd" on purpose. Adding a field makes old
    callback data unparseable — aiogram raises "takes 4 arguments but 3 were
    given" — so buttons left in the chat from before this change would blow up
    in the filter. Under a new prefix they simply match nothing.
    """

    action: DraftAction
    post_id: int
    preview_id: int
    preview_count: int = 1