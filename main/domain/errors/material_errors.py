from core.errors import AppError


class MaterialError(AppError):
    """Base class for all errors related to stored materials."""

class MaterialNotFoundError(MaterialError):
    user_message = "Material not found."

    def __init__(self, material_id: int | None = None) -> None:
        self.material_id = material_id
        super().__init__(f"Material (material_id: {material_id!r}) was not found.")

class MaterialAlreadyUsedError(MaterialError):
    user_message = "This file has already been posted to that channel."

    def __init__(self, file_unique_id: str | None = None) -> None:
        self.file_unique_id = file_unique_id
        super().__init__(f"Material (file_unique_id: {file_unique_id!r}) is already stored.")

class StorageChannelNotSetError(MaterialError):
    user_message = (
        "No storage channel is bound to this channel. "
        "An admin has to bind one before material posts can be made."
    )

    def __init__(self, channel_id: int | None = None) -> None:
        self.channel_id = channel_id
        super().__init__(f"Channel (channel_id: {channel_id!r}) has no storage channel bound.")

class StorageChannelNotPublicError(MaterialError):
    user_message = (
        "That channel is private. A material link only opens for members of a "
        "private channel, so the storage channel has to be public."
    )

    def __init__(self, channel_id: int | None = None) -> None:
        self.channel_id = channel_id
        super().__init__(f"Storage channel (channel_id: {channel_id!r}) has no username.")

class StorageChannelUnreachableError(MaterialError):
    """The storage channel is bound but no longer answers.

    storage_channel_id carries no foreign key - a storage channel is not a
    posting target and has no row of its own - so nothing stops it from being
    deleted, or the bot from being thrown out of it. This is where that turns up.
    """

    user_message = (
        "The storage channel does not answer. It may have been deleted, or the "
        "bot removed from it. Rebind it in Bot management -> Set up channel."
    )

    def __init__(self, channel_id: int | None = None, exc: Exception | None = None) -> None:
        self.channel_id = channel_id
        self.exc = exc
        super().__init__(
            f"Storage channel (channel_id: {channel_id!r}) is unreachable. Traceback: {exc!r}"
        )

class MaterialStorageError(MaterialError):
    user_message = "Couldn't put the file into the storage channel. Try again later."

    def __init__(self, channel_id: int | None = None, exc: Exception | None = None) -> None:
        self.channel_id = channel_id
        self.exc = exc
        super().__init__(
            f"Storing a file in channel {channel_id!r} failed. Traceback: {exc!r}"
        )

class InvalidMaterialDraftError(MaterialError):
    user_message = "The generated post came out unusable. Try again."

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(f"Material draft rejected: {reason}")
