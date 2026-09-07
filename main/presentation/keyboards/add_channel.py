from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonRequestChat

# Two different pickers, so a button left over in the chat from the previous
# step cannot feed a channel into the wrong one.
POSTING_REQUEST_ID = 1
STORAGE_REQUEST_ID = 2

choose_channel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(
            text="Add Channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=POSTING_REQUEST_ID,
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

choose_storage_keyboard = ReplyKeyboardMarkup(
    keyboard=[[
        KeyboardButton(
            text="Pick storage channel",
            request_chat=KeyboardButtonRequestChat(
                request_id=STORAGE_REQUEST_ID,
                chat_is_channel=True,
                bot_is_member=True,
                # A material link points at a post in the storage channel, and
                # t.me/c/<id>/<msg> only opens for its members. Telegram hides
                # channels without a username from the picker, so the admin
                # cannot pick an unusable one in the first place.
                chat_has_username=True,
                request_title=True,
                request_username=True
            )
        )
    ]],
    resize_keyboard=True,
    one_time_keyboard=True,
    input_field_placeholder="Click the button below.",
)
