from abc import ABC, abstractmethod

from main.domain.entities import QuizTopicAddEntity, QuizTopicEntity


class QuizTopicRepo(ABC):
    @abstractmethod
    async def get_topic_names(self, channel_id: int) -> list[str]:
        """Only topic texts, for generating new."""

    @abstractmethod
    async def find_unused(self, channel_id: int, limit: int = 10) -> list[QuizTopicEntity]:
        ...

    @abstractmethod
    async def add_topic(self, data: QuizTopicAddEntity) -> QuizTopicEntity | None:
        """None, if already exists."""

    @abstractmethod
    async def mark_used(self, topic_id: int, post_id: int) -> QuizTopicEntity | None:
        ...