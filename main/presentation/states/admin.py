from aiogram.fsm.state import StatesGroup, State


class AdminProvideRightsState(StatesGroup):
    contact = State()
    role = State()

class AdminAddChannelState(StatesGroup):
    waiting_for_channel = State()