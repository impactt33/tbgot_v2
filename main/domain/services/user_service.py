from abc import ABC, abstractmethod

from main.domain.enums import UserRole
from main.domain.entities import UserCreateEntity, UserEntity, NewUserEntity


class UserService(ABC):
    @abstractmethod
    async def get_or_create_user(self, user_create_entity: UserCreateEntity) -> NewUserEntity:
        ...

    @abstractmethod
    async def get_by_username(self, username: str) -> UserEntity:
        ...

    @abstractmethod
    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity:
        ...

    @abstractmethod
    async def find_by_username(self, username: str) -> UserEntity | None:
        ...

    @abstractmethod
    async def find_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        ...

    @abstractmethod
    async def change_user_role(self, actor_telegram_id: int, target_telegram_id: int, new_role: UserRole) -> UserEntity:
        ...

    @abstractmethod
    async def get_role(self, telegram_id: int) -> UserRole:
        ...

    @abstractmethod
    async def is_admin(self, telegram_id: int) -> bool:
        ...

    @abstractmethod
    async def has_access(self, telegram_id: int) -> bool:
        ...