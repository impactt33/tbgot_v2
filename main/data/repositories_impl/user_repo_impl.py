from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import connection
from main.data.enums import UserRole
from main.data.models import User
from main.domain.entities import UserCreateEntity
from main.domain.entities.user_entity import UserEntity, NewUserEntity
from main.domain.repositories import UserRepo


class UserRepoImpl(UserRepo):
    @connection
    async def get_by_username(self, username: str, session: AsyncSession) -> UserEntity | None:
        query = select(User).where(
            User.username == username
        )

        result = await session.execute(query)
        user = result.scalar_one_or_none()

        return user

    @connection
    async def get_by_telegram_id(self, telegram_id: int, session: AsyncSession) -> UserEntity | None:
        query = select(User).where(
            User.telegram_id == telegram_id
        )

        result = await session.execute(query)
        user = result.scalar_one_or_none()

        return user

    @connection
    async def get_or_create_user(self, user_entity: UserCreateEntity, session: AsyncSession) -> NewUserEntity:
        query = (
            insert(User)
            .values(telegram_id=user_entity.telegram_id, username=user_entity.username)
            .on_conflict_do_nothing(index_elements=["telegram_id"])
            .returning(User)
        )

        user = await session.scalar(query)
        created = user is not None

        if not created:
            user = await session.scalar(
                select(User).where(User.telegram_id == user_entity.telegram_id)
            )

        await session.commit()
        return NewUserEntity(user.to_entity(), created)

    @connection
    async def change_user_role(self, telegram_id: int, new_role: UserRole, session: AsyncSession) -> UserEntity | None:
        query = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(role=new_role)
            .returning(User)
        )
        user = await session.scalar(query)

        await session.commit()

        return user.to_entity() if user is not None else None

    @connection
    async def is_admin(self, telegram_id: int, session: AsyncSession) -> bool:
        user = await session.get(User, telegram_id)

        await session.commit()

        return User.role == UserRole.ADMIN if user is not None else False