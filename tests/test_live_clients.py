"""Живые проверки реальных API. По умолчанию пропускаются.

Запуск:  pytest -m live tests/test_live_clients.py -s
Нужны настоящие GEMINI_API_KEY и SERPER_API_KEY в app/.env
"""
import pytest

from main.domain.enums import AIFailure
from main.domain.use_cases.generate_quiz import QuizDraft, TopicDraft

pytestmark = [pytest.mark.live, pytest.mark.asyncio]


@pytest.fixture(scope="module")
def settings():
    from core.config import settings as s
    return s


@pytest.fixture
def ai_client(settings):
    from main.data.clients_impl.ai.gemini_ai_client import GeminiAIClient
    return GeminiAIClient(api_key=settings.GEMINI_API_KEY)


async def test_gemini_structured_returns_valid_schema(ai_client):
    """Проверяет, что response_schema реально работает и ответ ложится в модель."""
    result = await ai_client.ask_structured(
        "Составь один вопрос для квиза по теме «кернинг».",
        QuizDraft,
        system="Ты редактор канала о дизайне. Пиши по-русски.",
    )

    assert not isinstance(result, AIFailure), f"Gemini вернул {result}"
    assert isinstance(result, QuizDraft)
    print(f"\n  вопрос : {result.question}")
    print(f"  ответы : {result.options}")
    print(f"  верный : {result.options[result.correct_index]}")
    print(f"  пояснен: {result.explanation}")

    # лимиты sendPoll
    assert len(result.question) <= 300
    assert 2 <= len(result.options) <= 12
    assert all(len(o) <= 100 for o in result.options)
    assert len(result.explanation) <= 200
    assert result.correct_index < len(result.options)


async def test_gemini_respects_max_length(ai_client):
    result = await ai_client.ask_structured(
        "Придумай тему для квиза о типографике.", TopicDraft
    )
    assert not isinstance(result, AIFailure)
    print(f"\n  тема: {result.topic}")
    assert len(result.topic) <= 255


async def test_serper_returns_results(settings):
    import httpx

    from main.data.clients_impl.web_search.serper_web_search_client import (
        SerperWebSearchClient,
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as http:
        client = SerperWebSearchClient(api_key=settings.SERPER_API_KEY, http_client=http)
        results = await client.search("typography scale tool", limit=3)

    assert results, "Serper вернул пустой список"
    for r in results:
        print(f"\n  {r.title}\n  {r.url}\n  {r.snippet[:70]}")
        assert r.url.startswith("http")
