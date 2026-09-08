from aiogram.fsm.state import StatesGroup, State


class CreatePostState(StatesGroup):
    """Only free-text input needs a state: everything else is inline buttons."""

    waiting_for_time = State()

class CustomPostState(StatesGroup):
    """Waiting for the admin to send the post itself."""

    waiting_for_post = State()

class MaterialPostState(StatesGroup):
    """Pictures first, the file second, and that order is not a preference.

    The generated text mentions the link, and the link only exists once the
    file is in the storage channel - so there is nothing to generate until the
    file has arrived.
    """

    waiting_for_post = State()
    waiting_for_document = State()