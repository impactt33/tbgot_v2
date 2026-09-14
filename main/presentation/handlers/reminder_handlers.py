import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.text_decorations import html_decoration
from dishka import FromDishka

from core.config.settings import Settings
from main.domain.entities import ChannelEntity, MaterialReminderEntity
from main.domain.errors import InvalidReminderSettingsError, PostTemplateError, \
    StorageChannelNotSetError
from main.domain.services import ChannelService, MaterialReminderService
from main.domain.services.material_reminder_service import (
    DEFAULT_WORK_END,
    DEFAULT_WORK_START,
    MAX_INTERVAL_HOURS,
    MIN_INTERVAL_HOURS,
)
from main.domain.use_cases import CheckMaterialReadinessUseCase
from main.domain.use_cases.working_hours import is_working_time
from main.presentation.callbacks import MenuAction, MenuCB, ReminderAction, ReminderChannelCB, \
    ReminderHoursCB, ReminderIntervalCB, ReminderSetupCB, WorkingHoursPreset
from main.presentation.errors import ReminderInputError
from main.presentation.filters import HasAccessFilter
from main.presentation.keyboards import back_to_menu_keyboard, back_to_reminder_keyboard, \
    interval_keyboard, reminder_channels_keyboard, reminder_keyboard, working_hours_keyboard
from main.presentation.states import ReminderState
from main.presentation.utils import format_local, format_working_hours, parse_interval_hours, \
    parse_working_hours, render

reminder_router = Router(name=__name__)
logger = logging.getLogger(__name__)

reminder_router.message.filter(HasAccessFilter())
reminder_router.callback_query.filter(HasAccessFilter())

REMINDERS_TEXT = (
    "Reminders to post a material.\n\n"
    "Every channel keeps its own interval and working hours. A channel that "
    "cannot take a material post yet shows what is missing."
)
NO_CHANNELS_TEXT = "No channels connected yet. An admin has to add one first."
INTERVALS_TEXT = "How often should the reminder come?"
CUSTOM_INTERVAL_TEXT = (
    f"Send the interval in whole hours, from {MIN_INTERVAL_HOURS} to {MAX_INTERVAL_HOURS}.\n\n"
    "/quit to cancel."
)
HOURS_TEXT = (
    "When may reminders come?\n\n"
    "A reminder that falls due outside these hours waits for them to start."
)
CUSTOM_HOURS_TEXT = (
    "Send the start and the end, for example 9-23 or 09:30-22:00.\n"
    "An end earlier than the start goes across midnight, like 22-3.\n\n"
    "/quit to cancel."
)
NOT_TEXT = "Send it as text, or tap Back."
REMINDER_STATE_LOST_TEXT = "I lost track of which channel that was for. Start again from the menu."


@reminder_router.callback_query(MenuCB.filter(F.action == MenuAction.REMINDERS))
async def open_reminders(
    callback: CallbackQuery,
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    """Every channel with its reminder, the ones not ready for a material included."""
    channels = await channel_service.list_channels()

    if not channels:
        await callback.answer()
        await render(callback, NO_CHANNELS_TEXT, back_to_menu_keyboard())
        return

    reminders = {
        reminder.channel_id: reminder
        for reminder in await reminder_service.list_for_user(callback.from_user.id)
    }
    problems: dict[int, StorageChannelNotSetError | PostTemplateError] = {}

    for channel in channels:
        problem = await check_readiness.find_problem(channel)

        if problem is not None:
            problems[channel.channel_id] = problem

    await callback.answer()
    await render(
        callback, REMINDERS_TEXT, reminder_channels_keyboard(channels, reminders, problems)
    )

@reminder_router.callback_query(ReminderChannelCB.filter())
async def show_reminder(
    callback: CallbackQuery,
    callback_data: ReminderChannelCB,
    state: FSMContext,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    """The reminder screen of one channel.

    A channel that is not ready opens only when its reminder is already on:
    otherwise there is nothing to set up yet, and the alert says what is
    missing. An enabled one has to open anyway, or it could never be turned off.
    """
    # Both refusals alert, so they come before answer(): the channel may have
    # been removed while the list was open, and it may not be ready.
    channel = await channel_service.get_channel_by_id(callback_data.channel_id)
    problem = await check_readiness.find_problem(channel)

    if problem is not None:
        existing = await reminder_service.find(callback.from_user.id, channel.channel_id)

        if existing is None or not existing.enabled:
            raise problem

    reminder = await reminder_service.get_or_create(callback.from_user.id, channel.channel_id)

    # Back from typing a custom value lands here. The state that screen leaves
    # behind would otherwise hold back every reminder of this user.
    await state.clear()
    await callback.answer()

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await render(callback, text, markup)

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.ENABLE))
async def enable_reminder(
    callback: CallbackQuery,
    callback_data: ReminderSetupCB,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    channel = await channel_service.get_channel_by_id(callback_data.channel_id)

    # Turning on is refused for a channel that is not ready; turning off never
    # is. The refusal alerts, so it comes before answer().
    await check_readiness(channel)
    reminder = await reminder_service.enable(callback.from_user.id, channel.channel_id)

    await callback.answer("Reminder is on.")

    text, markup = _reminder_view(channel, reminder, None, settings)
    await render(callback, text, markup)

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.DISABLE))
async def disable_reminder(
    callback: CallbackQuery,
    callback_data: ReminderSetupCB,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    channel = await channel_service.get_channel_by_id(callback_data.channel_id)
    reminder = await reminder_service.disable(callback.from_user.id, channel.channel_id)
    problem = await check_readiness.find_problem(channel)

    await callback.answer("Reminder is off.")

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await render(callback, text, markup)

# ------------------------------ INTERVAL ------------------------------

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.INTERVALS))
async def show_intervals(
    callback: CallbackQuery,
    callback_data: ReminderSetupCB,
    reminder_service: FromDishka[MaterialReminderService]
) -> None:
    reminder = await reminder_service.find(callback.from_user.id, callback_data.channel_id)

    await callback.answer()
    await render(
        callback,
        INTERVALS_TEXT,
        interval_keyboard(
            callback_data.channel_id,
            reminder.interval_hours if reminder is not None else None
        )
    )

@reminder_router.callback_query(ReminderIntervalCB.filter())
async def set_interval_preset(
    callback: CallbackQuery,
    callback_data: ReminderIntervalCB,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    # Both writes can refuse with an alert, so they come before answer().
    channel = await channel_service.get_channel_by_id(callback_data.channel_id)
    reminder = await reminder_service.set_interval(
        callback.from_user.id, channel.channel_id, callback_data.hours
    )
    problem = await check_readiness.find_problem(channel)

    await callback.answer()

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await render(callback, text, markup)

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.CUSTOM_INTERVAL))
async def ask_for_interval(
    callback: CallbackQuery,
    callback_data: ReminderSetupCB,
    state: FSMContext
) -> None:
    await state.set_state(ReminderState.waiting_for_interval)
    await state.update_data(channel_id=callback_data.channel_id)

    await callback.answer()
    await render(
        callback, CUSTOM_INTERVAL_TEXT, back_to_reminder_keyboard(callback_data.channel_id)
    )

@reminder_router.message(ReminderState.waiting_for_interval, F.text)
async def on_interval_received(
    message: types.Message,
    state: FSMContext,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    if message.from_user is None:
        return

    try:
        hours = parse_interval_hours(message.text or "")
    except ReminderInputError as err:
        # The user just types it again, so the state stays open.
        await message.answer(err.user_message)
        return

    channel_id = await _reminder_target(message, state)

    if channel_id is None:
        return

    channel = await channel_service.get_channel_by_id(channel_id)
    reminder = await reminder_service.set_interval(message.from_user.id, channel_id, hours)
    problem = await check_readiness.find_problem(channel)

    await state.clear()

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await message.answer(text, reply_markup=markup)

@reminder_router.message(ReminderState.waiting_for_interval)
async def on_interval_not_text(message: types.Message) -> None:
    """Registered after the handler that takes text, so it only gets the rest.

    Without it a sticker would meet silence, the same gap as defects 14 and 35.
    """
    await message.answer(NOT_TEXT)

# ------------------------------ WORKING HOURS ------------------------------

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.HOURS))
async def show_working_hours(callback: CallbackQuery, callback_data: ReminderSetupCB) -> None:
    await callback.answer()
    await render(callback, HOURS_TEXT, working_hours_keyboard(callback_data.channel_id))

@reminder_router.callback_query(ReminderHoursCB.filter())
async def set_working_hours_preset(
    callback: CallbackQuery,
    callback_data: ReminderHoursCB,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    work_start: int | None
    work_end: int | None

    match callback_data.preset:
        case WorkingHoursPreset.DAYTIME:
            work_start, work_end = DEFAULT_WORK_START, DEFAULT_WORK_END
        case WorkingHoursPreset.ROUND_THE_CLOCK:
            work_start, work_end = None, None
        case _:
            raise InvalidReminderSettingsError(
                f"unknown working hours preset {callback_data.preset!r}"
            )

    channel = await channel_service.get_channel_by_id(callback_data.channel_id)
    reminder = await reminder_service.set_working_hours(
        callback.from_user.id, channel.channel_id, work_start, work_end
    )
    problem = await check_readiness.find_problem(channel)

    await callback.answer()

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await render(callback, text, markup)

@reminder_router.callback_query(ReminderSetupCB.filter(F.action == ReminderAction.CUSTOM_HOURS))
async def ask_for_working_hours(
    callback: CallbackQuery,
    callback_data: ReminderSetupCB,
    state: FSMContext
) -> None:
    await state.set_state(ReminderState.waiting_for_hours)
    await state.update_data(channel_id=callback_data.channel_id)

    await callback.answer()
    await render(
        callback, CUSTOM_HOURS_TEXT, back_to_reminder_keyboard(callback_data.channel_id)
    )

@reminder_router.message(ReminderState.waiting_for_hours, F.text)
async def on_working_hours_received(
    message: types.Message,
    state: FSMContext,
    settings: FromDishka[Settings],
    channel_service: FromDishka[ChannelService],
    reminder_service: FromDishka[MaterialReminderService],
    check_readiness: FromDishka[CheckMaterialReadinessUseCase]
) -> None:
    if message.from_user is None:
        return

    try:
        work_start, work_end = parse_working_hours(message.text or "")
    except ReminderInputError as err:
        # The user just types it again, so the state stays open.
        await message.answer(err.user_message)
        return

    channel_id = await _reminder_target(message, state)

    if channel_id is None:
        return

    channel = await channel_service.get_channel_by_id(channel_id)
    reminder = await reminder_service.set_working_hours(
        message.from_user.id, channel_id, work_start, work_end
    )
    problem = await check_readiness.find_problem(channel)

    await state.clear()

    text, markup = _reminder_view(channel, reminder, problem, settings)
    await message.answer(text, reply_markup=markup)

@reminder_router.message(ReminderState.waiting_for_hours)
async def on_working_hours_not_text(message: types.Message) -> None:
    """The same guard against silence as on_interval_not_text."""
    await message.answer(NOT_TEXT)

# ------------------------------ HELPERS ------------------------------

async def _reminder_target(message: types.Message, state: FSMContext) -> int | None:
    """The channel a typed value is for, or None if that is lost.

    It lives in FSM data because a message carries no callback_data to read it
    from. Losing it means the state outlived its screen, and the only honest
    answer is to send the user back to the menu.
    """
    data = await state.get_data()
    channel_id: int | None = data.get("channel_id")

    if channel_id is None:
        await state.clear()
        await message.answer(REMINDER_STATE_LOST_TEXT)
        return None

    return channel_id

def _reminder_view(
    channel: ChannelEntity,
    reminder: MaterialReminderEntity,
    problem: StorageChannelNotSetError | PostTemplateError | None,
    settings: Settings
) -> tuple[str, InlineKeyboardMarkup]:
    """Text and keyboard of the reminder screen, for callbacks and messages alike.

    A message handler has nothing to edit and answers with a fresh screen, so
    both paths build it here.
    """
    # The title and the error text are free text, and the bot sends everything
    # as HTML: a stray "<" or "&" would break the whole screen.
    name = html_decoration.quote(channel.title or channel.username or str(channel.channel_id))

    lines = [f"Material reminders for «{name}».", ""]

    if reminder.enabled and reminder.next_at is not None:
        lines.append("Status: on")
        next_line = f"Next reminder: {format_local(reminder.next_at, settings.user_tz)}"

        if not is_working_time(
            reminder.next_at, settings.user_tz, reminder.work_start, reminder.work_end
        ):
            next_line += ", outside working hours - it will wait for them"

        lines.append(next_line)
    else:
        lines.append("Status: off")

    lines += [
        f"Interval: every {reminder.interval_hours} h",
        f"Working hours: {format_working_hours(reminder.work_start, reminder.work_end)}",
    ]

    if problem is not None:
        lines += ["", f"⚠ {html_decoration.quote(problem.user_message)}"]

    return "\n".join(lines), reminder_keyboard(channel.channel_id, enabled=reminder.enabled)
