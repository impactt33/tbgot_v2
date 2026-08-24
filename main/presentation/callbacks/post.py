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

class DraftCB(CallbackData, prefix="npd"):
    """Action on freshly generated draft.

    preview_id rides along so the handler can delete the preview message
    without keeping any per-user state between updates.
    """

    action: DraftAction
    post_id: int
    preview_id: int