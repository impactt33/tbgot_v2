from abc import ABC, abstractmethod

from main.domain.entities import MaterialReminderEntity

# The worker looks once a minute, so the floor is about noise, not precision:
# a reminder more often than hourly stops being a reminder. The ceiling is a week.
MIN_INTERVAL_HOURS = 1
MAX_INTERVAL_HOURS = 168

# What a reminder starts with before the user has changed anything.
DEFAULT_INTERVAL_HOURS = 6
DEFAULT_WORK_START = 9 * 60
DEFAULT_WORK_END = 23 * 60

MINUTES_IN_DAY = 24 * 60


class MaterialReminderService(ABC):
    @abstractmethod
    async def find(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity | None:
        ...

    @abstractmethod
    async def list_for_user(self, telegram_id: int) -> list[MaterialReminderEntity]:
        ...

    @abstractmethod
    async def get_or_create(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        """The reminder, created switched off with the defaults if there is none yet.

        Raises UserNotFoundError.
        """

    @abstractmethod
    async def enable(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        """Raises UserNotFoundError, MaterialReminderNotFoundError."""

    @abstractmethod
    async def disable(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        """Raises UserNotFoundError, MaterialReminderNotFoundError."""

    @abstractmethod
    async def set_interval(
        self, telegram_id: int, channel_id: int, interval_hours: int
    ) -> MaterialReminderEntity:
        """Raises InvalidReminderSettingsError, UserNotFoundError,
        MaterialReminderNotFoundError."""

    @abstractmethod
    async def set_working_hours(
        self, telegram_id: int, channel_id: int, work_start: int | None, work_end: int | None
    ) -> MaterialReminderEntity:
        """Both None means round the clock.

        Raises InvalidReminderSettingsError, UserNotFoundError,
        MaterialReminderNotFoundError.
        """
