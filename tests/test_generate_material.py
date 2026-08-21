import pytest

from main.domain.clients import SearchResult
from main.domain.enums import AIFailure, PostType
from main.domain.errors import AIClientRejected, NoMaterialFoundError
from main.domain.use_cases.generate_source import (
    GenerateMaterialPostRequest,
    GenerateMaterialPostUseCase,
    MaterialDraft,
    SearchQueryDraft,
)

from tests.conftest import FakeAIClient, FakeWebSearch

pytestmark = pytest.mark.asyncio

RESULTS = [
    SearchResult(title="Type Scale", url="https://typescale.com", snippet="Модульная шкала"),
    SearchResult(title="Второй", url="https://other.com", snippet="..."),
]
DRAFT = MaterialDraft(title="Считаем шкалу типографики", text="Удобный калькулятор.")


async def test_happy_path(posts):
    ai = FakeAIClient([SearchQueryDraft(query="typography scale tool"), DRAFT])
    search = FakeWebSearch(RESULTS)

    post = await GenerateMaterialPostUseCase(ai, search, posts)(
        GenerateMaterialPostRequest(channel_id=-100123)
    )

    assert post.post_type is PostType.MATERIAL
    assert post.payload["url"] == "https://typescale.com"      # взят первый результат
    assert post.payload["source_title"] == "Type Scale"
    assert post.payload["text"] == DRAFT.text
    assert search.queries == ["typography scale tool"]


async def test_found_resource_goes_into_second_prompt(posts):
    ai = FakeAIClient([SearchQueryDraft(query="q"), DRAFT])

    await GenerateMaterialPostUseCase(ai, FakeWebSearch(RESULTS), posts)(
        GenerateMaterialPostRequest(channel_id=1)
    )

    post_prompt = ai.calls[1][1]
    assert "Type Scale" in post_prompt
    assert "https://typescale.com" in post_prompt
    assert "Модульная шкала" in post_prompt


async def test_empty_search_results(posts):
    ai = FakeAIClient([SearchQueryDraft(query="ничего не найдётся")])

    with pytest.raises(NoMaterialFoundError):
        await GenerateMaterialPostUseCase(ai, FakeWebSearch([]), posts)(
            GenerateMaterialPostRequest(channel_id=1)
        )

    assert posts.drafts == []


async def test_ai_failure_on_second_call(posts):
    ai = FakeAIClient([SearchQueryDraft(query="q"), AIFailure.REJECTED])

    with pytest.raises(AIClientRejected):
        await GenerateMaterialPostUseCase(ai, FakeWebSearch(RESULTS), posts)(
            GenerateMaterialPostRequest(channel_id=1)
        )

    assert posts.drafts == []      # поиск отработал, но черновик не создан
