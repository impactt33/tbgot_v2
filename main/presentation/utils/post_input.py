"""Turning the message (or messages) the admin sent into a CustomPayload.

Kept apart from the handler so the rules can be read — and tested — without a
Dispatcher: what we accept, what we refuse, and how long is too long.

An album arrives as several updates rather than one message, so everything here
takes a list. A plain post is simply a list of one.
"""
from aiogram.types import Message, MessageOriginChannel, MessageOriginChat
from pydantic import BaseModel

from main.domain.entities import CustomPayload
from main.presentation.errors import (
    PostInputEmptyError,
    PostInputNoPhotoError,
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

class MaterialInput(BaseModel):
    """Pictures and the words that came with them, before the file shows up.

    The description is plain text, not html_text: nobody publishes it. It goes
    to the model as facts about the material, and markup there would only be
    noise.
    """

    photo_file_ids: list[str]
    description: str


class ForwardSource(BaseModel):
    """Where a forwarded message came from, as far as Telegram will say.

    Every field is optional because forward_origin is a union of four, and only
    one of them carries a message id. A channel that hides forwards produces
    MessageOriginHiddenUser, which has no chat at all.
    """

    chat_id: int | None = None
    username: str | None = None
    message_id: int | None = None


def build_material_input(parts: list[Message]) -> MaterialInput:
    """The pictures half of a material post: photos plus their caption.

    `parts` is one message for a single photo, or every message of an album in
    the order they should appear - same shape as build_custom_payload takes.
    """
    if not parts:
        raise PostInputEmptyError()

    photo_file_ids: list[str] = []

    for part in parts:
        if part.photo:
            # PhotoSize list runs smallest to largest; the last is the original.
            # The same file_id is republished later, so the biggest is the one
            # worth keeping.
            photo_file_ids.append(part.photo[-1].file_id)
        elif part.text is None:
            # A sticker, a video, a document: nothing that could be a picture.
            # Plain text falls through to the check below, which has something
            # more useful to say about it.
            raise PostInputUnsupportedError(part.content_type)

    if not photo_file_ids:
        raise PostInputNoPhotoError()

    if len(photo_file_ids) > ALBUM_LIMIT:
        raise PostInputTooManyPhotosError(len(photo_file_ids), ALBUM_LIMIT)

    # Exactly one part of an album carries the caption, and it need not be the
    # one that arrived first. No length check: a caption cannot exceed 1024 in
    # the first place, and this text is never published.
    captioned = next((part for part in parts if (part.caption or part.text)), None)
    description = (captioned.caption or captioned.text or "") if captioned else ""

    return MaterialInput(photo_file_ids=photo_file_ids, description=description)


def read_forward_origin(message: Message) -> ForwardSource:
    """Provenance of a forwarded message, empty when there is none to have.

    Only a channel gives all three: MessageOriginChannel is the sole member of
    the union with a message_id, so it is the only origin a link could ever be
    built from. A forward from a group gives the chat but no message, and a
    forward from a person gives neither.
    """
    origin = message.forward_origin

    if isinstance(origin, MessageOriginChannel):
        return ForwardSource(
            chat_id=origin.chat.id,
            username=origin.chat.username,
            message_id=origin.message_id,
        )

    if isinstance(origin, MessageOriginChat):
        return ForwardSource(
            chat_id=origin.sender_chat.id,
            username=origin.sender_chat.username,
        )

    return ForwardSource()
