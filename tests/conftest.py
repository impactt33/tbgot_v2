from datetime import UTC, datetime

import pytest

from main.domain.entities import (
    PostCreateEntity,
    PostEntity,
    QuizTopicAddEntity,
    QuizTopicEntity,
)
from main.domain.enums import PostStatus


class FakeQuizTopicService:
    """Тема считается новой, если её ещё нет в _topics."""

    def __init__(self, existing: list[str] | None = None) -> None:
        self._topics: list[str] = list(existing or [])
        self._next_id = 1
        self.marked: list[tuple[int, int]] = []

    async def get_topic_names(self, channel_id: int) -> list[str]:
        return list(self._topics)

    async def add_topic(self, data: QuizTopicAddEntity) -> QuizTopicEntity | None:
        if data.topic in self._topics:
            return None
        self._topics.append(data.topic)
        entity = QuizTopicEntity(
            id=self._next_id,
            channel_id=data.channel_id,
            topic=data.topic,
            created_at=datetime.now(UTC),
            used_in_post=None,
        )
        self._next_id += 1
        return entity

    async def find_unused(self, channel_id: int, limit: int = 10) -> list[QuizTopicEntity]:
        return []

    async def mark_used(self, topic_id: int, post_id: int) -> QuizTopicEntity:
        self.marked.append((topic_id, post_id))
        return QuizTopicEntity(
            id=topic_id, channel_id=1, topic="x",
            created_at=datetime.now(UTC), used_in_post=post_id,
        )


class FakePostService:
    def __init__(self) -> None:
        self.drafts: list[PostCreateEntity] = []

    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        self.drafts.append(data)
        return PostEntity(
            id=len(self.drafts),
            channel_id=data.channel_id,
            post_type=data.post_type,
            status=PostStatus.DRAFT,
            payload=data.payload,
            telegram_message_id=None,
            created_at=datetime.now(UTC),
            scheduled_at=None,
            published_at=None
        )

    async def find_by_id(self, post_id): ...
    async def get_by_id(self, post_id): ...
    async def mark_published(self, post_id, telegram_message_id): ...
    async def mark_failed(self, post_id): ...


class FakeAIClient:
    """Отдаёт заранее заготовленные ответы по очереди."""

    def __init__(self, answers: list) -> None:
        self._answers = list(answers)
        self.calls: list[tuple[str, str]] = []

    async def ask_structured(self, prompt, schema, *, system=None):
        self.calls.append((schema.__name__, prompt))
        return self._answers.pop(0)

    async def ask_text(self, prompt, *, system=None): ...
    async def ask_image(self, prompt, images, *, mime_type="image/jpeg"): ...


class FakeWebSearch:
    def __init__(self, results) -> None:
        self._results = results
        self.queries: list[str] = []

    async def search(self, query: str, *, limit: int = 5):
        self.queries.append(query)
        return self._results


@pytest.fixture
def quiz_topics() -> FakeQuizTopicService:
    return FakeQuizTopicService()


@pytest.fixture
def posts() -> FakePostService:
    return FakePostService()
