import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from main.domain.clients import MaterialStorage
from main.domain.errors import (
    MaterialStorageError,
    StorageChannelNotPublicError,
    StorageChannelUnreachableError,
)

logger = logging.getLogger(__name__)


class TelegramMaterialStorage(MaterialStorage):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def resolve(self, storage_chat_id: int) -> str:
        try:
            chat = await self.bot.get_chat(storage_chat_id)
        except TelegramAPIError as exc:
            logger.warning("Storage channel %s is not reachable: %s", storage_chat_id, exc)
            raise StorageChannelUnreachableError(storage_chat_id, exc) from exc

        if not chat.username:
            # The binding wizard refuses private channels, so this means the
            # channel dropped its username after it was bound.
            raise StorageChannelNotPublicError(storage_chat_id)

        return chat.username

    async def store(self, file_id: str, storage_chat_id: int) -> int:
        """Re-send by file_id rather than copy_message.

        A file_id is accepted anywhere the Bot API takes an upload, so the file
        never travels through us: no download, and the 20 MB getFile limit is
        never touched. copy_message would work too, but it needs the admin's
        message to still be there, and this does not.

        Silently: the storage channel is public and has subscribers of its own,
        and they did not sign up for a notification per uploaded file.
        """
        try:
            message = await self.bot.send_document(
                chat_id=storage_chat_id,
                document=file_id,
                disable_notification=True,
            )
        except TelegramAPIError as exc:
            logger.exception("Storing a file in %s failed", storage_chat_id)
            raise MaterialStorageError(storage_chat_id, exc) from exc

        return message.message_id

    async def remove(self, storage_chat_id: int, message_id: int) -> bool:
        try:
            return await self.bot.delete_message(storage_chat_id, message_id)
        except TelegramAPIError:
            logger.warning(
                "Could not delete message %s from storage %s", message_id, storage_chat_id
            )
            return False
