from aiogram.fsm.state import StatesGroup, State

class AdminProvideRightsState(StatesGroup):
    contact = State()
    role = State()

class AdminChannelActionState(StatesGroup):
    waiting_for_channel = State()
    waiting_for_storage = State()

class TemplateState(StatesGroup):
    waiting_for_example = State()
    waiting_for_instruction = State()
    waiting_for_quiz_explanation = State()