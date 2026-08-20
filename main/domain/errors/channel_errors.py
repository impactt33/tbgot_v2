from core.errors import AppError


class ChannelError(AppError):
    """Base class for all errors related to channels."""

class ChannelNotFoundError(ChannelError):
    user_message = "Channel not found."

    def __init__(self, channel_id: int | None = None, username: str | None = None):
        self.channel_id = channel_id
        self.username = username
        super().__init__(f"Channel (channel_id={channel_id!r}, username={username!r}) was not found.")

class ChannelMissingError(ChannelError):
    user_message = "Missing channel."

class ChannelAlreadyAddedError(ChannelError):
    user_message = "Channel already connected."

class ChannelAddingError(ChannelError):
    user_message = "Error while adding channel. Try again later."

class ChannelRemovingError(ChannelError):
    user_message = "Error while removing channel. Try again later."

class BotNotMemberOfChannelError(ChannelError):
    user_message = "Bot is not member of this channel."