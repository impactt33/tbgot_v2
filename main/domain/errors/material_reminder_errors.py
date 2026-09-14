from core.errors import AppError


class MaterialReminderError(AppError):
    """Base class for everything about material reminders."""

class MaterialReminderNotFoundError(MaterialReminderError):
    user_message = "That reminder is gone. Open Reminders again."

    def __init__(self, user_id: int | None = None, channel_id: int | None = None) -> None:
        self.user_id = user_id
        self.channel_id = channel_id
        super().__init__(
            f"Material reminder (user_id: {user_id!r}, channel_id: {channel_id!r}) was not found."
        )

class InvalidReminderSettingsError(MaterialReminderError):
    """A value no screen offers, so it came from a crafted or a stale button.

    Settings typed by hand never get this far: the input parser answers first,
    with a message the user can act on.
    """

    user_message = "Those reminder settings are out of range."

    def __init__(self, reason: str = "") -> None:
        self.reason = reason
        super().__init__(f"Reminder settings rejected: {reason}")
