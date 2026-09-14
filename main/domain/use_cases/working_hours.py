"""Whether a moment falls inside a reminder's working hours.

Kept as a pure function with the moment passed in, like the time helpers in
presentation: the worker asks it about now, the settings screen asks it about
next_at, and neither needs a clock to be tested.
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def is_working_time(
    moment: datetime, tz: ZoneInfo, work_start: int | None, work_end: int | None
) -> bool:
    """Both ends None means round the clock.

    The ends are minutes from local midnight. The start is inside the window and
    the end is not, so 09:00-23:00 lets 22:59 through and holds 23:00 back.
    """
    if work_start is None or work_end is None:
        return True

    local = moment.astimezone(tz)
    minute = local.hour * 60 + local.minute

    if work_start < work_end:
        return work_start <= minute < work_end

    # Across midnight: 22:00-03:00 is the evening part plus the night part.
    return minute >= work_start or minute < work_end
