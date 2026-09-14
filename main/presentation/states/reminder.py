from aiogram.fsm.state import StatesGroup, State


class ReminderState(StatesGroup):
    """Only the custom values are typed; every other setting is a button."""

    waiting_for_interval = State()
    waiting_for_hours = State()
