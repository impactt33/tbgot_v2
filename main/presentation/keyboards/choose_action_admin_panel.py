from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

choose_action_admin_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[
        InlineKeyboardButton(
            text="Provide rights for users",
            callback_data="admin_action_provide_rights"
        ),
        InlineKeyboardButton(
            text="Add channels",
            callback_data="admin_action_add_channels"
        )
    ]]
)