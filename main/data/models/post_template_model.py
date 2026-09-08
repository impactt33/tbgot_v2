from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Text, UniqueConstraint, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, declared_attr, mapped_column, relationship

from core.database import Base
from main.domain.entities import PostTemplateEntity
from main.domain.enums import PostType

if TYPE_CHECKING:
    from main.data.models.channel_model import Channel


class PostTemplate(Base):
    """Examples and an instruction for one (channel, post_type) pair.

    The examples live in a JSONB array rather than in a table of their own.
    They are read all at once, five at most, and never queried by content, so a
    second table would buy nothing but a join. The price is that an example is
    addressed by its position in the array - fine here, because both writes that
    touch the array are single statements and the screen redraws after each one.
    """

    __tablename__ = "post_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    post_type: Mapped[PostType] = mapped_column(
        SAEnum(PostType, native_enum=False, length=16, create_constraint=True)
    )
    examples: Mapped[list[str]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    instruction: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    channel: Mapped[Channel] = relationship(back_populates="post_templates")

    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        # Named by hand: the naming convention builds `uq` from the first column
        # only, which would give `uq_post_templates_channel_id` and hide half the
        # key from anyone reading \d in psql.
        return (
            UniqueConstraint(
                "channel_id",
                "post_type",
                name="uq_post_templates_channel_id_post_type"
            ),
        )

    def to_entity(self) -> PostTemplateEntity:
        return PostTemplateEntity(
            id=self.id,
            channel_id=self.channel_id,
            post_type=self.post_type,
            examples=self.examples,
            instruction=self.instruction,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
