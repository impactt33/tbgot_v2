from core.errors import AppError


class UserError(AppError):
    """Base class for all errors related to users."""

class UserNotFoundError(UserError):
    user_message = "User not found."

    def __init__(self, telegram_id: int | None = None, username: str | None = None):
        self.telegram_id = telegram_id
        self.username = username
        super().__init__(f"User not found (telegram_id={telegram_id!r}, username={username!r})")

class UserAlreadyExistsError(UserError):
    user_message = "User already exists."

    def __init__(self, telegram_id: int | None = None, username: str | None = None):
        self.telegram_id = telegram_id
        self.username = username
        super().__init__(f"User (telegram_id={telegram_id!r}, username={username!r}) already exists.")

class AccessDeniedError(UserError):
    user_message = "You have not required rights. Access denied."

class CannotChangeOwnRoleError(UserError):
    user_message = "Cannot change own role. You can lose admin rights."