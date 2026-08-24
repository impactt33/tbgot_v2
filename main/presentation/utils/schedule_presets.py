from datetime import datetime
from zoneinfo import ZoneInfo

from main.presentation.callbacks import SchedulePreset
from main.presentation.utils.time_input import in_hours, next_day_at

MORNING_HOUR = 10
EVENING_HOUR = 19

PRESET_TITLES: dict[SchedulePreset, str] = {
    SchedulePreset.IN_1H: "In an hour",
    SchedulePreset.IN_2H: "In two hours",
    SchedulePreset.IN_3H: "In three hours",
    SchedulePreset.TOMORROW_MORNING: "Tomorrow morning (10:00)",
    SchedulePreset.TOMORROW_EVENING: "Tomorrow evening (19:00)",
    SchedulePreset.MANUAL: "Enter date and time"
}

TIMED_PRESETS: tuple[SchedulePreset, ...] = (
    SchedulePreset.IN_1H,
    SchedulePreset.IN_2H,
    SchedulePreset.IN_3H,
    SchedulePreset.TOMORROW_MORNING,
    SchedulePreset.TOMORROW_EVENING
)

def resolve_preset(
    preset: SchedulePreset,
    tz: ZoneInfo,
    now: datetime | None = None
) -> datetime:
    """Preset -> publication in UTC."""

    match preset:
        case SchedulePreset.IN_1H:
            return in_hours(hours=1, now=now)
        case SchedulePreset.IN_2H:
            return in_hours(hours=2, now=now)
        case SchedulePreset.IN_3H:
            return in_hours(hours=3, now=now)
        case SchedulePreset.TOMORROW_MORNING:
            return next_day_at(
                hour=MORNING_HOUR,
                minute=0,
                tz=tz,
                now=now
            )
        case SchedulePreset.TOMORROW_EVENING:
            return next_day_at(
                hour=EVENING_HOUR,
                minute=0,
                tz=tz,
                now=now
            )
        case _:
            raise ValueError(f"Preset carries no time of its own: {preset}")