from main.domain.cache import RoleCache
from main.domain.enums import UserRole


class RoleCacheImpl(RoleCache):
    def __init__(self):
        ...

    async def get(self, telegram_id: int) -> UserRole | None:
        return None

    async def set(self, telegram_id: int, role: UserRole) -> None:
        return None

    async def invalidate(self, telegram_id: int) -> None:
        return None