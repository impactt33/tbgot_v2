from datetime import datetime

from sqlalchemy import update, func, select, delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from main.data.models import Post
from main.domain.entities import PostEntity, PostCreateEntity
from main.domain.enums import PostStatus
from main.domain.repositories.post_repo import PostRepo


class PostRepoImpl(PostRepo):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_draft(self, data: PostCreateEntity) -> PostEntity:
        query = (
            insert(Post)
            .values(
                channel_id=data.channel_id,
                post_type=data.post_type,
                payload=data.payload
            )
            .returning(Post)
        )
        post: Post = await self.session.scalar(query) # type: ignore
        await self.session.commit()
        return post.to_entity()

    async def find_by_id(self, post_id: int) -> PostEntity | None:
        result: Post | None = await self.session.scalar(
            select(Post)
            .where(Post.id == post_id)
        )
        return result.to_entity() if result is not None else None

    async def mark_published(self, post_id: int, telegram_message_id: int) -> PostEntity | None:
        query = (
            update(Post)
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
            update(Post)
            .where(Post.id == post_id)
            .values(
                status=PostStatus.FAILED
            )
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None

    async def claim_scheduled(self, limit: int = 10) -> list[PostEntity]:
        subquery = (
            select(Post.id)
            .where(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= func.now())
            .order_by(Post.scheduled_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .scalar_subquery()
        )
        query = (
            update(Post)
            .where(Post.id.in_(subquery))
            .values(status=PostStatus.PUBLISHING)
            .returning(Post)
        )
        posts = (await self.session.scalars(query)).all()
        await self.session.commit()
        return [post.to_entity() for post in posts]

    async def schedule(self, post_id: int, when: datetime) -> PostEntity | None:
        query = (
            update(Post)
            .where(
                Post.id == post_id,
                Post.status.in_((PostStatus.DRAFT, PostStatus.SCHEDULED))
            )
            .values(status=PostStatus.SCHEDULED, scheduled_at=when)
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None

    async def find_scheduled(self, channel_id: int | None = None, limit: int = 20) -> list[PostEntity]:
        query = (
            select(Post)
            .where(Post.status == PostStatus.SCHEDULED)
            .order_by(Post.scheduled_at)
            .limit(limit)
        )

        if channel_id is not None:
            query = query.where(Post.channel_id == channel_id)

        posts = (await self.session.scalars(query)).all()

        return [post.to_entity() for post in posts]

    async def unschedule(self, post_id: int) -> PostEntity | None:
        query = (
            update(Post)
            .where(Post.id == post_id, Post.status == PostStatus.SCHEDULED)
            .values(status=PostStatus.DRAFT, scheduled_at=None)
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None

    async def delete_draft(self, post_id: int) -> PostEntity | None:
        query = (
            delete(Post)
            .where(
                Post.id == post_id,
                Post.status.in_((PostStatus.DRAFT, PostStatus.SCHEDULED)),
            )
            .returning(Post)
        )
        post: Post | None = await self.session.scalar(query)
        await self.session.commit()
        return post.to_entity() if post is not None else None