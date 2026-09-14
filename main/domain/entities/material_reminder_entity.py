from datetime import datetime

from pydantic import BaseModel


class MaterialReminderEntity(BaseModel):
    """One user's reminder to post a material in one channel.

    The settings belong to the person, not the channel: two users of one
    channel keep their own intervals and working hours.

    Working hours are minutes from local midnight in USER_TIMEZONE. An end
    earlier than the start is a window across midnight; both None means round
    the clock.

    `next_at` is None while the reminder is off. `message_id` is the reminder
    currently sitting in the user's chat, if there is one.
    """

    id: int
    user_id: int
    channel_id: int
    enabled: bool
    interval_hours: int
    work_start: int | None
    work_end: int | None
    next_at: datetime | None
    message_id: int | None
    created_at: datetime
    updated_at: datetime


class AddMaterialReminderEntity(BaseModel):
    user_id: int
    channel_id: int
    interval_hours: int
    work_start: int | None
    work_end: int | None
