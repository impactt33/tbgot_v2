import logging

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator, Contact, CallbackQuery
from dishka import FromDishka

from core.errors import AppError
from main.domain.entities import ChannelAddEntity
from main.domain.enums import UserRole, ChannelAction
from main.domain.errors import ChannelAddingError, ChannelMissingError, BotNotMemberOfChannelError, ChannelRemovingError
from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.presentation.filters import IsAdminFilter
from main.presentation.keyboards import roles_keyboard, choose_channel_keyboard
from main.presentation.states import AdminProvideRightsState, AdminChannelActionState, ADMIN_STATES

admin_router = Router(name=__name__)
logger = logging.getLogger(__name__)

admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


@admin_router.message(StateFilter(*ADMIN_STATES), Command("quit")) #type: ignore
async def command_quit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Quit from admin panel.", reply_markup=ReplyKeyboardRemove())

@admin_router.callback_query(F.data.startswith("admin_action_"))
async def choose_admin_action(callback: CallbackQuery, state: FSMContext):
    admin_action = callback.data.removeprefix("admin_action_")

    match admin_action:
        case "provide_rights":
            await state.set_state(AdminProvideRightsState.contact)
            await callback.answer()
            await callback.message.edit_text("Send the contact of any user to provide rights for him.")
        case "add_channel":
            await state.set_state(AdminChannelActionState.waiting_for_channel)
            await state.update_data(action=ChannelAction.ADD)
            await callback.answer()
            await callback.message.answer("Pick channels to add.", reply_markup=choose_channel_keyboard)
        case "remove_channel":
            await state.set_state(AdminChannelActionState.waiting_for_channel)
            await state.update_data(action=ChannelAction.REMOVE)
            await callback.answer()
            await callback.message.answer("Pick channels to remove.", reply_markup=choose_channel_keyboard)
        case _:
            pass

@admin_router.callback_query(AdminProvideRightsState.role, F.data.startswith("provide_role_"))
async def provide_role_callback(callback: CallbackQuery, bot: Bot, state: FSMContext, user_service: FromDishka[UserService]):
    logger.debug(f"Got callback query {callback.data}")

    new_role_name = callback.data.removeprefix("provide_role_")

    new_role = UserRole(new_role_name)

    logger.debug(f"New role is {new_role}")

    data = await state.get_data()
    telegram_id: int | None = data.get("contact")

    await user_service.change_user_role(
        actor_telegram_id=callback.from_user.id,
        target_telegram_id=telegram_id, #type: ignore
        new_role=new_role
    )

    await state.clear()

    await callback.message.edit_text("Successfully changed role.", reply_markup=None)

    try:
        await bot.send_message(
            chat_id=telegram_id, #type: ignore
            text=f"Your role was changed to {new_role_name} by {callback.from_user.username}"
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
    channel_service: FromDishka[ChannelService]
):
    shared = message.chat_shared

    if shared is None:
        raise ChannelMissingError()

    if shared.request_id != 1:
        return

    data = await state.get_data()
    action = data.get("action")

    if action is None:
        return

    await state.clear()

    try:
        member = await bot.get_chat_member(shared.chat_id, bot.id)
    except TelegramBadRequest:
        raise BotNotMemberOfChannelError()

    if not (isinstance(member, ChatMemberAdministrator) and member.can_post_messages):
        await message.answer(
            "The bot lacks permission to post messages in this channel. "
            "Grant this permission in the administrator settings and try again.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    channel = await channel_service.add_channel(
        ChannelAddEntity(
            channel_id=shared.chat_id,
            username=shared.username,
            title=shared.title
        )
    ) if action is ChannelAction.ADD else await channel_service.remove_channel(
        channel_id=shared.chat_id
    )

    if channel is None:
        raise ChannelAddingError() if action is ChannelAction.ADD else ChannelRemovingError()

    await message.answer(
        f"Channel «{channel.title or channel.channel_id}» connected." if action is ChannelAction.ADD else
        f"Channel «{channel.title or channel.channel_id}» removed.",
        reply_markup=ReplyKeyboardRemove()
    )

@admin_router.message(AdminProvideRightsState.contact, F.contact)
async def message_contact_handler(message: types.Message, state: FSMContext, user_service: FromDishka[UserService]):
    contact = message.contact

    user = await user_service.find_by_telegram_id(contact.user_id) #type: ignore

    if user is None:
        await message.answer("That user has not registered yet.")
        return

    await state.update_data(contact=user.telegram_id)

    await state.set_state(AdminProvideRightsState.role)

    await message.answer("Choose role to provide.", reply_markup=roles_keyboard)