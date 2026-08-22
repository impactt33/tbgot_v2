from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from main.domain.enums import UserRole

ROLE_CALLBACK_PREFIX = "provide_role_"

roles_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text=UserRole.USER.value,
                callback_data=f"{ROLE_CALLBACK_PREFIX}{UserRole.USER.value}",
            ),
            InlineKeyboardButton(
                text=UserRole.ADMIN.value,
                callback_data=f"{ROLE_CALLBACK_PREFIX}{UserRole.ADMIN.value}",
            )
        ]
    ]
)