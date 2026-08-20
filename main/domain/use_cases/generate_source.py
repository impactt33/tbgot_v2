import logging

from pydantic import BaseModel, Field

from main.domain.clients import AIClient, WebSearchClient
from main.domain.entities import PostCreateEntity, PostEntity
from main.domain.enums import PostType
from main.domain.errors import NoMaterialFoundError
from main.domain.services import PostService
from main.domain.use_cases.ai_guard import unwrap_ai

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Ты — редактор телеграм-канала о графическом и продуктовом дизайне. "
    "Пишешь по-русски, кратко и по делу, без канцелярита и восклицательных знаков."
)

_QUERY_PROMPT = """Предложи поисковый запрос, чтобы найти один полезный онлайн-ресурс
для дизайнера: инструмент, гайд, подборку или статью.

Запрос — на английском, 3-6 слов, как его набрал бы человек в поиске."""

_POST_PROMPT = """Напиши короткий пост для канала о дизайне про этот ресурс.

Название: {title}
Ссылка: {url}
Описание из выдачи: {snippet}

Расскажи, что это и кому пригодится. Ссылку в текст не вставляй — она будет отдельно."""


class SearchQueryDraft(BaseModel):
    query: str = Field(max_length=100, description="Поисковый запрос на английском")


class MaterialDraft(BaseModel):
    title: str = Field(max_length=100, description="Заголовок поста, до 8 слов")
    text: str = Field(
        max_length=700,
        description="Текст поста, 2-4 предложения. Без ссылок и хештегов",
    )


class GenerateMaterialPostRequest(BaseModel):
    channel_id: int


class GenerateMaterialPostUseCase:
    def __init__(
        self,
        ai_client: AIClient,
        web_search: WebSearchClient,
        post_service: PostService,
    ) -> None:
        self.ai_client = ai_client
        self.web_search = web_search
        self.post_service = post_service

    async def __call__(self, request: GenerateMaterialPostRequest) -> PostEntity:
        query = unwrap_ai(
            await self.ai_client.ask_structured(
                _QUERY_PROMPT, SearchQueryDraft, system=_SYSTEM
            )
        )
        logger.info("Finding material by request %r", query.query)

        results = await self.web_search.search(query.query, limit=5)
        if not results:
            raise NoMaterialFoundError(query=query.query)

        source = results[0]
        draft = unwrap_ai(
            await self.ai_client.ask_structured(
                _POST_PROMPT.format(
                    title=source.title, url=source.url, snippet=source.snippet
                ),
                MaterialDraft,
                system=_SYSTEM,
            )
        )

        return await self.post_service.create_draft(
            PostCreateEntity(
                channel_id=request.channel_id,
                post_type=PostType.MATERIAL,
                payload={
                    "title": draft.title,
                    "text": draft.text,
                    "url": source.url,
                    "source_title": source.title,
                },
            )
        )