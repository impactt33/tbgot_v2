from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.entities import ChannelEntity
from main.domain.enums import PostType
from main.presentation.callbacks import (
    ChannelCB,
    DraftAction,
    DraftCB,
    GenerateCB,
    MenuAction,
    MenuCB, ScheduleCB, SchedulePreset, CustomChannelCB,
)
from main.presentation.utils import TIMED_PRESETS, resolve_preset, PRESET_TITLES, format_local

SUPPORTED_POST_TYPES: tuple[PostType, ...] = (PostType.QUIZ, PostType.SOURCES)

POST_TYPE_TITLES: dict[PostType, str] = {
    PostType.QUIZ: "Quiz",
    PostType.SOURCES: "Sources"
}

DRAFT_ACTION_TITLES: tuple[tuple[DraftAction, str], ...] = (
    (DraftAction.PUBLISH, "Publish now"),
    (DraftAction.SCHEDULE, "Schedule"),
    (DraftAction.REGENERATE, "Regenerate"),
    (DraftAction.DISCARD, "Discard"),
)


def channels_keyboard(channels: list[ChannelEntity]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for channel in channels:
        builder.button(
            text=channel.title or channel.username or str(channel.channel_id),
            callback_data=ChannelCB(channel_id=channel.channel_id)
        )

    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ROOT))
    builder.adjust(1)
    return builder.as_markup()


def post_types_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for post_type in SUPPORTED_POST_TYPES:
        builder.button(
            text=POST_TYPE_TITLES[post_type],
            callback_data=GenerateCB(channel_id=channel_id, post_type=post_type)
        )

    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.NEW_POST))
    builder.adjust(1)
    return builder.as_markup()


def draft_actions_keyboard(
    post_id: int,
    preview_id: int,
    allow_regenerate: bool = True,
    preview_count: int = 1
) -> InlineKeyboardMarkup:
    """Actions on a fresh draft.

    A hand-written post has nothing to regenerate — there is no topic or source
    behind it — so the button is dropped rather than left to fail on tap.
    """
    builder = InlineKeyboardBuilder()

    for action, title in DRAFT_ACTION_TITLES:
        builder.button(
            text=title,
            callback_data=DraftCB(
                action=action,
                post_id=post_id,
                preview_id=preview_id,
                preview_count=preview_count
            )
        )

    builder.adjust(2)
    return builder.as_markup()

def custom_channels_keyboard(channels: list[ChannelEntity]) -> InlineKeyboardMarkup:
    """Same list as channel_keyboard, but pointed at the hand-written flow."""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        builder.button(
            text=channel.title or channel.username or str(channel.channel_id),
            callback_data=CustomChannelCB(channel_id=channel.channel_id)
        )

    builder.button(
        text="Back",
        callback_data=MenuCB(action=MenuAction.ROOT)
    )
    builder.adjust(1)
    return builder.as_markup()

def retry_keyboard(channel_id: int, post_type: PostType) -> InlineKeyboardMarkup:
    """Shown when generation failed: the screen must not become a dead end."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Try again",
        callback_data=GenerateCB(channel_id=channel_id, post_type=post_type)
    )
    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ROOT))
    builder.adjust(1)
    return builder.as_markup()

def schedule_preset_keyboard(
    post_id: int,
    preview_id: int,
    tz: ZoneInfo,
    now: datetime | None = None,
    preview_count: int = 1
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for preset in TIMED_PRESETS:
        when = resolve_preset(preset, tz, now)
        builder.button(
            text=f"{PRESET_TITLES[preset]} · {format_local(when, tz)}",
            callback_data=ScheduleCB(
                preset=preset,
                post_id=post_id,
                preview_id=preview_id,
                preview_count=preview_count
            )
        )

    builder.button(
        text=PRESET_TITLES[SchedulePreset.MANUAL],
        callback_data=ScheduleCB(
            preset=SchedulePreset.MANUAL,
            post_id=post_id,
            preview_id=preview_id,
            preview_count=preview_count
        )
    )

    builder.button(
        text="Back", callback_data=_back_to_draft(post_id, preview_id, preview_count)
    )
    builder.adjust(1)
    return builder.as_markup()

def back_to_draft_keyboard(
    post_id: int, preview_id: int, preview_count: int = 1
) -> InlineKeyboardMarkup:
    """The only way out from manual entering time."""
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Back", callback_data=_back_to_draft(post_id, preview_id, preview_count)
    )
    builder.adjust(1)
    return builder.as_markup()

def _back_to_draft(post_id: int, preview_id: int, preview_count: int = 1) -> DraftCB:
    return DraftCB(
        action=DraftAction.SHOW,
        post_id=post_id,
        preview_id=preview_id,
        preview_count=preview_count
    )