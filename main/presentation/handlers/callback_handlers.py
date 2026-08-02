import logging

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from dishka import FromDishka

from main.domain.enums import UserRole
from main.domain.services import UserService
from main.presentation.keyboards import choose_channel_keyboard
from main.presentation.states import AdminChannelActionState, AdminProvideRightsState

callback_router = Router(name=__name__)

logger = logging.getLogger(__name__)

