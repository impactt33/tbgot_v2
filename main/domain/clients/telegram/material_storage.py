from abc import ABC, abstractmethod


class MaterialStorage(ABC):
    """Our own copy of a material file, and the channel that holds it.

    A material lives in someone else's channel, which can delete it whenever it
    likes, and the Bot API refuses to copy from a chat the bot is not in. So the
    admin forwards the file to the bot, the bot re-sends it here, and the
    published post links to this copy instead of the original.

    The storage channel travels as an argument rather than living on the
    instance: one bot serves several posting channels, and each of them binds
    its own storage in channels.storage_channel_id.
    """

    @abstractmethod
    async def resolve(self, storage_chat_id: int) -> str:
        """The storage channel's username, which is what makes the link open.

        Binding a storage channel kept only its id, so this is the only way to
        learn the username - and asking for it doubles as the check that the
        channel still exists and still lets the bot in.

        Raises StorageChannelUnreachableError, StorageChannelNotPublicError.
        """

    @abstractmethod
    async def store(self, file_id: str, storage_chat_id: int) -> int:
        """Put a copy in storage, answer with its message id.

        Raises MaterialStorageError.
        """

    @abstractmethod
    async def remove(self, storage_chat_id: int, message_id: int) -> bool:
        """Take a copy back out. False when it was already gone.

        Returns rather than raises: both callers are cleaning up after
        something else, and cleanup must never mask what it is cleaning up
        after.
        """
