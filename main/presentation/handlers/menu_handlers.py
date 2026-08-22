import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from main.domain.enums import UserRole
from main.presentation.callbacks import MenuAction, MenuCB
from main.presentation.filters import HasAccessFilter
from main.presentation.keyboards import main_menu_keyboard
from main.presentation.utils import render

menu_router = Router(name=__name__)
logger = logging.getLogger(__name__)

menu_router.message.filter(HasAccessFilter())
menu_router.callback_query.filter(HasAccessFilter())

MENU_TEXT = "What do you want to do?"


@menu_router.callback_query(MenuCB.filter(F.action == MenuAction.ROOT))
async def back_to_menu(callback: CallbackQuery, state: FSMContext, role: UserRole):
    """Single exit point back to the root menu, reused by every screen."""
    await state.clear()
    await callback.answer()
    await render(callback, MENU_TEXT, main_menu_keyboard(role))