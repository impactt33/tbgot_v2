import logging

from aiogram import Bot
from aiogram.enums import ParseMode, PollType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputPollOption, LinkPreviewOptions, MediaUnion, InputMediaPhoto
from aiogram.utils.text_decorations import html_decoration as fmt

from main.domain.clients import Publisher
from main.domain.entities import SourcePayload, PostEntity, QuizPayload, CustomPayload
from main.domain.enums import PostType
from main.domain.errors import PublishError, UnsupportedPostTypeError

logger = logging.getLogger(__name__)


class TelegramPublisher(Publisher):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def publish(self, post: PostEntity, chat_id: int) -> int:
        try:
            match post.post_type:
                case PostType.QUIZ:
                    return await self._publish_quiz(post, chat_id)
                case PostType.SOURCES:
                    return await self._publish_source(post, chat_id)
                case PostType.CUSTOM:
                    return await self._publish_custom(post, chat_id)
                case _:
                    raise UnsupportedPostTypeError(post.post_type)
        except TelegramAPIError as exc:
            logger.exception("Publish of post %s to %s failed", post.id, chat_id)
            raise PublishError(post.id, exc) from exc

    async def _publish_quiz(self, post: PostEntity, chat_id: int) -> int:
        payload = QuizPayload.model_validate(post.payload)
        message = await self.bot.send_poll(
            chat_id=chat_id,
            question=payload.question,
            options=[InputPollOption(text=o) for o in payload.options],
            type=PollType.QUIZ,
            correct_option_id=payload.correct_index,
            explanation=payload.explanation,
            is_anonymous=True
        )
        return message.message_id

    async def _publish_source(self, post: PostEntity, chat_id: int) -> int:
        payload = SourcePayload.model_validate(post.payload)
        text = f"{fmt.quote(payload.title)}\n\n{fmt.quote(payload.text)}"
        message = await self.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            link_preview_options=LinkPreviewOptions(
                url=payload.url,
                prefer_large_media=True,
                show_above_text=True
            )
        )
        return message.message_id

    async def _publish_custom(self, post: PostEntity, chat_id: int) -> int:
        """Send back what the admin handed us, formatting and photo included.

        The photo travels as a file_id, not as bytes: Telegram already holds the
        file, and the Bot API takes a file_id string wherever it takes an upload.
        That keeps us clear of the 20 MB download limit entirely — we never
        fetch the image.

        The catch is that a file_id is only valid for the bot that received it.
        If the token is ever regenerated, previously stored ids stop resolving
        and scheduled posts will fail to publish. The durable variant is to
        forward the photo into a private storage channel once, keep that
        message id, and publish with copy_message.
        """

        payload = CustomPayload.model_validate(post.payload)
        photos = payload.photo_file_ids

        if not photos:
            message = await self.bot.send_message(
                chat_id=chat_id,
                text=payload.html_text,
                parse_mode=ParseMode.HTML,
            )
            return message.message_id

        if len(photos) == 1:
            message = await self.bot.send_photo(
                chat_id=chat_id,
                photo=photos[0],
                caption=payload.html_text or None,
                parse_mode=ParseMode.HTML,
            )
            return message.message_id

        # Only the first item may carry the caption; Telegram shows it under
        # the whole album.
        # Annotated as MediaUnion, the type send_media_group takes: a plain
        # list[InputMediaPhoto] would not satisfy it, because list is invariant.
        media: list[MediaUnion] = [
            InputMediaPhoto(
                media=file_id,
                caption=payload.html_text or None if index == 0 else None,
                parse_mode=ParseMode.HTML if index == 0 else None,
            )
            for index, file_id in enumerate(photos)
        ]
        messages = await self.bot.send_media_group(chat_id=chat_id, media=media)

        return messages[0].message_id