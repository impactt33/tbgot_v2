from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat

choose_channel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(
            text="Add Channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=1,
                chat_is_channel=True,
                bot_is_member=True,
                request_title=True,
                request_username=True
            )
        )
    ]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Click the button below.",
)