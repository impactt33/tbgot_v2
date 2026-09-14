import logging

from aiogram import Router, types
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove
from dishka import FromDishka

from main.domain.entities import UserCreateEntity
from main.domain.enums import UserRole
from main.domain.services import UserService
from main.presentation.keyboards import admin_menu_keyboard, main_menu_keyboard
from main.presentation.states import BOT_STATES

from aiogram.utils.text_decorations import html_decoration as fmt

command_router = Router(name = __name__)

logger = logging.getLogger(__name__)

MENU_TEXT = "What do you want to do?"
NO_ACCESS_TEXT = "You don't have access yet. Ask an admin (@Immpactt) to grant you rights."
CANCELLED_TEXT = "Cancelled."

@command_router.message(CommandStart()) #type: ignore
async def command_start(
    message: types.Message,
    state: FSMContext,
    role: UserRole,
    user_service: FromDishka[UserService]
):
    logger.debug(f"User %s started a bot", message.from_user.id)

    new_user = await user_service.get_or_create_user(
        UserCreateEntity(
            telegram_id=message.from_user.id,
            username=message.from_user.username
        )
    )

    greeting = (
        f"Welcome, {message.from_user.username}!"
        if new_user.was_created
        else "Welcome back!"
    )

    # role from Middleware read before this handler ran, means it is empty
    # taking it from NewUserEntity
    if new_user.user.role is UserRole.NONE:
        await message.answer(f"{greeting}\n\n{NO_ACCESS_TEXT}")
        return

    await _leave_state(message, state)
    await message.answer(greeting)
    await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(new_user.user.role))

@command_router.message(Command("menu")) # type: ignore
async def command_menu(message: types.Message, state: FSMContext, role: UserRole):
    if role is UserRole.NONE:
        await message.answer(NO_ACCESS_TEXT)
        return

    await _leave_state(message, state)
    await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(role))

@command_router.message(Command("admin")) #type: ignore
async def command_admin(
    message: types.Message,
    state: FSMContext,
    role: UserRole,
    user_service: FromDishka[UserService]
):
    """Shortcut straight into the management submenu."""
    logger.info(f"User {message.from_user.id} entered admin mode")

    if role is not UserRole.ADMIN:
        await message.answer("Oops, you don't have permission to do that.")
        return

    await _leave_state(message, state)
    await message.answer("Bot management:", reply_markup=admin_menu_keyboard())

@command_router.message(Command("self_info")) # type: ignore
async def command_self_info(message: types.Message, role: UserRole):
    await message.answer(
        f"You are @{message.from_user.username}, your role: {role.value}"
    )

@command_router.message(StateFilter(*BOT_STATES), Command("quit")) # type: ignore
async def command_quit(message: types.Message, state: FSMContext, role: UserRole):
    """Lives in command_router so that no feature router can swallow /quit.

    Routers are tried in registration order, and this one is registered first.
    """

    await state.clear()
    await message.answer(CANCELLED_TEXT, reply_markup=ReplyKeyboardRemove())
    await message.answer(MENU_TEXT, reply_markup=main_menu_keyboard(role))

async def _leave_state(message: types.Message, state: FSMContext) -> None:
    """Leave whatever flow was in progress, the way /quit does.

    A menu command is a way out. A state that outlives it turns the next
    unrelated message into input for a screen that is long gone (defect 4),
    and it holds material reminders back. A channel picker may still be
    showing its reply keyboard, and only a message can take that away - hence
    the separate "Cancelled." whenever there was something to cancel.
    """
    if await state.get_state() is None:
        return

    await state.clear()
    await message.answer(CANCELLED_TEXT, reply_markup=ReplyKeyboardRemove())