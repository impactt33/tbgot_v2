import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from dishka import AsyncContainer
from dishka.integrations.aiogram import CONTAINER_NAME

from main.domain.cache import RoleCache
from main.domain.enums import UserRole
from main.domain.services import UserService

logger = logging.getLogger(__name__)

class RoleMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any]
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")

        if tg_user is None or tg_user.is_bot:
            data["role"] = UserRole.NONE
            return await handler(event, data)

        container: AsyncContainer = data[CONTAINER_NAME]
        cache = await container.get(RoleCache)

        role = await cache.get(tg_user.id)

        if role is None:
            user_service = await container.get(UserService)
            role = await user_service.get_role(tg_user.id)
            await cache.set(tg_user.id, role)
            logger.debug("Role cache miss for %s: %s", tg_user.id, role)

        data["role"] = role
        return await handler(event, data)