import logging

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.enums import UserRole
from main.data.models import User
from main.domain.entities import UserCreateEntity
from main.domain.entities.user_entity import UserEntity, NewUserEntity
from main.domain.repositories import UserRepo


logger = logging.getLogger(__name__)

class UserRepoImpl(UserRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> UserEntity | None:
        query = select(User).where(
            User.username == username
        )

        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        return user

    async def get_by_telegram_id(self, telegram_id: int) -> UserEntity | None:
        query = select(User).where(
            User.telegram_id == telegram_id
        )

        user = await self.session.scalar(query)
        return user

    async def get_or_create_user(self, user_entity: UserCreateEntity) -> NewUserEntity:
        query = (
            insert(User)
            .values(telegram_id=user_entity.telegram_id, username=user_entity.username)
            .on_conflict_do_nothing(index_elements=["telegram_id"])
            .returning(User)
        )

        user = await self.session.scalar(query)
        created = user is not None

        if not created:
            user = await self.session.scalar(
                select(User).where(User.telegram_id == user_entity.telegram_id)
            )

        await self.session.commit()
        return NewUserEntity(user.to_entity(), created)

    async def change_user_role(self, telegram_id: int, new_role: UserRole) -> UserEntity | None:
        query = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(role=new_role)
            .returning(User)
        )
        user = await self.session.scalar(query)

        await self.session.commit()

        return user.to_entity() if user is not None else None

    async def is_admin(self, telegram_id: int) -> bool:
        query = (
            select(User)
            .where(User.telegram_id == telegram_id)
        )
        user = await self.session.scalar(query)

        return user.role == UserRole.ADMIN if user is not None else False