from enum import Enum

from aiogram.filters.callback_data import CallbackData


class ScheduledAction(str, Enum):
    CANCEL = "cancel"


class ScheduledCB(CallbackData, prefix="sch"):
    action: ScheduledAction
    post_id: int = 0