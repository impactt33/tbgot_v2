from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, BigInteger, ForeignKey, String, DateTime, func, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

from core.database import Base

if TYPE_CHECKING:
    from main.data.models.channel_model import Channel


class SourceModel(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    name: Mapped[str | None] = mapped_column(String(127))
    url: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_in_post: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="SET NULL")
    )
    channel: Mapped[Channel] = relationship(back_populates="sources")

    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return(
            UniqueConstraint("channel_id", "url", name="uq_channel_source_url"),
            Index(
                "ix_sources_unused",
                "channel_id",
                postgresql_where=cls.used_in_post.is_(None)
            ),
        )

    def to_entity(self) -> QuizTopicEntity:
        return QuizTopicEntity(
            id=self.id,
            channel_id=self.channel_id,
            topic=self.topic,
            created_at=self.created_at,
            used_in_post=self.used_in_post,
        )