from datetime import datetime

from sqlalchemy import BigInteger, String, text, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from main.data.enums import UserRole


class User(Base):
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
    username: Mapped[str] = mapped_column(String(63))
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