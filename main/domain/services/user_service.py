from abc import ABC, abstractmethod

from main.data.enums import UserRole
from main.domain.entities import UserCreateEntity, UserEntity


class UserService(ABC):
    @abstractmethod
    async def register_user(self, user_entity: UserCreateEntity) -> None:
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> UserEntity:
        ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity:
        ...

    @abstractmethod
    async def change_user_role(self, telegram_id: int, new_role: UserRole) -> None:
        ...