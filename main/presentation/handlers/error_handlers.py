import logging

from aiogram import Router, F, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import ExceptionTypeFilter
from aiogram.types import ErrorEvent

from core.errors import AppError

error_router = Router(name=__name__)
logger = logging.getLogger(__name__)

@error_router.errors(F.update.callback_query.as_("callback")) #type: ignore
async def unexpected_in_callback(event: ErrorEvent, callback: types.CallbackQuery) -> bool:
    """Without this the button keeps spinning and the user sees nothing at all."""
    logger.exception(
        "Unexpected error: %s",
        event.update.update_id,
        exc_info=event.exception
    )
    try:
        await callback.answer("Something went wrong. Try /menu.", show_alert=True)
    except TelegramAPIError:
        logger.warning("Failed to answer callback for user %s", callback.from_user.id)
    return True

@error_router.errors(F.update.message.as_("message")) #type: ignore
async def unexpected_in_message(event: ErrorEvent, message: types.Message) -> bool:
    logger.exception(
        "Unexpected error: %s",
        event.update.update_id,
        exc_info=event.exception
    )
    try:
        await message.answer("Something went wrong. Try /menu.")
    except TelegramAPIError:
        logger.warning("Failed to send message to user %s", message.chat.id)
    return True

@error_router.errors(ExceptionTypeFilter(AppError), F.update.message.as_("message")) #type: ignore
async def app_error_in_message(event: ErrorEvent, message: types.Message) -> bool:
    error: AppError = event.exception # type: ignore[assignment]
    logger.warning("AppError: %s", error.detail)
    try:
        await message.answer(error.user_message)
    except TelegramAPIError:
        logger.warning("Failed to send message to user %s", message.chat.id)
    return True

@error_router.errors(ExceptionTypeFilter(AppError), F.update.callback_query.as_("callback")) #type: ignore
async def app_error_in_callback(event: ErrorEvent, callback: types.CallbackQuery) -> bool:
    error: AppError = event.exception # type: ignore[assignment]
    logger.warning("AppError: %s", error.detail)
    try:
        await callback.answer(error.user_message, show_alert=True)
    except TelegramAPIError:
        logger.warning("Failed to send callback answer to user %s", callback.from_user.id)
    return True

@error_router.errors()
async def unexpected_error(event: ErrorEvent) -> bool:
    logger.exception(
        "Unexpected error: %s",
        event.update.update_id,
        exc_info=event.exception
    )
    return True