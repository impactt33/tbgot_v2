import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery
from dishka import FromDishka

from core.config.settings import Settings
from main.domain.errors import PostNotScheduledError
from main.domain.services import ChannelService, PostService
from main.presentation.callbacks import MenuAction, MenuCB, ScheduledAction, ScheduledCB
from main.presentation.filters import HasAccessFilter
from main.presentation.keyboards import back_to_menu_keyboard, scheduled_posts_keyboard
from main.presentation.utils import render

post_router = Router(name=__name__)
logger = logging.getLogger(__name__)

post_router.message.filter(HasAccessFilter())
post_router.callback_query.filter(HasAccessFilter())

SCHEDULED_TEXT = "Scheduled posts. Tap one to cancel its publication."
NOTHING_SCHEDULED_TEXT = "Nothing is scheduled right now."


@post_router.callback_query(MenuCB.filter(F.action == MenuAction.NEW_POST))
async def start_new_post(callback: CallbackQuery):
    # TODO: pick a channel -> pick a type -> generate -> preview.
    await callback.answer("Not implemented yet.", show_alert=True)

@post_router.callback_query(MenuCB.filter(F.action == MenuAction.SCHEDULED))
async def show_scheduled(
    callback: CallbackQuery,
    settings: FromDishka[Settings],
    post_service: FromDishka[PostService],
    channel_service: FromDishka[ChannelService]
):
    await callback.answer()
    await _render_scheduled(callback, settings, post_service, channel_service)

@post_router.callback_query(ScheduledCB.filter(F.action == ScheduledAction.CANCEL))
async def cancel_scheduled(
    callback: CallbackQuery,
    callback_data: ScheduledCB,
    settings: FromDishka[Settings],
    post_service: FromDishka[PostService],
    channel_service: FromDishka[ChannelService]
):
    try:
        await post_service.unschedule(callback_data.post_id)
    except PostNotScheduledError as err:
        # The scheduler claimed the post between rendering the list and this tap.
        logger.info("Cancel too late for post %s: %s", callback_data.post_id, err.detail)
        await callback.answer(err.user_message, show_alert=True)
    else:
        await callback.answer("Publication cancelled, the post is back to drafts.")

    await _render_scheduled(callback, settings, post_service, channel_service)

async def _render_scheduled(
    callback: CallbackQuery,
    settings: Settings,
    post_service: PostService,
    channel_service: ChannelService
) -> None:
    posts = await post_service.find_scheduled()

    if not posts:
        await render(callback, NOTHING_SCHEDULED_TEXT, back_to_menu_keyboard())
        return

    channels = {c.channel_id: c for c in await channel_service.list_channels()}

    await render(
        callback,
        SCHEDULED_TEXT,
        scheduled_posts_keyboard(posts, channels, settings.user_tz)
    )