from aiogram.fsm.state import StatesGroup, State

admin_states = []

class AdminProvideRightsState(StatesGroup):
    contact = State()
    role = State()

    admin_states.append(__name__)

class AdminAddChannelState(StatesGroup):
    waiting_for_channel = State()

    admin_states.append(__name__)