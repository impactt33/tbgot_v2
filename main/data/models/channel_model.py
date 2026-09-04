from __future__ import annotations

from typing import TYPE_CHECKING

from datetime import datetime

from sqlalchemy import BigInteger, String, DateTime, func
from sqlalchemy.orm import Mapped, relationship, mapped_column

from core.database import Base
from main.domain.entities import ChannelEntity

if TYPE_CHECKING:
    from main.data.models.quiz_topic_model import QuizTopic
    from main.data.models.source_model import Source
    from main.data.models.material_model import Material


class Channel(Base):
    __tablename__ = "channels"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, unique=True)
    username: Mapped[str | None] = mapped_column(String(63), unique=True, index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    storage_channel_id: Mapped[int | None] = mapped_column(BigInteger)
    """Channel we re-post material files into, so we own a durable link to them.

    Nullable: a news channel never posts materials and needs no storage. No
    foreign key to channels.channel_id either — the storage channel is not a
    posting target and has no row of its own.
    """
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    quiz_topics: Mapped[list[QuizTopic]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise"
    )
    sources: Mapped[list[Source]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise"
    )
    materials: Mapped[list[Material]] = relationship(
        back_populates="channel",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise"
    )

    def to_entity(self) -> ChannelEntity:
        return ChannelEntity(
            channel_id=self.channel_id,
            username=self.username,
            title=self.title,
            added_at=self.added_at,
            storage_channel_id=self.storage_channel_id
        )

    @classmethod
    def from_entity(cls, entity: ChannelEntity) -> Channel:
        return cls(
            channel_id=entity.channel_id,
            username=entity.username,
            title=entity.title,
            added_at=entity.added_at,
            storage_channel_id=entity.storage_channel_id
        )