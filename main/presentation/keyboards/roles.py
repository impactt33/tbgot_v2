from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from main.domain.enums import UserRole

roles_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=UserRole.USER.value,
                callback_data="provide_role_user",
            ),
            InlineKeyboardButton(
                text=UserRole.ADMIN.value,
                callback_data="provide_role_admin",
            )
        ]
    ]
)