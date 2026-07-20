from core.errors import AppError


class UserNotFountError(AppError):
    pass

class UserAlreadyExistsError(AppError):
    pass

