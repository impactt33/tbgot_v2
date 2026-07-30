from abc import ABC, abstractmethod

from main.data.enums import UserRole
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
    async def change_user_role(self, actor_telegram_id: int, target_telegram_id: int, new_role: UserRole) -> UserEntity:
        ...

    @abstractmethod
    async def is_admin(self, telegram_id: int) -> bool:
        ...