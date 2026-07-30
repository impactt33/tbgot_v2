import logging

from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

from main.data.enums import UserRole
from main.data.repositories_impl import UserRepoImpl
from main.domain.entities import UserCreateEntity
from main.domain.services import UserService
from main.domain.services_impl import UserServiceImpl
from main.presentation.states import AdminProvideRightsState

command_router = Router(name = __name__)

logger = logging.getLogger(__name__)

@command_router.message(CommandStart())
async def command_start(message: types.Message, user_service: UserService = UserServiceImpl(user_repo=UserRepoImpl())):
    logger.debug(f"User {message.from_user.id} started command")

    new_user = await user_service.get_or_create_user(
        UserCreateEntity(
            telegram_id = message.from_user.id,
            username = message.from_user.username
        )
    )

    if new_user.was_created:
        await message.answer(f"Welcome, {message.from_user.username}!")
    else:
        await message.answer("Welcome back!")

@command_router.message(Command("admin"))
async def command_admin(message: types.Message, state: FSMContext, user_service: UserService = UserServiceImpl(user_repo=UserRepoImpl())):
    logger.info(f"User {message.from_user.id} entered admin mode")

    user = await user_service.get_by_telegram_id(message.from_user.id)

    if user.role != UserRole.ADMIN:
        await message.answer(f"Oops, you don't have permission to do that.")
        return

    await state.set_state(AdminProvideRightsState.contact)
    await message.answer(f"Send the contact of any user to provide rights for him.")