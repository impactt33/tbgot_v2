from sqlalchemy import select, update, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import QuizTopic
from main.domain.entities import QuizTopicEntity, QuizTopicAddEntity
from main.domain.repositories import QuizTopicRepo


class QuizTopicRepoImpl(QuizTopicRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_topic_names(self, channel_id: int) -> list[str]:
        result = await self.session.scalars(
            select(QuizTopic.topic).where(QuizTopic.channel_id == channel_id)
        )
        return list(result.all())

    async def find_unused(self, channel_id: int, limit: int = 10) -> list[QuizTopicEntity]:
        result = await self.session.scalars(
            select(QuizTopic)
            .where(
                QuizTopic.channel_id == channel_id,
                QuizTopic.used_in_post.is_(None)
            )
            .order_by(QuizTopic.created_at)
            .limit(limit)
        )
        return [topic.to_entity() for topic in result.all()]

    async def add_topic(self, data: QuizTopicAddEntity) -> QuizTopicEntity | None:
        query = (
            insert(QuizTopic)
            .values(channel_id=data.channel_id, topic=data.topic)
            .on_conflict_do_nothing(index_elements=["channel_id", "topic"])
            .returning(QuizTopic)
        )
        topic: QuizTopic | None = await self.session.scalar(query)
        await self.session.commit()
        return topic.to_entity() if topic is not None else None

    async def mark_used(self, topic_id: int, post_id: int) -> QuizTopicEntity | None:
        query = (
            update(QuizTopic)
            .where(QuizTopic.id == topic_id)
            .values(used_in_post=post_id)
            .returning(QuizTopic)
        )
        topic: QuizTopic | None = await self.session.scalar(query)
        await self.session.commit()
        return topic.to_entity() if topic is not None else None

    async def delete_unused(self, topic_id: int) -> QuizTopicEntity | None:
        query = (
            delete(QuizTopic)
            .where(
                QuizTopic.id == topic_id,
                QuizTopic.used_in_post.is_(None)
            )
            .returning(QuizTopic)
        )
        topic: QuizTopic | None = await self.session.scalar(query)
        await self.session.commit()
        return topic.to_entity() if topic is not None else None