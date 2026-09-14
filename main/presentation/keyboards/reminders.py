from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.entities import ChannelEntity, MaterialReminderEntity
from main.domain.errors import NotEnoughExamplesError, PostTemplateError, StorageChannelNotSetError
from main.domain.services.material_reminder_service import DEFAULT_WORK_END, DEFAULT_WORK_START
from main.domain.services.post_template_service import MIN_EXAMPLES
from main.presentation.callbacks import (
    MenuAction,
    MenuCB,
    ReminderAction,
    ReminderChannelCB,
    ReminderHoursCB,
    ReminderIntervalCB,
    ReminderSetupCB,
    WorkingHoursPreset,
)
from main.presentation.utils.reminder_input import format_working_hours

INTERVAL_PRESETS = (6, 12, 24, 48)


def reminder_channels_keyboard(
    channels: list[ChannelEntity],
    reminders: dict[int, MaterialReminderEntity],
    problems: dict[int, StorageChannelNotSetError | PostTemplateError],
) -> InlineKeyboardMarkup:
    """Every channel, marked by what its reminder does.

    A channel that cannot take a material post is listed anyway, with the reason
    on the button: a missing channel would leave the user guessing why.
    """
    builder = InlineKeyboardBuilder()

    for channel in channels:
        name = channel.title or channel.username or str(channel.channel_id)
        problem = problems.get(channel.channel_id)
        reminder = reminders.get(channel.channel_id)

        if problem is not None:
            text = f"⚠ {name} — {problem_label(problem)}"
        elif reminder is not None and reminder.enabled:
            text = f"• {name} — every {reminder.interval_hours} h"
        else:
            text = f"○ {name} — off"

        builder.button(text=text, callback_data=ReminderChannelCB(channel_id=channel.channel_id))

    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ROOT))
    builder.adjust(1)
    return builder.as_markup()


def problem_label(problem: StorageChannelNotSetError | PostTemplateError) -> str:
    """The reason a channel is not ready, short enough for a button."""
    match problem:
        case StorageChannelNotSetError():
            return "no storage"
        case NotEnoughExamplesError():
            return f"{problem.count}/{problem.minimum} examples"
        case _:
            # No template at all is the same shortage, counted from zero.
            return f"0/{MIN_EXAMPLES} examples"


def reminder_keyboard(channel_id: int, *, enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Turn off" if enabled else "Turn on",
        callback_data=ReminderSetupCB(
            action=ReminderAction.DISABLE if enabled else ReminderAction.ENABLE,
            channel_id=channel_id
        )
    )
    builder.button(
        text="Change interval",
        callback_data=ReminderSetupCB(action=ReminderAction.INTERVALS, channel_id=channel_id)
    )
    builder.button(
        text="Change working hours",
        callback_data=ReminderSetupCB(action=ReminderAction.HOURS, channel_id=channel_id)
    )
    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.REMINDERS))

    builder.adjust(1)
    return builder.as_markup()


def interval_keyboard(channel_id: int, current: int | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for hours in INTERVAL_PRESETS:
        mark = "• " if hours == current else ""
        builder.button(
            text=f"{mark}{hours} h",
            callback_data=ReminderIntervalCB(channel_id=channel_id, hours=hours)
        )

    builder.button(
        text="Custom",
        callback_data=ReminderSetupCB(action=ReminderAction.CUSTOM_INTERVAL, channel_id=channel_id)
    )
    builder.button(text="Back", callback_data=ReminderChannelCB(channel_id=channel_id))

    builder.adjust(len(INTERVAL_PRESETS), 1)
    return builder.as_markup()


def working_hours_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text=format_working_hours(DEFAULT_WORK_START, DEFAULT_WORK_END),
        callback_data=ReminderHoursCB(channel_id=channel_id, preset=WorkingHoursPreset.DAYTIME)
    )
    builder.button(
        text="Around the clock",
        callback_data=ReminderHoursCB(
            channel_id=channel_id, preset=WorkingHoursPreset.ROUND_THE_CLOCK
        )
    )
    builder.button(
        text="Custom",
        callback_data=ReminderSetupCB(action=ReminderAction.CUSTOM_HOURS, channel_id=channel_id)
    )
    builder.button(text="Back", callback_data=ReminderChannelCB(channel_id=channel_id))

    builder.adjust(1)
    return builder.as_markup()


def back_to_reminder_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    """Escape hatch from typing a custom value."""
    builder = InlineKeyboardBuilder()
    builder.button(text="Back", callback_data=ReminderChannelCB(channel_id=channel_id))
    return builder.as_markup()
