import logging

from aiogram import Bot
from aiogram.enums import ParseMode, PollType
from aiogram.exceptions import TelegramAPIError
from aiogram.types import InputPollOption, LinkPreviewOptions
from aiogram.utils.text_decorations import html_decoration as fmt

from main.domain.clients import Publisher
from main.domain.entities import MaterialPayload, PostEntity, QuizPayload
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
                case PostType.MATERIAL:
                    return await self._publish_material(post, chat_id)
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

    async def _publish_material(self, post: PostEntity, chat_id: int) -> int:
        payload = MaterialPayload.model_validate(post.payload)
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