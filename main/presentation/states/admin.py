from aiogram.fsm.state import StatesGroup, State


class AdminProvideRightsState(StatesGroup):
    contact = State()
    role = State()