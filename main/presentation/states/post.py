from aiogram.fsm.state import StatesGroup, State


class CreatePostState(StatesGroup):
    """Only free-text input needs a state: everything else is inline buttons."""

    waiting_for_time = State()

class CustomPostState(StatesGroup):
    """Waiting for the admin to send the post itself."""

    waiting_for_post = State()