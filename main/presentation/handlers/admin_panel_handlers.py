import logging

from aiogram import Router, types, F, Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator, CallbackQuery
from dishka import FromDishka

from main.domain.entities import ChannelAddEntity
from main.domain.enums import UserRole, ChannelAction
from main.domain.errors import ChannelAddingError, ChannelMissingError, BotNotMemberOfChannelError, ChannelRemovingError
from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.domain.use_cases import ChangeUserRoleUseCase
from main.presentation.callbacks import MenuCB, MenuAction
from main.presentation.filters import IsAdminFilter
from main.presentation.keyboards import roles_keyboard, choose_channel_keyboard, admin_menu_keyboard, main_menu_keyboard
from main.presentation.keyboards.roles import ROLE_CALLBACK_PREFIX
from main.presentation.states import AdminProvideRightsState, AdminChannelActionState
from main.presentation.utils import render

admin_router = Router(name=__name__)
logger = logging.getLogger(__name__)

admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


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

    if shared.request_id != 1:
        return

    data = await state.get_data()
    raw_action = data.get("action")

    if raw_action is None:
        return

    action = ChannelAction(raw_action)

    await state.clear()

    if action is ChannelAction.ADD:
        try:
            member = await bot.get_chat_member(shared.chat_id, bot.id)
        except TelegramBadRequest:
            raise BotNotMemberOfChannelError() from None

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
        )
        if channel is None:
            raise ChannelAddingError()
        text = f"Channel «{channel.title or channel.channel_id}» connected."
    else:
        channel = await channel_service.remove_channel(shared.chat_id)
        if channel is None:
            raise ChannelRemovingError()
        text = f"Channel «{channel.title or channel.channel_id}» removed."


    await message.answer(text, reply_markup=ReplyKeyboardRemove())
    await message.answer("What do you want to do?", reply_markup=main_menu_keyboard(role))