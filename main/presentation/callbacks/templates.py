from enum import Enum

from aiogram.filters.callback_data import CallbackData

from main.domain.enums import PostType


class TemplateAction(str, Enum):
    OPEN = "open"
    ADD_EXAMPLE = "add_ex"
    LIST_EXAMPLES = "list_ex"
    SET_INSTRUCTION = "set_in"
    CLEAR_INSTRUCTION = "clr_in"


class TemplateTypesCB(CallbackData, prefix="tpt"):
    """The "which post types have a template" screen of one channel."""

    channel_id: int


class TemplateCB(CallbackData, prefix="tpl"):
    """An action on the template of one (channel, post_type) pair.

    Longest packing is 35 bytes of the 64 Telegram allows, measured rather than
    guessed: tpl:list_ex:-1001962556344:MATERIAL.
    """

    action: TemplateAction
    channel_id: int
    post_type: PostType


class TemplateRemoveExampleCB(CallbackData, prefix="tprmx"):
    """Removing one example, addressed by its position in the array.

    A separate class rather than another TemplateAction: the index has no
    meaning for any other button, and a field added to TemplateCB would make
    every button already sitting in a chat fail to unpack. `.filter()` swallows
    that TypeError, so those buttons would go mute instead of erroring.
    """

    channel_id: int
    post_type: PostType
    index: int
