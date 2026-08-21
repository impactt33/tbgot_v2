from aiogram.filters import Filter
from aiogram.types import TelegramObject

from main.domain.enums import UserRole

class HasAccessFilter(Filter):
    """All except UserRole.NONE."""

    async def __call__(self, event: TelegramObject, role: UserRole = UserRole.NONE) -> bool:
        return role is not UserRole.NONE

class IsAdminFilter(Filter):
    async def __call__(self, event: TelegramObject, role: UserRole = UserRole.NONE) -> bool:
        return role is UserRole.ADMIN