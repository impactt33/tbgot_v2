from abc import ABC, abstractmethod

from main.domain.enums import UserRole


class RoleCache(ABC):
    @abstractmethod
    async def get(self, telegram_id: int) -> UserRole | None:
        """None -> empty cache, go to DB."""

    @abstractmethod
    async def set(self, telegram_id: int, role: UserRole) -> None:
        ...

    @abstractmethod
    async def invalidate(self, telegram_id: int) -> None:
        ...