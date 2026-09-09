import logging

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator, CallbackQuery, \
    InlineKeyboardMarkup
from aiogram.utils.text_decorations import html_decoration
from dishka import FromDishka

from main.domain.entities import ChannelAddEntity, ChannelEntity, PostTemplateEntity
from main.domain.enums import UserRole, ChannelAction, PostType
from main.domain.errors import ChannelAddingError, ChannelMissingError, BotNotMemberOfChannelError, \
    ChannelRemovingError, StorageChannelNotPublicError
from main.domain.services import UserService, PostTemplateService
from main.domain.services.channel_service import ChannelService
from main.domain.services.post_template_service import (
    MAX_EXAMPLES,
    MAX_INSTRUCTION_LENGTH,
    MIN_EXAMPLES,
)
from main.domain.use_cases import ChangeUserRoleUseCase
from main.presentation.callbacks import MenuCB, MenuAction, SetupChannelCB, StorageAction, StorageCB, \
    TemplateAction, TemplateCB, TemplateRemoveExampleCB, TemplateTypesCB
from main.presentation.filters import IsAdminFilter
from main.presentation.keyboards import roles_keyboard, choose_channel_keyboard, admin_menu_keyboard, \
    main_menu_keyboard, choose_storage_keyboard, setup_channels_keyboard, storage_prompt_keyboard, \
    back_to_template_keyboard, examples_keyboard, skip_explanation_keyboard, template_keyboard, \
    template_types_keyboard
from main.presentation.keyboards.add_channel import POSTING_REQUEST_ID, STORAGE_REQUEST_ID
from main.presentation.keyboards.roles import ROLE_CALLBACK_PREFIX
from main.presentation.states import AdminProvideRightsState, AdminChannelActionState, TemplateState
from main.presentation.utils import render, render_poll_example, tg_length, with_explanation
from main.presentation.utils.post_input import POLL_EXPLANATION_LIMIT, TEXT_LIMIT

admin_router = Router(name=__name__)
logger = logging.getLogger(__name__)

admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())

MENU_TEXT = "What do you want to do?"
NO_CHANNELS_TEXT = "No channels connected yet. Add one first."
MENU_TOO_OLD_TEXT = "This menu is too old, send /menu again."
NO_POST_RIGHTS_TEXT = (
    "The bot lacks permission to post messages in this channel. "
    "Grant this permission in the administrator settings and try again."
)
SETUP_CHOOSE_TEXT = "Which channel do you want to set up?"
PICK_STORAGE_TEXT = "Pick the channel materials will be uploaded to."
STORAGE_IS_POSTING_CHANNEL_TEXT = (
    "That is the posting channel itself. The storage channel has to be a "
    "different one - otherwise the file would land in the feed."
)
SETUP_STATE_LOST_TEXT = "I lost track of which channel that was for. Start again from the menu."
TEMPLATE_TYPES_TEXT = (
    "Post templates for this channel.\n\n"
    "Each type keeps up to {max_examples} real posts, and generation needs at "
    "least {min_examples} of them. The bot copies their manner, not their "
    "content."
).format(max_examples=MAX_EXAMPLES, min_examples=MIN_EXAMPLES)
EXAMPLE_PROMPT_TEXT = (
    "Send a real post of this type - forward it from the channel or type it out.\n\n"
    "Photos are ignored, only the text is stored, formatting included."
)
EXAMPLE_EMPTY_TEXT = "There is no text in that message. Send a post with text or a caption."
EXAMPLE_TOO_LONG_TEXT = (
    "That is {length} characters, and a post cannot be longer than {limit}. "
    "It looks like more than one post."
)
EXAMPLES_LIST_TEXT = "Pick the example to remove."
INSTRUCTION_PROMPT_TEXT = (
    "Send the instruction for this post type - tone, length, emoji, hashtags, "
    "anything the examples do not make obvious.\n\n"
    f"Up to {MAX_INSTRUCTION_LENGTH} characters."
)
INSTRUCTION_TOO_LONG_TEXT = (
    "That is {length} characters, and the instruction is limited to {limit}."
)
TEMPLATE_STATE_LOST_TEXT = (
    "I lost track of which template that was for. Start again from the menu."
)
QUIZ_EXPLANATION_TEXT = (
    "Quiz saved. Now write its explanation - the text a reader sees after "
    "answering.\n"
    "It never comes along with a forwarded quiz, so it has to be typed by hand. "
    f"Up to {POLL_EXPLANATION_LIMIT} characters.\n\n"
    "Or tap Skip - the example works without one."
)
QUIZ_EXPLANATION_NOT_TEXT = "Send the explanation as text, or tap Skip."
QUIZ_EXPLANATION_TOO_LONG_TEXT = (
    "That is {length} characters, and an explanation is limited to {limit}."
)


@admin_router.callback_query(MenuCB.filter(F.action == MenuAction.ADMIN))
async def open_admin_menu(callback: CallbackQuery):
    await callback.answer()
    await render(callback, "Bot management:", admin_menu_keyboard())

@admin_router.callback_query(MenuCB.filter(F.action == MenuAction.PROVIDE_RIGHTS))
async def ask_for_contact(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminProvideRightsState.contact)
    await callback.answer()
    await render(callback, "Send the contact of the user you want to grant rights to.")

@admin_router.callback_query(MenuCB.filter(F.action.in_({MenuAction.ADD_CHANNEL, MenuAction.REMOVE_CHANNEL})))
async def ask_for_channel(callback: CallbackQuery, callback_data: MenuCB, state: FSMContext):
    action = (
        ChannelAction.ADD
        if callback_data.action is MenuAction.ADD_CHANNEL
        else ChannelAction.REMOVE
    )

    await state.set_state(AdminChannelActionState.waiting_for_channel)
    await state.update_data(action=action)
    await callback.answer()
    await callback.message.answer(
        f"Pick a channel to {action.value.lower()}.", reply_markup=choose_channel_keyboard
    )

@admin_router.message(AdminProvideRightsState.contact, F.contact)
async def message_contact_handler(
    message: types.Message, state: FSMContext, user_service: FromDishka[UserService]
):
    contact = message.contact

    user = await user_service.find_by_telegram_id(contact.user_id) #type: ignore

    if user is None:
        await message.answer("That user has not registered yet.")
        return

    await state.update_data(contact=user.telegram_id)
    await state.set_state(AdminProvideRightsState.role)

    await message.answer("Choose role to provide.", reply_markup=roles_keyboard)

@admin_router.callback_query(
    AdminProvideRightsState.role, F.data.startswith(ROLE_CALLBACK_PREFIX)
)
async def provide_role_callback(
    callback: CallbackQuery,
    bot: Bot,
    state: FSMContext,
    role: UserRole,
    change_user_role: FromDishka[ChangeUserRoleUseCase]
):
    logger.debug("Got callback query %s", callback.data)

    new_role = UserRole(callback.data.removeprefix(ROLE_CALLBACK_PREFIX))

    data = await state.get_data()
    telegram_id: int | None = data.get("contact")

    await change_user_role(
        actor_telegram_id=callback.from_user.id,
        target_telegram_id=telegram_id, #type: ignore
        new_role=new_role
    )

    await state.clear()
    await callback.answer()
    await render(callback,"Successfully changed role.", main_menu_keyboard(role))

    try:
        await bot.send_message(
            chat_id=telegram_id, #type: ignore
            text=f"Your role was changed to {new_role.value} by @{callback.from_user.username}"
        )
    except TelegramForbiddenError:
        logger.info("User %s blocked the bot, notification failed", telegram_id)
        await callback.message.answer("Role was provided, but user blocked the bot.")
    except TelegramAPIError:
        logger.exception("Notification for user %s failed", telegram_id)

@admin_router.message(AdminChannelActionState.waiting_for_channel, F.chat_shared)
async def on_chat_shared(
    message: types.Message,
    state: FSMContext,
    bot: Bot,
    role: UserRole,
    channel_service: FromDishka[ChannelService]
):
    shared = message.chat_shared

    if shared is None:
        raise ChannelMissingError()

    if shared.request_id != POSTING_REQUEST_ID:
        return

    data = await state.get_data()
    raw_action = data.get("action")

    if raw_action is None:
        return

    # Redis gives enums back as strings, so `is` comparisons need this cast.
    action = ChannelAction(raw_action)

    if action is ChannelAction.REMOVE:
        channel = await channel_service.remove_channel(shared.chat_id)

        if channel is None:
            raise ChannelRemovingError()

        await state.clear()
        await message.answer(
            f"Channel «{channel.title or channel.channel_id}» removed.",
            reply_markup=ReplyKeyboardRemove()
        )
        await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(role))
        return

    # Every check runs before the state is dropped. A refusal leaves the picker
    # button alive, so the admin fixes the rights and taps it again instead of
    # walking back through the menu.
    if not await _bot_can_post(bot, shared.chat_id):
        await message.answer(NO_POST_RIGHTS_TEXT)
        return

    channel = await channel_service.add_channel(
        ChannelAddEntity(
            channel_id=shared.chat_id,
            username=shared.username,
            title=shared.title
        )
    )

    if channel is None:
        raise ChannelAddingError()

    await state.clear()
    await message.answer(
        f"Channel «{channel.title or channel.channel_id}» connected.",
        reply_markup=ReplyKeyboardRemove()
    )
    # Storage is asked for right here rather than in a separate menu trip: an
    # admin who just connected a channel is the one who knows what it is for.
    await message.answer(
        _storage_status(channel),
        reply_markup=storage_prompt_keyboard(channel.channel_id, has_storage=False)
    )

# ------------------------------ CHANNEL SETUP ------------------------------

@admin_router.callback_query(MenuCB.filter(F.action == MenuAction.SETUP_CHANNEL))
async def open_channel_setup(
    callback: CallbackQuery,
    channel_service: FromDishka[ChannelService]
) -> None:
    """Storage can be bound long after the channel was added."""
    channels = await channel_service.list_channels()

    await callback.answer()

    if not channels:
        await render(callback, NO_CHANNELS_TEXT, admin_menu_keyboard())
        return

    await render(callback, SETUP_CHOOSE_TEXT, setup_channels_keyboard(channels))

@admin_router.callback_query(SetupChannelCB.filter())
async def show_channel_setup(
    callback: CallbackQuery,
    callback_data: SetupChannelCB,
    channel_service: FromDishka[ChannelService]
) -> None:
    # get_by_id raises when the channel was removed while the list was open,
    # and that alert has to reach the user - so it happens before answer().
    channel = await channel_service.get_channel_by_id(callback_data.channel_id)

    await callback.answer()
    await render(
        callback,
        _storage_status(channel),
        storage_prompt_keyboard(
            channel.channel_id, has_storage=channel.storage_channel_id is not None
        )
    )

@admin_router.callback_query(StorageCB.filter(F.action == StorageAction.BIND))
async def ask_for_storage_channel(
    callback: CallbackQuery,
    callback_data: StorageCB,
    state: FSMContext
) -> None:
    # A ReplyKeyboard cannot be attached to an edit, so this needs a live
    # message to answer into. The check alerts, so it precedes answer().
    if not isinstance(callback.message, types.Message):
        await callback.answer(MENU_TOO_OLD_TEXT, show_alert=True)
        return

    await state.set_state(AdminChannelActionState.waiting_for_storage)
    await state.update_data(channel_id=callback_data.channel_id)

    await callback.answer()
    await callback.message.answer(PICK_STORAGE_TEXT, reply_markup=choose_storage_keyboard)

@admin_router.callback_query(StorageCB.filter(F.action == StorageAction.UNBIND))
async def unbind_storage(
    callback: CallbackQuery,
    callback_data: StorageCB,
    state: FSMContext,
    role: UserRole,
    channel_service: FromDishka[ChannelService]
) -> None:
    await channel_service.set_storage_channel(callback_data.channel_id, None)

    await state.clear()
    await callback.answer("Storage unbound.")
    await render(callback, MENU_TEXT, main_menu_keyboard(role))

@admin_router.callback_query(StorageCB.filter(F.action == StorageAction.SKIP))
async def skip_storage(
    callback: CallbackQuery,
    state: FSMContext,
    role: UserRole
) -> None:
    """Skipping is a normal outcome: a news channel needs no storage."""
    await state.clear()
    await callback.answer()
    await render(callback, MENU_TEXT, main_menu_keyboard(role))

@admin_router.message(AdminChannelActionState.waiting_for_storage, F.chat_shared)
async def on_storage_shared(
    message: types.Message,
    state: FSMContext,
    bot: Bot,
    role: UserRole,
    channel_service: FromDishka[ChannelService]
) -> None:
    shared = message.chat_shared

    if shared is None:
        raise ChannelMissingError()

    if shared.request_id != STORAGE_REQUEST_ID:
        return

    data = await state.get_data()
    channel_id: int | None = data.get("channel_id")

    if channel_id is None:
        await state.clear()
        await message.answer(SETUP_STATE_LOST_TEXT, reply_markup=ReplyKeyboardRemove())
        return

    if shared.chat_id == channel_id:
        await message.answer(STORAGE_IS_POSTING_CHANNEL_TEXT)
        return

    # The picker already hides channels without a username, but a button left
    # over in the chat could still deliver one.
    if not shared.username:
        raise StorageChannelNotPublicError(shared.chat_id)

    if not await _bot_can_post(bot, shared.chat_id):
        await message.answer(NO_POST_RIGHTS_TEXT)
        return

    channel = await channel_service.set_storage_channel(channel_id, shared.chat_id)

    await state.clear()
    await message.answer(
        f"Storage «{shared.title or shared.username}» bound to "
        f"«{channel.title or channel.channel_id}».",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(role))

# ------------------------------ POST TEMPLATES ------------------------------

@admin_router.callback_query(TemplateTypesCB.filter())
async def show_template_types(
    callback: CallbackQuery,
    callback_data: TemplateTypesCB,
    template_service: FromDishka[PostTemplateService]
) -> None:
    """Which post types of this channel already have a usable template."""
    templates = await template_service.list_by_channel(callback_data.channel_id)
    counts = {template.post_type: len(template.examples) for template in templates}

    await callback.answer()
    await render(
        callback,
        TEMPLATE_TYPES_TEXT,
        template_types_keyboard(callback_data.channel_id, counts)
    )

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.OPEN))
async def show_template(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    template_service: FromDishka[PostTemplateService]
) -> None:
    template = await template_service.find(callback_data.channel_id, callback_data.post_type)
    text, markup = _template_view(callback_data.channel_id, callback_data.post_type, template)

    await callback.answer()
    await render(callback, text, markup)

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.ADD_EXAMPLE))
async def ask_for_example(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    state: FSMContext
) -> None:
    await state.set_state(TemplateState.waiting_for_example)
    # PostType is a plain Enum, and FSM data goes through json.dumps, so the
    # value travels instead of the member. It comes back as a string either way.
    await state.update_data(
        channel_id=callback_data.channel_id, post_type=callback_data.post_type.value
    )

    await callback.answer()
    await render(
        callback,
        EXAMPLE_PROMPT_TEXT,
        back_to_template_keyboard(callback_data.channel_id, callback_data.post_type)
    )

@admin_router.message(TemplateState.waiting_for_example)
async def on_example_received(
    message: types.Message,
    state: FSMContext,
    template_service: FromDishka[PostTemplateService]
) -> None:
    # html_text is empty when the message carries neither text nor a caption.
    # For an album that is every part but the first, and since the photos are
    # not stored at all, those extra updates are dropped without a word rather
    # than answering "that is empty" once per photo.
    text = message.html_text

    if not text:
        if message.poll is not None:
            await _ask_for_quiz_explanation(message, message.poll, state)
            return

        if message.media_group_id is None:
            await message.answer(EXAMPLE_EMPTY_TEXT)
        return

    length = tg_length(text)

    if length > TEXT_LIMIT:
        await message.answer(EXAMPLE_TOO_LONG_TEXT.format(length=length, limit=TEXT_LIMIT))
        return

    target = await _template_target(message, state)

    if target is None:
        return

    channel_id, post_type = target
    template = await template_service.add_example(channel_id, post_type, text)

    await state.clear()
    view_text, markup = _template_view(channel_id, post_type, template)
    await message.answer(view_text, reply_markup=markup)

async def _ask_for_quiz_explanation(
    message: types.Message, poll: types.Poll, state: FSMContext
) -> None:
    """A forwarded poll is the only way to add a QUIZ example.

    A poll carries no text at all, so it arrives here through the "nothing to
    store" branch rather than the usual one.
    """
    target = await _template_target(message, state)

    if target is None:
        return

    channel_id, post_type = target

    if post_type is not PostType.QUIZ:
        # A poll in a template for any other type would be junk in the examples.
        await message.answer(EXAMPLE_EMPTY_TEXT)
        return

    await state.set_state(TemplateState.waiting_for_quiz_explanation)
    await state.update_data(example=render_poll_example(poll))

    await message.answer(
        QUIZ_EXPLANATION_TEXT,
        reply_markup=skip_explanation_keyboard(channel_id, post_type)
    )

@admin_router.message(TemplateState.waiting_for_quiz_explanation, F.text)
async def on_quiz_explanation_received(
    message: types.Message,
    state: FSMContext,
    template_service: FromDishka[PostTemplateService]
) -> None:
    # html_text, not text: the admin may format the explanation, and Telegram
    # takes markup in that field - so the example keeps it.
    explanation = message.html_text
    length = tg_length(message.text or "")

    if length > POLL_EXPLANATION_LIMIT:
        await message.answer(
            QUIZ_EXPLANATION_TOO_LONG_TEXT.format(
                length=length, limit=POLL_EXPLANATION_LIMIT
            )
        )
        return

    target = await _template_target(message, state)

    if target is None:
        return

    data = await state.get_data()
    example: str | None = data.get("example")

    if example is None:
        await state.clear()
        await message.answer(TEMPLATE_STATE_LOST_TEXT)
        return

    channel_id, post_type = target
    template = await template_service.add_example(
        channel_id, post_type, with_explanation(example, explanation)
    )

    await state.clear()
    view_text, markup = _template_view(channel_id, post_type, template)
    await message.answer(view_text, reply_markup=markup)

@admin_router.message(TemplateState.waiting_for_quiz_explanation)
async def on_quiz_explanation_not_text(message: types.Message) -> None:
    """Anything that is not text, registered after the handler that takes it.

    Without this the bot goes quiet and the admin has no way to tell the state
    is still waiting. Defects 14 and 35 in STATE.md are that same silence.
    """
    await message.answer(QUIZ_EXPLANATION_NOT_TEXT)

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.SKIP_EXPLANATION))
async def skip_quiz_explanation(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    state: FSMContext,
    template_service: FromDishka[PostTemplateService]
) -> None:
    """Store the quiz with no explanation block at all.

    No block rather than an empty one: three examples ending in "Пояснение:"
    with nothing after it would teach the model that explanations are left
    blank.
    """
    data = await state.get_data()
    example: str | None = data.get("example")

    if example is None:
        await state.clear()
        await callback.answer(TEMPLATE_STATE_LOST_TEXT, show_alert=True)
        return

    # add_example raises when the fifth example is already there, and that alert
    # has to reach the user - so it runs before answer().
    template = await template_service.add_example(
        callback_data.channel_id, callback_data.post_type, example
    )

    await state.clear()
    text, markup = _template_view(callback_data.channel_id, callback_data.post_type, template)

    await callback.answer()
    await render(callback, text, markup)

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.LIST_EXAMPLES))
async def show_examples_for_remove(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    template_service: FromDishka[PostTemplateService]
) -> None:
    """The removal list. Falls back to the template screen if it is empty.

    The button that leads here is only drawn when there is something to remove,
    but one left over in the chat could still arrive after the last example is
    gone - and an empty list of buttons is a dead end.
    """
    template = await template_service.find(callback_data.channel_id, callback_data.post_type)

    await callback.answer()

    if template is None or not template.examples:
        text, markup = _template_view(callback_data.channel_id, callback_data.post_type, template)
        await render(callback, text, markup)
        return

    await render(
        callback,
        EXAMPLES_LIST_TEXT,
        examples_keyboard(
            callback_data.channel_id,
            callback_data.post_type,
            [tg_length(example) for example in template.examples]
        )
    )

@admin_router.callback_query(TemplateRemoveExampleCB.filter())
async def remove_example(
    callback: CallbackQuery,
    callback_data: TemplateRemoveExampleCB,
    template_service: FromDishka[PostTemplateService]
) -> None:
    # remove_example raises for a stale button pointing past the end of the
    # array, and that alert has to reach the user - so it runs before answer().
    template = await template_service.remove_example(
        callback_data.channel_id, callback_data.post_type, callback_data.index
    )
    text, markup = _template_view(callback_data.channel_id, callback_data.post_type, template)

    await callback.answer()
    await render(callback, text, markup)

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.SET_INSTRUCTION))
async def ask_for_instruction(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    state: FSMContext
) -> None:
    await state.set_state(TemplateState.waiting_for_instruction)
    await state.update_data(
        channel_id=callback_data.channel_id, post_type=callback_data.post_type.value
    )

    await callback.answer()
    await render(
        callback,
        INSTRUCTION_PROMPT_TEXT,
        back_to_template_keyboard(callback_data.channel_id, callback_data.post_type)
    )

@admin_router.message(TemplateState.waiting_for_instruction, F.text)
async def on_instruction_received(
    message: types.Message,
    state: FSMContext,
    template_service: FromDishka[PostTemplateService]
) -> None:
    # Plain text, not html_text: the instruction is read by the model, not
    # published, so markup in it would be noise.
    instruction = message.text or ""
    length = tg_length(instruction)

    if length > MAX_INSTRUCTION_LENGTH:
        await message.answer(
            INSTRUCTION_TOO_LONG_TEXT.format(length=length, limit=MAX_INSTRUCTION_LENGTH)
        )
        return

    target = await _template_target(message, state)

    if target is None:
        return

    channel_id, post_type = target
    template = await template_service.set_instruction(channel_id, post_type, instruction)

    await state.clear()
    view_text, markup = _template_view(channel_id, post_type, template)
    await message.answer(view_text, reply_markup=markup)

@admin_router.callback_query(TemplateCB.filter(F.action == TemplateAction.CLEAR_INSTRUCTION))
async def clear_instruction(
    callback: CallbackQuery,
    callback_data: TemplateCB,
    template_service: FromDishka[PostTemplateService]
) -> None:
    template = await template_service.set_instruction(
        callback_data.channel_id, callback_data.post_type, None
    )
    text, markup = _template_view(callback_data.channel_id, callback_data.post_type, template)

    await callback.answer("Instruction cleared.")
    await render(callback, text, markup)

# ------------------------------ HELPERS ------------------------------

async def _bot_can_post(bot: Bot, chat_id: int) -> bool:
    """Whether the bot is an administrator allowed to post in that channel.

    Raises BotNotMemberOfChannelError when Telegram refuses to answer at all,
    which is what happens when the bot is not in the chat.
    """
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
    except TelegramBadRequest:
        raise BotNotMemberOfChannelError() from None

    return isinstance(member, ChatMemberAdministrator) and bool(member.can_post_messages)

def _storage_status(channel: ChannelEntity) -> str:
    if channel.storage_channel_id is None:
        return (
            f"«{channel.title or channel.channel_id}» has no storage channel.\n\n"
            "Material posts need one: the bot re-uploads the file there and "
            "publishes a link to that copy. Channels that never post materials "
            "can skip this."
        )
    return (
        f"«{channel.title or channel.channel_id}» stores materials in "
        f"{channel.storage_channel_id}."
    )

async def _template_target(
    message: types.Message, state: FSMContext
) -> tuple[int, PostType] | None:
    """Which template the awaited message belongs to, or None if that is lost.

    The pair lives in FSM data rather than in callback_data because a message
    carries no callback to read it from. Losing it means the state outlived its
    screen, and the only honest answer is to send the admin back to the menu.
    """
    data = await state.get_data()
    channel_id: int | None = data.get("channel_id")
    raw_type: str | None = data.get("post_type")

    if channel_id is None or raw_type is None:
        await state.clear()
        await message.answer(TEMPLATE_STATE_LOST_TEXT)
        return None

    # Redis gives enums back as strings, so `is` comparisons need this cast.
    return channel_id, PostType(raw_type)

def _template_view(
    channel_id: int, post_type: PostType, template: PostTemplateEntity | None
) -> tuple[str, InlineKeyboardMarkup]:
    """Text and keyboard of the template screen, for both callbacks and messages.

    A message handler has nothing to edit, so it answers with a fresh screen
    instead of redrawing - both paths build it from here.
    """
    examples = template.examples if template is not None else []
    instruction = template.instruction if template is not None else None

    lines = [
        f"Template for {post_type.value} posts.",
        "",
        f"Examples: {len(examples)}/{MAX_EXAMPLES}"
        + ("" if len(examples) >= MIN_EXAMPLES else f" - {MIN_EXAMPLES} needed to generate"),
    ]

    if instruction:
        # The instruction is free text and the bot sends everything as HTML, so
        # a stray "<" in it would break the whole screen.
        lines.append(f"Instruction: {html_decoration.quote(instruction)}")
    else:
        lines.append("Instruction: not set")

    return (
        "\n".join(lines),
        template_keyboard(
            channel_id,
            post_type,
            example_count=len(examples),
            has_instruction=bool(instruction)
        )
    )
