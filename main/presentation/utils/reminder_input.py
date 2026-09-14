"""Parsing the reminder settings typed by hand.

Working hours come out as minutes from local midnight, the unit the database
keeps. An end earlier than the start is a window across midnight and is taken
as such. An end equal to the start is refused: it means either nothing or
everything, and "Around the clock" already says the second.
"""
import re

from main.domain.services.material_reminder_service import MAX_INTERVAL_HOURS, MIN_INTERVAL_HOURS
from main.presentation.errors import (
    ReminderIntervalInputError,
    WorkingHoursEmptyError,
    WorkingHoursInputError,
)

_INTERVAL = re.compile(r"^(?P<hours>\d{1,3})\s*h?$")
_RANGE = re.compile(
    r"^(?P<start_hour>\d{1,2})(?::(?P<start_minute>\d{2}))?"
    r"\s*[-–—]\s*"
    r"(?P<end_hour>\d{1,2})(?::(?P<end_minute>\d{2}))?$"
)

def parse_interval_hours(text: str) -> int:
    """"8", "8h" or "8 h" -> 8."""
    match = _INTERVAL.fullmatch(text.strip().lower())

    if match is None:
        raise ReminderIntervalInputError(f"Unparsable interval: {text!r}")

    hours = int(match["hours"])

    if not MIN_INTERVAL_HOURS <= hours <= MAX_INTERVAL_HOURS:
        raise ReminderIntervalInputError(f"Interval out of range: {hours}")

    return hours

def parse_working_hours(text: str) -> tuple[int, int]:
    """"9-23" or "09:30-22:00" -> (start, end) in minutes from midnight."""
    match = _RANGE.fullmatch(text.strip())

    if match is None:
        raise WorkingHoursInputError(f"Unparsable working hours: {text!r}")

    start = _minutes(match["start_hour"], match["start_minute"])
    end = _minutes(match["end_hour"], match["end_minute"])

    if start == end:
        raise WorkingHoursEmptyError(f"Working hours start and end together: {text!r}")

    return start, end

def format_working_hours(work_start: int | None, work_end: int | None) -> str:
    if work_start is None or work_end is None:
        return "around the clock"

    return f"{_clock(work_start)}–{_clock(work_end)}"

def _minutes(hour: str, minute: str | None) -> int:
    hours, minutes = int(hour), int(minute or 0)

    # 24:00 is how people write the end of a day, and it is the same moment as 00:00.
    if hours == 24 and minutes == 0:
        return 0

    if hours > 23 or minutes > 59:
        raise WorkingHoursInputError(f"Time out of range: {hours:02d}:{minutes:02d}")

    return hours * 60 + minutes

def _clock(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"
