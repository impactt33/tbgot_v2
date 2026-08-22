from main.domain.entities import QuizTopicEntity, QuizTopicAddEntity
from main.domain.errors import QuizTopicNotFoundError
from main.domain.repositories import QuizTopicRepo
from main.domain.services.quiz_topic_service import QuizTopicService


class QuizTopicServiceImpl(QuizTopicService):
    def __init__(self, quiz_topic_repo: QuizTopicRepo):
        self.quiz_topic_repo = quiz_topic_repo

    async def get_topic_names(self, channel_id: int) -> list[str]:
        return await self.quiz_topic_repo.get_topic_names(channel_id)

    async def find_unused(self, channel_id: int, limit: int = 10) -> list[QuizTopicEntity]:
        return await self.quiz_topic_repo.find_unused(channel_id, limit)

    async def add_topic(self, data: QuizTopicAddEntity) -> QuizTopicEntity | None:
        return await self.quiz_topic_repo.add_topic(data)

    async def mark_used(self, topic_id: int, post_id: int) -> QuizTopicEntity:
        topic = await self.quiz_topic_repo.mark_used(topic_id, post_id)
        if topic is None:
            raise QuizTopicNotFoundError(topic_id)
        return topic

    async def delete_unused(self, topic_id: int) -> QuizTopicEntity | None:
        return await self.quiz_topic_repo.delete_unused(topic_id)