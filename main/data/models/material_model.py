from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from core.database import Base
from main.domain.entities import MaterialEntity

if TYPE_CHECKING:
    from main.data.models.channel_model import Channel


class Material(Base):
    """A file forwarded by the admin and re-sent into our own storage channel.

    Deduplication runs on file_unique_id rather than file_id: the Bot API says
    the unique id stays the same over time and across bots, so it survives a
    token change. file_id is not stored at all — once the file sits in the
    storage channel, the pair (storage_chat_id, storage_message_id) is the
    durable handle, and it is what the published link is built from.

    The source_* columns are nullable on purpose. They come from the forwarded
    message's forward_origin, and a channel that hides forwards produces
    MessageOriginHiddenUser, which carries no chat.
    """

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    file_unique_id: Mapped[str] = mapped_column(String(127))

    source_chat_id: Mapped[int | None] = mapped_column(BigInteger)
    source_username: Mapped[str | None] = mapped_column(String(63))
    source_message_id: Mapped[int | None] = mapped_column(BigInteger)

    storage_chat_id: Mapped[int] = mapped_column(BigInteger)
    storage_message_id: Mapped[int] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    used_in_post: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="SET NULL")
    )
    channel: Mapped[Channel] = relationship(back_populates="materials")

    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return (
            UniqueConstraint(
                "channel_id", "file_unique_id", name="uq_channel_material_file"
            ),
            Index(
                "ix_materials_unused",
                "channel_id",
                postgresql_where=cls.used_in_post.is_(None)
            ),
        )

    def to_entity(self) -> MaterialEntity:
        return MaterialEntity(
            id=self.id,
            channel_id=self.channel_id,
            file_unique_id=self.file_unique_id,
            source_chat_id=self.source_chat_id,
            source_username=self.source_username,
            source_message_id=self.source_message_id,
            storage_chat_id=self.storage_chat_id,
            storage_message_id=self.storage_message_id,
            created_at=self.created_at,
            used_in_post=self.used_in_post,
        )
