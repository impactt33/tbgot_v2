from sqlalchemy import update, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import Post
from main.domain.entities import PostEntity, PostCreateEntity
from main.domain.enums import PostStatus
from main.domain.repositories.post_repo import PostRepo


class PostRepoImpl(PostRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_draft(self, data: PostCreateEntity) -> PostEntity | None:
        query = (
            insert(Post)
            .values(
                channel_id=data.channel_id,
                post_type=data.post_type,
                payload=data.payload
            )
            .on_conflict_do_nothing(index_elements=["channel_id"])
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None # если пост не был добавлен, то это ощибка БД, она поймается до этого момента?

    async def find_by_id(self, post_id: int) -> PostEntity | None:
        result = await self.session.scalar(
            select(Post).where(Post.id == post_id)
        )
        return result

    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity | None:
        query = (
            update(Post.status)
            .where(Post.id == post_id)
            .values(
                status=PostStatus.PUBLISHED,
                telegram_message_id=telegram_message_id,
                published_at=func.now()
            )
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None

    async def mark_failed(self, post_id: int) -> PostEntity | None:
        query = (
            update(Post.status)
            .where(Post.id == post_id)
            .values(
                status=PostStatus.FAILED,
                published_at=func.now()
            )
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None