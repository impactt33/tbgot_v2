from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from main.domain.enums import UserRole
from main.presentation.callbacks import MenuAction, MenuCB

def main_menu_keyboard(role: UserRole) -> InlineKeyboardMarkup:
    """Root menu. Management section is admin-only."""
    builder = InlineKeyboardBuilder()

    builder.button(text="Create post", callback_data=MenuCB(action=MenuAction.NEW_POST))
    builder.button(
        text="Scheduled posts",
        callback_data=MenuCB(action=MenuAction.SCHEDULED)
    )

    if role is UserRole.ADMIN:
        builder.button(
            text="Bot management",
            callback_data=MenuCB(action=MenuAction.ADMIN)
        )

    builder.adjust(1)
    return builder.as_markup()

def admin_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(
        text="Provide rights",
        callback_data=MenuCB(action=MenuAction.PROVIDE_RIGHTS)
    )
    builder.button(
        text="Add channel",
        callback_data=MenuCB(action=MenuAction.ADD_CHANNEL)
    )
    builder.button(
        text="Remove channel",
        callback_data=MenuCB(action=MenuAction.REMOVE_CHANNEL)
    )
    builder.button(
        text="Back",
        callback_data=MenuCB(action=MenuAction.ROOT)
    )

    builder.adjust(1)
    return builder.as_markup()

def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="Back", callback_data=MenuCB(action=MenuAction.ROOT))
    return builder.as_markup()