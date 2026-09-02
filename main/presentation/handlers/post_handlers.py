import logging
from datetime import datetime

from aiogram import F, Router, Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, InaccessibleMessage, ReplyKeyboardRemove
from dishka import FromDishka

from core.config.settings import Settings
from core.errors import AppError
from main.domain.entities import QuizTopicEntity, QuizPayload, SourceEntity, SourcePayload
from main.domain.enums import PostType, UserRole
from main.domain.errors import PostNotScheduledError
from main.domain.services import ChannelService, PostService, QuizTopicService, SourceService
from main.domain.use_cases import GenerateQuizUseCase, GenerateSourcePostUseCase, PreviewPostUseCase, \
    PublishPostUseCase, DiscardDraftUseCase
from main.domain.use_cases.create_custom_post import CreateCustomPostUseCase, CreateCustomPostRequest
from main.domain.use_cases.generate_quiz import GenerateQuizRequest
from main.domain.use_cases.generate_source import GenerateSourcePostRequest
from main.presentation.callbacks import MenuAction, MenuCB, ScheduledAction, ScheduledCB, ChannelCB, GenerateCB, \
    DraftCB, DraftAction, ScheduleCB, SchedulePreset, CustomChannelCB
from main.presentation.errors import TimeInputError, PostInputError
from main.presentation.filters import HasAccessFilter
from main.presentation.keyboards import back_to_menu_keyboard, scheduled_posts_keyboard, channels_keyboard, \
    post_types_keyboard, retry_keyboard, draft_actions_keyboard, main_menu_keyboard, schedule_preset_keyboard, \
    back_to_draft_keyboard, custom_channels_keyboard
from main.presentation.states import CreatePostState, CustomPostState
from main.presentation.utils import render, resolve_preset, format_local, parse_when
from main.presentation.utils.post_input import build_custom_payload

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

CHOOSE_TIME_TEXT = "When should it go out?"
ENTER_TIME_TEXT = (
    "Send the time:\n"
    "18:00 — today or tomorrow\n"
    "25.12 18:00 — day and month\n"
    "25.12.2026 18:00 — including the year\n\n"
    "/quit to cancel."
)
STATE_LOST_TEXT = "I lost track of that draft. It is still in drafts, start over from the menu."
CUSTOM_CHOOSE_CHANNEL_TEXT = "Which channel is this post for?"
SEND_POST_TEXT = (
    "Send me the post exactly as it should go out - text, or a photo with a caption.\n"
    "Formatting is kept as you write it.\n\n"
    "/quit to cancel."
)
CUSTOM_STATE_LOST_TEXT = "I lost track of which channel that was for. Start again from the menu."
CANNOT_REGENERATE_TEXT = "This post was written by hand - there is nothing to regenerate."

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
    source_service: FromDishka[SourceService],
    generate_quiz: FromDishka[GenerateQuizUseCase],
    generate_source: FromDishka[GenerateSourcePostUseCase],
    preview_post: FromDishka[PreviewPostUseCase]
):
    await callback.answer()

    # save post data before deleting.
    post = await post_service.get_by_id(callback_data.post_id)

    topic: QuizTopicEntity | None = None
    source: SourceEntity | None = None

    if post.post_type is PostType.QUIZ:
        topic_id = QuizPayload.model_validate(post.payload).topic_id
        topic = await quiz_topic_service.find_by_id(topic_id)
    else:
        source_id = SourcePayload.model_validate(post.payload).source_id
        if source_id is not None:
            source = await source_service.find_by_id(source_id)

    # delete_draft, not discard: discard would remove the quiz topic we want to reuse
    await post_service.delete_draft(post.id)
    await _cleanup_preview(bot, callback, callback_data.preview_id)

    # generating again, retry keyboard if failed.
    await _generate_and_preview(
        callback, post.channel_id, post.post_type,
        generate_quiz, generate_source, preview_post,
        topic, source
    )

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.SHOW))
async def show_draft_actions(
    callback: CallbackQuery,
    callback_data: DraftCB,
    state: FSMContext
):
    """Back from the manual entering time screen."""
    await callback.answer()
    await state.clear()
    await render(
        callback,
        DRAFT_TEXT,
        draft_actions_keyboard(callback_data.post_id, callback_data.preview_id)
    )

# ------------------------------ SCHEDULE A DRAFT ------------------------------

@post_router.callback_query(DraftCB.filter(F.action == DraftAction.SCHEDULE))
async def schedule_draft(
    callback: CallbackQuery,
    callback_data: DraftCB,
    settings: FromDishka[Settings]
):
    await callback.answer()
    await render(
        callback,
        CHOOSE_TIME_TEXT,
        schedule_preset_keyboard(callback_data.post_id, callback_data.preview_id, settings.user_tz)
    )

@post_router.callback_query(ScheduleCB.filter(F.preset != SchedulePreset.MANUAL))
async def schedule_at_preset(
    callback: CallbackQuery,
    callback_data: ScheduleCB,
    bot: Bot,
    role: UserRole,
    settings: FromDishka[Settings],
    post_service: FromDishka[PostService]
):
    when = resolve_preset(callback_data.preset, settings.user_tz)

    await post_service.schedule(callback_data.post_id, when)

    await callback.answer("Scheduled.")
    await _cleanup(bot, callback, callback_data.preview_id)
    await _confirm(callback.message, when, settings, role)

@post_router.callback_query(ScheduleCB.filter(F.preset == SchedulePreset.MANUAL))
async def ask_for_time(
    callback: CallbackQuery,
    callback_data: ScheduleCB,
    state: FSMContext
):
    await callback.answer()

    if not isinstance(callback.message, Message):
        await callback.answer("This menu is too old, send /menu again.", show_alert=True)
        return

    await render(
        callback,
        ENTER_TIME_TEXT,
        back_to_draft_keyboard(callback_data.post_id, callback_data.preview_id)
    )
    await state.set_state(CreatePostState.waiting_for_time)
    await state.update_data(
        post_id=callback_data.post_id,
        preview_id=callback_data.preview_id,
        prompt_id=callback.message.message_id
    )

@post_router.message(CreatePostState.waiting_for_time, F.text)
async def receive_time(
    message: Message,
    state: FSMContext,
    bot: Bot,
    role: UserRole,
    settings: FromDishka[Settings],
    post_service: FromDishka[PostService]
):
    data = await state.get_data()
    post_id: int | None = data.get("post_id")

    if post_id is None:
        # MemoryStorage: a restart keeps the state but drops what it was about.
        await state.clear()
        await message.answer(STATE_LOST_TEXT, reply_markup=main_menu_keyboard(role))
        return

    try:
        when = parse_when(message.text or "", settings.user_tz)
    except TimeInputError as err:
        logger.debug("Unusable time in chat %s: %s", message.chat.id, err.detail)
        await message.answer(err.user_message)
        return

    try:
        await post_service.schedule(post_id, when)
    except AppError as err:
        logger.warning("Could not schedule post %s: %s", post_id, err.detail)
        await state.clear()
        await message.answer(err.user_message, reply_markup=main_menu_keyboard(role))
        return

    await state.clear()
    await _delete(bot, message.chat.id, data.get("prompt_id"))
    await _delete(bot, message.chat.id, data.get("preview_id"))
    await _confirm(message, when, settings, role)

# ------------------------------ CUSTOM POST ------------------------------

@post_router.callback_query(MenuCB.filter(F.action == MenuAction.ADD_CUSTOM))
async def choose_channel_for_custom(
    callback: CallbackQuery,
    channel_service: FromDishka[ChannelService]
):
    channels = await channel_service.list_channels()

    await callback.answer()

    if not channels:
        await render(callback, NO_CHANNELS_TEXT, back_to_menu_keyboard())
        return

    await render(callback, CUSTOM_CHOOSE_CHANNEL_TEXT, custom_channels_keyboard(channels))

@post_router.callback_query(CustomChannelCB.filter())
async def ask_for_custom_post(
    callback: CallbackQuery,
    callback_data: CustomChannelCB,
    state: FSMContext
):
    await callback.answer()

    if not isinstance(callback.message, Message):
        await callback.answer("This menu is too old, send /menu again.", show_alert=True)
        return

    await render(callback, SEND_POST_TEXT, back_to_menu_keyboard())
    await state.set_state(CustomPostState.waiting_for_post)
    await state.update_data(
        channel_id=callback_data.channel_id,
        prompt_id=callback.message.message_id
    )

async def _store_custom_post(
    parts: list[Message],
    channel_id: int,
    prompt_id: int,
    message: Message,
    state: FSMContext,
    bot: Bot,
    role: UserRole,
    create_custom_post: FromDishka[CreateCustomPostUseCase],
    preview_post: FromDishka[PreviewPostUseCase]
) -> None:
    """Validate, store, preview. Shared by the single-message and album paths."""
    try:
        payload = build_custom_payload(parts)
    except PostInputError as err:
        # Same reasoning as a bad time: the admin just sends another message.
        # So thr state stays open.
        logger.debug("Unusable custom post in chat %s: %s", message.chat.id, err.detail)
        await message.answer(err.user_message)
        return

    try:
        post = await create_custom_post(
            CreateCustomPostRequest(channel_id=channel_id, payload=payload)
        )
        preview_id = await preview_post(post.id, message.chat.id)

    except AppError as err:
        logger.warning("Could not store custom post for channel %s: %s", channel_id, err.detail)
        await state.clear()
        await message.answer(err.user_message, reply_markup=main_menu_keyboard(role))
        return

    preview_count = max(len(payload.photo_file_ids), 1)

    await state.clear()
    await _delete(bot, message.chat.id, prompt_id)
    await message.answer(
        DRAFT_TEXT,
        reply_markup=draft_actions_keyboard(
            post.id, preview_id, allow_regenerate=False, preview_count=preview_count
        )
    )

# ------------------------------ SCHEDULED ------------------------------

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
    topic: QuizTopicEntity | None = None,
    source: SourceEntity | None = None
) -> None:
    """Generate, show the preview, offer the actions. Shared by new and regenerate."""
    # Removing keyboard needs to protect from multiple taps.
    await render(callback, GENERATING_TEXT)

    try:
        if post_type == PostType.QUIZ:
            post = await generate_quiz(GenerateQuizRequest(channel_id=channel_id, topic=topic))
        else:
            post = await generate_source(GenerateSourcePostRequest(channel_id=channel_id, source=source))

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

async def _cleanup_preview(bot: Bot, callback: CallbackQuery, preview_id: int) -> None:
    """Drop only preview, keeping the message buttons live on."""
    if isinstance(callback.message, Message):
        await _delete(bot, callback.message.chat.id, preview_id)

async def _delete(bot: Bot, chat_id: int, message_id: int | None) -> None:
    """Delete by id, for messages we no longer hold an object for."""
    if message_id is None:
        return
    try:
        await bot.delete_message(chat_id, message_id)
    except TelegramAPIError:
        logger.debug("Could not delete message %s", message_id)

async def _cleanup(bot: Bot, callback: CallbackQuery, preview_id: int) -> None:
    """Remove both the preview and the buttons that acted on it."""
    if isinstance(callback.message, Message):
        await _delete(bot, callback.message.chat.id, preview_id)
    await _drop(callback.message) # type: ignore

async def _confirm(
    message: Message | InaccessibleMessage | None,
    when: datetime,
    settings: Settings,
    role: UserRole
) -> None:
    if not isinstance(message, Message):
        return
    await message.answer(
        f"Scheduled for {format_local(when, settings.user_tz)}.",
        reply_markup=main_menu_keyboard(role)
    )