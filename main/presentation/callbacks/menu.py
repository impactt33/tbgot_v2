from enum import Enum

from aiogram.filters.callback_data import CallbackData


class MenuAction(str, Enum):
    """What the pressed main-menu button means."""

    ROOT = "root"
    NEW_POST = "new_post"
    SCHEDULED = "scheduled"
    ADMIN = "admin"
    PROVIDE_RIGHTS = "rights"
    ADD_CHANNEL = "add_channel"
    REMOVE_CHANNEL = "remove_channel"


class MenuCB(CallbackData, prefix="menu"):
    action: MenuAction
