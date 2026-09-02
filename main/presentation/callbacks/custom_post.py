from aiogram.filters.callback_data import CallbackData


class CustomChannelCB(CallbackData, prefix="cpc"):
    """Channel picked for a hand-written post.

    Separate from ChannelCB on purpose: that one leads to the post-type screen,
    while this one goes straight to waiting for the admin's message.
    """

    channel_id: int