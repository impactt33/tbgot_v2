from enum import Enum

from aiogram.filters.callback_data import CallbackData


class StorageAction(str, Enum):
    BIND = "bind"
    UNBIND = "unbind"
    SKIP = "skip"


class SetupChannelCB(CallbackData, prefix="stc"):
    """Channel picked in the "Set up channel" list."""

    channel_id: int


class StorageCB(CallbackData, prefix="stg"):
    """What to do with the storage channel of `channel_id`.

    The channel id rides along instead of living in FSM data: this screen is
    reachable both right after adding a channel and from the settings list, and
    neither path should depend on the state surviving in between.
    """

    action: StorageAction
    channel_id: int
