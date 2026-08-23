import logging

from pydantic import BaseModel, Field

from main.domain.clients import AIClient, SearchResult, WebSearchClient
from main.domain.entities import AddSourceEntity, PostCreateEntity, PostEntity, SourceEntity
from main.domain.enums import PostType
from main.domain.errors import InvalidSourceDraftError, NoSourceFoundError
from main.domain.services import PostService, SourceService
from main.domain.use_cases.ai_guard import unwrap_ai

logger = logging.getLogger(__name__)

_MAX_SOURCE_ATTEMPTS = 3
_SEARCH_LIMIT = 5

_SYSTEM = (
    "Ты — редактор телеграм-канала о графическом и продуктовом дизайне. "
    "Пишешь по-русски, кратко и по делу, без канцелярита и восклицательных знаков."
)

_QUERY_PROMPT = """Предложи поисковый запрос, чтобы найти один полезный онлайн-ресурс
для дизайнера: инструмент, гайд, подборку или статью.

Ресурсы, о которых уже писали — про них не надо:
{used_sources}

Запрос — на английском, 3-6 слов, как его набрал бы человек в поиске."""

_POST_PROMPT = """Напиши короткий пост для канала о дизайне про этот ресурс.

Название: {title}
Ссылка: {url}
Описание из выдачи: {snippet}

Расскажи, что это и кому пригодится. Ссылку в текст не вставляй — она будет отдельно."""

_NO_SNIPPET = "(описания нет)"


class SearchQueryDraft(BaseModel):
    query: str = Field(max_length=100, description="Поисковый запрос на английском")


class SourceDraft(BaseModel):
    title: str = Field(max_length=100, description="Заголовок поста, до 8 слов")
    text: str = Field(
        max_length=700,
        description="Текст поста, 2-4 предложения. Без ссылок и хештегов",
    )


class GenerateSourcePostRequest(BaseModel):
    channel_id: int
    source: SourceEntity | None = None


class GenerateSourcePostUseCase:
    def __init__(
        self,
        ai_client: AIClient,
        web_search: WebSearchClient,
        post_service: PostService,
        source_service: SourceService,
    ) -> None:
        self.ai_client = ai_client
        self.web_search = web_search
        self.post_service = post_service
        self.source_service = source_service

    async def __call__(self, request: GenerateSourcePostRequest) -> PostEntity:
        if request.source is None:
            source, snippet = await self._pick_new_source(request.channel_id)
        else:
            source, snippet = request.source, _NO_SNIPPET

        logger.info("Source for channel %s: %s", request.channel_id, source.url)

        draft = unwrap_ai(
            await self.ai_client.ask_structured(
                _POST_PROMPT.format(
                    title=source.name, url=source.url, snippet=snippet
                ),
                SourceDraft,
                system=_SYSTEM,
            )
        )

        self._validate(draft)

        post = await self.post_service.create_draft(
            PostCreateEntity(
                channel_id=request.channel_id,
                post_type=PostType.SOURCES,
                payload={
                    "title": draft.title,
                    "text": draft.text,
                    "url": source.url,
                    "source_title": source.name or source.url,
                    "source_id": source.id,
                },
            )
        )
        await self.source_service.mark_used(source.id, post.id)
        return post

    async def _pick_new_source(self, channel_id: int) -> tuple[SourceEntity, str]:
        """A source nobody wrote about yet, plus the snippet the search gave us.

        A row left over from a generation that died halfway is reused first: the
        url is already burned in uq_channel_source_url, so nothing else can take it.
        """
        leftover = await self.source_service.find_unused(channel_id, limit=1)
        if leftover:
            return leftover[0], _NO_SNIPPET

        used = await self.source_service.get_source_urls(channel_id)
        used_block = "\n".join(f"- {u}" for u in used) or "(пока ни одного)"

        for attempt in range(1, _MAX_SOURCE_ATTEMPTS + 1):
            query = unwrap_ai(
                await self.ai_client.ask_structured(
                    _QUERY_PROMPT.format(used_sources=used_block),
                    SearchQueryDraft,
                    system=_SYSTEM,
                )
            )
            logger.info("Attempt %s: searching for %r", attempt, query.query)

            results = await self.web_search.search(query.query, limit=_SEARCH_LIMIT)

            claimed = await self._claim_first_free(channel_id, results)
            if claimed is not None:
                return claimed

            logger.info("Attempt %s: every result was already used", attempt)

        raise NoSourceFoundError(channel_id=channel_id)

    async def _claim_first_free(
        self, channel_id: int, results: list[SearchResult]
    ) -> tuple[SourceEntity, str] | None:
        """Insert wins the race: add_source returns None for a url already taken."""
        for result in results:
            source = await self.source_service.add_source(
                AddSourceEntity(
                    channel_id=channel_id,
                    name=result.title,
                    url=result.url,
                )
            )
            if source is not None:
                return source, result.snippet or _NO_SNIPPET

        return None

    @staticmethod
    def _validate(draft: SourceDraft) -> None:
        if not draft.title.strip():
            raise InvalidSourceDraftError("Empty title.")
        if not draft.text.strip():
            raise InvalidSourceDraftError("Empty text.")