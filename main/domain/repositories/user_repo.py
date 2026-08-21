from abc import ABC, abstractmethod

from main.domain.enums import UserRole
from main.domain.entities import UserCreateEntity, UserEntity, NewUserEntity


class UserRepo(ABC):
    @abstractmethod
    async def get_by_username(self, username: str) -> UserEntity | None:
        ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        ...

    @abstractmethod
    async def get_or_create_user(self, user_entity: UserCreateEntity) -> NewUserEntity:
        ...

    @abstractmethod
    async def change_user_role(self, telegram_id: int, new_role: UserRole) -> UserEntity | None:
        ...

    @abstractmethod
    async def get_role(self, telegram_id: int) -> UserRole:
        ...