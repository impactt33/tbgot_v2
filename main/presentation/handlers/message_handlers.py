import logging

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, ChatMemberAdministrator
from dishka import FromDishka

from main.data.repositories_impl import UserRepoImpl
from main.domain.entities import ChannelAddEntity
from main.domain.errors import ChannelNotFoundError, ChannelMissingError, ChannelAddingError
from main.domain.services import UserService
from main.domain.services.channel_service import ChannelService
from main.domain.services_impl import UserServiceImpl
from main.presentation.keyboards import roles_keyboard
from main.presentation.states import AdminProvideRightsState, AdminChannelActionState

message_router = Router(name=__name__)

logger = logging.getLogger(__name__)