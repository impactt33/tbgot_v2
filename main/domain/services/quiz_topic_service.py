from abc import ABC, abstractmethod

from main.domain.entities import QuizTopicAddEntity, QuizTopicEntity


class QuizTopicService(ABC):
    @abstractmethod
    async def get_topic_names(self, channel_id: int) -> list[str]:
        ...

    @abstractmethod
    async def find_unused(self, channel_id: int, limit: int = 10) -> list[QuizTopicEntity]:
        ...

    @abstractmethod
    async def add_topic(self, data: QuizTopicAddEntity) -> QuizTopicEntity | None:
        ...

    @abstractmethod
    async def mark_used(self, topic_id: int, post_id: int) -> QuizTopicEntity:
        ...

    @abstractmethod
    async def delete_unused(self, topic_id: int) -> QuizTopicEntity | None:
        """None doesn`t raise an error because it`s okay if topic wasn`t delete. Check repo description."""
