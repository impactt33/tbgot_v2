from enum import Enum

from aiogram.filters.callback_data import CallbackData


class ReminderAction(str, Enum):
    ENABLE = "on"
    DISABLE = "off"
    INTERVALS = "intervals"
    CUSTOM_INTERVAL = "c_interval"
    HOURS = "hours"
    CUSTOM_HOURS = "c_hours"


class WorkingHoursPreset(str, Enum):
    DAYTIME = "day"
    ROUND_THE_CLOCK = "all"


class ReminderChannelCB(CallbackData, prefix="rmc"):
    """The reminder screen of one channel."""

    channel_id: int


class ReminderSetupCB(CallbackData, prefix="rms"):
    """A button on the reminder screen or one of its submenus.

    Longest packing is 29 bytes of the 64 Telegram allows:
    rms:c_interval:-1001962556344.
    """

    action: ReminderAction
    channel_id: int


class ReminderIntervalCB(CallbackData, prefix="rmi"):
    """An interval preset.

    The value rides in the button, unlike the schedule presets, which are
    resolved in the handler: an interval is a length rather than a moment, so a
    button that lay in the chat for a week still means the same thing.
    """

    channel_id: int
    hours: int


class ReminderHoursCB(CallbackData, prefix="rmh"):
    """A working hours preset."""

    channel_id: int
    preset: WorkingHoursPreset
