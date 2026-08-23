import logging

from aiogram import F, Router, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message
from dishka import FromDishka

from core.config.settings import Settings
from core.errors import AppError
from main.domain.entities import QuizTopicEntity, QuizPayload
from main.domain.enums import PostType, UserRole
from main.domain.errors import PostNotScheduledError
from main.domain.services import ChannelService, PostService, QuizTopicService
from main.domain.use_cases import GenerateQuizUseCase, GenerateSourcePostUseCase, PreviewPostUseCase, \
    PublishPostUseCase, DiscardDraftUseCase
from main.domain.use_cases.generate_quiz import GenerateQuizRequest
from main.domain.use_cases.generate_source import GenerateSourcePostRequest
from main.presentation.callbacks import MenuAction, MenuCB, ScheduledAction, ScheduledCB, ChannelCB, GenerateCB, \
    DraftCB, DraftAction
from main.presentation.filters import HasAccessFilter
from main.presentation.keyboards import back_to_menu_keyboard, scheduled_posts_keyboard, channels_keyboard, \
    post_types_keyboard, retry_keyboard, draft_actions_keyboard, main_menu_keyboard
from main.presentation.utils import render

post_router = Router(name=__name__)
logger = logging.getLogger(__name__)

post_router.message.filter(HasAccessFilter())
post_router.callback_query.filter(HasAccessFilter())

CHOOSE_CHANNEL_TEXT = "Which channel is this post for?"
NO_CHANNELS_TEXT = "No channels connected yet. An admin has to add one first."
CHOOSE_TYPE_TEXT = "What kind of post?"
GENERATING_TEXT = "Generating, this takes a few seconds…"
DRAFT_TEXT = "Draft is above. What do we do with it?"
MENU_TEXT = "What do you want to do?"
SCHEDULED_TEXT = "Scheduled posts. Tap one to cancel its publication."
NOTHING_SCHEDULED_TEXT = "Nothing is scheduled right now."

# ------------------------------ GENERATING ------------------------------

@post_router.callback_query(MenuCB.filter(F.action == MenuAction.NEW_POST))
async def choose_channel(callback: CallbackQuery, channel_service: FromDishka[ChannelService]):
    channels = await channel_service.list_channels()

    await callback.answer()

    if not channels:
        await render(callback, NO_CHANNELS_TEXT, back_to_menu_keyboard())
        return

    await render(callback, CHOOSE_CHANNEL_TEXT, channels_keyboard(channels))

@post_router.callback_query(ChannelCB.filter())
async def choose_post_type(callback: CallbackQuery, callback_data: ChannelCB):
    await callback.answer()
    await render(callback, CHOOSE_TYPE_TEXT, post_types_keyboard(callback_data.channel_id))

@post_router.callback_query(GenerateCB.filter())
async def generate_post(
    callback: CallbackQuery,
    callback_data: GenerateCB,
    generate_quiz: FromDishka[GenerateQuizUseCase],
    generate_source: FromDishka[GenerateSourcePostUseCase],
    preview_post: FromDishka[PreviewPostUseCase]
):
    await callback.answer()

    await _generate_and_preview(
        callback,
        callback_data.channel_id,
        callback_data.post_type,
        generate_quiz,
        generate_source,
        preview_post
    )


# ------------------------------ DRAFT ------------------------------

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.PUBLISH))
async def publish_draft(
    callback: CallbackQuery,
    callback_data: DraftCB,
    bot: Bot,
    role: UserRole,
    publish_post: FromDishka[PublishPostUseCase],
    channel_service: FromDishka[ChannelService]
):
    post = await publish_post(callback_data.post_id)

    await callback.answer("Published.")
    await _cleanup(bot, callback, callback_data.preview_id)

    channel = await channel_service.find_channel_by_id(post.channel_id)
    title = channel.title if channel is not None else str(post.channel_id)

    await callback.message.answer(
        f"Published to «{title}».", reply_markup=main_menu_keyboard(role)
    )

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.DISCARD))
async def discard_draft(
    callback: CallbackQuery,
    callback_data: DraftCB,
    bot: Bot,
    role: UserRole,
    discard: FromDishka[DiscardDraftUseCase]
):
    await discard(callback_data.post_id)

    await callback.answer("Draft discarded.")
    await _cleanup(bot, callback, callback_data.preview_id)
    await callback.message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(role))

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.REGENERATE))
async def regenerate_draft(
    callback: CallbackQuery,
    callback_data: DraftCB,
    bot: Bot,
    post_service: FromDishka[PostService],
    quiz_topic_service: FromDishka[QuizTopicService],
    generate_quiz: FromDishka[GenerateQuizUseCase],
    generate_source: FromDishka[GenerateSourcePostUseCase],
    preview_post: FromDishka[PreviewPostUseCase]
):
    await callback.answer()

    # save post data before deleting.
    post = await post_service.get_by_id(callback_data.post_id)

    topic: QuizTopicEntity | None = None
    if post.post_type is PostType.QUIZ:
        topic_id = QuizPayload.model_validate(post.payload).topic_id
        topic = await quiz_topic_service.find_by_id(topic_id)

    # delete, not discard, because quiz topic will be removed too.
    await post_service.delete_draft(post.id)
    await _delete(bot, callback, callback_data.preview_id)

    # generating again, retry keyboard if failed.
    await _generate_and_preview(
        callback,
        post.channel_id,
        post.post_type,
        generate_quiz,
        generate_source,
        preview_post,
        topic
    )

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.SCHEDULE))
async def schedule_draft(callback: CallbackQuery) -> None:
    await callback.answer("Not implemented yet", show_alert=True)

# ------------------------------ SCHEDULE ------------------------------

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

# ------------------------------ HELPERS ------------------------------

async def _generate_and_preview(
    callback: CallbackQuery,
    channel_id: int,
    post_type: PostType,
    generate_quiz: GenerateQuizUseCase,
    generate_source: GenerateSourcePostUseCase,
    preview_post: PreviewPostUseCase,
    topic: QuizTopicEntity | None = None
) -> None:
    """Generate, show the preview, offer the actions. Shared by new and regenerate."""
    # Removing keyboard needs to protect from multiple taps.
    await render(callback, GENERATING_TEXT)

    try:
        if post_type == PostType.QUIZ:
            post = await generate_quiz(GenerateQuizRequest(channel_id=channel_id, topic=topic))
        else:
            post = await generate_source(GenerateSourcePostRequest(channel_id=channel_id))

        preview_id = await preview_post(post.id, callback.from_user.id)

    except AppError as err:
        # error_router would answer and leave the user staring at "Generating..."
        # with no buttons. Put the screen back together instead.
        logger.warning("Generation failed for channel %s: %s", channel_id, err.detail)
        await render(callback, err.user_message, retry_keyboard(channel_id, post_type))
        return

    await _drop(callback.message) # type: ignore
    await callback.message.answer(
        DRAFT_TEXT, reply_markup=draft_actions_keyboard(post.id, preview_id)
    )

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

async def _drop(message: Message | None) -> None:
    """Delete a message we sent, ignoring the case when it is already gone."""
    if not isinstance(message, Message):
        return
    try:
        await message.delete()
    except TelegramAPIError:
        logger.debug("Could not delete message %s", message.message_id)

async def _delete(bot: Bot, callback: CallbackQuery, message_id: int) -> None:
    if not isinstance(callback.message, Message):
        return
    try:
        await bot.delete_message(callback.message.chat.id, message_id)
    except TelegramAPIError:
        logger.debug("Could not delete message %s", message_id)

async def _cleanup(bot: Bot, callback: CallbackQuery, preview_id: int) -> None:
    """Remove both the preview and the buttons that acted on it."""
    await _delete(bot, callback, preview_id)
    await _drop(callback.message) # type: ignore