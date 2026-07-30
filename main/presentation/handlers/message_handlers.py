import logging

from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext

from main.data.repositories_impl import UserRepoImpl
from main.domain.services import UserService
from main.domain.services_impl import UserServiceImpl
from main.presentation.keyboards import roles_keyboard
from main.presentation.states import AdminProvideRightsState

message_router = Router(name=__name__)

logger = logging.getLogger(__name__)

@message_router.message(AdminProvideRightsState.contact, F.contact)
async def message_contact_handler(message: types.Message, state: FSMContext, user_service: UserService = UserServiceImpl(user_repo=UserRepoImpl())):
    contact = message.contact

    user = await user_service.get_by_telegram_id(contact.user_id)

    await state.update_data(contact=user.telegram_id)

    if user is None:
        await message.answer("That user has not registered yet.")
        return

    await state.set_state(AdminProvideRightsState.role)

    await message.answer("Choose role to provide.", reply_markup=roles_keyboard)