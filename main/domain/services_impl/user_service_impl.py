from main.data.enums import UserRole
from main.domain.entities import UserEntity, UserCreateEntity
from main.domain.errors.user_errors import *
from main.domain.repositories import UserRepo
from main.domain.services.user_service import UserService


class UserServiceImpl(UserService):
    def __init__(self, user_repo: UserRepo):
        self.user_repo = user_repo

    async def register_user(self, user_entity: UserCreateEntity) -> None:
        await self.user_repo.register_user(user_entity)

    async def get_by_username(self, username: str) -> UserEntity:
        user = await self.user_repo.get_by_username(username)

        if user is None:
            raise UserNotFountError(username)

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            raise UserNotFountError(telegram_id)

        return user

    async def change_user_role(self, telegram_id: int, new_role: UserRole) -> None:
        await self.user_repo.change_user_role(telegram_id, new_role)