from main.domain.entities import AddMaterialReminderEntity, MaterialReminderEntity
from main.domain.errors import (
    InvalidReminderSettingsError,
    MaterialReminderNotFoundError,
    UserNotFoundError,
)
from main.domain.repositories import MaterialReminderRepo, UserRepo
from main.domain.services import MaterialReminderService
from main.domain.services.material_reminder_service import (
    DEFAULT_INTERVAL_HOURS,
    DEFAULT_WORK_END,
    DEFAULT_WORK_START,
    MAX_INTERVAL_HOURS,
    MIN_INTERVAL_HOURS,
    MINUTES_IN_DAY,
)


class MaterialReminderServiceImpl(MaterialReminderService):
    """Speaks telegram ids, stores users.id.

    Everything above this layer only ever has the id Telegram sent, while the
    table keys on the users row, so the lookup lives here once instead of in
    every handler.
    """

    def __init__(self, material_reminder_repo: MaterialReminderRepo, user_repo: UserRepo):
        self.material_reminder_repo = material_reminder_repo
        self.user_repo = user_repo

    async def find(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity | None:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            return None

        return await self.material_reminder_repo.find(user.id, channel_id)

    async def list_for_user(self, telegram_id: int) -> list[MaterialReminderEntity]:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            return []

        return await self.material_reminder_repo.list_by_user(user.id)

    async def get_or_create(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        user_id = await self._user_id(telegram_id)

        # Read first. Opening a screen again is the common case, and it stays a
        # single SELECT. Inserting first also cost an id on every visit:
        # INSERT ... ON CONFLICT DO NOTHING draws nextval() for the row it
        # proposes before it runs into the existing one.
        existing = await self.material_reminder_repo.find(user_id, channel_id)

        if existing is not None:
            return existing

        created = await self.material_reminder_repo.add_if_missing(
            AddMaterialReminderEntity(
                user_id=user_id,
                channel_id=channel_id,
                interval_hours=DEFAULT_INTERVAL_HOURS,
                work_start=DEFAULT_WORK_START,
                work_end=DEFAULT_WORK_END,
            )
        )

        if created is not None:
            return created

        # Another request created the row between the read and the insert.
        return self._found(
            await self.material_reminder_repo.find(user_id, channel_id), user_id, channel_id
        )

    async def enable(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        user_id = await self._user_id(telegram_id)

        return self._found(
            await self.material_reminder_repo.enable(user_id, channel_id), user_id, channel_id
        )

    async def disable(self, telegram_id: int, channel_id: int) -> MaterialReminderEntity:
        user_id = await self._user_id(telegram_id)

        return self._found(
            await self.material_reminder_repo.disable(user_id, channel_id), user_id, channel_id
        )

    async def set_interval(
        self, telegram_id: int, channel_id: int, interval_hours: int
    ) -> MaterialReminderEntity:
        if not MIN_INTERVAL_HOURS <= interval_hours <= MAX_INTERVAL_HOURS:
            raise InvalidReminderSettingsError(
                f"interval_hours={interval_hours!r} is outside "
                f"{MIN_INTERVAL_HOURS}..{MAX_INTERVAL_HOURS}"
            )

        user_id = await self._user_id(telegram_id)

        return self._found(
            await self.material_reminder_repo.set_interval(user_id, channel_id, interval_hours),
            user_id,
            channel_id
        )

    async def set_working_hours(
        self, telegram_id: int, channel_id: int, work_start: int | None, work_end: int | None
    ) -> MaterialReminderEntity:
        if work_start is None or work_end is None:
            if work_start is not work_end:
                raise InvalidReminderSettingsError(
                    f"only one end of working hours is set: {work_start!r}..{work_end!r}"
                )
        elif not (0 <= work_start < MINUTES_IN_DAY and 0 <= work_end < MINUTES_IN_DAY):
            raise InvalidReminderSettingsError(
                f"working hours {work_start!r}..{work_end!r} are outside a day"
            )
        elif work_start == work_end:
            raise InvalidReminderSettingsError(f"working hours start and end at {work_start!r}")

        user_id = await self._user_id(telegram_id)

        return self._found(
            await self.material_reminder_repo.set_working_hours(
                user_id, channel_id, work_start, work_end
            ),
            user_id,
            channel_id
        )

    async def _user_id(self, telegram_id: int) -> int:
        user = await self.user_repo.get_by_telegram_id(telegram_id)

        if user is None:
            raise UserNotFoundError(telegram_id=telegram_id)

        return user.id

    @staticmethod
    def _found(
        reminder: MaterialReminderEntity | None, user_id: int, channel_id: int
    ) -> MaterialReminderEntity:
        if reminder is None:
            raise MaterialReminderNotFoundError(user_id, channel_id)

        return reminder
