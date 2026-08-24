"""Parsing the time entered by the user as text.

We expose an aware datetime in UTC: the database uses a `timestamptz` column, and the scheduler
compares it against `func.now()`. The local time zone is relevant only here and in the output.
"""
import re
from datetime import timedelta, datetime, UTC, date
from zoneinfo import ZoneInfo

from main.presentation.errors import TimeInputError, TimeInPastError

MIN_LEAD = timedelta(minutes=1)

DISPLAY_FORMAT = "%d.%m.%Y %H:%M"

_TIME_ONLY = re.compile(r"^(?P<hour>\d{1,2}):(?P<minute>\d{2})$")
_DATE_TIME = re.compile(
    r"^(?P<day>\d{1,2})\.(?P<month>\d{1,2})(?:\.(?P<year>\d{4}))?"
    r"\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})$"
)

def parse_when(text: str, tz: ZoneInfo, now: datetime | None = None) -> datetime:
    """User text -> datetime fom publication.

    You can pass `now` explicitly—this way, the function remains pure and testable
    without mocking the system clock.
    """
    now_utc = now if now is not None else datetime.now(UTC)
    now_local = now_utc.astimezone(tz)

    raw = " ".join(text.split())

    if match := _TIME_ONLY.fullmatch(raw):
        hour, minutes = _time_parts(match)
        local = _at(now_local.date(), hour, minutes, tz)
        if local <= now_local:
            local = _at(now_local.date() + timedelta(days=1), hour, minutes, tz)

    elif match := _DATE_TIME.fullmatch(raw):
        hour, minutes = _time_parts(match)
        day, month = int(match["day"]), int(match["month"])
        year = int(match["year"]) if match["year"] else now_local.year

        local = _at(_date(year, month, day), hour, minutes, tz)
        if match["year"] is None and local <= now_local:
            local = _at(_date(year + 1, month, day), hour, minutes, tz)

    else:
        raise TimeInputError(f"Unparsable time format: {text!r}")

    when_utc = local.astimezone(UTC)

    if when_utc < now_utc + MIN_LEAD:
        raise TimeInPastError(f"{when_utc.isoformat()} is not at least {MIN_LEAD} ahead")

    return when_utc

def in_hours(hours: int, now: datetime | None = None) -> datetime:
    now_utc = now if now is not None else datetime.now(UTC)

    return (now_utc + timedelta(hours=hours)).replace(second=0, microsecond=0)

def next_day_at(hour: int, minute: int, tz: ZoneInfo, now: datetime | None = None) -> datetime:
    now_utc = now if now is not None else datetime.now(UTC)
    tomorrow = now_utc.astimezone(tz).date() + timedelta(days=1)

    return _at(tomorrow, hour, minute, tz).astimezone(UTC)

def format_local(when: datetime, tz: ZoneInfo) -> str:
    """UTC from DB -> str with tz for scheduled list."""
    return when.astimezone(tz).strftime(DISPLAY_FORMAT)

def _time_parts(match: re.Match[str]) -> tuple[int, int]:
    hour, minute = int(match.group("hour")), int(match.group("minute"))
    if hour > 23 or minute > 59:
        raise TimeInputError(f"Time out of range: {hour:02d}:{minute:02d}")

    return hour, minute

def _date(year: int, month: int, day: int) -> date:
    try:
        return date(year, month, day)
    except ValueError as exc:
        raise TimeInputError(f"No such date: {day:02d}.{month:02d}.{year}") from exc

def _at(day: date, hour: int, minute: int, tz: ZoneInfo) -> datetime:
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)

    if local.astimezone(UTC).astimezone(tz) != local:
        raise TimeInputError(f"Local time does not exist in {tz}: {local}")

    return local