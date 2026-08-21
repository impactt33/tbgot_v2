import pytest

from main.domain.enums import AIFailure, PostType
from main.domain.errors import (
    AIClientUnavailable,
    CannotGenerateTopicError,
    InvalidQuizDraftError,
)
from main.domain.use_cases.generate_quiz import (
    GenerateQuizRequest,
    GenerateQuizUseCase,
    QuizDraft,
    TopicDraft,
)

from tests.conftest import FakeAIClient, FakePostService, FakeQuizTopicService

pytestmark = pytest.mark.asyncio

GOOD_QUIZ = QuizDraft(
    question="Что описывает правило внутреннего и внешнего?",
    options=["Соотношение отступов", "Выбор шрифта", "Сетку колонок", "Контраст цвета"],
    correct_index=0,
    explanation="Внутренние отступы должны быть меньше внешних.",
)


async def test_happy_path(quiz_topics, posts):
    ai = FakeAIClient([TopicDraft(topic="Правило внутреннего и внешнего"), GOOD_QUIZ])
    use_case = GenerateQuizUseCase(ai, quiz_topics, posts)

    post = await use_case(GenerateQuizRequest(channel_id=-100123))

    assert post.post_type is PostType.QUIZ
    assert post.payload["question"] == GOOD_QUIZ.question
    assert post.payload["correct_index"] == 0
    assert post.payload["topic_id"] == 1
    assert quiz_topics.marked == [(1, 1)]          # тема привязана к посту
    assert [c[0] for c in ai.calls] == ["TopicDraft", "QuizDraft"]


async def test_used_topics_go_into_prompt(posts):
    topics = FakeQuizTopicService(existing=["Сетки", "Кернинг"])
    ai = FakeAIClient([TopicDraft(topic="Новая тема"), GOOD_QUIZ])

    await GenerateQuizUseCase(ai, topics, posts)(GenerateQuizRequest(channel_id=1))

    topic_prompt = ai.calls[0][1]
    assert "- Сетки" in topic_prompt
    assert "- Кернинг" in topic_prompt


async def test_retries_when_topic_is_duplicate(posts):
    topics = FakeQuizTopicService(existing=["Дубль"])
    ai = FakeAIClient([
        TopicDraft(topic="Дубль"),        # 1-я попытка — уже была
        TopicDraft(topic="Свежая тема"),  # 2-я — прошла
        GOOD_QUIZ,
    ])

    post = await GenerateQuizUseCase(ai, topics, posts)(GenerateQuizRequest(channel_id=1))

    assert post.payload["topic_id"] == 1
    assert [c[0] for c in ai.calls] == ["TopicDraft", "TopicDraft", "QuizDraft"]


async def test_gives_up_after_three_duplicates(posts):
    topics = FakeQuizTopicService(existing=["Дубль"])
    ai = FakeAIClient([TopicDraft(topic="Дубль")] * 3)

    with pytest.raises(CannotGenerateTopicError):
        await GenerateQuizUseCase(ai, topics, posts)(GenerateQuizRequest(channel_id=1))

    assert posts.drafts == []          # черновик не создан


async def test_ai_failure_becomes_domain_error(quiz_topics, posts):
    ai = FakeAIClient([AIFailure.UNAVAILABLE])

    with pytest.raises(AIClientUnavailable) as exc:
        await GenerateQuizUseCase(ai, quiz_topics, posts)(GenerateQuizRequest(channel_id=1))

    assert exc.value.user_message == AIClientUnavailable.user_message


@pytest.mark.parametrize(
    ("bad", "why"),
    [
        (QuizDraft(question="q", options=["a", "a", "b"], correct_index=0, explanation="e"), "дубли"),
        (QuizDraft(question="q", options=["a", "  "], correct_index=0, explanation="e"), "пустой вариант"),
        (QuizDraft(question="q", options=["a", "b"], correct_index=3, explanation="e"), "индекс вне диапазона"),
    ],
)
async def test_invalid_draft_rejected(quiz_topics, posts, bad, why):
    ai = FakeAIClient([TopicDraft(topic="Тема"), bad])

    with pytest.raises(InvalidQuizDraftError):
        await GenerateQuizUseCase(ai, quiz_topics, posts)(GenerateQuizRequest(channel_id=1))

    assert posts.drafts == [], f"черновик не должен создаваться: {why}"
