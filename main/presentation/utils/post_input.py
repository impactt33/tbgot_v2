"""Turning the message (or messages) the admin sent into a CustomPayload.

Kept apart from the handler so the rules can be read — and tested — without a
Dispatcher: what we accept, what we refuse, and how long is too long.

An album arrives as several updates rather than one message, so everything here
takes a list. A plain post is simply a list of one.
"""
from aiogram.types import Message

from main.domain.entities import CustomPayload
from main.presentation.errors import (
    PostInputEmptyError,
    PostInputTooLongError,
    PostInputTooManyPhotosError,
    PostInputUnsupportedError,
)

# Telegram's own limits. Text carried as a photo caption gets a quarter of the
# room a plain message gets, so the cap depends on whether photos came along.
CAPTION_LIMIT = 1024
TEXT_LIMIT = 4096
ALBUM_LIMIT = 10


def tg_length(text: str) -> int:
    """Length the way Telegram counts it: UTF-16 code units, not characters.

    Anything outside the BMP — most emoji — takes two units, so an ad post full
    of them runs out of caption sooner than len() suggests.
    """
    return len(text.encode("utf-16-le")) // 2


def build_custom_payload(parts: list[Message]) -> CustomPayload:
    """Messages -> payload, or a presentation error explaining what to fix.

    `parts` is one message for a plain post, or every message of an album in the
    order they should appear.
    """
    if not parts:
        raise PostInputEmptyError()

    photo_file_ids: list[str] = []

    for part in parts:
        if part.photo:
            # PhotoSize list runs smallest to largest; the last is the original.
            photo_file_ids.append(part.photo[-1].file_id)
        elif len(parts) > 1 or part.text is None:
            # Inside an album anything that is not a photo has nowhere to go;
            # on its own, only plain text is supported.
            raise PostInputUnsupportedError(part.content_type)

    if len(photo_file_ids) > ALBUM_LIMIT:
        raise PostInputTooManyPhotosError(len(photo_file_ids), ALBUM_LIMIT)

    # Exactly one part of an album carries the caption, and it need not be the
    # one that arrived first.
    captioned = next((p for p in parts if (p.caption or p.text)), None)

    # html_text renders text and caption alike, so formatting survives either
    # way; on a photo with no caption it comes back empty.
    html_text = captioned.html_text if captioned is not None else ""
    visible = (captioned.caption or captioned.text or "") if captioned is not None else ""

    if not photo_file_ids and not visible.strip():
        raise PostInputEmptyError()

    limit = CAPTION_LIMIT if photo_file_ids else TEXT_LIMIT
    length = tg_length(visible)

    if length > limit:
        raise PostInputTooLongError(length, limit, with_photo=bool(photo_file_ids))

    return CustomPayload(html_text=html_text, photo_file_ids=photo_file_ids)