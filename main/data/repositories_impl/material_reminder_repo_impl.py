from typing import Any

import sqlalchemy as sa
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import QueryableAttribute

from main.data.models import MaterialReminder
from main.domain.entities import AddMaterialReminderEntity, MaterialReminderEntity
from main.domain.repositories.material_reminder_repo import MaterialReminderRepo

_CONSTRAINT = "uq_material_reminders_user_id_channel_id"


def _hours_from_now(hours: QueryableAttribute[int] | int) -> sa.ColumnElement[Any]:
    """now() plus that many hours, on the database clock.

    The worker compares next_at against now() in the database too, so both
    sides of that comparison run on one clock. make_interval takes its
    arguments by position: years, months, weeks, days, hours.
    """
    return sa.func.now() + sa.func.make_interval(0, 0, 0, 0, hours)


class MaterialReminderRepoImpl(MaterialReminderRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        reminder: MaterialReminder | None = await self.session.scalar(
            select(MaterialReminder)
            .where(
                MaterialReminder.user_id == user_id,
                MaterialReminder.channel_id == channel_id
            )
        )

        return reminder.to_entity() if reminder is not None else None

    async def list_by_user(self, user_id: int) -> list[MaterialReminderEntity]:
        reminders = await self.session.scalars(
            select(MaterialReminder)
            .where(MaterialReminder.user_id == user_id)
            .order_by(MaterialReminder.channel_id)
        )

        return [reminder.to_entity() for reminder in reminders]

    async def add_if_missing(
        self, reminder: AddMaterialReminderEntity
    ) -> MaterialReminderEntity | None:
        added: MaterialReminder | None = await self.session.scalar(
            insert(MaterialReminder)
            .values(**reminder.model_dump())
            .on_conflict_do_nothing(constraint=_CONSTRAINT)
            .returning(MaterialReminder)
        )
        await self.session.commit()
        return added.to_entity() if added is not None else None

    async def enable(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        return await self._update(
            user_id,
            channel_id,
            enabled=True,
            next_at=_hours_from_now(MaterialReminder.interval_hours),
        )

    async def disable(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        return await self._update(
            user_id, channel_id, enabled=False, next_at=None, message_id=None
        )

    async def set_interval(
        self, user_id: int, channel_id: int, interval_hours: int
    ) -> MaterialReminderEntity | None:
        return await self._update(
            user_id,
            channel_id,
            interval_hours=interval_hours,
            # CASE reads `enabled` from the row being updated: a reminder that
            # is off keeps no send time at all.
            next_at=sa.case(
                (MaterialReminder.enabled, _hours_from_now(interval_hours)),
                else_=None
            ),
        )

    async def set_working_hours(
        self, user_id: int, channel_id: int, work_start: int | None, work_end: int | None
    ) -> MaterialReminderEntity | None:
        return await self._update(
            user_id, channel_id, work_start=work_start, work_end=work_end
        )

    async def _update(
        self, user_id: int, channel_id: int, **values: Any
    ) -> MaterialReminderEntity | None:
        reminder: MaterialReminder | None = await self.session.scalar(
            sa.update(MaterialReminder)
            .where(
                MaterialReminder.user_id == user_id,
                MaterialReminder.channel_id == channel_id
            )
            .values(**values, updated_at=sa.func.now())
            .returning(MaterialReminder)
        )
        await self.session.commit()
        return reminder.to_entity() if reminder is not None else None
