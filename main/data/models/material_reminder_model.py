from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, \
    SmallInteger, UniqueConstraint, false, func, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from core.database import Base
from main.domain.entities import MaterialReminderEntity
from main.domain.services.material_reminder_service import (
    MAX_INTERVAL_HOURS,
    MIN_INTERVAL_HOURS,
    MINUTES_IN_DAY,
)


class MaterialReminder(Base):
    """A user's own reminder to post a material in one channel.

    No relationship on either side: nothing loads reminders through a user or a
    channel, and removing either is left to ON DELETE CASCADE in the database.
    """

    __tablename__ = "material_reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE")
    )
    channel_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("channels.channel_id", ondelete="CASCADE")
    )
    enabled: Mapped[bool] = mapped_column(Boolean, server_default=false())
    interval_hours: Mapped[int] = mapped_column(Integer)
    work_start: Mapped[int | None] = mapped_column(SmallInteger)
    """Minutes from local midnight. Later than work_end means across midnight."""
    work_end: Mapped[int | None] = mapped_column(SmallInteger)
    next_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_id: Mapped[int | None] = mapped_column(BigInteger)
    """The reminder sitting in the user's chat, so the next one can replace it."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @declared_attr.directive
    def __table_args__(cls) -> tuple:
        return (
            # Named by hand: the naming convention builds `uq` from the first
            # column only and would hide half the key in \d.
            UniqueConstraint(
                "user_id",
                "channel_id",
                name="uq_material_reminders_user_id_channel_id"
            ),
            CheckConstraint(
                f"interval_hours BETWEEN {MIN_INTERVAL_HOURS} AND {MAX_INTERVAL_HOURS}",
                name="interval_hours_range"
            ),
            # One end alone is not a window.
            CheckConstraint(
                "(work_start IS NULL) = (work_end IS NULL)",
                name="working_hours_pair"
            ),
            # An equal start and end would mean either nothing or everything,
            # and everything is already spelled as both NULL.
            CheckConstraint(
                f"work_start >= 0 AND work_start < {MINUTES_IN_DAY} "
                f"AND work_end >= 0 AND work_end < {MINUTES_IN_DAY} "
                "AND work_start <> work_end",
                name="working_hours_range"
            ),
            # The only question the worker asks: which enabled reminders are due.
            Index("ix_material_reminders_due", "next_at", postgresql_where=text("enabled")),
        )

    def to_entity(self) -> MaterialReminderEntity:
        return MaterialReminderEntity(
            id=self.id,
            user_id=self.user_id,
            channel_id=self.channel_id,
            enabled=self.enabled,
            interval_hours=self.interval_hours,
            work_start=self.work_start,
            work_end=self.work_end,
            next_at=self.next_at,
            message_id=self.message_id,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )
