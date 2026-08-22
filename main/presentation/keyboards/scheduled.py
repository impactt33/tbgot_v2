from zoneinfo import ZoneInfo

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.entities import ChannelEntity, PostEntity
from main.presentation.callbacks import MenuAction, MenuCB, ScheduledAction, ScheduledCB
from main.presentation.utils import format_local


def scheduled_posts_keyboard(
    posts: list[PostEntity],
    channels: dict[int, ChannelEntity],
    tz: ZoneInfo
) -> InlineKeyboardMarkup:
    """One row per scheduled post: pressing it cancels the publication."""
    builder = InlineKeyboardBuilder()

    for post in posts:
        channel = channels.get(post.channel_id)
        title = channel.title if channel is not None else None
        when = format_local(post.scheduled_at, tz) if post.scheduled_at else "?"

        builder.button(
            text=f"Cancel · {when} · {post.post_type.value} · {title}",
            callback_data=ScheduledCB(action=ScheduledAction.CANCEL, post_id=post.id)
        )

    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ROOT))
    builder.adjust(1)

    return builder.as_markup()