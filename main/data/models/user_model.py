from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, String, text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from main.domain.enums import UserRole
from main.domain.entities import UserEntity


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        index=True
    )
    username: Mapped[str | None] = mapped_column(String(63))
    role: Mapped[UserRole] = mapped_column(
        default=UserRole.NONE,
        server_default=text("'NONE'")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        onupdate=func.now()
    )

    def to_entity(self) -> UserEntity:
        return UserEntity(
            id=self.id,
            telegram_id=self.telegram_id,
            username=self.username,
            role=self.role,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @classmethod
    def from_entity(cls, entity: UserEntity) -> User:
        return cls(
            id=entity.id,
            telegram_id=entity.telegram_id,
            username=entity.username,
            role=entity.role,
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )