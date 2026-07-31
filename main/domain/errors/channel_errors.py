from core.errors import AppError


class ChannelError(AppError):
    """Base class for errors raised by channel service."""

class ChannelNotFoundError(ChannelError):
    user_message = "Channel not found."

    def __init__(self, channel_id: int | None = None, username: str | None = None):
        self.channel_id = channel_id
        self.username = username
        super().__init__(f"Channel (channel_id={channel_id!r}, username={username!r}) was not found.")

class BotNotMemberOfChannelError(ChannelError):
    user_message = "Bot is not member of this channel."