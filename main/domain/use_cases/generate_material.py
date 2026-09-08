"""Turning a forwarded material into a post: PostType.MATERIAL.

The admin sends the pictures with whatever description came along, then the
file itself. Everything below happens after that, and the order is not free:

- the text mentions the link, and the link only exists once the file is in our
  storage channel, so generation comes last;
- the file is claimed in the database right after it is uploaded, so the same
  file forwarded twice gets a refusal instead of a second copy.
"""
import logging

from pydantic import BaseModel, Field

from main.domain.clients import AIClient, MaterialStorage, MediaDownloader
from main.domain.entities import (
    AddMaterialEntity,
    MaterialEntity,
    MaterialPayload,
    PostCreateEntity,
    PostEntity,
    PostTemplateEntity,
)
from main.domain.enums import PostType
from main.domain.errors import (
    InvalidMaterialDraftError,
    MaterialAlreadyUsedError,
    StorageChannelNotSetError,
    UnsupportedPostTypeError,
)
from main.domain.services import (
    ChannelService,
    MaterialService,
    PostService,
    PostTemplateService,
)
from main.domain.use_cases.ai_guard import unwrap_ai
from main.domain.use_cases.html_guard import (
    ALLOWED_TAGS_HINT,
    check_telegram_html,
    fallback_plain,
    strip_tags,
    visible_length,
)

logger = logging.getLogger(__name__)

# The whole post travels as a photo caption, and Telegram allows 1024 UTF-16
# units there - a quarter of what a plain message gets. Title, text and link
# share that budget.
_CAPTION_LIMIT = 1024
_TITLE_LIMIT = 100
_DESCRIPTION_LIMIT = 700

# The model gets the first few pictures, not all ten: past three they stop
# adding anything a description could use, and each one costs.
_PROMPT_IMAGES = 3

_SYSTEM = (
    "Ты — редактор телеграм-канала о графическом и продуктовом дизайне. "
    "Пишешь по-русски, кратко и по делу, без канцелярита и восклицательных знаков."
)

_POST_PROMPT = """Напиши пост о материале для этого канала.

Вот несколько постов канала. Воспроизведи их манеру: тон, длину, структуру,
оформление. Содержание из них не бери — это образцы формы, а не источник фактов.

{examples}
{instruction}
Материал — то, что на картинках.
{about}
Требования к ответу:
- title: заголовок обычным текстом, без разметки, до {title_limit} символов;
- description: текст поста в разметке Telegram HTML, как в примерах.
  Разрешены только теги {allowed_tags}.
  Символы < > & вне тегов пиши как &lt; &gt; &amp;.
  Не длиннее {description_limit} символов видимого текста;
- ссылку на материал не вставляй — она будет добавлена отдельной строкой."""

_WITH_DESCRIPTION = """Автор материала описал его так. Факты бери отсюда, но перепиши под формат канала:

{description}
"""

_WITHOUT_DESCRIPTION = "Описания к нему не прислали — опиши материал по картинкам.\n"

_INSTRUCTION_BLOCK = """
Отдельные требования владельца канала:
{instruction}
"""

_REWRITE_BLOCK = """
Такой пост уже был написан. Напиши другой: тот же материал, но другие слова и
другой заход.

Прошлый заголовок: {title}
Прошлый текст: {description}
"""

_REPAIR_PROMPT = """Разметка в поле description неверна:
{problems}

Заголовок: {title}
Текст: {description}

Верни тот же пост — тот же заголовок и тот же смысл — с исправленной разметкой.
Разрешены только теги {allowed_tags}. Символы < > & вне тегов пиши как
&lt; &gt; &amp;."""


class MaterialDraft(BaseModel):
    title: str = Field(
        max_length=_TITLE_LIMIT,
        description="Заголовок поста обычным текстом, без разметки",
    )
    # Deliberately roomier than _DESCRIPTION_LIMIT: this caps the raw string,
    # tags included, while the limit that matters is on the visible text. A
    # schema tight enough for the visible text would reject well-formatted
    # answers, and rejection here surfaces as an unparseable response.
    description: str = Field(
        max_length=1500,
        description="Текст поста в разметке Telegram HTML",
    )


class CreateMaterialPostRequest(BaseModel):
    channel_id: int
    photo_file_ids: list[str]
    description: str = ""
    document_file_id: str
    document_file_unique_id: str
    source_chat_id: int | None = None
    source_username: str | None = None
    source_message_id: int | None = None


def _build_prompt(
    template: PostTemplateEntity,
    description: str,
    previous: MaterialDraft | None,
) -> str:
    """Examples first, then the owner's instruction, then this material.

    The instruction comes after the examples on purpose: examples show, the
    instruction corrects, and what sits closer to the end weighs more.
    """
    about = (
        _WITH_DESCRIPTION.format(description=description)
        if description.strip()
        else _WITHOUT_DESCRIPTION
    )

    if previous is not None:
        about += _REWRITE_BLOCK.format(
            title=previous.title, description=previous.description
        )

    return _POST_PROMPT.format(
        examples="\n\n---\n\n".join(template.examples),
        instruction=(
            _INSTRUCTION_BLOCK.format(instruction=template.instruction)
            if template.instruction
            else ""
        ),
        about=about,
        title_limit=_TITLE_LIMIT,
        description_limit=_DESCRIPTION_LIMIT,
        allowed_tags=ALLOWED_TAGS_HINT,
    )


async def _generate_text(
    ai_client: AIClient,
    media_downloader: MediaDownloader,
    template: PostTemplateEntity,
    photo_file_ids: list[str],
    description: str,
    previous: MaterialDraft | None = None,
) -> MaterialDraft:
    """Ask for the post, then make sure its markup is markup Telegram takes.

    Shared by writing a post and by rewriting one, which differ only in the
    "here is the previous attempt" block.
    """
    images = await media_downloader.download_many(photo_file_ids[:_PROMPT_IMAGES])

    draft = unwrap_ai(
        await ai_client.ask_structured(
            _build_prompt(template, description, previous),
            MaterialDraft,
            system=_SYSTEM,
            images=images,
        )
    )

    problems = check_telegram_html(draft.description)

    if not problems:
        return draft

    # One repair round, not a loop. The problems go along verbatim: a model
    # fixes a named mistake far better than it re-rolls the whole post.
    logger.info("Model returned unusable markup: %s", problems)

    repaired = unwrap_ai(
        await ai_client.ask_structured(
            _REPAIR_PROMPT.format(
                problems="\n".join(f"- {problem}" for problem in problems),
                title=draft.title,
                description=draft.description,
                allowed_tags=ALLOWED_TAGS_HINT,
            ),
            MaterialDraft,
            system=_SYSTEM,
        )
    )

    if not check_telegram_html(repaired.description):
        return repaired

    # Formatting is worth less than a post the admin can publish. The words
    # survive, the markup goes, and Regenerate is one tap away.
    logger.warning("Markup still broken after a repair round, dropping it")

    return MaterialDraft(
        title=repaired.title,
        description=fallback_plain(repaired.description),
    )


def _validate(payload: MaterialPayload) -> None:
    """The finished post has to fit a caption, and the link is part of it."""
    if not payload.title.strip():
        raise InvalidMaterialDraftError("Empty title.")

    if not strip_tags(payload.description).strip():
        raise InvalidMaterialDraftError("Description has no text in it.")

    # Counted the way Telegram counts a caption: visible text only, UTF-16
    # units, plus the four units of the two blank lines holding the parts apart.
    length = (
        visible_length(payload.title)
        + visible_length(payload.description)
        + visible_length(payload.url)
        + 4
    )

    if length > _CAPTION_LIMIT:
        raise InvalidMaterialDraftError(
            f"Post is {length} units long, a caption allows {_CAPTION_LIMIT}."
        )


class CreateMaterialPostUseCase:
    def __init__(
        self,
        ai_client: AIClient,
        media_downloader: MediaDownloader,
        material_storage: MaterialStorage,
        channel_service: ChannelService,
        material_service: MaterialService,
        post_service: PostService,
        template_service: PostTemplateService,
    ) -> None:
        self.ai_client = ai_client
        self.media_downloader = media_downloader
        self.material_storage = material_storage
        self.channel_service = channel_service
        self.material_service = material_service
        self.post_service = post_service
        self.template_service = template_service

    async def __call__(self, request: CreateMaterialPostRequest) -> PostEntity:
        channel = await self.channel_service.get_channel_by_id(request.channel_id)

        if channel.storage_channel_id is None:
            raise StorageChannelNotSetError(channel.channel_id)

        # Raises when the channel has fewer than three examples. Cheap and local,
        # so it runs before anything reaches out to Telegram.
        template = await self.template_service.get_for_generation(
            request.channel_id, PostType.MATERIAL
        )

        # Binding a storage channel kept only its id, so the username has to be
        # asked for - and asking is also how a storage channel that has been
        # deleted, or that threw the bot out, gets noticed before the file is
        # uploaded rather than after the post is assembled.
        storage_username = await self.material_storage.resolve(channel.storage_channel_id)

        material = await self._claim(request, channel.storage_channel_id)

        draft = await _generate_text(
            self.ai_client,
            self.media_downloader,
            template,
            request.photo_file_ids,
            request.description,
        )

        payload = MaterialPayload(
            title=draft.title,
            description=draft.description,
            storage_chat_id=material.storage_chat_id,
            storage_message_id=material.storage_message_id,
            storage_username=storage_username,
            photo_file_ids=request.photo_file_ids,
            material_id=material.id,
        )
        _validate(payload)

        post = await self.post_service.create_draft(
            PostCreateEntity(
                channel_id=request.channel_id,
                post_type=PostType.MATERIAL,
                payload=payload.model_dump(),
            )
        )
        await self.material_service.mark_used(material.id, post.id)
        return post

    async def _claim(
        self, request: CreateMaterialPostRequest, storage_chat_id: int
    ) -> MaterialEntity:
        """The file, in storage and claimed in the database.

        A row left over from a generation that died halfway is reused rather
        than refused. Refusing would be a dead end: the file is already burned
        into uq_channel_material_file, so re-sending it could never work, and
        the copy in storage is perfectly good. Same reasoning as find_unused in
        GenerateSourcePostUseCase.
        """
        existing = await self.material_service.find_by_file(
            request.channel_id, request.document_file_unique_id
        )

        if existing is not None:
            if existing.used_in_post is not None:
                raise MaterialAlreadyUsedError(request.document_file_unique_id)

            logger.info("Reusing material %s, left unused by an earlier attempt", existing.id)
            return existing

        message_id = await self.material_storage.store(
            request.document_file_id, storage_chat_id
        )

        try:
            return await self.material_service.add_material(
                AddMaterialEntity(
                    channel_id=request.channel_id,
                    file_unique_id=request.document_file_unique_id,
                    source_chat_id=request.source_chat_id,
                    source_username=request.source_username,
                    source_message_id=request.source_message_id,
                    storage_chat_id=storage_chat_id,
                    storage_message_id=message_id,
                )
            )
        except MaterialAlreadyUsedError:
            # Two forwards of the same file racing each other: the unique index
            # let exactly one row in, and the copy this call just uploaded has
            # nothing pointing at it. Take it back out instead of leaving it.
            logger.info(
                "Lost the race for %s, removing the copy just uploaded",
                request.document_file_unique_id
            )
            await self.material_storage.remove(storage_chat_id, message_id)
            raise


class RegenerateMaterialTextUseCase:
    """Rewrite the text of a material draft, keeping the material itself.

    Nothing is uploaded and nothing is claimed again: the file stays in storage,
    the materials row stays bound to this post, only the payload changes. That
    is why this updates the draft rather than deleting and recreating it, the
    way QUIZ and SOURCES regenerate - there the whole subject changes, here only
    the wording does.

    The pictures are downloaded again and sent along. They are what the text is
    about, and without them a rewrite can only shuffle the previous wording,
    never correct something it got wrong.
    """

    def __init__(
        self,
        ai_client: AIClient,
        media_downloader: MediaDownloader,
        post_service: PostService,
        template_service: PostTemplateService,
    ) -> None:
        self.ai_client = ai_client
        self.media_downloader = media_downloader
        self.post_service = post_service
        self.template_service = template_service

    async def __call__(self, post_id: int) -> PostEntity:
        post = await self.post_service.get_by_id(post_id)

        if post.post_type is not PostType.MATERIAL:
            raise UnsupportedPostTypeError(post.post_type)

        payload = MaterialPayload.model_validate(post.payload)
        template = await self.template_service.get_for_generation(
            post.channel_id, PostType.MATERIAL
        )

        draft = await _generate_text(
            self.ai_client,
            self.media_downloader,
            template,
            payload.photo_file_ids,
            description="",
            previous=MaterialDraft(title=payload.title, description=payload.description),
        )

        rewritten = payload.model_copy(
            update={"title": draft.title, "description": draft.description}
        )
        _validate(rewritten)

        return await self.post_service.update_draft_payload(
            post_id, rewritten.model_dump()
        )
