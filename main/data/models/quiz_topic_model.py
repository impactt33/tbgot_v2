from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import Integer, ForeignKey, BigInteger, String, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

from core.database import Base

if TYPE_CHECKING:
    from main.data.models.channel_model import Channel


class QuizTopic(Base):
    __tablename__ = "quiz_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    topic: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_in_post: Mapped[int | None] = mapped_column(Integer)
    channel: Mapped[Channel] = relationship(back_populates="quiz_topics")


    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return(
            UniqueConstraint("channel_id", "topic", name="uq_channel_topic"),
            Index(
                "ix_quiz_topics_unused",
                "channel_id",
                postgresql_where=cls.used_in_post.is_(None),
            ),
        )