from aiogram.filters import Filter
from aiogram.types import TelegramObject, User

from main.presentation.states import admin_states


class IsAdminFilter(Filter):
    async def __call__(
        self,
        event: TelegramObject,
        raw_state: str | None = None,
        event_from_user: User | None = None
    ) -> bool:
        if event_from_user is None or raw_state is None:
            return False

        if raw_state.split(':')[0] in admin_states:
            return True

        return False