from aiogram.filters import Filter
from aiogram.types import TelegramObject, User
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from main.domain.services import UserService


class IsAdminStateFilter(Filter):
    @inject
    async def __call__(
        self,
        event: TelegramObject,
        user_service: FromDishka[UserService],
        event_from_user: User | None = None
    ) -> bool:
        if await user_service.is_admin(event_from_user.id):
            return True

        return False