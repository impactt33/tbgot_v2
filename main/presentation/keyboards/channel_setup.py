from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.entities import ChannelEntity
from main.presentation.callbacks import (
    MenuAction,
    MenuCB,
    SetupChannelCB,
    StorageAction,
    StorageCB,
    TemplateTypesCB,
)


def setup_channels_keyboard(channels: list[ChannelEntity]) -> InlineKeyboardMarkup:
    """Channels to configure, marked by whether a storage channel is bound."""
    builder = InlineKeyboardBuilder()

    for channel in channels:
        mark = "•" if channel.storage_channel_id is not None else "○"
        builder.button(
            text=f"{mark} {channel.title or channel.username or channel.channel_id}",
            callback_data=SetupChannelCB(channel_id=channel.channel_id)
        )

    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ADMIN))
    builder.adjust(1)
    return builder.as_markup()


def storage_prompt_keyboard(channel_id: int, *, has_storage: bool) -> InlineKeyboardMarkup:
    """Bind, rebind or drop the storage channel.

    Skipping is a normal outcome, not a refusal: a news channel never posts
    materials and needs no storage at all.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Rebind storage" if has_storage else "Bind storage",
        callback_data=StorageCB(action=StorageAction.BIND, channel_id=channel_id)
    )

    if has_storage:
        builder.button(
            text="Unbind storage",
            callback_data=StorageCB(action=StorageAction.UNBIND, channel_id=channel_id)
        )

    builder.button(
        text="Post templates",
        callback_data=TemplateTypesCB(channel_id=channel_id)
    )

    builder.button(
        text="Done" if has_storage else "Skip",
        callback_data=StorageCB(action=StorageAction.SKIP, channel_id=channel_id)
    )

    builder.adjust(1)
    return builder.as_markup()
