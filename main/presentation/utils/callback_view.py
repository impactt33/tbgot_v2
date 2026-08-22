import logging

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

logger = logging.getLogger(__name__)

async def render(
    callback: CallbackQuery,
    text: str,
    markup: InlineKeyboardMarkup | None = None
) -> None:
    """Redraw the message the button belongs to.

    callback.message is Message | InaccessibleMessage | None: Telegram hides the
    body of messages older than 48 hours, and then there is nothing to edit.
    """
    if not isinstance(callback.message, Message):
        await callback.answer("This menu is too old, send /menu again.", show_alert=True)
        return

    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        # Redrawing the same menu is not exception by telegram throws it.
        if "message is not modified" not in str(exc):
            raise
        logger.debug("Menu redraw skipped: content unchanged.")