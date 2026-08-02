import logging

from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator, Contact
from dishka import FromDishka

from main.domain.entities import ChannelAddEntity
from main.domain.errors import ChannelAddingError, ChannelMissingError
from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.presentation.filters import IsAdminFilter
from main.presentation.keyboards import choose_action_admin_keyboard, roles_keyboard
from main.presentation.states import AdminProvideRightsState, AdminAddChannelState

admin_router = Router(name=__name__)
logger = logging.getLogger(__name__)

admin_router.message.filter(IsAdminFilter())
admin_router.callback_query.filter(IsAdminFilter())


@admin_router.message(Command("quit")) #type: ignore
async def command_quit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Quit from admin panel.", reply_markup=ReplyKeyboardRemove())

@admin_router.message(AdminAddChannelState.waiting_for_channel, F.chat_shared)
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

    await state.clear()

    member = await bot.get_chat_member(shared.chat_id, bot.id)
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
            title=shared.title,
        )
    )

    if channel is None:
        raise ChannelAddingError()

    await message.answer(
        f"Channel «{channel.title or channel.channel_id}» connected.",
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