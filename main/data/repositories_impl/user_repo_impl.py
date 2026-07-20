from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.database.session import connection
from main.data.enums import UserRole
from main.data.models import User
from main.domain.entities import UserCreateEntity
from main.domain.entities.user_entity import UserEntity
from main.domain.errors import UserNotFountError
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
    async def register_user(self, user_entity: UserCreateEntity, session: AsyncSession) -> None:
        user = User(
            telegram_id=user_entity.telegram_id,
            username=user_entity.username
        )

        session.add(user)
        await session.commit()

    @connection
    async def change_user_role(self, telegram_id: int, new_role: UserRole, session: AsyncSession) -> None:
        query = (
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(role=new_role)
            .returning(User.id)
        )

        result = await session.scalar(query)

        if result is None:
            raise UserNotFountError()

        await session.commit()