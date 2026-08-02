import logging

from aiogram import Router, types
from aiogram.filters import CommandStart, Command
from dishka import FromDishka

from main.domain.entities import UserCreateEntity
from main.domain.services import UserService
from main.presentation.keyboards import choose_action_admin_keyboard

command_router = Router(name = __name__)

logger = logging.getLogger(__name__)

@command_router.message(CommandStart())
async def command_start(message: types.Message, user_service: FromDishka[UserService]):
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

@command_router.message(Command("admin")) #type: ignore
async def command_admin(message: types.Message, user_service: FromDishka[UserService]):
    logger.info(f"User {message.from_user.id} entered admin mode")

    user_is_admin = await user_service.is_admin(message.from_user.id)

    if not user_is_admin:
        await message.answer(f"Oops, you don't have permission to do that.")
        return

    await message.answer(
        f"Welcome, {message.from_user.username or "User"}! Choose action to continue:",
        reply_markup=choose_action_admin_keyboard
    )

@command_router.message(Command("self_info"))
async def command_self_info(message: types.Message, user_service: FromDishka[UserService]):
    user = await user_service.get_by_telegram_id(message.from_user.id)
    await message.answer(f"You {user.username}, your role: {user.role.value}")