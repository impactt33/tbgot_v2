from abc import ABC, abstractmethod

from main.domain.entities import AddMaterialReminderEntity, MaterialReminderEntity


class MaterialReminderRepo(ABC):
    @abstractmethod
    async def find(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[MaterialReminderEntity]:
        ...

    @abstractmethod
    async def add_if_missing(
        self, reminder: AddMaterialReminderEntity
    ) -> MaterialReminderEntity | None:
        """Insert with these settings, unless the pair already has a row.

        None means the row was already there and nothing was written.
        """

    @abstractmethod
    async def enable(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        """Turn on, with the first interval counted from now.

        None if there is no such reminder.
        """

    @abstractmethod
    async def disable(self, user_id: int, channel_id: int) -> MaterialReminderEntity | None:
        """Turn off, forgetting both the next send time and the reminder in the chat.

        None if there is no such reminder.
        """

    @abstractmethod
    async def set_interval(
        self, user_id: int, channel_id: int, interval_hours: int
    ) -> MaterialReminderEntity | None:
        """A reminder that is on starts counting the new interval from now.

        None if there is no such reminder.
        """

    @abstractmethod
    async def set_working_hours(
        self, user_id: int, channel_id: int, work_start: int | None, work_end: int | None
    ) -> MaterialReminderEntity | None:
        """None if there is no such reminder."""
