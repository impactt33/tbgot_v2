from aiogram.fsm.state import StatesGroup, State


class CreatePostState(StatesGroup):
    """Only free-text input needs a state: everything else is inline buttons."""

    waiting_for_time = State()