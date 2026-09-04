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
