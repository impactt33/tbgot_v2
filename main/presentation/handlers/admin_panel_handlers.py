import logging

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator, CallbackQuery
from dishka import FromDishka

from main.domain.entities import ChannelAddEntity, ChannelEntity
from main.domain.enums import UserRole, ChannelAction
from main.domain.errors import ChannelAddingError, ChannelMissingError, BotNotMemberOfChannelError, \
    ChannelRemovingError, StorageChannelNotPublicError
from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.domain.use_cases import ChangeUserRoleUseCase
from main.presentation.callbacks import MenuCB, MenuAction, SetupChannelCB, StorageAction, StorageCB
from main.presentation.filters import IsAdminFilter
from main.presentation.keyboards import roles_keyboard, choose_channel_keyboard, admin_menu_keyboard, \
    main_menu_keyboard, choose_storage_keyboard, setup_channels_keyboard, storage_prompt_keyboard
from main.presentation.keyboards.add_channel import POSTING_REQUEST_ID, STORAGE_REQUEST_ID
from main.presentation.keyboards.roles import ROLE_CALLBACK_PREFIX
from main.presentation.states import AdminProvideRightsState, AdminChannelActionState
from main.presentation.utils import render

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
