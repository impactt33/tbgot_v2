from main.domain.enums import UserRole
from main.domain.entities import UserEntity, UserCreateEntity, NewUserEntity
from main.domain.errors.user_errors import *
from main.domain.repositories import UserRepo
from main.domain.services.user_service import UserService


class UserServiceImpl(UserService):
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    async def get_or_create_user(self, user_create_entity: UserCreateEntity) -> NewUserEntity:
        return await self.user_repo.get_or_create_user(user_create_entity)

    async def get_by_username(self, username: str) -> UserEntity:
        user = await self.user_repo.get_by_username(username)

        if user is None:
            raise UserNotFoundError(username=username)

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            raise UserNotFoundError(telegram_id=telegram_id)

        return user

    async def change_user_role(self, actor_telegram_id: int, target_telegram_id: int, new_role: UserRole) -> UserEntity:
        if actor_telegram_id == target_telegram_id:
            raise CannotChangeOwnRoleError(f"User {actor_telegram_id} tried to change own role")

        user = await self.user_repo.change_user_role(target_telegram_id, new_role)

        if user is None:
            raise UserNotFoundError(telegram_id=target_telegram_id)
        return user

    async def is_admin(self, telegram_id: int) -> bool:
        return await self.user_repo.is_admin(telegram_id)