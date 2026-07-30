import logging

from aiogram import Router, F, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent

from core.errors import AppError

error_router = Router(name=__name__)
logger = logging.getLogger(__name__)

@error_router.errors(ExceptionTypeFilter(AppError), F.update.message.as_("message"))
async def app_error_in_message(event: ErrorEvent, message: types.Message) -> bool:
    error: AppError = event.exception # type: ignore[assigment]
    logger.warning("AppError: %s", error.detail)
    try:
        await message.answer(error.user_message)
    except TelegramAPIError:
        logger.warning("Failed to send message to user %s", message.chat.id)
    return True

@error_router.errors(ExceptionTypeFilter(AppError), F.update.callback_query.as_("callback"))
async def app_error_in_callback(event: ErrorEvent, callback: types.CallbackQuery) -> bool:
    error: AppError = event.exception # type: ignore[assigment]
    logger.warning("AppError: %s", error.detail)
    try:
        await callback.answer(error.user_message, show_alert=True)
    except TelegramAPIError:
        logger.warning("Failed to send callback answer to user %s", callback.chat.id)
    return True

@error_router.errors()
async def unexpected_error(event: ErrorEvent) -> bool:
    logger.exception(
        "Unexpected error: %s",
        event.update.update_id,
        exc_info=event.exception
    )
    return True