from enum import Enum

from aiogram.filters.callback_data import CallbackData


class SchedulePreset(str, Enum):
    IN_1H = "in_1h"
    IN_2H = "in_2h"
    IN_3H = "in_3h"
    TOMORROW_MORNING = "morning"
    TOMORROW_EVENING = "evening"
    MANUAL = "manual"

class ScheduleCB(CallbackData, prefix="nps2"):
    """Time picked for a draft.

    Carries the same message ids as DraftCB so the handler can clean up the
    preview and go back to the draft buttons without touching any FSM states.

    Prefix bumped to "nps2" alongside DraftCB's: adding a field makes old
    callback data unparseable, so buttons left in the chat must stop matching
    rather than blow up in the filter.
    """

    preset: SchedulePreset
    post_id: int
    preview_id: int # id of the message in chat where it was published for preview.
    preview_count: int = 1 # how many messages that preview took: an album is several.