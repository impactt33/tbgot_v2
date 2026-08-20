from datetime import datetime
from typing import Any

from sqlalchemy import Integer, BigInteger, ForeignKey, DateTime, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from main.domain.entities import PostEntity
from main.domain.enums import PostType, PostStatus


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE"),
        index=True
    )
    post_type: Mapped[PostType] = mapped_column(
        SAEnum(PostType, native_enum=False, length=16)
    )
    status: Mapped[PostStatus] = mapped_column(
        SAEnum(PostStatus, native_enum=False, length=16),
        default=PostStatus.DRAFT
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def to_entity(self) -> PostEntity:
        return PostEntity(
            id=self.id,
            channel_id=self.channel_id,
            post_type=self.post_type,
            status=self.status,
            payload=self.payload,
            telegram_message_id=self.telegram_message_id,
            created_at=self.created_at,
            published_at=self.published_at,
        )